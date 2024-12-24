from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional, Set
import asyncio
import httpx
import time
import random
from datetime import datetime
import dns.resolver
import dns.zone
import dns.update
import dns.query
from dataclasses import dataclass
import logging
import socket

app = FastAPI(title="JARVIS Network Control System")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ServiceInstance(BaseModel):
    server: str
    instance_id: int
    host: str = "localhost"
    port: int
    last_heartbeat: float = time.time()
    status: str = "healthy"
    metadata: Dict = {}
    performance_metrics: Dict = {
        "cpu": 0,
        "memory": 0,
        "network": 0,
        "requests_per_second": 0
    }
    security_status: str = "secure"
    power_level: float = 100.0  # Iron Man style power level

class ServiceRegistration(BaseModel):
    server: str
    instance_id: int
    port: int
    metadata: Optional[Dict] = {}

class ServiceDiscovery(BaseModel):
    service_type: str
    requirements: Optional[Dict] = {}

class SecurityThreat(BaseModel):
    threat_level: str
    description: str
    timestamp: datetime
    affected_services: List[str]

class NetworkDefense:
    """Iron Man style network defense system"""
    def __init__(self):
        self.threat_levels = ["low", "moderate", "high", "critical"]
        self.active_threats: List[SecurityThreat] = []
        self.blocked_ips: Set[str] = set()
        self.defense_protocols = {
            "lockdown": False,
            "enhanced_monitoring": False,
            "auto_recovery": True
        }
        
    def assess_threat(self, instance: ServiceInstance) -> Optional[SecurityThreat]:
        """Assess security threats for a service instance"""
        # Simulate threat detection
        if random.random() < 0.05:  # 5% chance of detecting a threat
            threat = SecurityThreat(
                threat_level=random.choice(self.threat_levels),
                description="Anomalous behavior detected",
                timestamp=datetime.now(),
                affected_services=[instance.server]
            )
            self.active_threats.append(threat)
            return threat
        return None

class PowerManagement:
    """Iron Man style power management system"""
    def __init__(self):
        self.total_power = 100.0
        self.power_distribution: Dict[str, float] = {}
        self.critical_services = ["main", "llm", "functional"]
        
    def allocate_power(self, services: Dict[str, List[ServiceInstance]]):
        """Allocate power to services"""
        total_instances = sum(len(instances) for instances in services.values())
        power_per_instance = self.total_power / total_instances if total_instances > 0 else 0
        
        self.power_distribution.clear()
        for service_type, instances in services.items():
            # Critical services get 50% more power
            multiplier = 1.5 if service_type in self.critical_services else 1.0
            self.power_distribution[service_type] = len(instances) * power_per_instance * multiplier
            
            # Update instance power levels
            for instance in instances:
                instance.power_level = power_per_instance * multiplier

class DNSServer:
    def __init__(self):
        self.services: Dict[str, List[ServiceInstance]] = {}
        self.health_check_interval = 10
        self.defense_system = NetworkDefense()
        self.power_management = PowerManagement()
        self.status = {
            "operational_status": "fully_operational",
            "security_level": "standard",
            "power_status": "optimal",
            "active_threats": 0
        }
        self._tasks = []

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()

    async def start(self):
        """Initialize async tasks"""
        self._tasks = [
            asyncio.create_task(self.health_check_loop()),
            asyncio.create_task(self.power_management_loop())
        ]
        return self

    async def cleanup(self):
        """Cleanup async resources"""
        for task in self._tasks:
            if not task.done():
                task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

    async def register_service(self, registration: ServiceRegistration) -> ServiceInstance:
        """Register a new service instance"""
        instance = ServiceInstance(
            server=registration.server,
            instance_id=registration.instance_id,
            port=registration.port,
            metadata=registration.metadata
        )
        
        if registration.server not in self.services:
            self.services[registration.server] = []
            
        # Update existing instance or add new one
        for i, existing in enumerate(self.services[registration.server]):
            if existing.instance_id == instance.instance_id:
                self.services[registration.server][i] = instance
                return instance
                
        self.services[registration.server].append(instance)
        
        # Reallocate power after adding new instance
        self.power_management.allocate_power(self.services)
        return instance

    async def get_service(self, service_type: str, requirements: Optional[Dict] = None) -> ServiceInstance:
        """Get best available service instance based on requirements"""
        if service_type not in self.services or not self.services[service_type]:
            raise HTTPException(status_code=404, detail=f"No {service_type} service available")
            
        # Filter healthy instances
        healthy_instances = [
            instance for instance in self.services[service_type]
            if instance.status == "healthy" and 
            time.time() - instance.last_heartbeat < 30 and
            instance.power_level > 20.0  # Require minimum power level
        ]
        
        if not healthy_instances:
            raise HTTPException(status_code=503, detail=f"No healthy {service_type} service available")
            
        # If requirements specified, filter based on them
        if requirements:
            matching_instances = [
                instance for instance in healthy_instances
                if all(
                    instance.metadata.get(key) == value 
                    for key, value in requirements.items()
                )
            ]
            if matching_instances:
                healthy_instances = matching_instances
        
        # Return instance with best combination of recent heartbeat and power level
        return max(
            healthy_instances,
            key=lambda x: (x.power_level * 0.7 + (1.0 / (time.time() - x.last_heartbeat + 0.0001)) * 0.3)
        )

    async def update_heartbeat(self, service_type: str, instance_id: int, metrics: Optional[Dict] = None) -> bool:
        """Update service instance heartbeat and metrics"""
        if service_type in self.services:
            for instance in self.services[service_type]:
                if instance.instance_id == instance_id:
                    instance.last_heartbeat = time.time()
                    instance.status = "healthy"
                    if metrics:
                        instance.performance_metrics.update(metrics)
                    return True
        return False

    async def health_check_loop(self):
        """Continuous health check loop"""
        while True:
            try:
                current_time = time.time()
                threats_detected = 0
                
                for service_type, instances in self.services.items():
                    for instance in instances:
                        # Check heartbeat
                        if current_time - instance.last_heartbeat > 30:
                            instance.status = "unhealthy"
                            instance.power_level *= 0.8  # Reduce power for unhealthy instances
                            
                        # Security check
                        if threat := self.defense_system.assess_threat(instance):
                            threats_detected += 1
                            if threat.threat_level in ["high", "critical"]:
                                instance.security_status = "compromised"
                                
                        # Try to recover unhealthy instances
                        if instance.status == "unhealthy":
                            try:
                                async with httpx.AsyncClient() as client:
                                    response = await client.get(
                                        f"http://{instance.host}:{instance.port}/health",
                                        timeout=5.0
                                    )
                                    if response.status_code == 200:
                                        instance.status = "healthy"
                                        instance.last_heartbeat = current_time
                                        instance.power_level = min(100.0, instance.power_level * 1.2)
                            except:
                                pass
                
                # Update system status
                self.status.update({
                    "operational_status": "degraded" if threats_detected > 0 else "fully_operational",
                    "security_level": "enhanced" if threats_detected > 0 else "standard",
                    "active_threats": threats_detected
                })
                
            except Exception as e:
                logging.error(f"Health check error: {str(e)}")
                
            await asyncio.sleep(self.health_check_interval)

    async def power_management_loop(self):
        """Manage power distribution across services"""
        while True:
            try:
                # Update power allocation
                self.power_management.allocate_power(self.services)
                
                # Update system power status
                total_power = sum(self.power_management.power_distribution.values())
                self.status["power_status"] = (
                    "critical" if total_power < 30 else
                    "low" if total_power < 50 else
                    "optimal"
                )
                
            except Exception as e:
                logging.error(f"Power management error: {str(e)}")
                
            await asyncio.sleep(5)

# Replace the global dns_server instance with a dependency
async def get_dns_server():
    """Dependency to get DNS server instance"""
    if not hasattr(get_dns_server, 'instance'):
        get_dns_server.instance = DNSServer()
        await get_dns_server.instance.start()
    return get_dns_server.instance

@app.post("/register")
async def register_service(
    registration: ServiceRegistration,
    dns_server: DNSServer = Depends(get_dns_server)
):
    """Register a new service instance"""
    instance = await dns_server.register_service(registration)
    return {
        "status": "registered",
        "instance": instance,
        "power_level": instance.power_level,
        "security_status": instance.security_status
    }

@app.get("/service/{service_type}")
async def get_service(
    service_type: str,
    requirements: Optional[Dict] = None,
    dns_server: DNSServer = Depends(get_dns_server)
):
    """Get available service instance"""
    instance = await dns_server.get_service(service_type, requirements)
    return {
        "url": f"http://{instance.host}:{instance.port}",
        "instance_id": instance.instance_id,
        "metadata": instance.metadata,
        "power_level": instance.power_level,
        "security_status": instance.security_status
    }

@app.post("/heartbeat/{service_type}/{instance_id}")
async def update_heartbeat(
    service_type: str,
    instance_id: int,
    metrics: Optional[Dict] = None,
    dns_server: DNSServer = Depends(get_dns_server)
):
    """Update service heartbeat and metrics"""
    success = await dns_server.update_heartbeat(service_type, instance_id, metrics)
    if not success:
        raise HTTPException(status_code=404, detail="Service instance not found")
    return {"status": "updated"}

@app.get("/status")
async def get_status(dns_server: DNSServer = Depends(get_dns_server)):
    """Get comprehensive system status"""
    return {
        "timestamp": datetime.now().isoformat(),
        "system_status": dns_server.status,
        "services": {
            service_type: [
                {
                    "id": instance.instance_id,
                    "status": instance.status,
                    "power_level": instance.power_level,
                    "security_status": instance.security_status,
                    "metrics": instance.performance_metrics
                }
                for instance in instances
            ]
            for service_type, instances in dns_server.services.items()
        },
        "power_distribution": dns_server.power_management.power_distribution,
        "active_threats": [
            {
                "level": threat.threat_level,
                "description": threat.description,
                "affected_services": threat.affected_services,
                "detected_at": threat.timestamp.isoformat()
            }
            for threat in dns_server.defense_system.active_threats
        ],
        "defense_protocols": dns_server.defense_system.defense_protocols
    }

@app.get("/servers/status")
async def get_servers_status(dns_server: DNSServer = Depends(get_dns_server)):
    """Get status of all registered servers and their instances"""
    result = {}
    current_time = time.time()
    
    for service_type, instances in dns_server.services.items():
        result[service_type] = {
            "total_instances": len(instances),
            "healthy_instances": sum(1 for i in instances if i.status == "healthy"),
            "instances": [
                {
                    "instance_id": instance.instance_id,
                    "host": instance.host,
                    "port": instance.port,
                    "status": instance.status,
                    "last_heartbeat_age": round(current_time - instance.last_heartbeat, 2),
                    "power_level": round(instance.power_level, 2),
                    "security_status": instance.security_status,
                    "performance_metrics": instance.performance_metrics,
                    "metadata": instance.metadata
                }
                for instance in instances
            ]
        }
    
    return {
        "timestamp": datetime.now().isoformat(),
        "total_services": len(dns_server.services),
        "services": result
    }

@app.post("/defense/activate/{protocol}")
async def activate_defense_protocol(protocol: str, dns_server: DNSServer = Depends(get_dns_server)):
    """Activate a defense protocol"""
    if protocol not in dns_server.defense_system.defense_protocols:
        raise HTTPException(status_code=404, detail="Protocol not found")
        
    dns_server.defense_system.defense_protocols[protocol] = True
    return {
        "status": "activated",
        "protocol": protocol,
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    print("Initializing JARVIS Network Control System...")
    uvicorn.run(app, host="0.0.0.0", port=9000)