from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from .services.orchestrator import ServiceOrchestrator
from .config import settings
from typing import Dict, Any, Optional
import uvicorn

app = FastAPI(title="Unified Service API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create service orchestrator
orchestrator = ServiceOrchestrator()

@app.post("/api/execute")
async def execute_task(
    task_type: str,
    params: Dict[str, Any],
    device_id: Optional[str] = None
):
    """Execute task across different services"""
    try:
        if task_type == "llm":
            return await orchestrator.execute_llm_query(params.get("messages", []))
        elif task_type == "ui":
            return await orchestrator.parse_ui_elements(params.get("image"))
        elif task_type == "android":
            return await orchestrator.execute_android_command(
                device_id,
                params.get("command"),
                params.get("command_params", {})
            )
        elif task_type == "script":
            return await orchestrator.execute_codebrew_script(params.get("script"))
        elif task_type == "google":
            return await orchestrator.authenticate_google(params.get("auth_code"))
        elif task_type == "functional":
            return await orchestrator.execute_functional_task(
                params.get("task"),
                params.get("task_params", {})
            )
        else:
            raise HTTPException(status_code=400, detail="Invalid task type")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080) 