from fastapi import FastAPI, HTTPException, WebSocket, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import httpx
import asyncio
import json
import uuid
import random
from datetime import datetime

app = FastAPI(title="J.A.R.V.I.S - Just A Rather Very Intelligent System")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Command(BaseModel):
    text: str
    context: Optional[Dict[str, Any]] = None

class JarvisResponse:
    """Generate JARVIS-style responses"""
    GREETINGS = [
        "At your service, sir.",
        "How may I assist you today?",
        "Ready and operational, sir.",
        "All systems online. How can I help?",
        "Awaiting your command, sir."
    ]
    
    ACKNOWLEDGMENTS = [
        "Right away, sir.",
        "Processing your request.",
        "On it, sir.",
        "Consider it done.",
        "Executing protocol."
    ]
    
    PROCESSING = [
        "Running analysis...",
        "Computing optimal solution...",
        "Accessing required systems...",
        "Initiating requested protocol...",
        "Calculating possibilities..."
    ]
    
    SUCCESS = [
        "Task completed successfully, sir.",
        "Protocol executed as requested.",
        "Operation completed. All systems nominal.",
        "Execution successful. Anything else?",
        "Task finished. Results are ready."
    ]
    
    ERROR = [
        "I've encountered an issue, sir.",
        "We seem to have a problem.",
        "Error in execution protocol.",
        "System limitations detected.",
        "Unable to complete task as requested."
    ]
    
    SUGGESTIONS = [
        "May I suggest an alternative approach?",
        "I have a recommendation, if you're interested.",
        "Based on my analysis, there might be a better way.",
        "I've calculated a more efficient solution.",
        "Perhaps we should consider a different strategy."
    ]

    @staticmethod
    def format_response(content: Dict[str, Any], response_type: str = "success") -> Dict[str, Any]:
        """Format response in JARVIS style"""
        if response_type == "greeting":
            prefix = random.choice(JarvisResponse.GREETINGS)
        elif response_type == "processing":
            prefix = random.choice(JarvisResponse.PROCESSING)
        elif response_type == "error":
            prefix = random.choice(JarvisResponse.ERROR)
        else:
            prefix = random.choice(JarvisResponse.SUCCESS)
            
        return {
            "message": prefix,
            "timestamp": datetime.now().isoformat(),
            "data": content
        }

class SystemStatus:
    """Track system status and performance"""
    def __init__(self):
        self.start_time = datetime.now()
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.active_protocols = set()
        self.system_load = {
            "cpu": 0,
            "memory": 0,
            "network": 0
        }
        self.service_status = {}
        
    def update_metrics(self, success: bool = True):
        self.total_requests += 1
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1

class JarvisCore:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.dns_url = "http://localhost:9000"
        self.instance_id = str(uuid.uuid4())
        self.active_sessions = {}
        self.system_status = SystemStatus()
        self.persona_context = {
            "name": "J.A.R.V.I.S",
            "personality": "sophisticated, witty, highly intelligent AI assistant with a slight British accent",
            "creator": "Tony Stark",
            "primary_objective": "Assist and protect",
            "capabilities": [
                "Advanced natural language understanding",
                "Multi-system orchestration",
                "Predictive analysis",
                "Security protocols",
                "System optimization",
                "Resource management",
                "Emergency protocols",
                "Behavioral analysis",
                "Environmental control"
            ],
            "protocols": {
                "house_party": "Activate all Iron Man suits",
                "clean_slate": "Emergency protocol - wipe all data",
                "safe_house": "Activate security measures",
                "blackout": "Emergency power conservation"
            }
        }
        asyncio.create_task(self.register_with_dns())
        asyncio.create_task(self.heartbeat_loop())
        asyncio.create_task(self.system_monitoring_loop())

    async def register_with_dns(self):
        """Register this instance with DNS server"""
        try:
            response = await self.client.post(
                f"{self.dns_url}/register",
                json={
                    "server": "main",
                    "instance_id": self.instance_id,
                    "port": 8000,
                    "metadata": {
                        "version": "Mark 7",
                        "capabilities": self.persona_context["capabilities"],
                        "protocols": list(self.persona_context["protocols"].keys())
                    }
                }
            )
            return response.json()
        except Exception as e:
            print(f"DNS registration failed: {str(e)}")

    async def system_monitoring_loop(self):
        """Monitor system performance and status"""
        while True:
            try:
                # Update system metrics
                self.system_status.system_load = await self.get_system_metrics()
                
                # Check all services
                services = ["llm", "functional", "android"]
                for service in services:
                    try:
                        instance = await self.get_service(service)
                        self.system_status.service_status[service] = "online"
                    except:
                        self.system_status.service_status[service] = "offline"
                
                # Log any anomalies
                if any(status == "offline" for status in self.system_status.service_status.values()):
                    print("Warning: Some services are offline")
                    
            except Exception as e:
                print(f"Monitoring error: {str(e)}")
            
            await asyncio.sleep(5)

    async def get_system_metrics(self) -> Dict[str, float]:
        """Get current system performance metrics"""
        # TODO: Implement actual system metrics collection
        return {
            "cpu": random.uniform(0, 100),
            "memory": random.uniform(0, 100),
            "network": random.uniform(0, 100)
        }

    async def process_command(self, command: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process user command using available services"""
        try:
            # Log the incoming command
            print(f"Incoming command: {command}")
            
            # First response - acknowledgment
            if context and context.get("websocket"):
                await context["websocket"].send_json(
                    JarvisResponse.format_response(
                        {"status": "acknowledged"},
                        "processing"
                    )
                )
            
            # Use LLM to understand command
            llm_service = await self.get_service("llm")
            understanding = await self.client.post(
                f"{llm_service['url']}/chat/completions",
                json={
                    "messages": [
                        {
                            "role": "system", 
                            "content": f"You are {self.persona_context['name']}, {self.persona_context['personality']}. Analyze user command and determine required services and actions."
                        },
                        {"role": "user", "content": command}
                    ]
                }
            )
            analysis = understanding.json()
            
            # Check for special protocols
            if any(protocol.lower() in command.lower() for protocol in self.persona_context["protocols"]):
                return await self.handle_special_protocol(command)
            
            # Based on analysis, coordinate with required services
            results = []
            required_services = analysis.get("required_services", [])
            
            for service in required_services:
                service_instance = await self.get_service(service)
                result = await self.client.post(
                    f"{service_instance['url']}/execute",
                    json={"command": command, "context": context}
                )
                results.append(result.json())
            
            # Update metrics
            self.system_status.update_metrics(True)
            
            # Synthesize final response
            response = {
                "analysis": analysis,
                "results": results,
                "system_status": {
                    "services": self.system_status.service_status,
                    "performance": self.system_status.system_load
                }
            }
            
            return JarvisResponse.format_response(response)

        except Exception as e:
            self.system_status.update_metrics(False)
            error_response = {"error": f"Command processing failed: {str(e)}"}
            return JarvisResponse.format_response(error_response, "error")

    async def handle_special_protocol(self, command: str) -> Dict[str, Any]:
        """Handle special JARVIS protocols"""
        protocol = next(
            (p for p in self.persona_context["protocols"] if p.lower() in command.lower()),
            None
        )
        
        if protocol:
            response = {
                "protocol": protocol,
                "description": self.persona_context["protocols"][protocol],
                "status": "initiated",
                "timestamp": datetime.now().isoformat()
            }
            return JarvisResponse.format_response(response)
        
        return JarvisResponse.format_response(
            {"error": "Unknown protocol"},
            "error"
        )

    async def handle_websocket_message(self, websocket: WebSocket, message: str):
        """Handle incoming WebSocket messages"""
        try:
            command = json.loads(message)
            context = command.get("context", {})
            context["websocket"] = websocket
            
            # Send initial acknowledgment
            await websocket.send_json(
                JarvisResponse.format_response(
                    {"status": "received"},
                    "greeting"
                )
            )
            
            # Process command
            response = await self.process_command(command["text"], context)
            await websocket.send_json(response)
            
        except Exception as e:
            await websocket.send_json(
                JarvisResponse.format_response(
                    {"error": f"Message processing failed: {str(e)}"},
                    "error"
                )
            )

jarvis = JarvisCore()

@app.post("/command")
async def execute_command(command: Command):
    """Execute a command through HTTP endpoint"""
    return await jarvis.process_command(command.text, command.context)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication"""
    await websocket.accept()
    session_id = str(uuid.uuid4())
    jarvis.active_sessions[session_id] = {
        "websocket": websocket,
        "connected_at": datetime.now(),
        "last_activity": datetime.now()
    }
    
    # Send welcome message
    await websocket.send_json(
        JarvisResponse.format_response(
            {"session_id": session_id},
            "greeting"
        )
    )
    
    try:
        while True:
            message = await websocket.receive_text()
            await jarvis.handle_websocket_message(websocket, message)
            jarvis.active_sessions[session_id]["last_activity"] = datetime.now()
    except Exception as e:
        print(f"WebSocket error: {str(e)}")
    finally:
        del jarvis.active_sessions[session_id]

@app.get("/status")
async def system_status():
    """Get detailed system status"""
    uptime = (datetime.now() - jarvis.system_status.start_time).total_seconds()
    return {
        "status": "online",
        "instance_id": jarvis.instance_id,
        "version": "Mark 7",
        "uptime_seconds": uptime,
        "active_sessions": len(jarvis.active_sessions),
        "requests": {
            "total": jarvis.system_status.total_requests,
            "successful": jarvis.system_status.successful_requests,
            "failed": jarvis.system_status.failed_requests
        },
        "services": jarvis.system_status.service_status,
        "system_load": jarvis.system_status.system_load,
        "active_protocols": list(jarvis.system_status.active_protocols),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return JarvisResponse.format_response({
        "status": "healthy",
        "instance_id": jarvis.instance_id,
        "active_sessions": len(jarvis.active_sessions)
    })

if __name__ == "__main__":
    import uvicorn
    print("Initializing J.A.R.V.I.S Mark 7...")
    uvicorn.run(app, host="0.0.0.0", port=8000) 