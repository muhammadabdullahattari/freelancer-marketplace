from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import asyncio
import logging

logger = logging.getLogger(__name__)

class RateLimitMiddleware(BaseHTTPMiddleware):
    
    def __init__(self, app, requests_per_minute: int = 100):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_history = defaultdict(list)
        self.cleanup_interval = 60  # seconds
        asyncio.create_task(self._cleanup_old_requests())
    
    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/health":
            return await call_next(request)
        
        identifier = self._get_identifier(request)
        
        now = datetime.now(timezone.utc)
        minute_ago = now - timedelta(minutes=1)
        
        self.request_history[identifier] = [
            req_time for req_time in self.request_history[identifier]
            if req_time > minute_ago]
        
        if len(self.request_history[identifier]) >= self.requests_per_minute:
            logger.warning(f"Rate limit exceeded for {identifier}")
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": f"Too many requests. Maximum {self.requests_per_minute} requests per minute",
                        "status": 429
                    }
                }
            )
        
        self.request_history[identifier].append(now)
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(self.requests_per_minute - len(self.request_history[identifier]))
        return response
    
    def _get_identifier(self, request: Request) -> str:
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return f"user:{auth_header[7:20]}"  # First 20 chars of token
        
        return f"ip:{request.client.host if request.client else 'unknown'}"
    
    async def _cleanup_old_requests(self):
        while True:
            await asyncio.sleep(self.cleanup_interval)
            now = datetime.now(timezone.utc)
            hour_ago = now - timedelta(hours=1)
            
            for identifier in list(self.request_history.keys()):
                self.request_history[identifier] = [
                    req_time for req_time in self.request_history[identifier] if req_time > hour_ago]
                
                if not self.request_history[identifier]:
                    del self.request_history[identifier]