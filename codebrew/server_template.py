from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio
import os
import time
from dns_server.dns_client import DNSClient, ServiceConfig

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