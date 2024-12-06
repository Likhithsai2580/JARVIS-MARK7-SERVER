import subprocess
import sys
import time
from pathlib import Path
import signal
import os

def start_servers():
    root_dir = Path(__file__).parent
    servers = []

    # Start all servers
    server_configs = [
        ("llm_server/llm_server.py", 8000),
        ("android_bridge_server/dist/index.js", 3000),
        ("codebrew/main.py", 8001),
        ("google_auth_services_server/app/main.py", 8002),
        ("openpaser_server/server.py", 8003),
        ("functional_server/api.py", 8004),
        ("main_server/main.py", 8080)
    ]

    for server_path, port in server_configs:
        if server_path.endswith('.js'):
            process = subprocess.Popen(
                ["node", server_path],
                cwd=root_dir
            )
        else:
            process = subprocess.Popen(
                [sys.executable, server_path],
                cwd=root_dir
            )
        servers.append(process)
        print(f"Started server {server_path} on port {port}")
        time.sleep(2)

    def cleanup(signum, frame):
        print("\nShutting down all servers...")
        for process in servers:
            process.terminate()
            process.wait()
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        cleanup(None, None)

if __name__ == "__main__":
    start_servers() 