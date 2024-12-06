from typing import Dict, Any, Optional
import httpx
from datetime import datetime
import asyncio
from ..config import settings
from .skills import SkillRegistry

class Jarvis:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30)
        self.skill_registry = SkillRegistry()
        self.context = {}
        self.dns_client = DNSClient()
        
    async def process_command(self, command: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process user commands and route to appropriate services"""
        try:
            # Get LLM interpretation of command
            llm_response = await self.get_command_intent(command)
            
            # Route to appropriate skill
            skill_name = llm_response.get("skill")
            params = llm_response.get("parameters", {})
            
            if skill = self.skill_registry.get_skill(skill_name):
                return await skill.execute(params, context)
            else:
                return {"error": f"Skill {skill_name} not found"}
                
    async def get_command_intent(self, command: str) -> Dict[str, Any]:
        """Use LLM to understand command intent"""
        messages = [
            {"role": "system", "content": "You are Jarvis, an AI assistant. Parse user commands into structured actions."},
            {"role": "user", "content": command}
        ]
        
        llm_service = await self.dns_client.get_service("llm")
        response = await self.client.post(
            f"{llm_service.url}/chat/completions",
            json={"messages": messages}
        )
        return response.json()

class DNSClient:
    def __init__(self, dns_url: str = "http://localhost:9000"):
        self.dns_url = dns_url
        self.client = httpx.AsyncClient()
        self.cache = {}
        
    async def get_service(self, service_name: str) -> Dict[str, Any]:
        """Get service details from DNS server with caching"""
        if service_name in self.cache:
            if (datetime.now() - self.cache[service_name]["timestamp"]).seconds < 300:
                return self.cache[service_name]["data"]
                
        response = await self.client.get(f"{self.dns_url}/status/{service_name}")
        service_data = response.json()
        
        self.cache[service_name] = {
            "data": service_data,
            "timestamp": datetime.now()
        }
        
        return service_data 