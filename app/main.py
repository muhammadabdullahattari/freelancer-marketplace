from fastapi import FastAPI
from app.routers.auth import router as Authrouter
from app.routers.user import router as Userrouter
from app.routers.contracts import router as Contractsrouter
from app.routers.freelancer import router as Freelancerrouter
from app.routers.jobs import router as Jobsrouter
from app.routers.milestones import router as Milestonesrouter
from app.routers.proposals import router as Proposalsrouter
from app.routers.reviews import router as Reviewsrouter
from app.routers.skills import router as Skillsrouter
from app.routers.sessions import router as Sessionsrouter
from app.routers.uploads import router as Uploadsrouter
from app.database import Base,engine
import app.models
from fastapi.exceptions import RequestValidationError, HTTPException 
from app.exceptions.handlers import http_exception_handler, validation_exception_handler, general_exception_handler
from app.core.startup import startup_event
from app.middleware.logging import RequestIDMiddleware, RequestLoggingMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.exceptions.handlers import setup_exception_handlers
from app.middleware.csrf import CSRFProtectionMiddleware

app = FastAPI(title="Freelancer Marketplace API")

app.add_middleware(RateLimitMiddleware, requests_per_minute=100)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(CSRFProtectionMiddleware)

setup_exception_handlers(app)

@app.on_event("startup")
async def on_startup():
    await startup_event()

app.add_exception_handler(HTTPException,http_exception_handler)
app.add_exception_handler(RequestValidationError,validation_exception_handler)
app.add_exception_handler(Exception,general_exception_handler)

app.include_router(Authrouter)
app.include_router(Userrouter)
app.include_router(Freelancerrouter)
app.include_router(Jobsrouter)
app.include_router(Skillsrouter)
app.include_router(Proposalsrouter)
app.include_router(Contractsrouter)
app.include_router(Milestonesrouter)
app.include_router(Reviewsrouter)
app.include_router(Sessionsrouter)
app.include_router(Uploadsrouter)

@app.get("/")
def root():
    return {"message": "API is running"}
