from typing import List, Dict
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import logging
from blackbox import send_message
from deepseek import DeepSeek
from server_template import BaseServer
import asyncio
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    model: str = "claude-sonnet-3.5"

class LLMServer(BaseServer):
    def __init__(self):
        super().__init__("llm")
        self.deepseek = DeepSeek()
        self.model_routes = {
            "claude-sonnet-3.5": self._blackbox_route,
            "deepseek": self._deepseek_route
        }

        @self.app.post("/chat/completions")
        async def chat_completion(request: ChatRequest):
            self.set_busy(True)
            try:
                logger.info(f"Received chat request: {request.messages}")
                
                # Route to appropriate model handler
                route_handler = self.model_routes.get(request.model, self._blackbox_route)
                response = await route_handler(request.messages)
                
                logger.info(f"Response from LLM: {response}")
                
                # Update DNS with success metrics
                await self.dns_client.update_status(False, {
                    "last_success": datetime.now().isoformat(),
                    "model_used": request.model,
                    "response_length": len(str(response))
                })
                
                return {"response": response}
                
            except Exception as e:
                logger.error(f"Error processing chat request: {str(e)}")
                # Update DNS with error status
                await self.dns_client.update_status(False, {
                    "last_error": str(e),
                    "error_timestamp": datetime.now().isoformat()
                })
                raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
            finally:
                self.set_busy(False)

    async def _blackbox_route(self, messages: List[Message]) -> str:
        """Handle requests for Blackbox API"""
        message_text = "\n".join([msg.content for msg in messages])
        return send_message(message=message_text)

    async def _deepseek_route(self, messages: List[Message]) -> str:
        """Handle requests for DeepSeek API"""
        # Create session if not exists
        if not self.deepseek.session_data:
            await self.deepseek.create_session()
        
        # Send last message in conversation
        last_message = messages[-1].content
        response = await self.deepseek.chat(last_message)
        return response.get('response', '')

if __name__ == "__main__":
    server = LLMServer()
    server.run()