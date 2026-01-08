# JWT Authentication System

This module implements a complete JWT-based authentication system for the Stock Analysis API.

## Features

- **JWT Token Management**: Access and refresh tokens with configurable expiration
- **Token Rotation**: Refresh tokens are rotated on each refresh for enhanced security
- **Password Hashing**: Secure password hashing using bcrypt
- **Middleware Protection**: Automatic token validation for protected routes
- **Role-Based Access Control**: Support for user roles and permissions
- **Token Cleanup**: Automatic cleanup of expired tokens
- **Comprehensive Logging**: Structured logging for all authentication events

## Components

### Models (`models.py`)
- `TokenData`: JWT token payload structure
- `User`: User model for authentication
- `TokenResponse`: Token response format
- `LoginRequest`: Login request format
- `RefreshTokenRequest`: Token refresh request format

### JWT Service (`jwt_service.py`)
- Token generation and validation
- Password hashing and verification
- Refresh token management with rotation
- Token cleanup utilities

### Middleware (`middleware.py`)
- `JWTAuthenticationMiddleware`: Validates JWT tokens on protected routes
- Handles token extraction from Authorization header
- Manages public/protected route distinction

### Dependencies (`dependencies.py`)
- FastAPI dependency injection for authentication
- Role-based access control decorators
- Current user extraction from request state

### Routes (`routes.py`)
- `POST /api/auth/login`: User authentication
- `POST /api/auth/refresh`: Token refresh with rotation
- `POST /api/auth/logout`: Single device logout
- `POST /api/auth/logout-all`: All devices logout
- `GET /api/auth/me`: Current user information

## Configuration

Environment variables:
- `JWT_SECRET_KEY`: Secret key for JWT signing (default: "your-secret-key-change-in-production")
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`: Access token expiration in minutes (default: 30)
- `JWT_REFRESH_TOKEN_EXPIRE_DAYS`: Refresh token expiration in days (default: 7)

## Usage

### Login
```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "secret"}'
```

### Access Protected Endpoint
```bash
curl -X GET "http://localhost:8000/api/auth/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Refresh Token
```bash
curl -X POST "http://localhost:8000/api/auth/refresh" \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "YOUR_REFRESH_TOKEN"}'
```

## Default Test Users

For development and testing:
- **Admin User**: username=`admin`, password=`secret`, roles=`["admin", "user"]`
- **Regular User**: username=`user`, password=`secret`, roles=`["user"]`

## Security Features

1. **Token Rotation**: Refresh tokens are invalidated and replaced on each refresh
2. **Expiration Handling**: Both access and refresh tokens have configurable expiration
3. **Password Security**: Passwords are hashed using bcrypt with proper length handling
4. **Token Revocation**: Support for single and all-device logout
5. **Role-Based Access**: Granular permission control based on user roles
6. **Audit Logging**: All authentication events are logged with correlation IDs

## Integration

The authentication system is automatically integrated into the FastAPI application:
- Middleware is added to the application stack
- Routes are included under `/api/auth`
- Dependencies are available for protecting endpoints
- Error handling is integrated with the global exception system

## Production Considerations

1. **Secret Key**: Change `JWT_SECRET_KEY` to a secure random value
2. **Token Storage**: Replace in-memory refresh token storage with Redis or database
3. **User Management**: Integrate with a proper user database
4. **Rate Limiting**: Consider adding rate limiting to authentication endpoints
5. **HTTPS**: Ensure all authentication endpoints use HTTPS in production