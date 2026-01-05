"""
FastAPI application entry point for Stock Analysis Tool
"""
from dotenv import load_dotenv
import os
import asyncio
import logging

# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import Message
from app.api.routes import router
from datetime import datetime

logger = logging.getLogger(__name__)

# Generate build timestamp in yymmdd-hh:mm format
BUILD_TIMESTAMP = datetime.now().strftime("%y%m%d-%H:%M")

app = FastAPI(
    title="Stock Analysis API",
    description="Value investing stock analysis API",
    version="1.0.0"
)

# Custom middleware to ensure CORS headers on all responses
class CORSResponseMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Get origin from request
        origin = request.headers.get("origin")
        allowed_origins = ["http://localhost:3000", "http://localhost:3001", "http://localhost:3003", "http://127.0.0.1:3000", "http://127.0.0.1:3001", "http://127.0.0.1:3003"]
        
        # Add CORS headers if origin is allowed
        if origin in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, HEAD, PATCH"
            response.headers["Access-Control-Allow-Headers"] = "*"
            response.headers["Access-Control-Expose-Headers"] = "*"
        
        return response

# Add custom CORS middleware first (before CORSMiddleware)
app.add_middleware(CORSResponseMiddleware)

# Configure CORS - must be added before routes
app.add_middleware(
    CORSMiddleware,
    # Allow local frontend dev servers
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001", 
        "http://localhost:3003",
        "http://127.0.0.1:3000",  # Add 127.0.0.1 variants
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3003",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# Exception handler to ensure CORS headers on errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Ensure CORS headers are present even on unhandled exceptions"""
    import traceback
    
    # Get origin from request
    origin = request.headers.get("origin")
    allowed_origins = ["http://localhost:3000", "http://localhost:3001", "http://localhost:3003", "http://127.0.0.1:3000", "http://127.0.0.1:3001", "http://127.0.0.1:3003"]
    
    headers = {}
    if origin in allowed_origins:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
        headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, HEAD, PATCH"
        headers["Access-Control-Allow-Headers"] = "*"
        headers["Access-Control-Expose-Headers"] = "*"
    
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
        headers=headers
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Ensure CORS headers on HTTP exceptions"""
    origin = request.headers.get("origin")
    allowed_origins = ["http://localhost:3000", "http://localhost:3001", "http://localhost:3003", "http://127.0.0.1:3000", "http://127.0.0.1:3001", "http://127.0.0.1:3003"]
    
    headers = {}
    if origin in allowed_origins:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
        headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, HEAD, PATCH"
        headers["Access-Control-Allow-Headers"] = "*"
        headers["Access-Control-Expose-Headers"] = "*"
    
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=headers
    )

# Include API routes
app.include_router(router, prefix="/api")

# Include optimized routes with different prefix to avoid conflicts
from app.api.optimized_routes import router as optimized_router
app.include_router(optimized_router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "Stock Analysis API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


# Background task for EC2 auto-stop monitoring
async def ec2_idle_monitor():
    """Background task to monitor EC2 instance idle time and stop if idle"""
    try:
        from app.utils.ec2_manager import get_ec2_manager
        ec2_manager = get_ec2_manager()
        
        if not ec2_manager.auto_stop_enabled:
            logger.info("EC2 auto-stop is disabled, skipping idle monitoring")
            return
        
        logger.info("Starting EC2 idle monitor background task")
        
        while True:
            try:
                await ec2_manager.check_and_stop_if_idle()
            except Exception as e:
                logger.error(f"Error in EC2 idle monitor: {e}")
            
            # Check every minute
            await asyncio.sleep(60)
    except Exception as e:
        logger.error(f"Failed to start EC2 idle monitor: {e}")


@app.on_event("startup")
async def startup_event():
    """Start background tasks on application startup"""
    # Start EC2 idle monitor if enabled
    auto_stop_enabled = os.getenv("EC2_AUTO_STOP", "true").lower() == "true"
    if auto_stop_enabled:
        try:
            asyncio.create_task(ec2_idle_monitor())
            logger.info("EC2 auto-stop monitor started")
        except Exception as e:
            logger.warning(f"Failed to start EC2 auto-stop monitor: {e}")

