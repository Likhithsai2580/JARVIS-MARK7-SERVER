import pytest
from fastapi.testclient import TestClient
from dns_server import app, DNSServer, ServiceRegistration, ServiceInstance
import time
import asyncio
from unittest.mock import Mock, patch
import json
from contextlib import asynccontextmanager
from fastapi import HTTPException

# Configure pytest-asyncio to use strict mode
pytestmark = pytest.mark.asyncio

@pytest.fixture
@asynccontextmanager
async def dns_server_instance():
    """Create a DNS server instance for testing"""
    server = DNSServer()
    await server.start()
    try:
        yield server
    finally:
        # Cleanup
        await server.cleanup()
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

@pytest.fixture
def test_client(dns_server_instance):
    with TestClient(app) as client:
        yield client

@pytest.fixture
def test_service_registration():
    return ServiceRegistration(
        server="test_service",
        instance_id=1,
        port=8000,
        metadata={"version": "1.0"}
    )

@pytest.mark.asyncio
async def test_register_service(dns_server_instance):
    async with dns_server_instance as server:
        registration = ServiceRegistration(
            server="test_service",
            instance_id=1,
            port=8000
        )
        instance = await server.register_service(registration)
        assert instance.server == "test_service"
        assert instance.instance_id == 1
        assert instance.port == 8000
        assert instance.status == "healthy"

@pytest.mark.asyncio
async def test_get_service(dns_server_instance):
    async with dns_server_instance as server:
        # First register a service
        registration = ServiceRegistration(
            server="test_service",
            instance_id=1,
            port=8000
        )
        await server.register_service(registration)
        
        # Then try to get it
        instance = await server.get_service("test_service")
        assert instance.server == "test_service"
        assert instance.instance_id == 1
        assert instance.port == 8000

@pytest.mark.asyncio
async def test_update_heartbeat(dns_server_instance):
    async with dns_server_instance as server:
        # Register service first
        registration = ServiceRegistration(
            server="test_service",
            instance_id=1,
            port=8000
        )
        await server.register_service(registration)
        
        # Update heartbeat
        metrics = {"cpu": 50, "memory": 60}
        success = await server.update_heartbeat("test_service", 1, metrics)
        assert success == True
        
        # Verify metrics were updated
        instance = await server.get_service("test_service")
        assert instance.performance_metrics["cpu"] == 50
        assert instance.performance_metrics["memory"] == 60

@pytest.mark.asyncio
async def test_power_management(dns_server_instance):
    async with dns_server_instance as server:
        # Register multiple services
        services = [
            ServiceRegistration(server="test_service", instance_id=i, port=8000+i)
            for i in range(3)
        ]
        
        for service in services:
            await server.register_service(service)
        
        # Let power management run
        await asyncio.sleep(1)
        
        # Check power distribution
        total_power = sum(server.power_management.power_distribution.values())
        assert total_power > 0
        assert server.status["power_status"] in ["critical", "low", "optimal"]

@pytest.mark.asyncio
async def test_api_register_service(test_client, test_service_registration):
    response = test_client.post(
        "/register",
        json=test_service_registration.model_dump()
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "registered"
    assert data["instance"]["server"] == test_service_registration.server
    assert data["instance"]["instance_id"] == test_service_registration.instance_id

@pytest.mark.asyncio
async def test_api_get_service(test_client, test_service_registration):
    # First register a service
    test_client.post("/register", json=test_service_registration.model_dump())
    
    # Then try to get it
    response = test_client.get(f"/service/{test_service_registration.server}")
    assert response.status_code == 200
    data = response.json()
    assert data["instance_id"] == test_service_registration.instance_id

@pytest.mark.asyncio
async def test_api_heartbeat(test_client, test_service_registration):
    # Register service first
    test_client.post("/register", json=test_service_registration.model_dump())
    
    # Send heartbeat
    metrics = {"cpu": 50, "memory": 60}
    response = test_client.post(
        f"/heartbeat/{test_service_registration.server}/{test_service_registration.instance_id}",
        json=metrics
    )
    assert response.status_code == 200
    assert response.json()["status"] == "updated"

@pytest.mark.asyncio
async def test_api_status(test_client):
    response = test_client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert "system_status" in data
    assert "services" in data
    assert "power_distribution" in data
    assert "active_threats" in data
    assert "defense_protocols" in data

@pytest.mark.asyncio
async def test_api_servers_status(test_client, test_service_registration):
    # Register service first
    test_client.post("/register", json=test_service_registration.model_dump())
    
    response = test_client.get("/servers/status")
    assert response.status_code == 200
    data = response.json()
    assert "services" in data
    assert test_service_registration.server in data["services"]

@pytest.mark.asyncio
async def test_health_check_loop(dns_server_instance):
    async with dns_server_instance as server:
        # Register a service
        registration = ServiceRegistration(
            server="test_service",
            instance_id=1,
            port=8000
        )
        await server.register_service(registration)
        
        # Let health check run
        await asyncio.sleep(1)
        
        # Verify service status is being monitored
        instance = server.services["test_service"][0]
        assert instance.status in ["healthy", "unhealthy"]

@pytest.mark.asyncio
async def test_defense_system(dns_server_instance):
    async with dns_server_instance as server:
        # Register a service
        registration = ServiceRegistration(
            server="test_service",
            instance_id=1,
            port=8000
        )
        instance = await server.register_service(registration)
        
        # Test threat assessment
        threat = server.defense_system.assess_threat(instance)
        if threat:
            assert threat.threat_level in server.defense_system.threat_levels
            assert "test_service" in threat.affected_services

@pytest.mark.asyncio
async def test_api_defense_protocol(test_client):
    response = test_client.post("/defense/activate/lockdown")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "activated"
    assert data["protocol"] == "lockdown"

@pytest.mark.asyncio
async def test_service_not_found(dns_server_instance):
    async with dns_server_instance as server:
        with pytest.raises(HTTPException) as exc_info:
            await server.get_service("nonexistent_service")
        assert exc_info.value.status_code == 404

@pytest.mark.asyncio
async def test_api_service_not_found(test_client):
    response = test_client.get("/service/nonexistent_service")
    assert response.status_code == 404

if __name__ == "__main__":
    pytest.main(["-v"]) 