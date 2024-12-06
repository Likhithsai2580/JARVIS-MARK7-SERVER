import subprocess
import sys
import time
import signal
import logging
import asyncio
from pathlib import Path
from typing import List, Optional, Dict
from dns_server.dns_client import DNSClient, ServiceConfig
import random
import os

class ServerManager:
    def __init__(self):
        # Get the root directory
        self.root_dir = Path(__file__).parent
        # Initialize logging
        self.setup_logging()
        # Store server processes
        self.servers: List[subprocess.Popen] = []
        # DNS client for service registration
        self.dns_client = DNSClient()
        # Server ports mapping
        self.server_ports: Dict[str, int] = {
            "llm": 5000,
            "main": 5001,
            "functional": 5002,
            "face_auth": 5003,
            "database": 5004,
            "android_bridge": 5005,
            "google_auth": 5006,
            "openparser": 5007
        }

    def setup_logging(self) -> None:
        """Configure logging for the server manager"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(self.root_dir / 'server.log')
            ]
        )

    async def register_with_dns(self, server_name: str, port: int) -> None:
        """Register a server with the DNS service"""
        config = ServiceConfig(
            service_type=server_name,
            instance_id=random.randint(1000, 9999),
            port=port,
            metadata={
                "start_time": time.time(),
                "version": "1.0"
            }
        )
        if await self.dns_client.register_service(config):
            logging.info(f"Registered {server_name} with DNS server")
        else:
            logging.error(f"Failed to register {server_name} with DNS server")

    def start_server(self, script_path: str, name: str) -> Optional[subprocess.Popen]:
        """Start a server process with error handling"""
        try:
            port = self.server_ports.get(name.lower(), 5000)
            process = subprocess.Popen(
                [sys.executable, script_path],
                cwd=self.root_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env={**os.environ, "PORT": str(port)}
            )
            self.servers.append(process)
            logging.info(f"Started {name} server (PID: {process.pid}) on port {port}")
            
            # Register with DNS asynchronously
            asyncio.create_task(self.register_with_dns(name.lower(), port))
            return process
        except Exception as e:
            logging.error(f"Failed to start {name} server: {str(e)}")
            return None

    def check_server_health(self, process: subprocess.Popen, name: str) -> bool:
        """Check if a server process is healthy"""
        if process.poll() is not None:
            logging.error(f"{name} server crashed (exit code: {process.returncode})")
            # Capture any error output
            _, stderr = process.communicate()
            if stderr:
                logging.error(f"{name} server error: {stderr}")
            return False
        return True

    async def shutdown_servers(self) -> None:
        """Gracefully shutdown all server processes"""
        logging.info("Shutting down servers...")
        # Close DNS client
        await self.dns_client.close()
        
        for process in self.servers:
            if process.poll() is None:  # If process is still running
                process.terminate()
                try:
                    process.wait(timeout=5)  # Wait up to 5 seconds
                except subprocess.TimeoutExpired:
                    logging.warning(f"Server (PID: {process.pid}) didn't terminate, forcing...")
                    process.kill()  # Force kill if it doesn't terminate
                    process.wait()

    async def start_servers(self) -> None:
        """Start and monitor all servers"""
        # Start all servers
        servers_to_start = [
            ("llm_server/llm_server.py", "LLM"),
            ("main_server/main_server.py", "Main"),
            ("functional_server/functional_server.py", "Functional"),
            ("face_auth/face_auth_server.py", "FaceAuth"),
            ("database_server/database_server.py", "Database"),
            ("android_bridge_server/android_bridge_server.py", "AndroidBridge"),
            ("google_auth_services_server/google_auth_server.py", "GoogleAuth"),
            ("openpaser_server/openparser_server.py", "OpenParser")
        ]

        running_servers = []
        for script_path, name in servers_to_start:
            server = self.start_server(script_path, name)
            if server:
                running_servers.append((server, name))

        # Setup signal handlers for graceful shutdown
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, lambda s, f: asyncio.create_task(self.shutdown_servers()))

        try:
            while True:
                # Monitor server health
                for server, name in running_servers:
                    if not self.check_server_health(server, name):
                        return
                await asyncio.sleep(5)  # Check every 5 seconds
        except KeyboardInterrupt:
            pass
        finally:
            await self.shutdown_servers()

async def main():
    manager = ServerManager()
    await manager.start_servers()

if __name__ == "__main__":
    asyncio.run(main()) 