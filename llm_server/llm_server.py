from typing import List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import logging
from api import send_chat_request

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]

async def get_completion(messages: List[Message]) -> str:
    """
    Get a completion from one of the available LLM providers
    """
    try:
        response = await send_chat_request(messages)
        return response
    except Exception as e:
        logger.error(f"Error getting completion: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

@app.post("/chat/completions")
async def chat_completion(request: ChatRequest):
    try:
        logger.info(f"Received chat request: {request.messages}")
        response = await get_completion(request.messages)
        logger.info(f"Response from LLM: {response}")
        return {"response": response}
    except HTTPException as http_e:
        raise http_e
    except Exception as e:
        logger.error(f"Error processing chat request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)