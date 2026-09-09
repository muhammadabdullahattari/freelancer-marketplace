from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import logging
import time
import uuid
from typing import Callable

logger = logging.getLogger(__name__)

class RequestIDMiddleware(BaseHTTPMiddleware):
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = getattr(request.state, 'request_id', 'unknown')
        
        logger.info(
            f"[{request_id}] {request.method} {request.url.path}",
            extra={"method": request.method,"path": request.url.path,"query": str(request.url.query),
                   "client_ip": request.client.host if request.client else "unknown"})
        
        start_time = time.time()
        
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            logger.info(
                f"[{request_id}] {request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s",
                extra={"status_code": response.status_code,"duration_ms": process_time * 1000})
            
            response.headers["X-Process-Time"] = str(process_time)
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(f"[{request_id}] {request.method} {request.url.path} - Error - {process_time:.3f}s",
                extra={"error": str(e), "duration_ms": process_time * 1000},exc_info=True)
            raise