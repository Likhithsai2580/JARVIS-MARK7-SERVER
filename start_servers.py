import subprocess
import sys
import time
import signal
import logging
from pathlib import Path
from typing import List, Optional

class ServerManager:
    def __init__(self):
        # Get the root directory
        self.root_dir = Path(__file__).parent
        # Initialize logging
        self.setup_logging()
        # Store server processes
        self.servers: List[subprocess.Popen] = []

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

    def start_server(self, script_path: str, name: str) -> Optional[subprocess.Popen]:
        """Start a server process with error handling"""
        try:
            process = subprocess.Popen(
                [sys.executable, script_path],
                cwd=self.root_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            self.servers.append(process)
            logging.info(f"Started {name} server (PID: {process.pid})")
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

    def shutdown_servers(self) -> None:
        """Gracefully shutdown all server processes"""
        logging.info("Shutting down servers...")
        for process in self.servers:
            if process.poll() is None:  # If process is still running
                process.terminate()
                try:
                    process.wait(timeout=5)  # Wait up to 5 seconds
                except subprocess.TimeoutExpired:
                    logging.warning(f"Server (PID: {process.pid}) didn't terminate, forcing...")
                    process.kill()  # Force kill if it doesn't terminate
                    process.wait()

    def start_servers(self) -> None:
        """Start and monitor all servers"""
        # Start LLM server
        llm_server = self.start_server("llm_server/llm_server.py", "LLM")
        if not llm_server:
            return

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, lambda sig, frame: self.shutdown_servers())
        signal.signal(signal.SIGTERM, lambda sig, frame: self.shutdown_servers())

        try:
            while True:
                # Monitor server health
                if not self.check_server_health(llm_server, "LLM"):
                    break
                time.sleep(5)  # Check every 5 seconds
        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown_servers()

def main():
    manager = ServerManager()
    manager.start_servers()

if __name__ == "__main__":
    main() 