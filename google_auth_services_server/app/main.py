from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.v1.endpoints import router as api_router
from app.core.config import settings
from app.core.middleware import RequestLoggingMiddleware
from app.core.security import SecurityMiddleware, RateLimiter, SecurityConfig
from app.core.metrics import MetricsMiddleware
from app.core.cache import Cache
from datetime import datetime
import structlog
from prometheus_client import make_asgi_app

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()

# Initialize cache
cache = Cache(redis_url=settings.REDIS_URL)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Mount metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(MetricsMiddleware)
app.add_middleware(
    SecurityMiddleware,
    config=SecurityConfig(
        allowed_hosts=["localhost", "127.0.0.1"],
        max_body_size=10 * 1024 * 1024,  # 10MB
        max_uri_length=2048
    ),
    rate_limiter=RateLimiter(
        requests_per_minute=100,
        burst_size=20
    )
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.error(
        "http_error",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
        request_id=getattr(request.state, "request_id", None)
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "request_id": getattr(request.state, "request_id", None)
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(
        "internal_error",
        error=str(exc),
        path=request.url.path,
        request_id=getattr(request.state, "request_id", None)
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "request_id": getattr(request.state, "request_id", None)
        }
    )

@app.get("/")
async def root():
    return {
        "message": "Welcome to Google Auth Service",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "openapi_url": f"{settings.API_V1_STR}/openapi.json",
        "metrics_url": "/metrics"
    }

@app.get("/health")
@cache.cache_response(expire=60)
async def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "cache": await cache.get("health_check") is not None
    } 