from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi import Request, HTTPException,FastAPI
from fastapi.encoders import jsonable_encoder
from app.core.errors import APIException
from datetime import datetime, timezone
import logging

async def http_exception_handler( request: Request, exc: HTTPException):

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "status_code": exc.status_code,
            "message": exc.detail,
            "data": None
        }
    )
    
async def validation_exception_handler( request: Request, exc: RequestValidationError):

    return JSONResponse(
        status_code=422,
        content=jsonable_encoder(
            {
                "success": False,
                "status_code": 422,
                "message": "Validation failed",
                "errors": exc.errors(),
            }
        ),
    )
    
async def general_exception_handler(
    request: Request,
    exc: Exception
):

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "status_code": 500,
            "message": "Internal Server Error"
        }
    )

logger = logging.getLogger(__name__)

def setup_exception_handlers(app: FastAPI):
    
    @app.exception_handler(APIException)
    async def api_exception_handler(request: Request, exc: APIException):
        request_id = getattr(request.state, 'request_id', None)
        exc.request_id = request_id
        
        return JSONResponse(status_code=exc.status_code,content=exc.to_dict())
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, 'request_id', 'unknown')
        
        logger.error(f"[{request_id}] Unhandled exception: {str(exc)}",exc_info=True)
        
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "status": 500,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "request_id": request_id
                }
            }
        )