"""
Advanced Security and OAuth2 Routes Module

Demonstrates:
- JWT token generation with PyJWT
- Password hashing with pwdlib
- OAuth2 Password Bearer flow
- Token validation and user authentication
- Secure endpoint access control

This module provides complete OAuth2 + JWT implementation for the FastAPI application.
"""

from datetime import datetime, timedelta, timezone
from typing import Annotated
import secrets

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from pydantic import BaseModel, Field, EmailStr

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# ==================== CONFIGURATION ====================

# Password hashing setup with Argon2
password_hash = PasswordHash.recommended()

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/security/token")

# Create router
security_router = APIRouter(prefix="/security", tags=["Security & OAuth2"])

# ==================== PYDANTIC MODELS ====================

class Token(BaseModel):
    """OAuth2 token response"""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")


class TokenData(BaseModel):
    """Data extracted from token"""
    username: str | None = None
    scopes: list[str] = []


class User(BaseModel):
    """User response model"""
    id: int
    username: str
    email: EmailStr
    full_name: str | None = None
    disabled: bool = False
    roles: list[str] = ["user"]


class UserInDB(User):
    """User model with hashed password"""
    hashed_password: str


class LoginRequest(BaseModel):
    """Login request model"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)


class RegisterRequest(BaseModel):
    """User registration model"""
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    email: EmailStr = Field(..., description="Valid email address")
    password: str = Field(..., min_length=8, description="Strong password (min 8 chars)")
    full_name: str | None = Field(None, max_length=100)


class ChangePasswordRequest(BaseModel):
    """Change password model"""
    old_password: str = Field(..., min_length=8)
    new_password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)


# ==================== IN-MEMORY USER DATABASE ====================

# In production, use a real database
FAKE_USERS_DB = {
    "johndoe": {
        "id": 1,
        "username": "johndoe",
        "full_name": "John Doe",
        "email": "john@example.com",
        "hashed_password": password_hash.hash("secretpassword123"),
        "disabled": False,
        "roles": ["user", "admin"]
    },
    "janedoe": {
        "id": 2,
        "username": "janedoe",
        "full_name": "Jane Doe",
        "email": "jane@example.com",
        "hashed_password": password_hash.hash("securepass456"),
        "disabled": False,
        "roles": ["user"]
    },
    "admin": {
        "id": 3,
        "username": "admin",
        "full_name": "Admin User",
        "email": "admin@example.com",
        "hashed_password": password_hash.hash("adminpass789"),
        "disabled": False,
        "roles": ["admin", "moderator"]
    }
}


# ==================== UTILITY FUNCTIONS ====================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash"""
    try:
        return password_hash.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error("Password verification error", error=str(e))
        return False


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return password_hash.hash(password)


def get_user_from_db(username: str) -> UserInDB | None:
    """Retrieve user from fake database"""
    if username in FAKE_USERS_DB:
        user_dict = FAKE_USERS_DB[username]
        return UserInDB(**user_dict)
    return None


def authenticate_user(username: str, password: str) -> UserInDB | None:
    """Authenticate user with username and password"""
    user = get_user_from_db(username)
    if not user:
        logger.warning("Authentication failed - user not found", username=username)
        return None
    
    if not verify_password(password, user.hashed_password):
        logger.warning("Authentication failed - invalid password", username=username)
        return None
    
    logger.info("User authenticated successfully", username=username)
    return user


def create_access_token(
    data: dict,
    expires_delta: timedelta | None = None,
    secret_key: str | None = None,
    algorithm: str | None = None
) -> str:
    """
    Create JWT access token
    
    Args:
        data: Payload data to encode
        expires_delta: Token expiration time delta
        secret_key: Secret key for signing
        algorithm: Algorithm for encoding
        
    Returns:
        Encoded JWT token
    """
    settings = get_settings()
    secret_key = secret_key or settings.SECRET_KEY
    algorithm = algorithm or settings.ALGORITHM
    
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode.update({"exp": expire})
    
    try:
        encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=algorithm)
        logger.debug("Token created", user=data.get("sub"))
        return encoded_jwt
    except Exception as e:
        logger.error("Token creation error", error=str(e))
        raise


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)]
) -> User:
    """
    Get current authenticated user from token
    
    Args:
        token: JWT bearer token
        
    Returns:
        Current user information
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    settings = get_settings()
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        username: str = payload.get("sub")
        
        if username is None:
            logger.warning("Token missing 'sub' claim")
            raise credentials_exception
            
        token_data = TokenData(username=username)
        
    except InvalidTokenError as e:
        logger.warning("Invalid token", error=str(e))
        raise credentials_exception
    
    user = get_user_from_db(username=token_data.username)
    
    if user is None:
        logger.warning("User not found from token", username=token_data.username)
        raise credentials_exception
    
    return User(**user.model_dump(exclude={"hashed_password"}))


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Verify current user is active
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Active user
        
    Raises:
        HTTPException: If user is disabled
    """
    if current_user.disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    return current_user


async def get_admin_user(
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> User:
    """
    Verify current user has admin role
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Admin user
        
    Raises:
        HTTPException: If user doesn't have admin role
    """
    if "admin" not in current_user.roles:
        logger.warning("Admin access denied", username=current_user.username)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


# ==================== ENDPOINTS ====================

@security_router.post(
    "/token",
    response_model=Token,
    summary="Login and get access token",
    description="Authenticate with username and password to receive JWT token"
)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> Token:
    """
    OAuth2 login endpoint.
    
    Uses standard OAuth2PasswordRequestForm for compatibility.
    Returns JWT access token on successful authentication.
    
    Args:
        form_data: Username and password from form
        
    Returns:
        Token response with access_token and token_type
        
    Raises:
        HTTPException: If credentials are invalid
    """
    user = authenticate_user(form_data.username, form_data.password)
    
    if not user:
        logger.warning("Login failed", username=form_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    settings = get_settings()
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )
    
    logger.info("Token issued", username=user.username)
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=int(access_token_expires.total_seconds())
    )


@security_router.post(
    "/register",
    response_model=User,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
    description="Create a new user account with email and password"
)
async def register_user(user_data: RegisterRequest) -> User:
    """
    Register a new user.
    
    Creates a new user account with validation:
    - Unique username
    - Valid email
    - Strong password (min 8 chars)
    
    Args:
        user_data: Registration data
        
    Returns:
        Created user information
        
    Raises:
        HTTPException: If username or email already exists
    """
    # Check if username exists
    if user_data.username in FAKE_USERS_DB:
        logger.warning("Registration failed - username exists", username=user_data.username)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email exists
    for user in FAKE_USERS_DB.values():
        if user["email"] == user_data.email:
            logger.warning("Registration failed - email exists", email=user_data.email)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
    
    # Create new user
    user_id = len(FAKE_USERS_DB) + 1
    new_user = {
        "id": user_id,
        "username": user_data.username,
        "email": user_data.email,
        "full_name": user_data.full_name,
        "hashed_password": get_password_hash(user_data.password),
        "disabled": False,
        "roles": ["user"]
    }
    
    FAKE_USERS_DB[user_data.username] = new_user
    
    logger.info("User registered", username=user_data.username, email=user_data.email)
    
    user_response = {**new_user}
    del user_response["hashed_password"]
    return User(**user_response)


@security_router.get(
    "/me",
    response_model=User,
    summary="Get current user",
    description="Get information about the currently authenticated user"
)
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> User:
    """
    Get current authenticated user's information.
    
    Requires valid JWT token in Authorization header.
    
    Args:
        current_user: Current user (dependency injection)
        
    Returns:
        Current user information
    """
    logger.info("User info retrieved", username=current_user.username)
    return current_user


@security_router.post(
    "/change-password",
    summary="Change user password",
    description="Change password for the currently authenticated user"
)
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> dict:
    """
    Change user's password.
    
    Requires:
    - Valid old password
    - New passwords match
    - Password meets requirements (min 8 chars)
    
    Args:
        password_data: Old and new password
        current_user: Current user
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If old password is incorrect or validation fails
    """
    # Validate new passwords match
    if password_data.new_password != password_data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New passwords do not match"
        )
    
    # Verify old password
    user = get_user_from_db(current_user.username)
    if not verify_password(password_data.old_password, user.hashed_password):
        logger.warning("Password change failed - invalid old password", username=current_user.username)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )
    
    # Update password
    new_hash = get_password_hash(password_data.new_password)
    FAKE_USERS_DB[current_user.username]["hashed_password"] = new_hash
    
    logger.info("Password changed", username=current_user.username)
    return {"message": "Password changed successfully"}


@security_router.get(
    "/admin-only",
    summary="Admin-only endpoint",
    description="Endpoint accessible only to admin users"
)
async def admin_endpoint(
    admin_user: Annotated[User, Depends(get_admin_user)]
) -> dict:
    """
    Admin-only endpoint.
    
    Demonstrates role-based access control.
    
    Args:
        admin_user: Admin user (requires 'admin' role)
        
    Returns:
        Admin-only data
    """
    logger.info("Admin endpoint accessed", username=admin_user.username)
    return {
        "message": f"Welcome Admin {admin_user.full_name}",
        "admin_id": admin_user.id,
        "roles": admin_user.roles
    }


@security_router.get(
    "/validate-token",
    response_model=dict,
    summary="Validate token",
    description="Check if a provided token is valid"
)
async def validate_token(
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> dict:
    """
    Validate JWT token.
    
    Simply having a valid dependency on get_current_active_user
    means the token is valid. If token is invalid, HTTPException is raised.
    
    Args:
        current_user: Current user
        
    Returns:
        Token validation result with user info
    """
    return {
        "valid": True,
        "username": current_user.username,
        "email": current_user.email,
        "roles": current_user.roles
    }


class RefreshTokenRequest(BaseModel):
    """Refresh token request model"""
    refresh_token: str = Field(..., description="Refresh token")


class TokenResponse(BaseModel):
    """Enhanced token response with refresh token"""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="Refresh token for getting new access tokens")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiration in seconds")


class LogoutRequest(BaseModel):
    """Logout request model"""
    token: str = Field(..., description="Token to revoke")


@security_router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description="Get a new access token using refresh token"
)
async def refresh_access_token(request: RefreshTokenRequest) -> TokenResponse:
    """
    Refresh access token using refresh token.
    
    Refresh tokens have longer expiration time (7 days).
    Use this endpoint when access token expires to get a new one.
    
    Args:
        request: Refresh token
        
    Returns:
        New access and refresh tokens
        
    Raises:
        HTTPException: If refresh token is invalid
    """
    settings = get_settings()
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            request.refresh_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        username: str = payload.get("sub")
        
        if username is None:
            raise credentials_exception
            
    except InvalidTokenError as e:
        logger.warning("Invalid refresh token", error=str(e))
        raise credentials_exception
    
    user = get_user_from_db(username=username)
    if user is None:
        raise credentials_exception
    
    # Create new tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    new_access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )
    
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    new_refresh_token = create_access_token(
        data={"sub": user.username},
        expires_delta=refresh_token_expires
    )
    
    logger.info("Token refreshed", username=user.username)
    
    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=int(access_token_expires.total_seconds())
    )


@security_router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout user",
    description="Revoke current token and logout"
)
async def logout(
    current_user: Annotated[User, Depends(get_current_active_user)],
    token: Annotated[str, Depends(oauth2_scheme)]
) -> None:
    """
    Logout endpoint.
    
    Revokes the current token to prevent further use.
    In production, store revoked tokens in Redis with TTL.
    
    Args:
        current_user: Current user
        token: Current token to revoke
    """
    # In a production system, you would:
    # 1. Store the token in Redis/blacklist with TTL matching token expiration
    # 2. Check this blacklist on token verification
    # For now, we just log the action
    
    logger.info("User logged out", username=current_user.username)
    # Token revocation would happen here
    # Example: await redis.setex(f"blacklist:{token}", token_ttl, "revoked")

