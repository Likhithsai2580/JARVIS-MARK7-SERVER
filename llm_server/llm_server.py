from litellm import Router
import os
from typing import List, Dict, Any
import random

class LLMRouter:
    def __init__(self):
        # Define the model deployments for different providers
        self.model_list = [
            {
                "model_name": "gpt-3.5-turbo",
                "litellm_params": {
                    "model": "gpt-3.5-turbo",
                    "api_base": "https://proxy.blackgaypornis.fun/v1",
                    "api_key": "not-needed"
                }
            },
            {
                "model_name": "gpt-3.5-turbo",
                "litellm_params": {
                    "model": "gpt-3.5-turbo", 
                    "api_base": "https://shard-ai.xyz/v1",
                    "api_key": "not-needed"
                }
            },
            {
                "model_name": "gpt-3.5-turbo",
                "litellm_params": {
                    "model": "gpt-3.5-turbo",
                    "api_base": "https://fresedgpt.space/v1",
                    "api_key": "not-needed"
                }
            },
            {
                "model_name": "gpt-3.5-turbo",
                "litellm_params": {
                    "model": "gpt-3.5-turbo",
                    "api_base": "https://www.electronhub.top/v1",
                    "api_key": "not-needed"
                }
            },
            {
                "model_name": "gpt-3.5-turbo",
                "litellm_params": {
                    "model": "gpt-3.5-turbo",
                    "api_base": "https://api.webraft.in/freeapi/v1",
                    "api_key": "not-needed"
                }
            },
            {
                "model_name": "gpt-3.5-turbo", 
                "litellm_params": {
                    "model": "gpt-3.5-turbo",
                    "api_base": "https://helixmind.online/v1",
                    "api_key": "not-needed"
                }
            }
        ]

        # Initialize the router with load balancing and fallback settings
        self.router = Router(
            model_list=self.model_list,
            routing_strategy="simple-shuffle",  # Randomly select from available models
            fallbacks=[{
                "gpt-3.5-turbo": [m["model_name"] for m in self.model_list]
            }],
            context_window_fallbacks=[{
                "gpt-3.5-turbo": [m["model_name"] for m in self.model_list]
            }],
            enable_pre_call_check=True,  # Enable health checks
        )

    async def get_completion(self, messages: List[Dict[str, str]]) -> str:
        """
        Get a completion from one of the available LLM providers
        """
        try:
            response = await self.router.acompletion(
                model="gpt-3.5-turbo",
                messages=messages
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error occurred: {str(e)}")
            # The router will automatically try fallback models if one fails
            raise

# FastAPI implementation
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()
llm_router = LLMRouter()

class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]

@app.post("/chat/completions")
async def chat_completion(request: ChatRequest):
    try:
        response = await llm_router.get_completion(request.messages)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 