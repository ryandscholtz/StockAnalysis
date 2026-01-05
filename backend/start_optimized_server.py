#!/usr/bin/env python3
"""
Optimized server startup with multiple workers and performance tuning
"""
import uvicorn
import multiprocessing
import os
from pathlib import Path

def get_optimal_workers():
    """Calculate optimal number of workers based on CPU cores"""
    cpu_count = multiprocessing.cpu_count()
    
    # For I/O bound applications like this one, use more workers
    # Formula: (2 x CPU cores) + 1, but cap at 8 for development
    optimal_workers = min((2 * cpu_count) + 1, 8)
    
    # Allow override via environment variable
    env_workers = os.getenv("UVICORN_WORKERS")
    if env_workers:
        try:
            return int(env_workers)
        except ValueError:
            pass
    
    return optimal_workers

def main():
    """Start the optimized server"""
    
    # Server configuration
    config = {
        "app": "app.main:app",
        "host": "0.0.0.0",
        "port": 8000,
        "workers": get_optimal_workers(),
        "worker_class": "uvicorn.workers.UvicornWorker",
        "reload": False,  # Disable reload in production
        "access_log": True,
        "log_level": "info",
        
        # Performance optimizations
        "loop": "asyncio",  # Use asyncio event loop
        "http": "httptools",  # Use httptools for better performance
        "ws_ping_interval": 20,
        "ws_ping_timeout": 20,
        
        # Connection limits
        "limit_concurrency": 1000,
        "limit_max_requests": 10000,
        "timeout_keep_alive": 5,
        
        # SSL (if certificates are available)
        # "ssl_keyfile": "path/to/keyfile.pem",
        # "ssl_certfile": "path/to/certfile.pem",
    }
    
    # Development mode adjustments
    if os.getenv("ENVIRONMENT", "development") == "development":
        config.update({
            "reload": True,
            "workers": 1,  # Single worker for development to enable reload
            "log_level": "debug"
        })
        print("🔧 Starting in DEVELOPMENT mode with auto-reload")
    else:
        print(f"🚀 Starting in PRODUCTION mode with {config['workers']} workers")
    
    print(f"📊 Server configuration:")
    print(f"   - Workers: {config['workers']}")
    print(f"   - Host: {config['host']}:{config['port']}")
    print(f"   - Concurrency limit: {config['limit_concurrency']}")
    print(f"   - Max requests per worker: {config['limit_max_requests']}")
    
    # Start the server
    uvicorn.run(**config)

if __name__ == "__main__":
    main()