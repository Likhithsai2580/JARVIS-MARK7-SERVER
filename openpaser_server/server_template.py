from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio
import os
import time
import httpx
import asyncio
from typing import Dict, Optional
import time
import os
from dataclasses import dataclass
import json

@dataclass
class ServiceConfig:
    service_type: str
    instance_id: int
    port: int
    metadata: Dict = None
    host: str = None
    busy: bool = False

class DNSClient:
    def __init__(self, dns_url: str = None, base_port: int = None):
        self.dns_url = dns_url or os.getenv("DNS_SERVER_URL", "https://jarvis-dns.netlify.app")
        self.service_config: Optional[ServiceConfig] = None
        self.heartbeat_task = None
        self.health_check_task = None
        self._client = httpx.AsyncClient(timeout=10.0)
        self.base_port = base_port or int(os.getenv("BASE_PORT", 5000))
        self.host = os.getenv("HOST", "localhost")
        self.busy = False

    async def register_service(self, config: ServiceConfig) -> bool:
        """Register the service with DNS server"""
        self.service_config = config
        self.service_config.host = self.host
        try:
            response = await self._client.post(
                f"{self.dns_url}/register",
                json={
                    "server": config.service_type,
                    "instance_id": config.instance_id,
                    "port": config.port,
                    "host": config.host,
                    "metadata": config.metadata or {}
                }
            )
            if response.status_code == 200:
                # Start monitoring tasks
                if not self.heartbeat_task:
                    self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
                if not self.health_check_task:
                    self.health_check_task = asyncio.create_task(self._health_check_loop())
                return True
            return False
        except Exception as e:
            print(f"Registration error: {str(e)}")
            return False

    async def discover_service(self, service_type: str, requirements: Dict = None) -> Dict:
        """Discover a non-busy service instance"""
        try:
            response = await self._client.post(
                f"{self.dns_url}/discover",
                json={
                    "service_type": service_type,
                    "requirements": {
                        **(requirements or {}),
                        "busy": False  # Only discover non-busy instances
                    }
                }
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Service discovery error: {str(e)}")
            return None

    async def update_status(self, busy: bool = None):
        """Update the service's busy status"""
        if busy is not None:
            self.busy = busy
        if self.service_config:
            try:
                await self._client.post(
                    f"{self.dns_url}/status",
                    json={
                        "server": self.service_config.service_type,
                        "instance_id": self.service_config.instance_id,
                        "status": "active",
                        "busy": self.busy
                    }
                )
            except Exception as e:
                print(f"Status update error: {str(e)}")

    async def _health_check_loop(self):
        """Monitor service health and busy status"""
        while True:
            try:
                # Get health status from local service
                try:
                    response = await self._client.get(
                        f"http://{self.host}:{self.service_config.port}/health",
                        timeout=5.0
                    )
                    if response.status_code == 200:
                        health_data = response.json()
                        await self.update_status(health_data.get("busy", False))
                    else:
                        await self.update_status(True)  # Mark as busy if health check fails
                except:
                    # Report instance as dead if health check fails
                    await self._client.post(
                        f"{self.dns_url}/status",
                        json={
                            "server": self.service_config.service_type,
                            "instance_id": self.service_config.instance_id,
                            "status": "dead"
                        }
                    )
                    break  # Stop health check loop if instance is dead
            except Exception as e:
                print(f"Health check error: {str(e)}")
            await asyncio.sleep(60)  # Check every minute

    async def _heartbeat_loop(self):
        """Send periodic heartbeats with status"""
        while True:
            try:
                if self.service_config:
                    await self._client.post(
                        f"{self.dns_url}/heartbeat",
                        json={
                            "service_type": self.service_config.service_type,
                            "instance_id": self.service_config.instance_id,
                            "host": self.service_config.host,
                            "port": self.service_config.port,
                            "busy": self.busy,
                            "metrics": {
                                "timestamp": time.time(),
                                "status": "active"
                            }
                        }
                    )
            except Exception as e:
                print(f"Heartbeat error: {str(e)}")
            await asyncio.sleep(10)  # Heartbeat every 10 seconds

    async def close(self):
        """Clean up resources and mark instance as dead"""
        try:
            if self.service_config:
                await self._client.post(
                    f"{self.dns_url}/status",
                    json={
                        "server": self.service_config.service_type,
                        "instance_id": self.service_config.instance_id,
                        "status": "dead"
                    }
                )
        except:
            pass

        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass

        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass

        await self._client.aclose() 

class BaseServer:
    def __init__(self, service_name: str):
        self.app = FastAPI(title=f"JARVIS {service_name} Server")
        self.service_name = service_name
        self.dns_client = None
        self.busy = False
        
        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Add health check endpoint
        @self.app.get("/health")
        async def health_check():
            return {
                "status": "active",
                "busy": self.busy,
                "timestamp": time.time()
            }
        
        # Add startup and shutdown events
        @self.app.on_event("startup")
        async def startup_event():
            await self.register_with_dns()
        
        @self.app.on_event("shutdown")
        async def shutdown_event():
            if self.dns_client:
                await self.dns_client.close()
    
    async def register_with_dns(self):
        """Register server with DNS service"""
        try:
            instance_id = int(os.getenv("INSTANCE_ID", 1))
            base_port = int(os.getenv("BASE_PORT", 5000))
            port = int(os.getenv("PORT", base_port + instance_id))
            
            self.dns_client = DNSClient(
                dns_url=os.getenv("DNS_SERVER_URL"),
                base_port=base_port
            )
            
            config = ServiceConfig(
                service_type=self.service_name,
                instance_id=instance_id,
                port=port,
                metadata={
                    "version": "1.0",
                    "start_time": time.time()
                }
            )
            
            if not await self.dns_client.register_service(config):
                raise Exception("Failed to register with DNS server")
                
        except Exception as e:
            print(f"DNS registration error: {str(e)}")
            # Continue running even if DNS registration fails
    
    def set_busy(self, busy: bool):
        """Update server's busy status"""
        self.busy = busy
        if self.dns_client:
            asyncio.create_task(self.dns_client.update_status(busy))
    
    def run(self):
        """Run the server"""
        port = int(os.getenv("PORT", 5000))
        uvicorn.run(self.app, host="0.0.0.0", port=port)

# Example usage:
"""
from server_template import BaseServer

class MyServer(BaseServer):
    def __init__(self):
        super().__init__("MyService")
        
        @self.app.post("/process")
        async def process_request(data: dict):
            self.set_busy(True)
            try:
                # Process request
                result = await self.process_data(data)
                return result
            finally:
                self.set_busy(False)
    
    async def process_data(self, data: dict):
        # Implement processing logic
        pass

if __name__ == "__main__":
    server = MyServer()
    server.run()
""" 