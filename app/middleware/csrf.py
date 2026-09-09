from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    
    PROTECTED_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
    CSRF_EXEMPT_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}
    
    async def dispatch(self, request: Request, call_next):
        if request.method not in self.PROTECTED_METHODS:
            return await call_next(request)
        
        if request.url.path in self.CSRF_EXEMPT_PATHS:
            return await call_next(request)
        
        if request.headers.get("authorization"):
            return await call_next(request)
        
        return await call_next(request)