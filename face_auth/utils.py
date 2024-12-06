import json
import os
import threading
import time
import logging
import queue
import signal
from datetime import datetime, timedelta
import requests
from typing import Dict, Any

logger = logging.getLogger(__name__)

class DataManager:
    def __init__(self, data_dir: str = "user_data"):
        self.data_dir = data_dir
        self.write_queue = queue.Queue()
        self.users_cache = {}
        self.write_lock = threading.Lock()
        self.shutdown_event = threading.Event()
        self.load_users()
        
        # Start background writer thread
        self.writer_thread = threading.Thread(target=self._background_writer, daemon=True)
        self.writer_thread.start()

    def load_users(self):
        """Load users from JSON file into memory"""
        users_file = os.path.join(self.data_dir, 'users.json')
        if os.path.exists(users_file):
            with open(users_file, 'r') as f:
                self.users_cache = json.load(f)

    def queue_write(self, data: Dict[str, Any], sync_db: bool = True):
        """Queue data to be written to file"""
        self.write_queue.put((data, sync_db))

    def _background_writer(self):
        """Background thread for handling file writes"""
        while not self.shutdown_event.is_set() or not self.write_queue.empty():
            try:
                if not self.write_queue.empty():
                    data, sync_db = self.write_queue.get(timeout=1)
                    
                    # Update cache
                    self.users_cache.update(data)
                    
                    # Write to file with lock
                    with self.write_lock:
                        users_file = os.path.join(self.data_dir, 'users.json')
                        with open(users_file, 'w') as f:
                            json.dump(self.users_cache, f, indent=4)
                    
                    # Sync with database server if needed
                    if sync_db:
                        try:
                            requests.post(
                                'http://localhost:8000/sync_user',  # Adjust port as needed
                                json=data,
                                timeout=5
                            )
                        except Exception as e:
                            logger.error(f"Failed to sync with database server: {e}")
                    
                    self.write_queue.task_done()
                else:
                    time.sleep(1)  # Prevent busy waiting
                    
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in background writer: {e}")
                time.sleep(1)

    def shutdown(self):
        """Gracefully shutdown the writer thread"""
        self.shutdown_event.set()
        self.writer_thread.join()

class ServerManager:
    def __init__(self, data_manager: DataManager):
        self.data_manager = data_manager
        self.shutdown_time = datetime.now() + timedelta(hours=5, minutes=55)
        self.shutdown_thread = threading.Thread(target=self._shutdown_monitor, daemon=True)
        self.shutdown_thread.start()

    def _shutdown_monitor(self):
        """Monitor thread for graceful server shutdown"""
        while datetime.now() < self.shutdown_time:
            time.sleep(60)  # Check every minute
            
        logger.info("Initiating graceful shutdown")
        
        # Wait for all writes to complete
        self.data_manager.shutdown()
        
        # Send SIGTERM to the current process
        os.kill(os.getpid(), signal.SIGTERM)

def setup_server():
    """Setup the server with data manager and shutdown monitor"""
    data_dir = "user_data"
    os.makedirs(data_dir, exist_ok=True)
    
    data_manager = DataManager(data_dir)
    server_manager = ServerManager(data_manager)
    
    return data_manager, server_manager 