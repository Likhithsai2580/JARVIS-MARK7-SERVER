from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional
from .jarvis.core import Jarvis
import uvicorn

app = FastAPI(title="Jarvis Functional Server")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

jarvis = Jarvis()

class CommandRequest(BaseModel):
    command: str
    context: Optional[Dict[str, Any]] = None

@app.post("/execute")
async def execute_command(request: CommandRequest):
    try:
        result = await jarvis.process_command(request.command, request.context)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/register")
async def register_with_dns():
    """Register this service with DNS server"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:9000/register",
                json={
                    "server": "functional",
                    "instance_id": 1,
                    "port": 8004,
                    "metadata": {
                        "version": "1.0",
                        "capabilities": ["jarvis", "automation"]
                    }
                }
            )
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8004) 