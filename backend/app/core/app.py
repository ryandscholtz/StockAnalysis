"""
Modern FastAPI application factory with dependency injection and structured logging
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
import os
from datetime import datetime

from app.core.logging import setup_logging, app_logger
from app.core.exceptions import (
    AppException,
    app_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler
)
from app.core.middleware import (
    CorrelationIdMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware
)
from app.core.metrics_middleware import MetricsMiddleware
from app.core.xray_middleware import XRayMiddleware
from app.auth.middleware import JWTAuthenticationMiddleware
from app.core.dependencies import startup_services, shutdown_services
from app.core.metrics import initialize_metrics_service
from app.core.cloudwatch_dashboards import initialize_dashboards
from app.api.routes import router
from app.api.optimized_routes import router as optimized_router
from app.api.websocket_routes import router as websocket_router
from app.auth.routes import router as auth_router

# Generate build timestamp
BUILD_TIMESTAMP = datetime.now().strftime("%y%m%d-%H:%M")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    app_logger.info("Starting Stock Analysis API", extra={"build_timestamp": BUILD_TIMESTAMP})
    
    # Initialize services
    await startup_services()
    
    # Initialize metrics service
    await initialize_metrics_service()
    
    # Initialize dashboards (only in production or when explicitly enabled)
    dashboard_init_enabled = os.getenv("INIT_DASHBOARDS_ON_STARTUP", "false").lower() == "true"
    if dashboard_init_enabled:
        try:
            await initialize_dashboards()
            app_logger.info("CloudWatch dashboards initialized")
        except Exception as e:
            app_logger.warning(f"Failed to initialize dashboards: {e}")
    
    # Start background tasks if needed
    auto_stop_enabled = os.getenv("EC2_AUTO_STOP", "true").lower() == "true"
    if auto_stop_enabled:
        try:
            import asyncio
            from app.utils.ec2_manager import get_ec2_manager
            
            async def ec2_idle_monitor():
                """Background task to monitor EC2 instance idle time"""
                try:
                    ec2_manager = get_ec2_manager()
                    if not ec2_manager.auto_stop_enabled:
                        app_logger.info("EC2 auto-stop is disabled, skipping idle monitoring")
                        return
                    
                    app_logger.info("Starting EC2 idle monitor background task")
                    while True:
                        try:
                            await ec2_manager.check_and_stop_if_idle()
                        except Exception as e:
                            app_logger.error("Error in EC2 idle monitor", extra={"error": str(e)})
                        await asyncio.sleep(60)
                except Exception as e:
                    app_logger.error("Failed to start EC2 idle monitor", extra={"error": str(e)})
            
            asyncio.create_task(ec2_idle_monitor())
            app_logger.info("EC2 auto-stop monitor started")
        except Exception as e:
            app_logger.warning("Failed to start EC2 auto-stop monitor", extra={"error": str(e)})
    
    app_logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    app_logger.info("Shutting down Stock Analysis API")
    await shutdown_services()
    app_logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    
    # Setup logging
    log_level = os.getenv("LOG_LEVEL", "INFO")
    structured_logging = os.getenv("STRUCTURED_LOGGING", "true").lower() == "true"
    setup_logging(level=log_level, structured=structured_logging)
    
    # Create FastAPI app
    app = FastAPI(
        title="Stock Analysis API",
        description="Modern value investing stock analysis API with comprehensive financial analysis",
        version="2.0.0",
        lifespan=lifespan,
        docs_url="/docs" if os.getenv("ENVIRONMENT") != "production" else None,
        redoc_url="/redoc" if os.getenv("ENVIRONMENT") != "production" else None
    )
    
    # Add middleware (order matters - first added is outermost)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(MetricsMiddleware)  # Add metrics middleware
    app.add_middleware(JWTAuthenticationMiddleware)
    app.add_middleware(CorrelationIdMiddleware)
    
    # Add X-Ray tracing middleware (should be early in the chain)
    xray_enabled = os.getenv("XRAY_ENABLED", "true").lower() == "true"
    if xray_enabled:
        app.add_middleware(XRayMiddleware, service_name="stock-analysis-api")
    
    # Configure CORS
    allowed_origins = [
        "http://localhost:3000",
        "http://localhost:3001", 
        "http://localhost:3003",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3003",
    ]
    
    # Add production origins if configured
    production_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
    if production_origins and production_origins[0]:
        allowed_origins.extend([origin.strip() for origin in production_origins])
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
        allow_headers=["*"],
        expose_headers=["*"],
        max_age=3600,
    )
    
    # Register exception handlers
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
    
    # Include routers
    app.include_router(auth_router, prefix="/api", tags=["Authentication"])
    app.include_router(router, prefix="/api", tags=["Stock Analysis"])
    app.include_router(optimized_router, prefix="/api", tags=["Optimized Endpoints"])
    app.include_router(websocket_router, prefix="/api", tags=["WebSocket Streaming"])
    
    # Health check endpoints
    @app.get("/", tags=["Health"])
    async def root():
        """Root endpoint with API information"""
        return {
            "message": "Stock Analysis API",
            "version": "2.0.0",
            "build_timestamp": BUILD_TIMESTAMP,
            "status": "healthy"
        }
    
    @app.get("/health", tags=["Health"])
    async def health_check():
        """Health check endpoint for monitoring"""
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "version": "2.0.0",
            "build_timestamp": BUILD_TIMESTAMP
        }
    
    @app.get("/metrics", tags=["Health"])
    async def metrics():
        """Enhanced metrics endpoint with real-time data"""
        try:
            from app.core.metrics import get_metrics_service
            from app.cache_manager import cache_manager
            
            metrics_service = get_metrics_service()
            collector = metrics_service.get_collector()
            
            # Get cache statistics
            cache_stats = cache_manager.get_stats()
            
            # Get metrics from collector
            cache_hit_ratio = await collector.get_cache_hit_ratio()
            avg_response_time = await collector.get_average_response_time()
            error_rate = await collector.get_error_rate()
            
            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "version": "2.0.0",
                "build_timestamp": BUILD_TIMESTAMP,
                "metrics": {
                    "api_performance": {
                        "average_response_time_ms": round(avg_response_time, 2),
                        "error_rate_percent": round(error_rate * 100, 2)
                    },
                    "cache": {
                        "hit_ratio_percent": round(cache_hit_ratio * 100, 2),
                        "total_entries": cache_stats["total_entries"],
                        "active_entries": cache_stats["active_entries"],
                        "utilization_percent": cache_stats["utilization_percent"]
                    },
                    "business": {
                        "analyses_completed": collector.analysis_stats["completed"],
                        "analyses_failed": collector.analysis_stats["failed"],
                        "analyses_in_progress": collector.analysis_stats["in_progress"]
                    },
                    "system": {
                        "cloudwatch_enabled": metrics_service.enabled,
                        "metrics_namespace": metrics_service.namespace
                    }
                }
            }
        except Exception as e:
            logger.error(f"Error generating metrics: {e}")
            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "version": "2.0.0",
                "build_timestamp": BUILD_TIMESTAMP,
                "error": "Failed to generate detailed metrics"
            }
    
    return app


# Create the app instance
app = create_app()