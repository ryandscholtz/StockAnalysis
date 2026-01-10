#!/usr/bin/env python3
"""
Simple server runner for development
"""
import uvicorn
from app.main import app

if __name__ == "__main__":
    print("Starting Stock Analysis API server...")
    print("Server will be available at: http://localhost:8000")
    print("API documentation at: http://localhost:8000/docs")
    
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )