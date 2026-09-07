from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi import Request, HTTPException
from fastapi.encoders import jsonable_encoder

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