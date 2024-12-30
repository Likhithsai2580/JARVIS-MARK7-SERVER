import httpx
import asyncio
from typing import Dict, Optional
import time
import os
from dataclasses import dataclass
import json

@dataclass
class ServiceConfig:
    service_type: str
    instance_id: int
    port: int
    metadata: Dict = None
    host: str = None
    busy: bool = False

class DNSClient:
    def __init__(self, dns_url: str = None, base_port: int = None):
        self.dns_url = dns_url or os.getenv("DNS_SERVER_URL", "https://jarvis-dns.netlify.app")
        self.service_config: Optional[ServiceConfig] = None
        self.heartbeat_task = None
        self.health_check_task = None
        self._client = httpx.AsyncClient(timeout=10.0)
        self.base_port = base_port or int(os.getenv("BASE_PORT", 5000))
        self.host = os.getenv("HOST", "localhost")
        self.busy = False

    async def register_service(self, config: ServiceConfig) -> bool:
        """Register the service with DNS server"""
        self.service_config = config
        self.service_config.host = self.host
        try:
            response = await self._client.post(
                f"{self.dns_url}/register",
                json={
                    "server": config.service_type,
                    "instance_id": config.instance_id,
                    "port": config.port,
                    "host": config.host,
                    "metadata": config.metadata or {}
                }
            )
            if response.status_code == 200:
                # Start monitoring tasks
                if not self.heartbeat_task:
                    self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
                if not self.health_check_task:
                    self.health_check_task = asyncio.create_task(self._health_check_loop())
                return True
            return False
        except Exception as e:
            print(f"Registration error: {str(e)}")
            return False

    async def discover_service(self, service_type: str, requirements: Dict = None) -> Dict:
        """Discover a non-busy service instance"""
        try:
            response = await self._client.post(
                f"{self.dns_url}/discover",
                json={
                    "service_type": service_type,
                    "requirements": {
                        **(requirements or {}),
                        "busy": False  # Only discover non-busy instances
                    }
                }
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Service discovery error: {str(e)}")
            return None

    async def update_status(self, busy: bool = None):
        """Update the service's busy status"""
        if busy is not None:
            self.busy = busy
        if self.service_config:
            try:
                await self._client.post(
                    f"{self.dns_url}/status",
                    json={
                        "server": self.service_config.service_type,
                        "instance_id": self.service_config.instance_id,
                        "status": "active",
                        "busy": self.busy
                    }
                )
            except Exception as e:
                print(f"Status update error: {str(e)}")

    async def _health_check_loop(self):
        """Monitor service health and busy status"""
        while True:
            try:
                # Get health status from local service
                try:
                    response = await self._client.get(
                        f"http://{self.host}:{self.service_config.port}/health",
                        timeout=5.0
                    )
                    if response.status_code == 200:
                        health_data = response.json()
                        await self.update_status(health_data.get("busy", False))
                    else:
                        await self.update_status(True)  # Mark as busy if health check fails
                except:
                    # Report instance as dead if health check fails
                    await self._client.post(
                        f"{self.dns_url}/status",
                        json={
                            "server": self.service_config.service_type,
                            "instance_id": self.service_config.instance_id,
                            "status": "dead"
                        }
                    )
                    break  # Stop health check loop if instance is dead
            except Exception as e:
                print(f"Health check error: {str(e)}")
            await asyncio.sleep(60)  # Check every minute

    async def _heartbeat_loop(self):
        """Send periodic heartbeats with status"""
        while True:
            try:
                if self.service_config:
                    await self._client.post(
                        f"{self.dns_url}/heartbeat",
                        json={
                            "service_type": self.service_config.service_type,
                            "instance_id": self.service_config.instance_id,
                            "host": self.service_config.host,
                            "port": self.service_config.port,
                            "busy": self.busy,
                            "metrics": {
                                "timestamp": time.time(),
                                "status": "active"
                            }
                        }
                    )
            except Exception as e:
                print(f"Heartbeat error: {str(e)}")
            await asyncio.sleep(10)  # Heartbeat every 10 seconds

    async def close(self):
        """Clean up resources and mark instance as dead"""
        try:
            if self.service_config:
                await self._client.post(
                    f"{self.dns_url}/status",
                    json={
                        "server": self.service_config.service_type,
                        "instance_id": self.service_config.instance_id,
                        "status": "dead"
                    }
                )
        except:
            pass

        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass

        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass

        await self._client.aclose()