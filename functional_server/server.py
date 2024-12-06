from .server_template import BaseServer
from fastapi import HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import asyncio
from jarvis.core import Jarvis, ExecutionContext
from jarvis.skills import SkillRegistry
import logging
import json
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FunctionRequest(BaseModel):
    function_name: str
    args: Optional[List[Any]] = None
    kwargs: Optional[Dict[str, Any]] = None
    context: Optional[Dict[str, Any]] = None

class FunctionResponse(BaseModel):
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: float
    metadata: Optional[Dict[str, Any]] = None

class FunctionalServer(BaseServer):
    def __init__(self):
        super().__init__("Functional")
        self.jarvis = Jarvis()
        self.skill_registry = SkillRegistry()
        self.execution_history = []
        
        @self.app.post("/execute", response_model=FunctionResponse)
        async def execute_function(request: FunctionRequest):
            self.set_busy(True)
            start_time = datetime.now()
            try:
                await self.logger.log(
                    message=f"Executing function: {request.function_name}",
                    log_type="info",
                    details={
                        "args": request.args,
                        "kwargs": request.kwargs,
                        "context": request.context
                    }
                )
                response = await self.process_function(request)
                execution_time = (datetime.now() - start_time).total_seconds()
                
                await self.logger.log(
                    message=f"Function executed successfully: {request.function_name}",
                    log_type="info",
                    details={
                        "execution_time": execution_time,
                        "status": "success"
                    }
                )
                
                return FunctionResponse(
                    status="success",
                    result=response,
                    execution_time=execution_time,
                    metadata={
                        "function_name": request.function_name,
                        "timestamp": start_time.isoformat()
                    }
                )
            except Exception as e:
                execution_time = (datetime.now() - start_time).total_seconds()
                await self.logger.log(
                    message=f"Function execution failed: {request.function_name}",
                    log_type="error",
                    details={
                        "error": str(e),
                        "execution_time": execution_time
                    }
                )
                return FunctionResponse(
                    status="error",
                    error=str(e),
                    execution_time=execution_time,
                    metadata={
                        "function_name": request.function_name,
                        "timestamp": start_time.isoformat()
                    }
                )
            finally:
                self.set_busy(False)
        
        @self.app.get("/functions")
        async def list_functions():
            """List available functions and skills"""
            try:
                await self.logger.log(
                    message="Listing available functions",
                    log_type="info"
                )
                # Get available skills
                skills = list(self.skill_registry.skills.keys())
                
                # Get recent execution history
                recent_executions = self.execution_history[-10:] if self.execution_history else []
                
                response = {
                    "available_skills": skills,
                    "recent_executions": recent_executions,
                    "system_status": {
                        "is_busy": self.is_busy(),
                        "uptime": self.get_uptime(),
                        "total_executions": len(self.execution_history)
                    }
                }
                
                await self.logger.log(
                    message="Functions listed successfully",
                    log_type="info",
                    details={
                        "skill_count": len(skills),
                        "total_executions": len(self.execution_history)
                    }
                )
                
                return response
            except Exception as e:
                await self.logger.log(
                    message="Failed to list functions",
                    log_type="error",
                    details={"error": str(e)}
                )
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/history")
        async def get_execution_history(limit: int = 10, function_name: Optional[str] = None):
            """Get execution history with optional filtering"""
            try:
                await self.logger.log(
                    message="Retrieving execution history",
                    log_type="info",
                    details={
                        "limit": limit,
                        "function_name": function_name
                    }
                )
                
                history = self.execution_history
                if function_name:
                    history = [h for h in history if h["function_name"] == function_name]
                
                response = {
                    "history": history[-limit:],
                    "total_entries": len(history)
                }
                
                await self.logger.log(
                    message="Execution history retrieved successfully",
                    log_type="info",
                    details={
                        "entries_returned": len(response["history"]),
                        "total_entries": response["total_entries"]
                    }
                )
                
                return response
            except Exception as e:
                await self.logger.log(
                    message="Failed to retrieve execution history",
                    log_type="error",
                    details={"error": str(e)}
                )
                raise HTTPException(status_code=500, detail=str(e))
    
    async def process_function(self, request: FunctionRequest) -> Dict:
        """Process and execute the requested function using Jarvis"""
        try:
            # Create execution context
            context = ExecutionContext()
            
            # Add request metadata to context
            context.metadata = {
                "function_name": request.function_name,
                "timestamp": datetime.now().isoformat(),
                "args": request.args,
                "kwargs": request.kwargs
            }
            
            await self.logger.log(
                message=f"Processing function: {request.function_name}",
                log_type="info",
                details=context.metadata
            )
            
            # Check if function is a skill
            if request.function_name in self.skill_registry.skills:
                skill = self.skill_registry.get_skill(request.function_name)
                if skill:
                    await self.logger.log(
                        message=f"Executing skill: {request.function_name}",
                        log_type="info"
                    )
                    # Execute skill
                    params = {
                        **(request.kwargs or {}),
                        "args": request.args
                    }
                    result = await skill.execute(params, request.context)
                    
                    # Record execution
                    self._record_execution(request.function_name, "success", result, context)
                    
                    await self.logger.log(
                        message=f"Skill executed successfully: {request.function_name}",
                        log_type="info",
                        details={"context": context.metrics}
                    )
                    
                    return result
            
            # If not a skill, process as a command through Jarvis
            command = self._build_command(request)
            await self.logger.log(
                message=f"Processing command: {command}",
                log_type="info"
            )
            
            result = await self.jarvis.process_command(command, request.context)
            
            # Record execution
            self._record_execution(request.function_name, "success", result, context)
            
            await self.logger.log(
                message=f"Command processed successfully: {request.function_name}",
                log_type="info",
                details={"context": context.metrics}
            )
            
            return result
            
        except Exception as e:
            await self.logger.log(
                message=f"Function processing failed: {request.function_name}",
                log_type="error",
                details={
                    "error": str(e),
                    "context": context.errors if context else None
                }
            )
            # Record failed execution
            self._record_execution(request.function_name, "error", str(e), context)
            raise HTTPException(status_code=500, detail=str(e))
    
    def _build_command(self, request: FunctionRequest) -> str:
        """Build a command string from the function request"""
        command_parts = [request.function_name]
        
        if request.args:
            command_parts.extend(str(arg) for arg in request.args)
            
        if request.kwargs:
            for key, value in request.kwargs.items():
                command_parts.append(f"--{key}={value}")
                
        return " ".join(command_parts)
    
    def _record_execution(self, function_name: str, status: str, result: Any, context: ExecutionContext):
        """Record function execution in history"""
        execution_record = {
            "function_name": function_name,
            "timestamp": datetime.now().isoformat(),
            "status": status,
            "result": result if status == "success" else None,
            "error": result if status == "error" else None,
            "context": {
                "steps_executed": context.steps_executed,
                "metrics": context.metrics,
                "errors": context.errors
            }
        }
        
        self.execution_history.append(execution_record)
        # Keep only last 1000 executions
        if len(self.execution_history) > 1000:
            self.execution_history = self.execution_history[-1000:]
    
    def get_uptime(self) -> float:
        """Get server uptime in seconds"""
        return (datetime.now() - self.start_time).total_seconds()

if __name__ == "__main__":
    server = FunctionalServer()
    server.run() 