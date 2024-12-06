from prometheus_client import Counter, Histogram, Gauge
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import time

# Define metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

active_requests = Gauge(
    'active_requests',
    'Number of active requests'
)

rate_limit_hits = Counter(
    'rate_limit_hits_total',
    'Number of rate limit hits',
    ['client_ip']
)

auth_failures = Counter(
    'auth_failures_total',
    'Number of authentication failures',
    ['reason']
)

class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Increment active requests
        active_requests.inc()
        
        # Start timer
        start_time = time.time()
        
        try:
            # Process request
            response = await call_next(request)
            
            # Record metrics
            duration = time.time() - start_time
            endpoint = request.url.path
            method = request.method
            status = response.status_code
            
            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status=status
            ).inc()
            
            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
            
            return response
            
        except Exception as e:
            # Record error metrics
            http_requests_total.labels(
                method=request.method,
                endpoint=request.url.path,
                status=500
            ).inc()
            raise
            
        finally:
            # Decrement active requests
            active_requests.dec()

def record_auth_failure(reason: str):
    """Record authentication failure metrics"""
    auth_failures.labels(reason=reason).inc()

def record_rate_limit_hit(client_ip: str):
    """Record rate limit hit metrics"""
    rate_limit_hits.labels(client_ip=client_ip).inc() 