import pytest
from fastapi.testclient import TestClient
from fastapi import WebSocket
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import json
import logging

from server import AndroidBridgeServer, AndroidCommand
from device_manager import DeviceStatus

@pytest.fixture
def app():
    server = AndroidBridgeServer()
    return server.app

@pytest.fixture
def client(app):
    return TestClient(app)

@pytest.fixture
def mock_device_setup():
    with patch('server.DeviceManager') as mock_manager:
        mock_manager_instance = mock_manager.return_value
        mock_status = DeviceStatus(
            connected=True,
            last_heartbeat=datetime.now(),
            battery_level=85,
            running_apps=["com.example.app"],
            system_stats={"cpu": 30, "memory": 45},
            capabilities=["screenshot", "input"]
        )
        mock_manager_instance.devices = {"device1": mock_status}
        yield mock_manager_instance, mock_status

@pytest.fixture
def mock_logger():
    with patch('logging.Logger.log') as mock_log:
        yield mock_log

def test_list_devices_empty(client, mock_device_setup):
    mock_device_manager, _ = mock_device_setup
    mock_device_manager.devices = {}
    response = client.get("/devices")
    assert response.status_code == 200
    assert response.json() == {"devices": {}, "count": 0}

def test_list_devices_with_devices(client, mock_device_setup):
    mock_device_manager, mock_status = mock_device_setup
    response = client.get("/devices")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert "device1" in data["devices"]
    device = data["devices"]["device1"]
    assert device["connected"] == True
    assert device["battery_level"] == 85

def test_get_device_status_not_found(client, mock_device_setup):
    mock_device_manager, _ = mock_device_setup
    mock_device_manager.devices = {}
    response = client.get("/device/nonexistent")
    assert response.status_code == 404
    assert response.json()["detail"] == "Device not found"

def test_get_device_status_success(client, mock_device_setup):
    mock_device_manager, mock_status = mock_device_setup
    response = client.get("/device/device1")
    assert response.status_code == 200
    device = response.json()
    assert device["connected"] == True
    assert device["battery_level"] == 85
    assert device["running_apps"] == ["com.example.app"]

@pytest.mark.asyncio
async def test_websocket_connection(app, mock_device_setup):
    mock_device_manager, _ = mock_device_setup
    with patch('fastapi.WebSocket') as mock_ws:
        mock_ws.accept = AsyncMock()
        mock_ws.receive_text = AsyncMock(side_effect=["test message", Exception("Connection closed")])
        
        await app.websocket_endpoint(mock_ws, "test_device")
        
        mock_ws.accept.assert_called_once()
        mock_device_manager.register_device.assert_called_once_with("test_device", mock_ws)

def test_launch_app(client, mock_device_setup):
    mock_device_manager, _ = mock_device_setup
    mock_device_manager.handle_app_launch = AsyncMock(return_value={"status": "success"})
    response = client.post("/device/device1/app/launch?package_name=com.example.app")
    assert response.status_code == 200
    assert response.json() == {"status": "success"}

def test_stop_app(client, mock_device_setup):
    mock_device_manager, _ = mock_device_setup
    mock_device_manager.handle_app_stop = AsyncMock(return_value={"status": "success"})
    response = client.post("/device/device1/app/stop?package_name=com.example.app")
    assert response.status_code == 200
    assert response.json() == {"status": "success"}

def test_input_text(client, mock_device_setup):
    mock_device_manager, _ = mock_device_setup
    mock_device_manager.handle_input_text = AsyncMock(return_value={"status": "success"})
    response = client.post("/device/device1/input/text?text=hello")
    assert response.status_code == 200
    assert response.json() == {"status": "success"}

def test_tap(client, mock_device_setup):
    mock_device_manager, _ = mock_device_setup
    mock_device_manager.handle_tap = AsyncMock(return_value={"status": "success"})
    response = client.post("/device/device1/input/tap?x=100&y=200")
    assert response.status_code == 200
    assert response.json() == {"status": "success"}

def test_get_screenshot(client, mock_device_setup):
    mock_device_manager, _ = mock_device_setup
    mock_device_manager.handle_get_screenshot = AsyncMock(return_value={"image": "base64_data"})
    response = client.post("/device/device1/screenshot")
    assert response.status_code == 200
    assert response.json() == {"image": "base64_data"}

def test_send_notification(client, mock_device_setup):
    mock_device_manager, _ = mock_device_setup
    mock_device_manager.handle_notification = AsyncMock(return_value={"status": "success"})
    response = client.post(
        "/device/device1/notification",
        params={
            "title": "Test",
            "message": "Hello",
            "priority": "high"
        }
    )
    assert response.status_code == 200
    assert response.json() == {"status": "success"}

@pytest.mark.asyncio
async def test_send_command(client, mock_device_setup):
    mock_device_manager, _ = mock_device_setup
    mock_device_manager.command_handlers = {
        "test_command": AsyncMock(return_value={"status": "success"})
    }
    command = {
        "command_type": "test_command",
        "data": {"key": "value"},
        "device_id": "device1"
    }
    response = client.post("/send/device1", json=command)
    assert response.status_code == 200
    assert response.json() == {"status": "success"}

@pytest.mark.asyncio
async def test_send_invalid_command(client, mock_device_setup):
    mock_device_manager, _ = mock_device_setup
    mock_device_manager.command_handlers = {}
    command = {
        "command_type": "invalid_command",
        "data": {"key": "value"},
        "device_id": "device1"
    }
    response = client.post("/send/device1", json=command)
    assert response.status_code == 400
    assert "Unknown command type" in response.json()["detail"]

def test_logging(client, mock_device_setup, mock_logger):
    mock_device_manager, _ = mock_device_setup
    mock_device_manager.devices = {}
    client.get("/devices")
    assert mock_logger.call_count > 0
