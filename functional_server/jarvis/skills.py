from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

class Skill(ABC):
    @abstractmethod
    async def execute(self, params: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        pass

class AndroidSkill(Skill):
    async def execute(self, params: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        device_id = params.get("device_id")
        command = params.get("command")
        android_service = await self.dns_client.get_service("android")
        
        response = await self.client.post(
            f"{android_service.url}/api/send-command",
            json={
                "device_id": device_id,
                "command": command,
                "params": params.get("command_params", {})
            }
        )
        return response.json()

class GoogleServicesSkill(Skill):
    async def execute(self, params: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        service_type = params.get("service_type")
        action = params.get("action")
        google_service = await self.dns_client.get_service("google")
        
        response = await self.client.post(
            f"{google_service.url}/api/v1/services/{service_type}/{action}",
            json=params.get("data", {})
        )
        return response.json()

class UIAnalysisSkill(Skill):
    async def execute(self, params: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        image_data = params.get("image")
        task = params.get("task")
        omniparser_service = await self.dns_client.get_service("omniparser")
        
        response = await self.client.post(
            f"{omniparser_service.url}/parse",
            files={"file": image_data}
        )
        return response.json()

class CodeExecutionSkill(Skill):
    async def execute(self, params: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        script = params.get("script")
        codebrew_service = await self.dns_client.get_service("codebrew")
        
        response = await self.client.post(
            f"{codebrew_service.url}/execute",
            json={"script": script}
        )
        return response.json()

class SkillRegistry:
    def __init__(self):
        self.skills = {
            "android": AndroidSkill(),
            "google": GoogleServicesSkill(),
            "ui": UIAnalysisSkill(),
            "code": CodeExecutionSkill()
        }
    
    def get_skill(self, skill_name: str) -> Optional[Skill]:
        return self.skills.get(skill_name) 