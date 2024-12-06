from .server_template import BaseServer
from fastapi import HTTPException, WebSocket
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging
from datetime import datetime
from main_server import JarvisCore, JarvisResponse, Command, SystemStatus
import json
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MainServer(BaseServer):
    def __init__(self):
        super().__init__("Main")
        self.jarvis = JarvisCore()
        
        @self.app.post("/command")
        async def execute_command(command: Command):
            """Execute a command through HTTP endpoint"""
            self.set_busy(True)
            try:
                await self.logger.log(
                    message="Processing command",
                    log_type="info",
                    details={"command": command.text}
                )
                response = await self.process_command(command)
                await self.logger.log(
                    message="Command executed successfully",
                    log_type="info",
                    details={"command": command.text, "response_type": response.get("type")}
                )
                return response
            except Exception as e:
                await self.logger.log(
                    message=f"Command execution failed: {str(e)}",
                    log_type="error",
                    details={"command": command.text, "error": str(e)}
                )
                raise
            finally:
                self.set_busy(False)
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time communication"""
            await websocket.accept()
            await self.logger.log(
                message="New WebSocket connection",
                log_type="info"
            )
            session_id = await self.handle_websocket_connection(websocket)
            
            try:
                while True:
                    message = await websocket.receive_text()
                    await self.handle_websocket_message(websocket, message, session_id)
            except Exception as e:
                await self.logger.log(
                    message=f"WebSocket error: {str(e)}",
                    log_type="error",
                    details={"session_id": session_id, "error": str(e)}
                )
            finally:
                await self.cleanup_websocket_session(session_id)
                await self.logger.log(
                    message="WebSocket connection closed",
                    log_type="info",
                    details={"session_id": session_id}
                )
        
        @self.app.get("/status")
        async def system_status():
            """Get detailed system status"""
            try:
                await self.logger.log(
                    message="System status check requested",
                    log_type="info"
                )
                status = await self.get_system_status()
                await self.logger.log(
                    message="System status check completed",
                    log_type="info",
                    details={"active_sessions": status.get("active_sessions")}
                )
                return status
            except Exception as e:
                await self.logger.log(
                    message=f"System status check failed: {str(e)}",
                    log_type="error",
                    details={"error": str(e)}
                )
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/health")
        async def health_check():
            """Basic health check endpoint"""
            try:
                await self.logger.log(
                    message="Health check requested",
                    log_type="info"
                )
                health = await self.check_health()
                await self.logger.log(
                    message="Health check completed",
                    log_type="info",
                    details={"status": health.get("status")}
                )
                return health
            except Exception as e:
                await self.logger.log(
                    message=f"Health check failed: {str(e)}",
                    log_type="error",
                    details={"error": str(e)}
                )
                raise HTTPException(status_code=500, detail=str(e))
    
    async def process_command(self, command: Command) -> Dict[str, Any]:
        """Process incoming command"""
        try:
            # Process command using JarvisCore
            response = await self.jarvis.process_command(command.text, command.context)
            return response
        except Exception as e:
            await self.logger.log(
                message=f"Command processing error: {str(e)}",
                log_type="error",
                details={"command": command.text, "error": str(e)}
            )
            return JarvisResponse.format_response(
                {"error": f"Command processing failed: {str(e)}"},
                "error"
            )
    
    async def handle_websocket_connection(self, websocket: WebSocket) -> str:
        """Handle new WebSocket connection"""
        try:
            # Add session to JarvisCore active sessions
            session_id = await self.jarvis.handle_websocket_message(
                websocket,
                json.dumps({
                    "text": "initialize",
                    "context": {"type": "connection"}
                })
            )
            await self.logger.log(
                message="WebSocket session initialized",
                log_type="info",
                details={"session_id": session_id}
            )
            return session_id
        except Exception as e:
            await self.logger.log(
                message=f"WebSocket connection error: {str(e)}",
                log_type="error",
                details={"error": str(e)}
            )
            raise
    
    async def handle_websocket_message(self, websocket: WebSocket, message: str, session_id: str):
        """Handle incoming WebSocket message"""
        try:
            await self.jarvis.handle_websocket_message(websocket, message)
            # Update last activity
            if session_id in self.jarvis.active_sessions:
                self.jarvis.active_sessions[session_id]["last_activity"] = datetime.now()
                await self.logger.log(
                    message="WebSocket message handled",
                    log_type="info",
                    details={"session_id": session_id}
                )
        except Exception as e:
            await self.logger.log(
                message=f"WebSocket message handling error: {str(e)}",
                log_type="error",
                details={"session_id": session_id, "error": str(e)}
            )
            await websocket.send_json(
                JarvisResponse.format_response(
                    {"error": f"Message processing failed: {str(e)}"},
                    "error"
                )
            )
    
    async def cleanup_websocket_session(self, session_id: str):
        """Clean up WebSocket session"""
        try:
            if session_id in self.jarvis.active_sessions:
                del self.jarvis.active_sessions[session_id]
        except Exception as e:
            logger.error(f"Session cleanup error: {str(e)}")
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get detailed system status"""
        try:
            uptime = (datetime.now() - self.jarvis.system_status.start_time).total_seconds()
            return {
                "status": "online",
                "instance_id": self.jarvis.instance_id,
                "version": "Mark 7",
                "uptime_seconds": uptime,
                "active_sessions": len(self.jarvis.active_sessions),
                "requests": {
                    "total": self.jarvis.system_status.total_requests,
                    "successful": self.jarvis.system_status.successful_requests,
                    "failed": self.jarvis.system_status.failed_requests
                },
                "services": self.jarvis.system_status.service_status,
                "system_load": self.jarvis.system_status.system_load,
                "active_protocols": list(self.jarvis.system_status.active_protocols),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Status retrieval error: {str(e)}")
            raise
    
    async def check_health(self) -> Dict[str, Any]:
        """Perform health check"""
        try:
            return JarvisResponse.format_response({
                "status": "healthy",
                "instance_id": self.jarvis.instance_id,
                "active_sessions": len(self.jarvis.active_sessions)
            })
        except Exception as e:
            logger.error(f"Health check error: {str(e)}")
            raise

if __name__ == "__main__":
    server = MainServer()
    server.run() 