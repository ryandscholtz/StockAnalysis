"""
JWT service for token generation and validation
"""
import jwt
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from passlib.context import CryptContext

from app.auth.models import TokenData, User, TokenResponse
from app.core.exceptions import AppException, ErrorCategory


class JWTService:
    """Service for JWT token operations"""

    def __init__(self):
        self.secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
        self.algorithm = "HS256"
        self.access_token_expire_minutes = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
        self.refresh_token_expire_days = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))

        # Password hashing
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        # In-memory storage for refresh tokens (in production, use Redis or database)
        self.refresh_tokens: Dict[str, Dict[str, Any]] = {}

    def create_access_token(self, user: User) -> str:
        """Create JWT access token"""
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=self.access_token_expire_minutes)

        payload = {
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "roles": user.roles,
            "exp": expire,
            "iat": now,
            "type": "access"
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, user: User) -> str:
        """Create JWT refresh token"""
        now = datetime.now(timezone.utc)
        expire = now + timedelta(days=self.refresh_token_expire_days)

        payload = {
            "user_id": user.id,
            "username": user.username,
            "exp": expire,
            "iat": now,
            "type": "refresh"
        }

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

        # Store refresh token (in production, use Redis with TTL)
        self.refresh_tokens[token] = {
            "user_id": user.id,
            "created_at": now,
            "expires_at": expire
        }

        return token

    def create_token_response(self, user: User) -> TokenResponse:
        """Create complete token response"""
        access_token = self.create_access_token(user)
        refresh_token = self.create_refresh_token(user)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self.access_token_expire_minutes * 60
        )

    def verify_token(self, token: str, token_type: str = "access") -> TokenData:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            # Verify token type
            if payload.get("type") != token_type:
                raise AppException(
                    message=f"Invalid token type. Expected {token_type}",
                    category=ErrorCategory.AUTHENTICATION,
                    status_code=401
                )

            # Create TokenData from payload
            token_data = TokenData(
                user_id=payload["user_id"],
                username=payload.get("username"),
                email=payload.get("email"),
                roles=payload.get("roles", []),
                exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
                iat=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
                token_type=payload["type"]
            )

            return token_data

        except jwt.ExpiredSignatureError:
            raise AppException(
                message="Token has expired",
                category=ErrorCategory.AUTHENTICATION,
                status_code=401
            )
        except jwt.InvalidTokenError as e:
            raise AppException(
                message=f"Invalid token: {str(e)}",
                category=ErrorCategory.AUTHENTICATION,
                status_code=401
            )

    def refresh_access_token(self, refresh_token: str) -> TokenResponse:
        """Generate new access token using refresh token with rotation"""
        # Verify refresh token
        token_data = self.verify_token(refresh_token, token_type="refresh")

        # Check if refresh token is still valid in storage
        if refresh_token not in self.refresh_tokens:
            raise AppException(
                message="Refresh token not found or revoked",
                category=ErrorCategory.AUTHENTICATION,
                status_code=401
            )

        stored_token = self.refresh_tokens[refresh_token]

        # Check expiration
        if datetime.now(timezone.utc) > stored_token["expires_at"]:
            # Clean up expired token
            del self.refresh_tokens[refresh_token]
            raise AppException(
                message="Refresh token has expired",
                category=ErrorCategory.AUTHENTICATION,
                status_code=401
            )

        # Create new user object (in production, fetch from database)
        user = User(
            id=token_data.user_id,
            username=token_data.username or "",
            email=token_data.email or "",
            roles=token_data.roles
        )

        # Rotate refresh token for security - revoke old token before creating new one
        self.revoke_refresh_token(refresh_token)

        # Create new token pair
        return self.create_token_response(user)

    def revoke_refresh_token(self, refresh_token: str) -> bool:
        """Revoke a refresh token"""
        if refresh_token in self.refresh_tokens:
            del self.refresh_tokens[refresh_token]
            return True
        return False

    def cleanup_expired_tokens(self) -> int:
        """Clean up expired refresh tokens and return count of removed tokens"""
        now = datetime.now(timezone.utc)
        expired_tokens = []

        for token, data in self.refresh_tokens.items():
            if now > data["expires_at"]:
                expired_tokens.append(token)

        for token in expired_tokens:
            del self.refresh_tokens[token]

        return len(expired_tokens)

    def revoke_all_user_tokens(self, user_id: str) -> int:
        """Revoke all refresh tokens for a specific user"""
        user_tokens = []

        for token, data in self.refresh_tokens.items():
            if data["user_id"] == user_id:
                user_tokens.append(token)

        for token in user_tokens:
            del self.refresh_tokens[token]

        return len(user_tokens)

    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        # Ensure password is not too long for bcrypt (72 bytes max)
        if len(password.encode('utf-8')) > 72:
            password = password[:72]
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        # Ensure password is not too long for bcrypt (72 bytes max)
        if len(plain_password.encode('utf-8')) > 72:
            plain_password = plain_password[:72]
        return self.pwd_context.verify(plain_password, hashed_password)


# Global JWT service instance
_jwt_service: Optional[JWTService] = None


def get_jwt_service() -> JWTService:
    """Get JWT service singleton"""
    global _jwt_service
    if _jwt_service is None:
        _jwt_service = JWTService()
    return _jwt_service
