from .server_template import BaseServer
from fastapi import HTTPException, WebSocket
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import asyncio
import json
from .device_manager import DeviceManager, DeviceStatus

class AndroidCommand(BaseModel):
    command_type: str
    data: Dict[str, Any]
    device_id: Optional[str] = None

class AndroidBridgeServer(BaseServer):
    def __init__(self):
        super().__init__("AndroidBridge")
        self.device_manager = DeviceManager()
        
        @self.app.websocket("/ws/{device_id}")
        async def websocket_endpoint(websocket: WebSocket, device_id: str):
            await websocket.accept()
            await self.logger.log(
                message=f"New device connection: {device_id}",
                log_type="info"
            )
            await self.device_manager.register_device(device_id, websocket)
            
            try:
                while True:
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    await self.logger.log(
                        message=f"Received message from device: {device_id}",
                        log_type="info",
                        details={"message_type": message.get("type")}
                    )
                    await self.device_manager.handle_device_message(device_id, message)
            except Exception as e:
                await self.logger.log(
                    message=f"WebSocket error for device {device_id}: {str(e)}",
                    log_type="error",
                    details={"error": str(e)}
                )
            finally:
                await self.device_manager.unregister_device(device_id)
                await self.logger.log(
                    message=f"Device disconnected: {device_id}",
                    log_type="info"
                )
        
        @self.app.post("/send/{device_id}")
        async def send_command(device_id: str, command: AndroidCommand):
            self.set_busy(True)
            try:
                await self.logger.log(
                    message=f"Sending command to device: {device_id}",
                    log_type="info",
                    details={
                        "command_type": command.command_type,
                        "data": command.data
                    }
                )
                
                if command.command_type not in self.device_manager.command_handlers:
                    await self.logger.log(
                        message=f"Unknown command type: {command.command_type}",
                        log_type="error",
                        details={"device_id": device_id}
                    )
                    raise HTTPException(
                        status_code=400,
                        detail=f"Unknown command type: {command.command_type}"
                    )
                
                handler = self.device_manager.command_handlers[command.command_type]
                response = await handler(device_id, command.data)
                
                await self.logger.log(
                    message=f"Command executed successfully: {command.command_type}",
                    log_type="info",
                    details={
                        "device_id": device_id,
                        "response": response
                    }
                )
                
                return response
            except Exception as e:
                await self.logger.log(
                    message=f"Command execution failed: {command.command_type}",
                    log_type="error",
                    details={
                        "device_id": device_id,
                        "error": str(e)
                    }
                )
                raise
            finally:
                self.set_busy(False)
        
        @self.app.get("/devices")
        async def list_devices():
            """List connected devices with their status"""
            try:
                await self.logger.log(
                    message="Listing connected devices",
                    log_type="info"
                )
                
                devices = {}
                for device_id, status in self.device_manager.devices.items():
                    devices[device_id] = {
                        "connected": status.connected,
                        "last_heartbeat": status.last_heartbeat.isoformat() if status.last_heartbeat else None,
                        "battery_level": status.battery_level,
                        "running_apps": status.running_apps,
                        "system_stats": status.system_stats,
                        "capabilities": status.capabilities
                    }
                
                await self.logger.log(
                    message="Device list retrieved successfully",
                    log_type="info",
                    details={"device_count": len(devices)}
                )
                
                return {
                    "devices": devices,
                    "count": len(devices)
                }
            except Exception as e:
                await self.logger.log(
                    message="Failed to list devices",
                    log_type="error",
                    details={"error": str(e)}
                )
                raise
        
        @self.app.get("/device/{device_id}")
        async def get_device_status(device_id: str):
            """Get detailed status of a specific device"""
            try:
                await self.logger.log(
                    message=f"Getting status for device: {device_id}",
                    log_type="info"
                )
                
                if device_id not in self.device_manager.devices:
                    await self.logger.log(
                        message=f"Device not found: {device_id}",
                        log_type="warning"
                    )
                    raise HTTPException(status_code=404, detail="Device not found")
                
                status = self.device_manager.devices[device_id]
                response = {
                    "connected": status.connected,
                    "last_heartbeat": status.last_heartbeat.isoformat() if status.last_heartbeat else None,
                    "battery_level": status.battery_level,
                    "running_apps": status.running_apps,
                    "system_stats": status.system_stats,
                    "capabilities": status.capabilities
                }
                
                await self.logger.log(
                    message=f"Device status retrieved: {device_id}",
                    log_type="info",
                    details={
                        "connected": status.connected,
                        "battery_level": status.battery_level
                    }
                )
                
                return response
            except Exception as e:
                await self.logger.log(
                    message=f"Failed to get device status: {device_id}",
                    log_type="error",
                    details={"error": str(e)}
                )
                raise
        
        @self.app.post("/device/{device_id}/app/launch")
        async def launch_app(device_id: str, package_name: str, activity: Optional[str] = None):
            """Launch an app on the device"""
            self.set_busy(True)
            try:
                await self.logger.log(
                    message=f"Launching app on device: {device_id}",
                    log_type="info",
                    details={
                        "package_name": package_name,
                        "activity": activity
                    }
                )
                
                response = await self.device_manager.handle_app_launch(
                    device_id,
                    {
                        "package_name": package_name,
                        "activity": activity
                    }
                )
                
                await self.logger.log(
                    message=f"App launched successfully: {package_name}",
                    log_type="info",
                    details={
                        "device_id": device_id,
                        "response": response
                    }
                )
                
                return response
            except Exception as e:
                await self.logger.log(
                    message=f"Failed to launch app: {package_name}",
                    log_type="error",
                    details={
                        "device_id": device_id,
                        "error": str(e)
                    }
                )
                raise
            finally:
                self.set_busy(False)
        
        @self.app.post("/device/{device_id}/app/stop")
        async def stop_app(device_id: str, package_name: str):
            """Stop an app on the device"""
            self.set_busy(True)
            try:
                response = await self.device_manager.handle_app_stop(
                    device_id,
                    {"package_name": package_name}
                )
                return response
            finally:
                self.set_busy(False)
        
        @self.app.post("/device/{device_id}/input/text")
        async def input_text(device_id: str, text: str):
            """Input text on the device"""
            self.set_busy(True)
            try:
                response = await self.device_manager.handle_input_text(
                    device_id,
                    {"text": text}
                )
                return response
            finally:
                self.set_busy(False)
        
        @self.app.post("/device/{device_id}/input/tap")
        async def tap(device_id: str, x: int, y: int):
            """Perform tap gesture"""
            self.set_busy(True)
            try:
                response = await self.device_manager.handle_tap(
                    device_id,
                    {"x": x, "y": y}
                )
                return response
            finally:
                self.set_busy(False)
        
        @self.app.post("/device/{device_id}/screenshot")
        async def get_screenshot(
            device_id: str,
            format: Optional[str] = "png",
            quality: Optional[int] = 80
        ):
            """Get a screenshot from the device"""
            self.set_busy(True)
            try:
                response = await self.device_manager.handle_get_screenshot(
                    device_id,
                    {
                        "format": format,
                        "quality": quality
                    }
                )
                return response
            finally:
                self.set_busy(False)
        
        @self.app.post("/device/{device_id}/notification")
        async def send_notification(
            device_id: str,
            title: str,
            message: str,
            priority: Optional[str] = "normal"
        ):
            """Send notification to device"""
            self.set_busy(True)
            try:
                response = await self.device_manager.handle_notification(
                    device_id,
                    {
                        "title": title,
                        "message": message,
                        "priority": priority
                    }
                )
                return response
            finally:
                self.set_busy(False)

if __name__ == "__main__":
    server = AndroidBridgeServer()
    server.run() 