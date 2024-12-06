try:
    from llm.base import LLM, Model, ModelType, Role
except ImportError:
    import os
    import sys
    
    sys.path.append(os.path.dirname(__file__))
    from base import LLM, Model, ModelType, Role

from typing import Optional, List, Dict, Generator, AsyncGenerator, Any
import requests
from dotenv import load_dotenv
from rich import print
import aiohttp
import asyncio
import json

load_dotenv()

# Define available models
GPT35_TURBO = Model(name="gpt-3.5-turbo", typeof=ModelType.textonly)

class LLMServer(LLM):
    def __init__(
        self,
        model: Model,
        server_url: str = "http://localhost:8000",
        apiKey: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.7,
        systemPrompt: Optional[str] = None,
        maxTokens: int = 2048,
        logFile: Optional[str] = None,
        extra: Dict[str, str] = {},
    ):
        messages = messages if messages is not None else []
        super().__init__(model, apiKey, messages, temperature, systemPrompt, maxTokens, logFile)
        
        self.server_url = server_url.rstrip('/')
        self.extra = extra
        self.session = None

    async def constructClient(self) -> Any:
        """Create aiohttp session"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self.session

    async def testClient(self) -> bool:
        """Test server connection asynchronously"""
        if not self.session:
            self.session = await self.constructClient()
            
        try:
            async with self.session.get(
                f"{self.server_url}/health",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                response.raise_for_status()
                return True
        except Exception as e:
            self.logger.error(f"Failed to connect to LLM server: {str(e)}")
            return False

    async def run(self, prompt: str = "", imageUrl: Optional[str] = None, save: bool = True) -> str:
        """Run completion asynchronously"""
        if not self.session:
            self.session = await self.constructClient()
            
        toSend = []
        if save and prompt:
            self.addMessage(Role.user, prompt, imageUrl)
        elif not save and prompt:
            toSend.append(self.getMessage(Role.user, prompt, imageUrl))

        try:
            async with self.session.post(
                f"{self.server_url}/chat/completions",
                json={
                    "messages": self.messages + toSend,
                    "model": self.model.name,
                    "temperature": self.temperature,
                    "max_tokens": self.maxTokens,
                    **self.extra
                },
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                response.raise_for_status()
                result = await response.json()
                
                if save and "response" in result:
                    self.addMessage(Role.assistant, result["response"])
                
                return result.get("response", "No response received")

        except asyncio.TimeoutError:
            self.logger.error("Request timed out")
            return "Error: Request timed out"
        except aiohttp.ClientError as e:
            self.logger.error(f"Request failed: {str(e)}")
            return f"Error: {str(e)}"
        except Exception as e:
            self.logger.error(f"Unexpected error: {str(e)}")
            return f"Error: {str(e)}"

    async def streamRun(self, prompt: str = "", imageUrl: Optional[str] = None, save: bool = True) -> AsyncGenerator[str, None]:
        """Stream responses from the LLM server with proper async handling."""
        if not self.session:
            self.session = await self.constructClient()
            
        toSend = []
        if save and prompt:
            self.addMessage(Role.user, prompt, imageUrl)
        elif not save and prompt:
            toSend.append(self.getMessage(Role.user, prompt, imageUrl))

        try:
            async with self.session.post(
                f"{self.server_url}/chat/completions/stream",
                json={
                    "messages": self.messages + toSend,
                    "model": self.model.name,
                    "temperature": self.temperature,
                    "max_tokens": self.maxTokens,
                    "stream": True,
                    **self.extra
                },
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                response.raise_for_status()
                final_response = ""
                
                async for line in response.content:
                    if line:
                        try:
                            data = json.loads(line.decode('utf-8'))
                            if "delta" in data:
                                chunk = data["delta"].get("content", "")
                                if chunk:
                                    final_response += chunk
                                    yield chunk
                        except json.JSONDecodeError:
                            self.logger.warning(f"Failed to decode response chunk: {line}")
                            continue
                
                if save and final_response:
                    self.addMessage(Role.assistant, final_response)

        except aiohttp.ClientError as e:
            self.logger.error(f"Stream request failed: {str(e)}")
            yield f"Error: {str(e)}"
        except asyncio.TimeoutError:
            self.logger.error("Stream request timed out")
            yield "Error: Request timed out"
        except Exception as e:
            self.logger.error(f"Unexpected error in stream: {str(e)}")
            yield f"Error: {str(e)}"
            
    async def close(self):
        """Close the aiohttp session"""
        if self.session:
            await self.session.close()
            self.session = None