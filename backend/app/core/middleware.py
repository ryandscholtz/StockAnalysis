"""
Custom middleware for the Stock Analysis API
"""
import time
import uuid
from typing import Callable, Dict, Optional
from collections import defaultdict, deque
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.logging import set_correlation_id, app_logger


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce rate limiting per IP/user"""
    
    def __init__(
        self, 
        app: ASGIApp, 
        calls_per_minute: int = 60, 
        burst_limit: int = 10,
        cleanup_interval: int = 300  # 5 minutes
    ):
        super().__init__(app)
        self.calls_per_minute = calls_per_minute
        self.burst_limit = burst_limit
        self.cleanup_interval = cleanup_interval
        
        # Store request timestamps per client
        self.request_history: Dict[str, deque] = defaultdict(deque)
        self.last_cleanup = time.time()
    
    def _get_client_id(self, request: Request) -> str:
        """Get unique client identifier from request"""
        # Try user ID first, then IP address
        user_id = request.headers.get("X-User-ID")
        if user_id:
            return f"user:{user_id}"
        
        # Use forwarded IP if available, otherwise client IP
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take first IP in case of multiple proxies
            return f"ip:{forwarded_for.split(',')[0].strip()}"
        
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"
    
    def _cleanup_old_requests(self):
        """Remove old request timestamps to prevent memory leaks"""
        current_time = time.time()
        
        # Only cleanup periodically
        if current_time - self.last_cleanup < self.cleanup_interval:
            return
        
        cutoff_time = current_time - 60  # Remove requests older than 1 minute
        
        for client_id in list(self.request_history.keys()):
            history = self.request_history[client_id]
            
            # Remove old timestamps
            while history and history[0] < cutoff_time:
                history.popleft()
            
            # Remove empty histories
            if not history:
                del self.request_history[client_id]
        
        self.last_cleanup = current_time
    
    def _is_rate_limited(self, client_id: str, current_time: float) -> tuple[bool, Dict[str, str]]:
        """Check if client is rate limited and return headers"""
        history = self.request_history[client_id]
        
        # Remove requests older than 1 minute
        cutoff_time = current_time - 60
        while history and history[0] < cutoff_time:
            history.popleft()
        
        # Check burst limit (immediate requests)
        recent_requests = sum(1 for timestamp in history if current_time - timestamp < 1)
        
        # Check rate limit (requests per minute)
        requests_in_minute = len(history)
        
        # Calculate remaining requests
        remaining_burst = max(0, self.burst_limit - recent_requests)
        remaining_minute = max(0, self.calls_per_minute - requests_in_minute)
        
        # Prepare headers
        headers = {
            "X-RateLimit-Limit": str(self.calls_per_minute),
            "X-RateLimit-Remaining": str(remaining_minute),
            "X-RateLimit-Reset": str(int(current_time + 60))
        }
        
        # Check if rate limited
        if recent_requests >= self.burst_limit or requests_in_minute >= self.calls_per_minute:
            headers["Retry-After"] = "60"  # Retry after 1 minute
            return True, headers
        
        return False, headers
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        current_time = time.time()
        client_id = self._get_client_id(request)
        
        # Periodic cleanup
        self._cleanup_old_requests()
        
        # Check rate limit
        is_limited, headers = self._is_rate_limited(client_id, current_time)
        
        if is_limited:
            app_logger.warning(
                "Rate limit exceeded",
                extra={
                    "client_id": client_id,
                    "path": request.url.path,
                    "method": request.method
                }
            )
            
            # Return rate limit error
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "message": "Rate limit exceeded",
                        "category": "rate_limit",
                        "details": {
                            "limit": self.calls_per_minute,
                            "window": "1 minute"
                        }
                    }
                },
                headers=headers
            )
        
        # Record this request
        self.request_history[client_id].append(current_time)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers to successful responses
        for key, value in headers.items():
            response.headers[key] = value
        
        return response


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware to handle correlation ID for request tracking"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extract or generate correlation ID
        correlation_id = request.headers.get("x-correlation-id")
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        
        # Set correlation ID in context
        set_correlation_id(correlation_id)
        
        # Process request
        response = await call_next(request)
        
        # Add correlation ID to response headers
        response.headers["x-correlation-id"] = correlation_id
        
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log HTTP requests and responses"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Log request
        app_logger.info(
            "HTTP request started",
            extra={
                "method": request.method,
                "url": str(request.url),
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "client_ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent")
            }
        )
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log response
        app_logger.info(
            "HTTP request completed",
            extra={
                "method": request.method,
                "url": str(request.url),
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration * 1000, 2),
                "response_size": response.headers.get("content-length")
            }
        )
        
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Add HSTS header for HTTPS
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response