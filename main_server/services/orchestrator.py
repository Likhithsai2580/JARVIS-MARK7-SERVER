from typing import Dict, Any, Optional
import httpx
from ..config import settings
import asyncio
from functools import wraps
import os
from datetime import datetime

class ServiceOrchestrator:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=settings.TIMEOUT)
        self.dns_client = httpx.AsyncClient(timeout=settings.TIMEOUT)
        self.dns_url = os.getenv("DNS_SERVER_URL", "http://localhost:9000")
        self.instance_id = int(os.getenv("INSTANCE_ID", "1"))
        self.service_cache = {}
        asyncio.create_task(self.register_with_dns())
        asyncio.create_task(self.heartbeat_loop())
        
    async def register_with_dns(self):
        """Register this orchestrator instance with DNS"""
        try:
            await self.dns_client.post(
                f"{self.dns_url}/register",
                json={
                    "server": "orchestrator",
                    "instance_id": self.instance_id,
                    "port": int(os.getenv("PORT", "8000")),
                    "metadata": {
                        "version": "1.0",
                        "capabilities": ["llm", "android", "codebrew", "omniparser", "google_auth", "functional"]
                    }
                }
            )
        except Exception as e:
            print(f"DNS registration failed: {str(e)}")

    async def heartbeat_loop(self):
        """Send periodic heartbeats to DNS"""
        while True:
            try:
                await self.dns_client.post(
                    f"{self.dns_url}/heartbeat/orchestrator/{self.instance_id}",
                    json={
                        "metrics": {
                            "timestamp": datetime.now().isoformat(),
                            "status": "healthy"
                        }
                    }
                )
            except Exception as e:
                print(f"Heartbeat error: {str(e)}")
            await asyncio.sleep(10)

    async def get_service_url(self, service_type: str) -> str:
        """Get service URL from DNS with caching"""
        # Check cache first
        if service_type in self.service_cache:
            cache_entry = self.service_cache[service_type]
            if (datetime.now() - cache_entry["timestamp"]).seconds < 300:  # 5 min cache
                return cache_entry["url"]

        try:
            response = await self.dns_client.get(
                f"{self.dns_url}/service/{service_type}",
                params={"requirements": {"busy": False}}  # Only get non-busy instances
            )
            service_data = response.json()
            service_url = service_data["url"]
            
            # Update cache
            self.service_cache[service_type] = {
                "url": service_url,
                "timestamp": datetime.now()
            }
            
            return service_url
        except Exception as e:
            # Fallback to config URLs if DNS fails
            fallback_urls = {
                "llm": settings.LLM_SERVER_URL,
                "android": settings.ANDROID_BRIDGE_URL,
                "codebrew": settings.CODEBREW_SERVER_URL,
                "omniparser": settings.OMNIPARSER_URL,
                "google_auth": settings.GOOGLE_AUTH_URL,
                "functional": settings.FUNCTIONAL_SERVER_URL
            }
            return fallback_urls.get(service_type, "")

    async def execute_llm_query(self, messages: list) -> Dict[str, Any]:
        """Execute query on LLM server"""
        try:
            llm_url = await self.get_service_url("llm")
            if not llm_url:
                return {"error": "LLM service not available"}
                
            response = await self.client.post(
                f"{llm_url}/chat/completions",
                json={"messages": messages}
            )
            return response.json()
        except Exception as e:
            # Fallback to direct config URL
            try:
                response = await self.client.post(
                    f"{settings.LLM_SERVER_URL}/chat/completions",
                    json={"messages": messages}
                )
                return response.json()
            except Exception as nested_e:
                return {"error": str(nested_e)}

    async def parse_ui_elements(self, image_data: bytes) -> Dict[str, Any]:
        """Parse UI elements using OmniParser"""
        try:
            parser_url = await self.get_service_url("omniparser")
            if not parser_url:
                return {"error": "OmniParser service not available"}
                
            files = {"file": image_data}
            response = await self.client.post(
                f"{parser_url}/parse",
                files=files
            )
            return response.json()
        except Exception as e:
            # Fallback to direct config URL
            try:
                response = await self.client.post(
                    f"{settings.OMNIPARSER_URL}/parse",
                    files=files
                )
                return response.json()
            except Exception as nested_e:
                return {"error": str(nested_e)}

    async def execute_android_command(self, device_id: str, command: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute command on Android device"""
        try:
            android_url = await self.get_service_url("android")
            if not android_url:
                return {"error": "Android Bridge service not available"}
                
            response = await self.client.post(
                f"{android_url}/api/send-command",
                json={
                    "targetDevice": device_id,
                    "command": command,
                    "params": params
                }
            )
            return response.json()
        except Exception as e:
            # Fallback to direct config URL
            try:
                response = await self.client.post(
                    f"{settings.ANDROID_BRIDGE_URL}/api/send-command",
                    json={
                        "targetDevice": device_id,
                        "command": command,
                        "params": params
                    }
                )
                return response.json()
            except Exception as nested_e:
                return {"error": str(nested_e)}

    async def execute_codebrew_script(self, script: str) -> Dict[str, Any]:
        """Execute Python script using CodeBrew"""
        try:
            codebrew_url = await self.get_service_url("codebrew")
            if not codebrew_url:
                return {"error": "CodeBrew service not available"}
                
            response = await self.client.post(
                f"{codebrew_url}/execute",
                json={"script": script}
            )
            return response.json()
        except Exception as e:
            # Fallback to direct config URL
            try:
                response = await self.client.post(
                    f"{settings.CODEBREW_SERVER_URL}/execute",
                    json={"script": script}
                )
                return response.json()
            except Exception as nested_e:
                return {"error": str(nested_e)}

    async def authenticate_google(self, auth_code: str) -> Dict[str, Any]:
        """Authenticate with Google services"""
        try:
            auth_url = await self.get_service_url("google_auth")
            if not auth_url:
                return {"error": "Google Auth service not available"}
                
            response = await self.client.post(
                f"{auth_url}/api/v1/auth/token",
                json={"code": auth_code}
            )
            return response.json()
        except Exception as e:
            # Fallback to direct config URL
            try:
                response = await self.client.post(
                    f"{settings.GOOGLE_AUTH_URL}/api/v1/auth/token",
                    json={"code": auth_code}
                )
                return response.json()
            except Exception as nested_e:
                return {"error": str(nested_e)}

    async def execute_functional_task(self, task: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute task on functional server"""
        try:
            functional_url = await self.get_service_url("functional")
            if not functional_url:
                return {"error": "Functional service not available"}
                
            response = await self.client.post(
                f"{functional_url}/execute",
                json={
                    "task": task,
                    "params": params
                }
            )
            return response.json()
        except Exception as e:
            # Fallback to direct config URL
            try:
                response = await self.client.post(
                    f"{settings.FUNCTIONAL_SERVER_URL}/execute",
                    json={
                        "task": task,
                        "params": params
                    }
                )
                return response.json()
            except Exception as nested_e:
                return {"error": str(nested_e)}

    async def close(self):
        """Cleanup when shutting down"""
        try:
            # Mark instance as dead in DNS
            await self.dns_client.post(
                f"{self.dns_url}/status/orchestrator/{self.instance_id}",
                json={"status": "dead"}
            )
        except:
            pass
        await self.client.aclose()
        await self.dns_client.aclose() 