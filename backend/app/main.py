"""
FastAPI application entry point for Stock Analysis Tool
"""
from dotenv import load_dotenv
import os

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

app = FastAPI(
    title="Stock Analysis API",
    description="Charlie Munger methodology stock analysis API",
    version="1.0.0"
)

# Custom middleware to ensure CORS headers on all responses
class CORSResponseMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Get origin from request
        origin = request.headers.get("origin")
        allowed_origins = ["http://localhost:3000", "http://localhost:3001", "http://localhost:3003"]
        
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
    allowed_origins = ["http://localhost:3000", "http://localhost:3001", "http://localhost:3003"]
    
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
    allowed_origins = ["http://localhost:3000", "http://localhost:3001", "http://localhost:3003"]
    
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


@app.get("/")
async def root():
    return {"message": "Stock Analysis API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}

