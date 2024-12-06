from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime, timedelta
import time
from collections import defaultdict
import threading
import re
from typing import List, Optional
from app.core.metrics import record_rate_limit_hit

class SecurityConfig:
    def __init__(
        self,
        allowed_hosts: List[str] = None,
        allowed_paths: List[str] = None,
        blocked_ips: List[str] = None,
        max_body_size: int = 10 * 1024 * 1024,  # 10MB
        max_uri_length: int = 2048
    ):
        self.allowed_hosts = allowed_hosts or ["localhost", "127.0.0.1"]
        self.allowed_paths = allowed_paths or [r".*"]
        self.blocked_ips = set(blocked_ips or [])
        self.max_body_size = max_body_size
        self.max_uri_length = max_uri_length

class RateLimiter:
    def __init__(self, requests_per_minute: int = 60, burst_size: int = 10):
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.requests = defaultdict(list)
        self.lock = threading.Lock()

    def is_allowed(self, client_ip: str) -> bool:
        now = time.time()
        minute_ago = now - 60

        with self.lock:
            # Remove old requests
            self.requests[client_ip] = [
                req_time for req_time in self.requests[client_ip]
                if req_time > minute_ago
            ]

            # Check burst limit
            if len(self.requests[client_ip]) >= self.burst_size:
                time_diff = now - self.requests[client_ip][-self.burst_size]
                if time_diff < 1:  # Less than 1 second
                    record_rate_limit_hit(client_ip)
                    return False

            # Check rate limit
            if len(self.requests[client_ip]) >= self.requests_per_minute:
                record_rate_limit_hit(client_ip)
                return False

            # Add new request
            self.requests[client_ip].append(now)
            return True

class SecurityMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        config: Optional[SecurityConfig] = None,
        rate_limiter: Optional[RateLimiter] = None
    ):
        super().__init__(app)
        self.config = config or SecurityConfig()
        self.rate_limiter = rate_limiter or RateLimiter()

    async def dispatch(self, request: Request, call_next):
        # Get client IP
        client_ip = request.client.host

        # Check blocked IPs
        if client_ip in self.config.blocked_ips:
            raise HTTPException(
                status_code=403,
                detail="Access denied"
            )

        # Check allowed hosts
        host = request.headers.get("host", "").split(":")[0]
        if host not in self.config.allowed_hosts:
            raise HTTPException(
                status_code=403,
                detail="Invalid host"
            )

        # Check URI length
        if len(str(request.url)) > self.config.max_uri_length:
            raise HTTPException(
                status_code=414,
                detail="URI too long"
            )

        # Check allowed paths
        path = request.url.path
        if not any(re.match(pattern, path) for pattern in self.config.allowed_paths):
            raise HTTPException(
                status_code=404,
                detail="Path not found"
            )

        # Check rate limit
        if not self.rate_limiter.is_allowed(client_ip):
            raise HTTPException(
                status_code=429,
                detail="Too many requests"
            )

        # Check body size for POST/PUT requests
        if request.method in ["POST", "PUT"]:
            body_size = int(request.headers.get("content-length", 0))
            if body_size > self.config.max_body_size:
                raise HTTPException(
                    status_code=413,
                    detail="Request entity too large"
                )

        # Add security headers
        response = await call_next(request)
        response.headers.update({
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self'; "
                "connect-src 'self' https:;"
            ),
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": (
                "accelerometer=(), "
                "camera=(), "
                "geolocation=(), "
                "gyroscope=(), "
                "magnetometer=(), "
                "microphone=(), "
                "payment=(), "
                "usb=()"
            )
        })
        
        return response 