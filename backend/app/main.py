"""
FastAPI application entry point for Stock Analysis Tool
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router

app = FastAPI(
    title="Stock Analysis API",
    description="Charlie Munger methodology stock analysis API",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    # Allow local frontend dev servers
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3003",
    ],  # Add production URL later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "Stock Analysis API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}

