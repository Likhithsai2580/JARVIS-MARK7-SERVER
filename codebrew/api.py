import os
import sys
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import uvicorn
from datetime import datetime
import asyncio
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler
from cachetools import TTLCache
from dataclasses import dataclass
from llm.base import LLM
from llm._llmserver import Groq, LLAMA_32_90B_TEXT_PREVIEW
from main import CodeBrew, CodeBrewConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler('api.log', maxBytes=1024*1024, backupCount=5),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get environment variables with defaults
HOST = os.getenv('HOST', '0.0.0.0')
PORT = int(os.getenv('PORT', '8000'))
INSTANCE_ID = int(os.getenv('INSTANCE_ID', '0'))
MAX_INSTANCES = int(os.getenv('MAX_INSTANCES', '10'))
CACHE_TTL = int(os.getenv('CACHE_TTL', '3600'))  # 1 hour
MAX_CACHE_SIZE = int(os.getenv('MAX_CACHE_SIZE', '1000'))

@dataclass
class Instance:
    codebrew: CodeBrew
    last_used: datetime
    busy: bool = False

class QueryRequest(BaseModel):
    prompt: str
    api_key: str = Field(..., description="API key for authentication")
    verbose: bool = Field(False, description="Enable verbose output")
    keep_history: bool = Field(True, description="Keep conversation history")
    max_retries: int = Field(3, description="Maximum number of retry attempts")
    timeout: float = Field(30.0, description="Execution timeout in seconds")

class QueryResponse(BaseModel):
    success: bool
    output: str
    execution_time: float
    timestamp: datetime

class HealthCheck(BaseModel):
    status: str
    timestamp: datetime
    instance_id: int
    busy: bool
    active_instances: int
    cache_size: int
    uptime: float

# Initialize FastAPI with lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(f"Starting API server instance {INSTANCE_ID}")
    yield
    # Shutdown
    logger.info(f"Shutting down API server instance {INSTANCE_ID}")
    await cleanup_instances()

app = FastAPI(
    title=f"CodeBrew API Instance {INSTANCE_ID}",
    description="API for CodeBrew code execution and LLM interaction",
    version="1.0.0",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Store LLM instances and response cache
instances: Dict[str, Instance] = {}
response_cache = TTLCache(maxsize=MAX_CACHE_SIZE, ttl=CACHE_TTL)
start_time = datetime.now()

async def cleanup_instances():
    """Clean up inactive instances."""
    current_time = datetime.now()
    to_remove = []
    for api_key, instance in instances.items():
        if (current_time - instance.last_used).total_seconds() > CACHE_TTL:
            to_remove.append(api_key)
    
    for api_key in to_remove:
        instance = instances.pop(api_key)
        instance.codebrew.cleanup()
        logger.info(f"Cleaned up inactive instance for API key: {api_key[:8]}...")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log requests and handle errors."""
    start_time = datetime.now()
    try:
        response = await call_next(request)
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"{request.method} {request.url.path} completed in {duration:.2f}s")
        return response
    except Exception as e:
        logger.error(f"Request failed: {str(e)}")
        return Response(
            content=str(e),
            status_code=500
        )

@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Enhanced health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(),
        "instance_id": INSTANCE_ID,
        "busy": any(instance.busy for instance in instances.values()),
        "active_instances": len(instances),
        "cache_size": len(response_cache),
        "uptime": (datetime.now() - start_time).total_seconds()
    }

@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """Execute query with improved error handling and caching."""
    try:
        # Check cache
        cache_key = f"{request.api_key}:{request.prompt}"
        cached_response = response_cache.get(cache_key)
        if cached_response:
            logger.info("Returning cached response")
            return cached_response

        # Get or create instance
        instance = instances.get(request.api_key)
        if not instance:
            if len(instances) >= MAX_INSTANCES:
                await cleanup_instances()
            
            llm = Groq(
                LLAMA_32_90B_TEXT_PREVIEW,
                apiKey=request.api_key
            )
            config = CodeBrewConfig(
                max_retries=request.max_retries,
                keep_history=request.keep_history,
                verbose=request.verbose,
                timeout=request.timeout
            )
            codebrew = CodeBrew(llm=llm, config=config)
            instance = Instance(codebrew=codebrew, last_used=datetime.now())
            instances[request.api_key] = instance

        if instance.busy:
            raise HTTPException(
                status_code=429,
                detail="Instance is busy processing another request"
            )

        # Execute query
        instance.busy = True
        start_time = datetime.now()
        try:
            output = await instance.codebrew.run(request.prompt)
            execution_time = (datetime.now() - start_time).total_seconds()
            
            response = QueryResponse(
                success=True,
                output=output,
                execution_time=execution_time,
                timestamp=datetime.now()
            )
            
            # Cache successful responses
            response_cache[cache_key] = response
            return response

        finally:
            instance.busy = False
            instance.last_used = datetime.now()

    except Exception as e:
        logger.error(f"Query execution failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@app.delete("/cache")
async def clear_cache():
    """Clear response cache."""
    response_cache.clear()
    return {"message": "Cache cleared"}

@app.delete("/instances/{api_key}")
async def remove_instance(api_key: str):
    """Remove specific instance."""
    if api_key in instances:
        instance = instances.pop(api_key)
        instance.codebrew.cleanup()
        return {"message": f"Instance removed for API key: {api_key[:8]}..."}
    raise HTTPException(status_code=404, detail="Instance not found")

if __name__ == "__main__":
    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        log_level="info",
        reload=os.getenv('ENV') == 'development'
    ) 