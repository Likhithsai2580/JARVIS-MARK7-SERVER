from typing import Optional, Any
import json
from datetime import timedelta
import aioredis
from functools import wraps
from fastapi import Request
import hashlib

class Cache:
    def __init__(self, redis_url: str = "redis://localhost"):
        self.redis = aioredis.from_url(redis_url, decode_responses=True)

    async def get(self, key: str) -> Optional[str]:
        """Get value from cache"""
        return await self.redis.get(key)

    async def set(self, key: str, value: Any, expire: int = 300):
        """Set value in cache with expiration in seconds"""
        await self.redis.set(key, value, ex=expire)

    async def delete(self, key: str):
        """Delete value from cache"""
        await self.redis.delete(key)

    def cache_response(self, expire: int = 300):
        """Decorator to cache endpoint responses"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Get request object
                request = next((arg for arg in args if isinstance(arg, Request)), None)
                if not request:
                    return await func(*args, **kwargs)

                # Create cache key from request details
                cache_key = self._create_cache_key(request)
                
                # Try to get from cache
                cached_response = await self.get(cache_key)
                if cached_response:
                    return json.loads(cached_response)

                # Get fresh response
                response = await func(*args, **kwargs)
                
                # Cache response
                await self.set(
                    cache_key,
                    json.dumps(response),
                    expire
                )
                
                return response
            return wrapper
        return decorator

    def _create_cache_key(self, request: Request) -> str:
        """Create a unique cache key from request details"""
        key_parts = [
            request.method,
            str(request.url),
            request.headers.get("authorization", ""),
        ]
        return hashlib.md5("|".join(key_parts).encode()).hexdigest()

# Initialize cache
cache = Cache()

# Decorator for token caching
def cache_token(func):
    """Decorator to cache tokens with user-specific keys"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Get user identifier from kwargs or args
        user_id = kwargs.get("user_id") or next(
            (arg for arg in args if isinstance(arg, str)), None
        )
        
        if not user_id:
            return await func(*args, **kwargs)

        cache_key = f"token:{user_id}"
        
        # Try to get from cache
        cached_token = await cache.get(cache_key)
        if cached_token:
            return json.loads(cached_token)

        # Get fresh token
        token = await func(*args, **kwargs)
        
        # Cache token with expiration
        await cache.set(
            cache_key,
            json.dumps(token),
            expire=3600  # 1 hour
        )
        
        return token
    return wrapper 