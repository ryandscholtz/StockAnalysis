"""
Authentication routes for login and token management
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer

from app.auth.models import LoginRequest, RefreshTokenRequest, TokenResponse, User
from app.auth.jwt_service import get_jwt_service
from app.auth.dependencies import get_current_user
from app.core.exceptions import AppException
from app.core.logging import app_logger

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()


# Mock user database (in production, use real database)
MOCK_USERS = {
    "admin": {
        "id": "1",
        "username": "admin",
        "email": "admin@example.com",
        "password_hash": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "secret"
        "roles": ["admin", "user"],
        "is_active": True
    },
    "user": {
        "id": "2", 
        "username": "user",
        "email": "user@example.com",
        "password_hash": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "secret"
        "roles": ["user"],
        "is_active": True
    }
}


def authenticate_user(username: str, password: str) -> User:
    """Authenticate user credentials"""
    jwt_service = get_jwt_service()
    
    # Get user from mock database
    user_data = MOCK_USERS.get(username)
    if not user_data:
        raise AppException(
            message="Invalid username or password",
            category="authentication",
            status_code=401
        )
    
    # Verify password
    if not jwt_service.verify_password(password, user_data["password_hash"]):
        raise AppException(
            message="Invalid username or password", 
            category="authentication",
            status_code=401
        )
    
    # Check if user is active
    if not user_data["is_active"]:
        raise AppException(
            message="User account is disabled",
            category="authentication",
            status_code=401
        )
    
    return User(
        id=user_data["id"],
        username=user_data["username"],
        email=user_data["email"],
        roles=user_data["roles"],
        is_active=user_data["is_active"]
    )


@router.post("/login", response_model=TokenResponse)
async def login(login_request: LoginRequest):
    """
    Authenticate user and return JWT tokens
    
    Default credentials for testing:
    - Username: admin, Password: secret (admin role)
    - Username: user, Password: secret (user role)
    """
    try:
        # Authenticate user
        user = authenticate_user(login_request.username, login_request.password)
        
        # Generate tokens
        jwt_service = get_jwt_service()
        token_response = jwt_service.create_token_response(user)
        
        app_logger.info(
            "User logged in successfully",
            extra={
                "user_id": user.id,
                "username": user.username,
                "roles": user.roles
            }
        )
        
        return token_response
        
    except AppException as e:
        app_logger.warning(
            "Login attempt failed",
            extra={
                "username": login_request.username,
                "error": e.message
            }
        )
        raise HTTPException(
            status_code=e.status_code,
            detail={
                "error": {
                    "message": e.message,
                    "category": e.category,
                    "details": e.details
                }
            }
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_request: RefreshTokenRequest):
    """
    Refresh access token using refresh token
    """
    try:
        jwt_service = get_jwt_service()
        token_response = jwt_service.refresh_access_token(refresh_request.refresh_token)
        
        app_logger.info("Token refreshed successfully")
        
        return token_response
        
    except AppException as e:
        app_logger.warning(
            "Token refresh failed",
            extra={"error": e.message}
        )
        raise HTTPException(
            status_code=e.status_code,
            detail={
                "error": {
                    "message": e.message,
                    "category": e.category,
                    "details": e.details
                }
            }
        )


@router.post("/logout")
async def logout(refresh_request: RefreshTokenRequest):
    """
    Logout user by revoking refresh token
    """
    try:
        jwt_service = get_jwt_service()
        revoked = jwt_service.revoke_refresh_token(refresh_request.refresh_token)
        
        if revoked:
            app_logger.info("User logged out successfully")
            return {"message": "Logged out successfully"}
        else:
            return {"message": "Token already revoked or invalid"}
            
    except Exception as e:
        app_logger.error(f"Logout error: {e}")
        return {"message": "Logout completed"}


@router.post("/logout-all")
async def logout_all(current_user = Depends(get_current_user)):
    """
    Logout user from all devices by revoking all refresh tokens
    """
    try:
        jwt_service = get_jwt_service()
        revoked_count = jwt_service.revoke_all_user_tokens(current_user.user_id)
        
        app_logger.info(
            "User logged out from all devices",
            extra={
                "user_id": current_user.user_id,
                "revoked_tokens": revoked_count
            }
        )
        
        return {
            "message": f"Logged out from all devices successfully",
            "revoked_tokens": revoked_count
        }
        
    except Exception as e:
        app_logger.error(f"Logout all error: {e}")
        return {"message": "Logout from all devices completed"}


@router.get("/me")
async def get_current_user_info(current_user = Depends(get_current_user)):
    """
    Get current user information
    """
    return {
        "user_id": current_user.user_id,
        "username": current_user.username,
        "email": current_user.email,
        "roles": current_user.roles,
        "token_type": current_user.token_type
    }