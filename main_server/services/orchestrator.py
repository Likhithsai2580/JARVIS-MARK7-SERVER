from typing import Dict, Any, Optional
import httpx
from ..config import settings
import asyncio
from functools import wraps

class ServiceOrchestrator:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=settings.TIMEOUT)
        
    async def execute_llm_query(self, messages: list) -> Dict[str, Any]:
        """Execute query on LLM server"""
        try:
            response = await self.client.post(
                f"{settings.LLM_SERVER_URL}/chat/completions",
                json={"messages": messages}
            )
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    async def parse_ui_elements(self, image_data: bytes) -> Dict[str, Any]:
        """Parse UI elements using OmniParser"""
        try:
            files = {"file": image_data}
            response = await self.client.post(
                f"{settings.OMNIPARSER_URL}/parse",
                files=files
            )
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    async def execute_android_command(self, device_id: str, command: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute command on Android device"""
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
        except Exception as e:
            return {"error": str(e)}

    async def execute_codebrew_script(self, script: str) -> Dict[str, Any]:
        """Execute Python script using CodeBrew"""
        try:
            response = await self.client.post(
                f"{settings.CODEBREW_SERVER_URL}/execute",
                json={"script": script}
            )
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    async def authenticate_google(self, auth_code: str) -> Dict[str, Any]:
        """Authenticate with Google services"""
        try:
            response = await self.client.post(
                f"{settings.GOOGLE_AUTH_URL}/api/v1/auth/token",
                json={"code": auth_code}
            )
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    async def execute_functional_task(self, task: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute task on functional server"""
        try:
            response = await self.client.post(
                f"{settings.FUNCTIONAL_SERVER_URL}/execute",
                json={
                    "task": task,
                    "params": params
                }
            )
            return response.json()
        except Exception as e:
            return {"error": str(e)} 