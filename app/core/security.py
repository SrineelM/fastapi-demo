"""
Security Module

Provides comprehensive security utilities for authentication and authorization.

Features:
- JWT token generation/validation with HS256 and RS256
- Refresh tokens with longer expiration
- Token blacklist for logout/revocation
- Password hashing with Argon2 (offloaded to thread pool)
- Clock skew tolerance for distributed systems
- Key rotation support

Usage:
    from app.core.security import SecurityManager, get_security_manager
    
    manager = get_security_manager()
    token = manager.create_access_token({"sub": "user@example.com"})
    payload = manager.verify_token(token)
    manager.add_token_to_blacklist(token)  # Logout
"""

import os
import secrets
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Optional, Dict, Any, Set
import asyncio
from concurrent.futures import ThreadPoolExecutor

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_cached_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# ==================== PASSWORD HASHING ====================

# Use Argon2 for password hashing (more secure than bcrypt)
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    argon2__memory_cost=65536,  # 64 MB
    argon2__time_cost=3,
    argon2__parallelism=4
)

# Thread pool for CPU-bound operations like hashing
_thread_pool = ThreadPoolExecutor(max_workers=4)


async def hash_password_async(password: str) -> str:
    """
    Hash password asynchronously using thread pool.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password
        
    Note:
        Argon2 is CPU-intensive, so we use a thread pool to avoid
        blocking the async event loop.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        _thread_pool,
        pwd_context.hash,
        password
    )


async def verify_password_async(plain_password: str, hashed_password: str) -> bool:
    """
    Verify password asynchronously using thread pool.
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to compare against
        
    Returns:
        True if password matches, False otherwise
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        _thread_pool,
        pwd_context.verify,
        plain_password,
        hashed_password
    )


def hash_password(password: str) -> str:
    """Hash password (synchronous version for compatibility)."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password (synchronous version for compatibility)."""
    return pwd_context.verify(plain_password, hashed_password)


# ==================== TOKEN BLACKLIST ====================

# In-memory blacklist for development
# In production, use Redis with TTL matching token expiration
_token_blacklist: Set[str] = set()


def add_token_to_blacklist(token: str) -> None:
    """Add token to blacklist (revocation/logout)."""
    _token_blacklist.add(token)
    logger.debug("Token added to blacklist")


def is_token_blacklisted(token: str) -> bool:
    """Check if token is blacklisted."""
    return token in _token_blacklist


def clear_token_blacklist() -> None:
    """Clear all blacklisted tokens (debug only)."""
    _token_blacklist.clear()
    logger.warning("Token blacklist cleared")


# ==================== RSA KEY MANAGEMENT ====================

class RSAKeyManager:
    """Manage RSA keys for RS256 JWT signing."""
    
    def __init__(self, private_key_path: str, public_key_path: str):
        """
        Initialize RSA key manager.
        
        Args:
            private_key_path: Path to private key PEM file
            public_key_path: Path to public key PEM file
        """
        self.private_key_path = Path(private_key_path)
        self.public_key_path = Path(public_key_path)
        self.private_key = None
        self.public_key = None
        self._load_keys()
    
    def _load_keys(self) -> None:
        """Load RSA keys from filesystem."""
        try:
            if self.private_key_path.exists():
                with open(self.private_key_path, 'r') as f:
                    self.private_key = f.read()
                logger.info("Private RSA key loaded")
            
            if self.public_key_path.exists():
                with open(self.public_key_path, 'r') as f:
                    self.public_key = f.read()
                logger.info("Public RSA key loaded")
        except Exception as e:
            logger.error(f"Failed to load RSA keys: {e}")
            raise
    
    def get_private_key(self) -> str:
        """Get private key."""
        if not self.private_key:
            raise ValueError("Private key not loaded")
        return self.private_key
    
    def get_public_key(self) -> str:
        """Get public key."""
        if not self.public_key:
            raise ValueError("Public key not loaded")
        return self.public_key


# ==================== SECURITY MANAGER ====================

class SecurityManager:
    """
    Manages all security operations.
    
    Supports:
    - HS256 (shared secret) for development
    - RS256 (RSA key pair) for production
    - Token refresh with longer expiration
    - Token blacklist for logout/revocation
    - Clock skew tolerance
    """
    
    def __init__(self):
        """Initialize security manager."""
        self.settings = get_cached_settings()
        self.rsa_manager = None
        
        # Load RSA keys if using RS256
        if self.settings.use_rsa_keys():
            try:
                self.rsa_manager = RSAKeyManager(
                    self.settings.PRIVATE_KEY_PATH,
                    self.settings.PUBLIC_KEY_PATH
                )
            except Exception as e:
                if self.settings.is_production():
                    raise
                logger.warning(f"RSA keys not available, using HS256: {e}")
    
    def create_access_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create JWT access token.
        
        Args:
            data: Claims to include in token
            expires_delta: Custom expiration time
            
        Returns:
            Encoded JWT token
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=self.settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "access",
            "jti": secrets.token_urlsafe(16)  # JWT ID for tracking
        })
        
        return self._encode_token(to_encode, "access")
    
    def create_refresh_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create JWT refresh token (longer expiration).
        
        Args:
            data: Claims to include in token
            expires_delta: Custom expiration time
            
        Returns:
            Encoded JWT token
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                days=self.settings.REFRESH_TOKEN_EXPIRE_DAYS
            )
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "refresh",
            "jti": secrets.token_urlsafe(16)
        })
        
        return self._encode_token(to_encode, "refresh")
    
    def _encode_token(self, payload: Dict[str, Any], token_type: str) -> str:
        """
        Encode JWT token using appropriate algorithm.
        
        Args:
            payload: Token claims
            token_type: Token type ("access" or "refresh")
            
        Returns:
            Encoded JWT token
        """
        if self.rsa_manager and self.settings.ALGORITHM == "RS256":
            return jwt.encode(
                payload,
                self.rsa_manager.get_private_key(),
                algorithm="RS256"
            )
        else:
            return jwt.encode(
                payload,
                self.settings.SECRET_KEY,
                algorithm="HS256"
            )
    
    def verify_token(
        self,
        token: str,
        token_type: str = "access",
        clock_skew_seconds: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Verify and decode JWT token.
        
        Args:
            token: Token to verify
            token_type: Expected token type ("access" or "refresh")
            clock_skew_seconds: Clock skew tolerance (default from config)
            
        Returns:
            Decoded token claims
            
        Raises:
            JWTError: If token is invalid or blacklisted
        """
        # Check blacklist
        if is_token_blacklisted(token):
            raise JWTError("Token has been revoked")
        
        # Set clock skew
        if clock_skew_seconds is None:
            clock_skew_seconds = self.settings.CLOCK_SKEW_TOLERANCE_SECONDS
        
        options = {
            "verify_signature": True,
            "verify_exp": True,
            "leeway": clock_skew_seconds
        }
        
        try:
            if self.rsa_manager and self.settings.ALGORITHM == "RS256":
                payload = jwt.decode(
                    token,
                    self.rsa_manager.get_public_key(),
                    algorithms=["RS256"],
                    options=options
                )
            else:
                payload = jwt.decode(
                    token,
                    self.settings.SECRET_KEY,
                    algorithms=["HS256"],
                    options=options
                )
            
            # Verify token type
            if payload.get("type") != token_type:
                raise JWTError(f"Invalid token type: expected {token_type}")
            
            logger.debug(f"Token verified: {payload.get('sub')}")
            return payload
        
        except JWTError as e:
            logger.warning(f"Token verification failed: {e}")
            raise
    
    def revoke_token(self, token: str) -> None:
        """
        Revoke token (add to blacklist).
        
        Typically used for logout.
        """
        add_token_to_blacklist(token)
        logger.info("Token revoked")


# ==================== SINGLETON INSTANCE ====================

@lru_cache()
def get_security_manager() -> SecurityManager:
    """Get cached security manager instance."""
    return SecurityManager()


# ==================== COMPATIBILITY FUNCTIONS ====================

def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create access token (backward compatibility)."""
    manager = get_security_manager()
    return manager.create_access_token(data, expires_delta)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode access token (backward compatibility)."""
    try:
        manager = get_security_manager()
        return manager.verify_token(token, token_type="access")
    except JWTError:
        return None


def create_api_key() -> str:
    """Generate a secure API key."""
    return secrets.token_urlsafe(32)


def validate_api_key(api_key: str, valid_keys: Set[str]) -> bool:
    """Validate API key against set of valid keys."""
    return api_key in valid_keys

