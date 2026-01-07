"""
FastAPI application entry point for Stock Analysis Tool
Modern architecture with dependency injection and structured logging
"""
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import the modern FastAPI app
from app.core.app import app

# Export the app for uvicorn
__all__ = ["app"]

