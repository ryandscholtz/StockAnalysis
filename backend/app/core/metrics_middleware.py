"""
Metrics collection middleware for automatic API performance tracking
"""
import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.metrics import record_api_response_time, record_error
from app.core.logging import LoggerMixin


class MetricsMiddleware(BaseHTTPMiddleware, LoggerMixin):
    """Middleware to automatically collect API performance metrics"""

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    def _get_endpoint_name(self, request: Request) -> str:
        """Extract a clean endpoint name from the request path"""
        path = request.url.path

        # Remove API prefix
        if path.startswith("/api/"):
            path = path[4:]

        # Normalize common patterns
        if path.startswith("/analyze/"):
            return "/analyze/{ticker}"
        elif path.startswith("/quote/"):
            return "/quote/{ticker}"
        elif path.startswith("/watchlist/"):
            return "/watchlist/{id}"
        elif path.startswith("/batch/"):
            return "/batch/{operation}"
        elif path.startswith("/auth/"):
            return f"/auth{path[5:]}"  # Keep auth endpoints specific

        # For other paths, return as-is but limit length
        return path[:50] if len(path) <= 50 else path[:47] + "..."

    def _should_track_endpoint(self, path: str) -> bool:
        """Determine if we should track metrics for this endpoint"""
        # Skip static files and health checks that are too frequent
        skip_patterns = [
            "/favicon.ico",
            "/robots.txt",
            "/static/",
            "/assets/",
            "/_next/",
        ]

        for pattern in skip_patterns:
            if pattern in path:
                return False

        return True

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip tracking for certain endpoints
        if not self._should_track_endpoint(request.url.path):
            return await call_next(request)

        start_time = time.time()
        endpoint_name = self._get_endpoint_name(request)
        method = request.method

        try:
            # Process the request
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Record metrics
            await record_api_response_time(
                endpoint=endpoint_name,
                method=method,
                duration_ms=duration_ms,
                status_code=response.status_code
            )

            # Log slow requests
            if duration_ms > 1000:  # Log requests slower than 1 second
                self.log_warning(
                    "Slow API request detected",
                    extra={
                        "endpoint": endpoint_name,
                        "method": method,
                        "duration_ms": duration_ms,
                        "status_code": response.status_code
                    }
                )

            return response

        except Exception as e:
            # Calculate duration even for errors
            duration_ms = (time.time() - start_time) * 1000

            # Determine error category
            error_category = "internal_error"
            status_code = 500

            if hasattr(e, 'status_code'):
                status_code = e.status_code
                if status_code == 400:
                    error_category = "validation_error"
                elif status_code == 401:
                    error_category = "authentication_error"
                elif status_code == 403:
                    error_category = "authorization_error"
                elif status_code == 404:
                    error_category = "not_found_error"
                elif status_code == 429:
                    error_category = "rate_limit_error"
                elif 500 <= status_code < 600:
                    error_category = "server_error"

            # Record error metrics
            await record_error(error_category, endpoint_name)

            # Record response time even for errors
            await record_api_response_time(
                endpoint=endpoint_name,
                method=method,
                duration_ms=duration_ms,
                status_code=status_code
            )

            # Re-raise the exception
            raise
