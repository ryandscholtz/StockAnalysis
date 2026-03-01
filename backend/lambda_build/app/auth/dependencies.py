"""
Authentication dependencies for FastAPI
"""
from typing import Optional, List
from fastapi import Depends, HTTPException, Request
from functools import wraps

from app.auth.models import TokenData, User
from app.auth.jwt_service import get_jwt_service
from app.core.exceptions import AppException, ErrorCategory


async def get_current_user(request: Request) -> TokenData:
    """Get current authenticated user from request state"""
    if not hasattr(request.state, 'user') or not request.state.user:
        raise HTTPException(
            status_code=401,
            detail={
                "error": {
                    "message": "Authentication required",
                    "category": "authentication",
                    "details": {"reason": "no_user_in_state"}
                }
            }
        )

    return request.state.user


async def get_current_active_user(
    current_user: TokenData = Depends(get_current_user)
) -> TokenData:
    """Get current active user (additional checks can be added here)"""
    # In a real application, you might check if user is active in database
    # For now, we assume all users with valid tokens are active
    return current_user


def require_roles(required_roles: List[str]):
    """Dependency factory for role-based access control"""
    async def check_roles(
        current_user: TokenData = Depends(get_current_user)
    ) -> TokenData:
        if not any(role in current_user.roles for role in required_roles):
            raise HTTPException(
                status_code=403,
                detail={
                    "error": {
                        "message": "Insufficient permissions",
                        "category": "authorization",
                        "details": {
                            "required_roles": required_roles,
                            "user_roles": current_user.roles
                        }
                    }
                }
            )
        return current_user

    return check_roles


def require_admin():
    """Dependency for admin-only endpoints"""
    return require_roles(["admin"])


def require_user():
    """Dependency for user-level access"""
    return require_roles(["user", "admin"])


# Decorator for protecting routes
def protected_route(roles: Optional[List[str]] = None):
    """Decorator to protect routes with authentication and optional role requirements"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # This decorator is mainly for documentation
            # The actual protection is handled by middleware and dependencies
            return await func(*args, **kwargs)
        return wrapper
    return decorator
