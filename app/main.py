from fastapi import FastAPI
from app.routers.auth import router as Authrouter
from app.routers.user import router as Userrouter
from app.database import Base,engine
import app.models
from fastapi.exceptions import RequestValidationError, HTTPException 
from app.exceptions.handlers import http_exception_handler, validation_exception_handler, general_exception_handler
from app.core.startup import startup_event

app = FastAPI(title="Freelancer Marketplace API")

@app.on_event("startup")
async def on_startup():
    await startup_event()

app.add_exception_handler(HTTPException,http_exception_handler)
app.add_exception_handler(RequestValidationError,validation_exception_handler)
app.add_exception_handler(Exception,general_exception_handler)

app.include_router(Authrouter)
app.include_router(Userrouter)

@app.get("/")
def root():
    return {"message": "API is running"}
