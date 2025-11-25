"""
Pydantic Schemas Module

This module defines Pydantic models for request/response validation.
Pydantic provides automatic validation, serialization, and documentation.

Key Features:
- Type validation
- Custom validators
- Nested models
- Optional fields with defaults
- Automatic OpenAPI schema generation

Usage:
    from app.schemas.user import UserCreate, UserResponse
    
    user_data = UserCreate(name="John", email="john@example.com")
    response = UserResponse(**user_data.dict(), id=1)
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, validator, field_validator
from enum import Enum


class UserRole(str, Enum):
    """User role enumeration."""
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


class UserBase(BaseModel):
    """
    Base user model with common fields.
    
    This demonstrates Pydantic's base model pattern for sharing
    common fields across multiple schemas.
    """
    name: str = Field(..., min_length=1, max_length=100, description="User's full name")
    email: EmailStr = Field(..., description="User's email address")
    age: Optional[int] = Field(None, ge=0, le=150, description="User's age")
    role: UserRole = Field(default=UserRole.USER, description="User's role")
    is_active: bool = Field(default=True, description="Whether user is active")
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """
        Validate name field.
        
        Ensures name doesn't contain only whitespace.
        """
        if not v.strip():
            raise ValueError("Name cannot be empty or whitespace only")
        return v.strip()


class UserCreate(UserBase):
    """
    Schema for creating a new user.
    
    Inherits from UserBase and adds password field.
    
    Example:
        >>> user = UserCreate(
        ...     name="John Doe",
        ...     email="john@example.com",
        ...     age=30,
        ...     password="securepass123"
        ... )
    """
    password: str = Field(..., min_length=8, description="User's password")
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """
        Validate password strength.
        
        Ensures password meets minimum security requirements.
        """
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserUpdate(BaseModel):
    """
    Schema for updating a user.
    
    All fields are optional to support partial updates.
    
    Example:
        >>> update = UserUpdate(name="Jane Doe", age=31)
    """
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    age: Optional[int] = Field(None, ge=0, le=150)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    """
    Schema for user response.
    
    Includes all user data except password (security best practice).
    
    Example:
        >>> user = UserResponse(
        ...     id=1,
        ...     name="John Doe",
        ...     email="john@example.com",
        ...     age=30,
        ...     role=UserRole.USER,
        ...     is_active=True,
        ...     created_at=datetime.utcnow(),
        ...     updated_at=datetime.utcnow()
        ... )
    """
    id: int = Field(..., description="User's unique identifier")
    created_at: str = Field(..., description="User creation timestamp")
    updated_at: str = Field(..., description="User last update timestamp")
    
    class Config:
        """Pydantic configuration."""
        from_attributes = True  # Pydantic v2 (formerly orm_mode)
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "John Doe",
                "email": "john@example.com",
                "age": 30,
                "role": "user",
                "is_active": True,
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00"
            }
        }


class UserListResponse(BaseModel):
    """
    Schema for paginated user list response.
    
    Demonstrates pagination pattern.
    """
    users: List[UserResponse] = Field(..., description="List of users")
    total: int = Field(..., description="Total number of users")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    
    @property
    def has_more(self) -> bool:
        """Check if there are more pages."""
        return (self.page * self.page_size) < self.total


class ProductBase(BaseModel):
    """
    Base product model.
    
    Demonstrates nested models and complex validation.
    """
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    price: float = Field(..., gt=0, description="Product price in USD")
    stock: int = Field(default=0, ge=0, description="Available stock quantity")
    category: str = Field(..., description="Product category")
    tags: List[str] = Field(default_factory=list, description="Product tags")
    
    @field_validator("price")
    @classmethod
    def validate_price(cls, v: float) -> float:
        """Validate price has max 2 decimal places."""
        if round(v, 2) != v:
            raise ValueError("Price must have at most 2 decimal places")
        return v


class ProductCreate(ProductBase):
    """Schema for creating a product."""
    pass


class ProductUpdate(BaseModel):
    """Schema for updating a product (all fields optional)."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    price: Optional[float] = Field(None, gt=0)
    stock: Optional[int] = Field(None, ge=0)
    category: Optional[str] = None
    tags: Optional[List[str]] = None


class ProductResponse(ProductBase):
    """Schema for product response."""
    id: int = Field(..., description="Product ID")
    created_at: str
    updated_at: str
    
    class Config:
        """Pydantic configuration."""
        from_attributes = True


class OrderStatus(str, Enum):
    """Order status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class OrderItem(BaseModel):
    """
    Order item model (nested in Order).
    
    Demonstrates nested model validation.
    """
    product_id: int = Field(..., description="Product ID")
    quantity: int = Field(..., gt=0, description="Order quantity")
    unit_price: float = Field(..., gt=0, description="Price per unit")
    
    @property
    def subtotal(self) -> float:
        """Calculate subtotal for this item."""
        return self.quantity * self.unit_price


class OrderCreate(BaseModel):
    """Schema for creating an order."""
    user_id: int = Field(..., description="User ID placing the order")
    items: List[OrderItem] = Field(..., min_length=1, description="Order items")
    shipping_address: str = Field(..., min_length=5)
    
    @property
    def total(self) -> float:
        """Calculate order total."""
        return sum(item.subtotal for item in self.items)


class OrderResponse(BaseModel):
    """Schema for order response."""
    id: int
    user_id: int
    items: List[OrderItem]
    shipping_address: str
    status: OrderStatus
    total: float
    created_at: str
    updated_at: str
    
    class Config:
        """Pydantic configuration."""
        from_attributes = True


class HealthCheck(BaseModel):
    """
    Health check response model.
    
    Used for monitoring and load balancer health checks.
    """
    status: str = Field(..., description="Service status (healthy/unhealthy)")
    version: str = Field(..., description="Application version")
    timestamp: str = Field(..., description="Check timestamp")
    database: str = Field(..., description="Database status")
    cache: str = Field(..., description="Cache status")


class ErrorResponse(BaseModel):
    """
    Standard error response model.
    
    Provides consistent error formatting across the API.
    """
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[dict] = Field(None, description="Additional error details")
    timestamp: str = Field(..., description="Error timestamp")


class PaginationParams(BaseModel):
    """
    Pagination parameters model.
    
    Reusable model for pagination query parameters.
    """
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")
    
    @property
    def skip(self) -> int:
        """Calculate number of items to skip."""
        return (self.page - 1) * self.page_size
