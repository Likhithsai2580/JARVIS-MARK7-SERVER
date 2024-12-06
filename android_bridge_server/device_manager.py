from typing import Dict, Any, Optional
from datetime import datetime
import json
import asyncio
from fastapi import WebSocket

class DeviceStatus:
    def __init__(self):
        self.connected = False
        self.last_heartbeat = None
        self.battery_level = None
        self.running_apps = []
        self.system_stats = {}
        self.capabilities = []

class DeviceManager:
    def __init__(self):
        self.devices: Dict[str, DeviceStatus] = {}
        self.websockets: Dict[str, WebSocket] = {}
        self.command_handlers = {
            "app_launch": self.handle_app_launch,
            "app_stop": self.handle_app_stop,
            "get_screenshot": self.handle_get_screenshot,
            "input_text": self.handle_input_text,
            "tap": self.handle_tap,
            "swipe": self.handle_swipe,
            "back": self.handle_back,
            "home": self.handle_home,
            "recent": self.handle_recent,
            "volume": self.handle_volume,
            "brightness": self.handle_brightness,
            "notification": self.handle_notification,
        }
    
    async def register_device(self, device_id: str, websocket: WebSocket):
        """Register a new device connection"""
        self.websockets[device_id] = websocket
        self.devices[device_id] = DeviceStatus()
        self.devices[device_id].connected = True
        self.devices[device_id].last_heartbeat = datetime.now()
        
        # Request device capabilities
        await self.send_command(device_id, {
            "type": "get_capabilities",
            "data": {}
        })
    
    async def unregister_device(self, device_id: str):
        """Unregister a device"""
        if device_id in self.websockets:
            del self.websockets[device_id]
        if device_id in self.devices:
            del self.devices[device_id]
    
    async def send_command(self, device_id: str, command: Dict[str, Any]) -> Dict:
        """Send command to device and wait for response"""
        if device_id not in self.websockets:
            raise ValueError("Device not connected")
        
        websocket = self.websockets[device_id]
        await websocket.send_text(json.dumps(command))
        
        # Wait for response
        response = await websocket.receive_text()
        return json.loads(response)
    
    async def handle_device_message(self, device_id: str, message: Dict[str, Any]):
        """Handle incoming message from device"""
        message_type = message.get("type")
        
        if message_type == "heartbeat":
            await self.handle_heartbeat(device_id, message)
        elif message_type == "capabilities":
            await self.handle_capabilities(device_id, message)
        elif message_type == "status_update":
            await self.handle_status_update(device_id, message)
        elif message_type == "error":
            await self.handle_error(device_id, message)
    
    # Command Handlers
    async def handle_app_launch(self, device_id: str, data: Dict[str, Any]) -> Dict:
        """Launch an app on the device"""
        self.validate_command_data("app_launch", data)
        command = {
            "type": "app_launch",
            "data": {
                "package_name": data["package_name"],
                "activity": data.get("activity"),
                "extras": data.get("extras", {})
            }
        }
        return await self.send_command(device_id, command)
    
    async def handle_app_stop(self, device_id: str, data: Dict[str, Any]) -> Dict:
        """Stop an app on the device"""
        self.validate_command_data("app_stop", data)
        command = {
            "type": "app_stop",
            "data": {
                "package_name": data["package_name"]
            }
        }
        return await self.send_command(device_id, command)
    
    async def handle_get_screenshot(self, device_id: str, data: Dict[str, Any]) -> Dict:
        """Get a screenshot from the device"""
        command = {
            "type": "get_screenshot",
            "data": {
                "format": data.get("format", "png"),
                "quality": data.get("quality", 80)
            }
        }
        return await self.send_command(device_id, command)
    
    async def handle_input_text(self, device_id: str, data: Dict[str, Any]) -> Dict:
        """Input text on the device"""
        self.validate_command_data("input_text", data)
        command = {
            "type": "input_text",
            "data": {
                "text": data["text"]
            }
        }
        return await self.send_command(device_id, command)
    
    async def handle_tap(self, device_id: str, data: Dict[str, Any]) -> Dict:
        """Perform tap gesture"""
        self.validate_command_data("tap", data)
        command = {
            "type": "tap",
            "data": {
                "x": data["x"],
                "y": data["y"]
            }
        }
        return await self.send_command(device_id, command)
    
    async def handle_swipe(self, device_id: str, data: Dict[str, Any]) -> Dict:
        """Perform swipe gesture"""
        self.validate_command_data("swipe", data)
        command = {
            "type": "swipe",
            "data": {
                "start_x": data["start_x"],
                "start_y": data["start_y"],
                "end_x": data["end_x"],
                "end_y": data["end_y"],
                "duration": data.get("duration", 300)
            }
        }
        return await self.send_command(device_id, command)
    
    async def handle_back(self, device_id: str, data: Dict[str, Any]) -> Dict:
        """Press back button"""
        command = {"type": "back", "data": {}}
        return await self.send_command(device_id, command)
    
    async def handle_home(self, device_id: str, data: Dict[str, Any]) -> Dict:
        """Press home button"""
        command = {"type": "home", "data": {}}
        return await self.send_command(device_id, command)
    
    async def handle_recent(self, device_id: str, data: Dict[str, Any]) -> Dict:
        """Show recent apps"""
        command = {"type": "recent", "data": {}}
        return await self.send_command(device_id, command)
    
    async def handle_volume(self, device_id: str, data: Dict[str, Any]) -> Dict:
        """Control volume"""
        self.validate_command_data("volume", data)
        command = {
            "type": "volume",
            "data": {
                "stream": data.get("stream", "music"),
                "level": data["level"]
            }
        }
        return await self.send_command(device_id, command)
    
    async def handle_brightness(self, device_id: str, data: Dict[str, Any]) -> Dict:
        """Control screen brightness"""
        self.validate_command_data("brightness", data)
        command = {
            "type": "brightness",
            "data": {
                "level": data["level"],
                "auto": data.get("auto", False)
            }
        }
        return await self.send_command(device_id, command)
    
    async def handle_notification(self, device_id: str, data: Dict[str, Any]) -> Dict:
        """Send notification to device"""
        self.validate_command_data("notification", data)
        command = {
            "type": "notification",
            "data": {
                "title": data["title"],
                "message": data["message"],
                "priority": data.get("priority", "normal"),
                "actions": data.get("actions", [])
            }
        }
        return await self.send_command(device_id, command)
    
    # Status Handlers
    async def handle_heartbeat(self, device_id: str, message: Dict[str, Any]):
        """Handle device heartbeat"""
        if device_id in self.devices:
            self.devices[device_id].last_heartbeat = datetime.now()
            self.devices[device_id].battery_level = message["data"].get("battery_level")
            self.devices[device_id].running_apps = message["data"].get("running_apps", [])
            self.devices[device_id].system_stats = message["data"].get("system_stats", {})
    
    async def handle_capabilities(self, device_id: str, message: Dict[str, Any]):
        """Handle device capabilities update"""
        if device_id in self.devices:
            self.devices[device_id].capabilities = message["data"].get("capabilities", [])
    
    async def handle_status_update(self, device_id: str, message: Dict[str, Any]):
        """Handle device status update"""
        if device_id in self.devices:
            status_data = message["data"]
            device_status = self.devices[device_id]
            
            if "battery_level" in status_data:
                device_status.battery_level = status_data["battery_level"]
            if "running_apps" in status_data:
                device_status.running_apps = status_data["running_apps"]
            if "system_stats" in status_data:
                device_status.system_stats.update(status_data["system_stats"])
    
    async def handle_error(self, device_id: str, message: Dict[str, Any]):
        """Handle device error"""
        error_data = message['data']
        error_message = error_data.get('error', 'Unknown error')
        error_code = error_data.get('code', 'UNKNOWN')
        error_details = error_data.get('details', {})
        
        # Log the error
        print(f"Error from device {device_id}: {error_message} (Code: {error_code})")
        if error_details:
            print(f"Error details: {json.dumps(error_details, indent=2)}")
            
        # Update device status if needed
        if device_id in self.devices:
            if error_code in ['DEVICE_OFFLINE', 'CONNECTION_LOST']:
                self.devices[device_id].connected = False
            elif error_code == 'LOW_BATTERY':
                self.devices[device_id].battery_level = error_details.get('battery_level')
                
        # Emit error event to connected clients if needed
        if device_id in self.websockets:
            try:
                await self.websockets[device_id].send_text(json.dumps({
                    "type": "error_notification",
                    "data": {
                        "message": error_message,
                        "code": error_code,
                        "details": error_details
                    }
                }))
            except Exception as e:
                print(f"Failed to send error notification: {str(e)}")