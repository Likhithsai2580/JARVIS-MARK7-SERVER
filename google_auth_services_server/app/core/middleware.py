import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Add request ID to request state
        request.state.request_id = request_id
        
        # Log request
        logger.info(f"Request {request_id} started: {request.method} {request.url}")
        
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(process_time)
            
            # Log response
            logger.info(
                f"Request {request_id} completed: {response.status_code} "
                f"Process Time: {process_time:.3f}s"
            )
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"Request {request_id} failed: {str(e)} "
                f"Process Time: {process_time:.3f}s"
            )
            raise 