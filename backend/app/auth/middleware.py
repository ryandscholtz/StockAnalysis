"""
JWT authentication middleware
"""
from typing import Callable, Optional
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.auth.jwt_service import get_jwt_service
from app.auth.models import TokenData
from app.core.exceptions import AppException, ErrorCategory
from app.core.logging import app_logger


class JWTAuthenticationMiddleware(BaseHTTPMiddleware):
    """Middleware for JWT token validation"""

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.jwt_service = get_jwt_service()

        # Public endpoints that don't require authentication
        self.public_paths = {
            "/",
            "/health",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/auth/login",
            "/api/auth/refresh"
        }

    def _is_public_path(self, path: str) -> bool:
        """Check if path is public (doesn't require authentication)"""
        # Exact match
        if path in self.public_paths:
            return True

        # Pattern matching for public paths
        public_patterns = [
            "/docs",
            "/redoc",
            "/static/",
            "/favicon.ico",
            "/api/"  # Make all API endpoints public for now
        ]

        for pattern in public_patterns:
            if path.startswith(pattern):
                return True

        return False

    def _extract_token(self, request: Request) -> Optional[str]:
        """Extract JWT token from request headers"""
        authorization = request.headers.get("Authorization")

        if not authorization:
            return None

        # Check for Bearer token format
        if not authorization.startswith("Bearer "):
            return None

        return authorization[7:]  # Remove "Bearer " prefix

    async def dispatch(self, request: Request, call_next: Callable):
        """Process request with JWT authentication"""
        path = request.url.path

        # Skip authentication for public paths
        if self._is_public_path(path):
            return await call_next(request)

        # Extract token from request
        token = self._extract_token(request)

        if not token:
            app_logger.warning(
                "Missing authentication token",
                extra={
                    "path": path,
                    "method": request.method,
                    "client_ip": request.client.host if request.client else None
                }
            )

            raise HTTPException(
                status_code=401,
                detail={
                    "error": {
                        "message": "Authentication required",
                        "category": "authentication",
                        "details": {"reason": "missing_token"}
                    }
                }
            )

        try:
            # Validate token
            token_data = self.jwt_service.verify_token(token)

            # Add user information to request state
            request.state.user = token_data
            request.state.authenticated = True

            app_logger.debug(
                "User authenticated successfully",
                extra={
                    "user_id": token_data.user_id,
                    "username": token_data.username,
                    "path": path,
                    "method": request.method
                }
            )

        except AppException as e:
            app_logger.warning(
                "Token validation failed",
                extra={
                    "path": path,
                    "method": request.method,
                    "error": e.message,
                    "client_ip": request.client.host if request.client else None
                }
            )

            raise HTTPException(
                status_code=e.status_code,
                detail={
                    "error": {
                        "message": e.message,
                        "category": e.category.value,
                        "details": e.details
                    }
                }
            )

        # Process request
        response = await call_next(request)
        return response
