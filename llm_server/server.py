from .server_template import BaseServer
from fastapi import HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, List
import logging
from llm_server import LLMRouter
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMRequest(BaseModel):
    prompt: str
    model: Optional[str] = "gpt-3.5-turbo"
    max_tokens: Optional[int] = 2000
    temperature: Optional[float] = 0.7
    messages: Optional[List[Dict[str, str]]] = None

    def to_messages(self) -> List[Dict[str, str]]:
        """Convert prompt to messages format if not provided"""
        if self.messages:
            return self.messages
        return [
            {"role": "user", "content": self.prompt}
        ]

class LLMResponse(BaseModel):
    text: str
    model: str
    tokens: Optional[int] = None
    metadata: Optional[Dict] = None

class LLMServer(BaseServer):
    def __init__(self):
        # Initialize with service name "llm"
        super().__init__("llm")
        self.llm_router = LLMRouter()
        
        @self.app.post("/generate", response_model=LLMResponse)
        async def generate_text(request: LLMRequest):
            self.set_busy(True)
            try:
                # Add more detailed metadata for DNS monitoring
                await self.dns_client.update_status(True, {
                    "request_type": "generate",
                    "model": request.model,
                    "max_tokens": request.max_tokens,
                    "performance_metrics": {
                        "requests_per_second": 1,  # You can track this more accurately
                        "cpu": 0.5,  # Add actual CPU metrics
                        "memory": 0.3  # Add actual memory metrics
                    }
                })
                
                response = await self.process_llm_request(request)
                
                # Update DNS with success status
                await self.dns_client.update_status(False, {
                    "last_success": datetime.now().isoformat(),
                    "tokens_generated": response.tokens
                })
                
                return response
            except Exception as e:
                # Update DNS with error status
                await self.dns_client.update_status(False, {
                    "last_error": str(e),
                    "error_timestamp": datetime.now().isoformat()
                })
                raise HTTPException(status_code=500, detail=str(e))
            finally:
                self.set_busy(False)

        @self.app.get("/models")
        async def list_models():
            """List available LLM models"""
            try:
                models = [
                    {
                        "id": model["model_name"],
                        "api_base": model["litellm_params"]["api_base"]
                    }
                    for model in self.llm_router.model_list
                ]
                
                # Update DNS with model information
                await self.dns_client.update_status(False, {
                    "available_models": len(models),
                    "models": [m["id"] for m in models]
                })
                
                return {"models": models}
            except Exception as e:
                await self.dns_client.update_status(False, {
                    "last_error": str(e),
                    "error_timestamp": datetime.now().isoformat()
                })
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/health")
        async def health_check():
            """Enhanced health check with metrics"""
            try:
                test_messages = [{"role": "user", "content": "test"}]
                response = await self.llm_router.get_completion(test_messages)
                status = "healthy" if response else "unhealthy"
                
                metrics = {
                    "status": status,
                    "active_models": len(self.llm_router.model_list),
                    "timestamp": datetime.now().isoformat(),
                    "performance_metrics": {
                        "cpu": 0.5,  # Add actual CPU metrics
                        "memory": 0.3,  # Add actual memory metrics
                        "network": 0.4  # Add actual network metrics
                    }
                }
                
                # Update DNS with health metrics
                await self.dns_client.update_status(self.busy, metrics)
                
                return metrics
            except Exception as e:
                error_metrics = {
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
                await self.dns_client.update_status(True, error_metrics)
                return error_metrics
    
    async def process_llm_request(self, request: LLMRequest) -> Dict:
        """Process LLM request with the specified model"""
        try:
            # Convert request to messages format
            messages = request.to_messages()
            
            # Get completion from router
            response_text = await self.llm_router.get_completion(messages)
            
            # Prepare response
            return LLMResponse(
                text=response_text,
                model=request.model,
                tokens=len(response_text.split()),  # Approximate token count
                metadata={
                    "temperature": request.temperature,
                    "max_tokens": request.max_tokens,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"LLM processing error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"LLM processing failed: {str(e)}"
            )

if __name__ == "__main__":
    server = LLMServer()
    server.run() 