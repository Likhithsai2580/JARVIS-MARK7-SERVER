from typing import Dict, Any, List, Optional
import json
from datetime import datetime
import math

class HolographicElement:
    """Base class for holographic UI elements"""
    def __init__(self, element_id: str, position: Dict[str, float], size: Dict[str, float]):
        self.id = element_id
        self.position = position
        self.size = size
        self.opacity = 1.0
        self.rotation = 0.0
        self.visible = True
        self.animations = []
        
    def to_json(self) -> Dict[str, Any]:
        """Convert element to JSON representation"""
        return {
            "id": self.id,
            "type": self.__class__.__name__,
            "position": self.position,
            "size": self.size,
            "opacity": self.opacity,
            "rotation": self.rotation,
            "visible": self.visible,
            "animations": self.animations
        }

class HolographicText(HolographicElement):
    """Text display element"""
    def __init__(self, element_id: str, position: Dict[str, float], size: Dict[str, float], text: str):
        super().__init__(element_id, position, size)
        self.text = text
        self.font_size = 16
        self.color = "#00A6FF"  # Iron Man blue
        
    def to_json(self) -> Dict[str, Any]:
        data = super().to_json()
        data.update({
            "text": self.text,
            "font_size": self.font_size,
            "color": self.color
        })
        return data

class HolographicChart(HolographicElement):
    """Data visualization chart"""
    def __init__(self, element_id: str, position: Dict[str, float], size: Dict[str, float], chart_type: str):
        super().__init__(element_id, position, size)
        self.chart_type = chart_type
        self.data = []
        self.labels = []
        self.title = ""
        
    def update_data(self, data: List[float], labels: List[str]):
        self.data = data
        self.labels = labels
        
    def to_json(self) -> Dict[str, Any]:
        data = super().to_json()
        data.update({
            "chart_type": self.chart_type,
            "data": self.data,
            "labels": self.labels,
            "title": self.title
        })
        return data

class HolographicModel(HolographicElement):
    """3D model display"""
    def __init__(self, element_id: str, position: Dict[str, float], size: Dict[str, float], model_url: str):
        super().__init__(element_id, position, size)
        self.model_url = model_url
        self.animation_state = "idle"
        self.highlight_parts = []
        
    def to_json(self) -> Dict[str, Any]:
        data = super().to_json()
        data.update({
            "model_url": self.model_url,
            "animation_state": self.animation_state,
            "highlight_parts": self.highlight_parts
        })
        return data

class HolographicAlert(HolographicElement):
    """Alert display element"""
    def __init__(self, element_id: str, position: Dict[str, float], size: Dict[str, float], level: str):
        super().__init__(element_id, position, size)
        self.level = level
        self.message = ""
        self.pulse_animation = True
        self.color_map = {
            "info": "#00A6FF",
            "warning": "#FFA500",
            "critical": "#FF0000"
        }
        
    def to_json(self) -> Dict[str, Any]:
        data = super().to_json()
        data.update({
            "level": self.level,
            "message": self.message,
            "pulse_animation": self.pulse_animation,
            "color": self.color_map.get(self.level, "#00A6FF")
        })
        return data

class CircularMenu(HolographicElement):
    """Iron Man style circular menu"""
    def __init__(self, element_id: str, position: Dict[str, float], size: Dict[str, float]):
        super().__init__(element_id, position, size)
        self.items = []
        self.active_item = None
        self.rotation_speed = 0.5
        self.expanded = False
        
    def add_item(self, item: Dict[str, Any]):
        self.items.append(item)
        self._update_item_positions()
        
    def _update_item_positions(self):
        """Update positions of menu items in circular arrangement"""
        num_items = len(self.items)
        if num_items == 0:
            return
            
        radius = min(self.size["width"], self.size["height"]) / 2
        angle_step = 2 * math.pi / num_items
        
        for i, item in enumerate(self.items):
            angle = i * angle_step
            item["position"] = {
                "x": self.position["x"] + radius * math.cos(angle),
                "y": self.position["y"] + radius * math.sin(angle)
            }
            
    def to_json(self) -> Dict[str, Any]:
        data = super().to_json()
        data.update({
            "items": self.items,
            "active_item": self.active_item,
            "rotation_speed": self.rotation_speed,
            "expanded": self.expanded
        })
        return data

class HolographicInterface:
    """JARVIS's holographic interface manager"""
    def __init__(self):
        self.elements: Dict[str, HolographicElement] = {}
        self.active_view = "main"
        self.views = {
            "main": self._create_main_view(),
            "system": self._create_system_view(),
            "alerts": self._create_alerts_view(),
            "protocols": self._create_protocols_view()
        }
        
    def _create_main_view(self) -> Dict[str, HolographicElement]:
        """Create main view elements"""
        elements = {}
        
        # Add circular menu
        menu = CircularMenu("main_menu", {"x": 0, "y": 0}, {"width": 400, "height": 400})
        menu.add_item({"id": "system", "label": "System Status"})
        menu.add_item({"id": "protocols", "label": "Protocols"})
        menu.add_item({"id": "alerts", "label": "Alerts"})
        menu.add_item({"id": "analytics", "label": "Analytics"})
        elements["main_menu"] = menu
        
        # Add status text
        status = HolographicText("status_text", {"x": 0, "y": -200}, {"width": 300, "height": 50}, "JARVIS Online")
        elements["status_text"] = status
        
        return elements
        
    def _create_system_view(self) -> Dict[str, HolographicElement]:
        """Create system monitoring view"""
        elements = {}
        
        # Add system charts
        cpu_chart = HolographicChart("cpu_chart", {"x": -200, "y": 0}, {"width": 200, "height": 200}, "line")
        memory_chart = HolographicChart("memory_chart", {"x": 200, "y": 0}, {"width": 200, "height": 200}, "line")
        elements["cpu_chart"] = cpu_chart
        elements["memory_chart"] = memory_chart
        
        # Add 3D model of system
        model = HolographicModel("system_model", {"x": 0, "y": 0}, {"width": 400, "height": 400}, "system_model.glb")
        elements["system_model"] = model
        
        return elements
        
    def _create_alerts_view(self) -> Dict[str, HolographicElement]:
        """Create alerts view"""
        elements = {}
        
        # Add alert displays
        for i in range(5):
            alert = HolographicAlert(f"alert_{i}", {"x": 0, "y": i * 60}, {"width": 300, "height": 50}, "info")
            elements[f"alert_{i}"] = alert
            
        return elements
        
    def _create_protocols_view(self) -> Dict[str, HolographicElement]:
        """Create protocols view"""
        elements = {}
        
        # Add circular protocol selector
        protocols = CircularMenu("protocol_menu", {"x": 0, "y": 0}, {"width": 500, "height": 500})
        protocols.add_item({"id": "house_party", "label": "House Party Protocol"})
        protocols.add_item({"id": "clean_slate", "label": "Clean Slate Protocol"})
        protocols.add_item({"id": "safe_house", "label": "Safe House Protocol"})
        protocols.add_item({"id": "blackout", "label": "Blackout Protocol"})
        elements["protocol_menu"] = protocols
        
        return elements
        
    def switch_view(self, view_name: str):
        """Switch to a different view"""
        if view_name in self.views:
            self.active_view = view_name
            self.elements = self.views[view_name]
            
    def update_element(self, element_id: str, updates: Dict[str, Any]):
        """Update properties of an element"""
        if element_id in self.elements:
            element = self.elements[element_id]
            for key, value in updates.items():
                if hasattr(element, key):
                    setattr(element, key, value)
                    
    def get_current_view(self) -> Dict[str, Any]:
        """Get current view state"""
        return {
            "view": self.active_view,
            "elements": {
                element_id: element.to_json()
                for element_id, element in self.elements.items()
            },
            "timestamp": datetime.now().isoformat()
        }

class HolographicSystem:
    """Complete holographic system manager"""
    def __init__(self):
        self.interface = HolographicInterface()
        self.active_animations = []
        self.render_quality = "high"
        self.fps = 60
        self.enabled = True
        
    async def update(self, system_state: Dict[str, Any]):
        """Update holographic display based on system state"""
        # Update system view charts
        if self.interface.active_view == "system":
            if "cpu_usage" in system_state:
                self.interface.update_element("cpu_chart", {
                    "data": system_state["cpu_usage"],
                    "title": "CPU Usage"
                })
            if "memory_usage" in system_state:
                self.interface.update_element("memory_chart", {
                    "data": system_state["memory_usage"],
                    "title": "Memory Usage"
                })
                
        # Update alerts
        if "alerts" in system_state:
            for i, alert in enumerate(system_state["alerts"][:5]):
                self.interface.update_element(f"alert_{i}", {
                    "level": alert["level"],
                    "message": alert["message"]
                })
                
        # Update protocols
        if "active_protocols" in system_state:
            menu = self.interface.elements.get("protocol_menu")
            if menu:
                for item in menu.items:
                    item["active"] = item["id"] in system_state["active_protocols"]
                    
    def get_display_state(self) -> Dict[str, Any]:
        """Get complete display state"""
        return {
            "interface": self.interface.get_current_view(),
            "animations": self.active_animations,
            "quality": self.render_quality,
            "fps": self.fps,
            "enabled": self.enabled
        } 