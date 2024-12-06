from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
import uvicorn
from dotenv import load_dotenv
import os
import logging
from collections import deque
from dns_server import JarvisDNSServer, ServiceRecord

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Service Monitor")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enhanced instance status model
class InstanceStatus(BaseModel):
    server: str
    instance_id: int
    status: str
    port: Optional[int]
    busy: Optional[bool] = False
    last_ping: datetime
    registered_at: datetime
    metadata: Dict = {}
    tags: Set[str] = set()
    error_count: int = 0
    last_error: Optional[str] = None

# Store instance history (last 100 status changes per instance)
history: Dict[str, Dict[int, deque]] = {}

# Store for all instances across different servers
instances: Dict[str, Dict[int, InstanceStatus]] = {}

class RegisterRequest(BaseModel):
    server: str
    instance_id: int
    port: int
    metadata: Optional[Dict] = {}
    tags: Optional[Set[str]] = set()

class StatusUpdate(BaseModel):
    server: str
    instance_id: int
    status: str
    busy: Optional[bool] = False
    error: Optional[str] = None

class ServiceRegistration(BaseModel):
    service_type: str
    ip: str
    port: int

class ServiceResponse(BaseModel):
    name: str
    ip: str
    port: int
    health: bool

dns_server = JarvisDNSServer()

@app.post("/register")
async def register_instance(request: RegisterRequest):
    try:
        if request.server not in instances:
            instances[request.server] = {}
            history[request.server] = {}
        
        instances[request.server][request.instance_id] = InstanceStatus(
            server=request.server,
            instance_id=request.instance_id,
            status="active",
            port=request.port,
            busy=False,
            last_ping=datetime.now(),
            registered_at=datetime.now(),
            metadata=request.metadata,
            tags=request.tags
        )
        
        # Initialize history
        history[request.server][request.instance_id] = deque(maxlen=100)
        logger.info(f"Registered new instance: {request.server}:{request.instance_id}")
        return {"status": "registered"}
    except Exception as e:
        logger.error(f"Error registering instance: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/status")
async def update_status(update: StatusUpdate):
    try:
        if update.server not in instances or update.instance_id not in instances[update.server]:
            raise HTTPException(status_code=404, detail="Instance not found")
        
        instance = instances[update.server][update.instance_id]
        old_status = instance.status
        
        # Update instance
        instance.status = update.status
        instance.busy = update.busy
        instance.last_ping = datetime.now()
        
        # Handle error reporting
        if update.error:
            instance.error_count += 1
            instance.last_error = update.error
        
        # Record status change in history
        if old_status != update.status:
            history[update.server][update.instance_id].append({
                "timestamp": datetime.now(),
                "old_status": old_status,
                "new_status": update.status
            })
        
        return {"status": "updated"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history/{server}/{instance_id}")
async def get_instance_history(server: str, instance_id: int):
    if (server not in history or 
        instance_id not in history[server]):
        raise HTTPException(status_code=404, detail="Instance history not found")
    
    return list(history[server][instance_id])

@app.get("/status/{server}")
async def get_server_status(server: str):
    if server not in instances:
        raise HTTPException(status_code=404, detail="Server not found")
    
    return {
        "server": server,
        "instances": instances[server]
    }

@app.get("/status")
async def get_all_status():
    return instances

@app.get("/health")
async def monitor_health():
    threshold = datetime.now() - timedelta(minutes=5)
    error_threshold = 10
    
    status_counts = {
        "active": 0,
        "dead": 0,
        "error": 0
    }
    
    for server in instances:
        for instance_id in list(instances[server].keys()):
            instance = instances[server][instance_id]
            if instance.last_ping < threshold:
                instance.status = "dead"
                status_counts["dead"] += 1
            elif instance.error_count > error_threshold:
                status_counts["error"] += 1
            elif instance.status == "active":
                status_counts["active"] += 1
    
    return {
        "total_servers": len(instances),
        "total_instances": sum(len(server_instances) for server_instances in instances.values()),
        "status_counts": status_counts,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/cleanup")
async def cleanup_dead_instances():
    threshold = datetime.now() - timedelta(minutes=30)
    cleaned = 0
    
    for server in list(instances.keys()):
        for instance_id in list(instances[server].keys()):
            if instances[server][instance_id].last_ping < threshold:
                del instances[server][instance_id]
                del history[server][instance_id]
                cleaned += 1
        
        # Clean up empty servers
        if not instances[server]:
            del instances[server]
            del history[server]
    
    return {"cleaned_instances": cleaned}

@app.post("/register")
async def register_service(service: ServiceRegistration):
    success = await dns_server.register_service(
        service.service_type,
        service.ip,
        service.port
    )
    if not success:
        raise HTTPException(status_code=400, detail="Invalid service type")
    return {"status": "registered"}

@app.get("/service/{service_type}")
async def get_service(service_type: str) -> ServiceResponse:
    service = await dns_server.get_service(service_type)
    if not service:
        raise HTTPException(
            status_code=404,
            detail=f"No healthy {service_type} services available"
        )
    return ServiceResponse(
        name=service.name,
        ip=service.ip,
        port=service.port,
        health=service.health
    )

@app.get("/status")
async def get_status() -> Dict[str, List[Dict]]:
    return dns_server.get_service_status()

@app.on_event("startup")
async def startup_event():
    await dns_server.run()

if __name__ == "__main__":
    uvicorn.run(
        app, 
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "9000"))
    ) 