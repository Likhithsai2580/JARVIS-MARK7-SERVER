import aiohttp
import json
from typing import Optional, Dict, Any
from datetime import datetime

class DatabaseLoggerClient:
    def __init__(self, server_name: str, database_url: str):
        self.server_name = server_name
        self.database_url = database_url.rstrip("/")
        self.session = None
    
    async def connect(self):
        if not self.session:
            self.session = aiohttp.ClientSession()
    
    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None
    
    async def log(
        self,
        message: str,
        log_type: str = "info",
        details: Optional[Dict[str, Any]] = None
    ):
        await self.connect()
        try:
            async with self.session.post(
                f"{self.database_url}/logs/",
                json={
                    "server_name": self.server_name,
                    "log_type": log_type,
                    "message": message,
                    "details": details
                }
            ) as response:
                if response.status != 200:
                    print(f"Failed to log to database: {await response.text()}")
        except Exception as e:
            print(f"Error logging to database: {str(e)}") 