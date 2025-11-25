"""
Basic CRUD Routes Module

This module demonstrates all HTTP verbs with path and query parameters.
Implements RESTful API patterns for user and product management.

HTTP Methods Demonstrated:
- GET: Retrieve resources (with query params)
- POST: Create resources
- PUT: Full resource update
- PATCH: Partial resource update
- DELETE: Remove resources
- HEAD: Get resource metadata
- OPTIONS: Get supported methods

Usage:
    Include this router in main application:
    app.include_router(crud_router, prefix="/api/v1")
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Path, status, Response
from app.schemas.models import (
    UserCreate, UserUpdate, UserResponse, UserListResponse,
    ProductCreate, ProductUpdate, ProductResponse,
    PaginationParams
)
from app.db.memory import get_db
from app.services.cache import get_cache, cache_result
from app.core.logging import get_logger

logger = get_logger(__name__)

# Create router for CRUD operations
crud_router = APIRouter(tags=["CRUD Operations"])


# ==================== USER ENDPOINTS ====================

@crud_router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user",
    description="Create a new user with email validation and password requirements"
)
async def create_user(user: UserCreate) -> UserResponse:
    """
    Create a new user (POST method example).
    
    This demonstrates:
    - POST request handling
    - Pydantic validation
    - Database insertion
    - Cache invalidation
    
    Args:
        user: User creation data
        
    Returns:
        Created user data with generated ID
        
    Raises:
        HTTPException: If email already exists
    """
    db = get_db()
    cache = get_cache()
    
    # Check if email already exists
    existing_users = await db.read_all(
        "users",
        filter_fn=lambda u: u.get("email") == user.email
    )
    
    if existing_users:
        logger.warning("User creation failed - email exists", email=user.email)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user (exclude password from storage in real app)
    user_dict = user.model_dump(exclude={"password"})
    created_user = await db.create("users", user_dict)
    
    # Invalidate users list cache
    await cache.invalidate_pattern("users:list:")
    
    logger.info("User created", user_id=created_user["id"], email=user.email)
    return UserResponse(**created_user)


@crud_router.get(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Get user by ID",
    description="Retrieve a single user by their ID (path parameter example)"
)
async def get_user(
    user_id: int = Path(..., description="User ID", ge=1)
) -> UserResponse:
    """
    Get user by ID (GET with path parameter).
    
    This demonstrates:
    - GET request handling
    - Path parameter validation
    - Cache utilization
    - 404 error handling
    
    Args:
        user_id: User ID from path
        
    Returns:
        User data
        
    Raises:
        HTTPException: If user not found (404)
    """
    db = get_db()
    cache = get_cache()
    
    # Try cache first
    cache_key = f"user:{user_id}"
    cached_user = await cache.get(cache_key)
    
    if cached_user:
        logger.debug("User retrieved from cache", user_id=user_id)
        return UserResponse(**cached_user)
    
    # Fetch from database
    user = await db.read_by_id("users", user_id)
    
    if not user:
        logger.warning("User not found", user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    # Cache the result
    await cache.set(cache_key, user, ttl=300)
    
    logger.info("User retrieved", user_id=user_id)
    return UserResponse(**user)


@crud_router.get(
    "/users",
    response_model=UserListResponse,
    summary="List users with pagination",
    description="Get list of users with query parameter filters and pagination"
)
async def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    role: Optional[str] = Query(None, description="Filter by role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search by name or email")
) -> UserListResponse:
    """
    List users with pagination and filters (GET with query parameters).
    
    This demonstrates:
    - Query parameter handling
    - Pagination
    - Filtering
    - Search functionality
    - Cache for list results
    
    Query Parameters:
        page: Page number (default 1)
        page_size: Items per page (default 20, max 100)
        role: Filter by user role
        is_active: Filter by active status
        search: Search in name or email
        
    Returns:
        Paginated list of users
    """
    db = get_db()
    cache = get_cache()
    
    # Generate cache key from parameters
    cache_key = f"users:list:{page}:{page_size}:{role}:{is_active}:{search}"
    cached_result = await cache.get(cache_key)
    
    if cached_result:
        logger.debug("User list retrieved from cache")
        return UserListResponse(**cached_result)
    
    # Build filter function
    def user_filter(user: dict) -> bool:
        if role and user.get("role") != role:
            return False
        if is_active is not None and user.get("is_active") != is_active:
            return False
        if search:
            search_lower = search.lower()
            name_match = search_lower in user.get("name", "").lower()
            email_match = search_lower in user.get("email", "").lower()
            if not (name_match or email_match):
                return False
        return True
    
    # Get filtered users
    skip = (page - 1) * page_size
    all_users = await db.read_all("users", filter_fn=user_filter)
    total = len(all_users)
    users = all_users[skip:skip + page_size]
    
    # Convert to response models
    user_responses = [UserResponse(**user) for user in users]
    
    result = {
        "users": user_responses,
        "total": total,
        "page": page,
        "page_size": page_size
    }
    
    # Cache the result
    await cache.set(cache_key, result, ttl=60)
    
    logger.info("Users listed", total=total, page=page, page_size=page_size)
    return UserListResponse(**result)


@crud_router.put(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Update user (full replacement)",
    description="Replace all user fields (PUT method example)"
)
async def update_user_full(
    user_id: int = Path(..., description="User ID", ge=1),
    user: UserCreate = None
) -> UserResponse:
    """
    Full user update (PUT method).
    
    This demonstrates:
    - PUT for complete resource replacement
    - Validation of all fields
    - Cache invalidation
    
    Args:
        user_id: User ID from path
        user: Complete user data
        
    Returns:
        Updated user data
        
    Raises:
        HTTPException: If user not found
    """
    db = get_db()
    cache = get_cache()
    
    # Check if user exists
    existing_user = await db.read_by_id("users", user_id)
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    # Update all fields
    update_dict = user.model_dump(exclude={"password"})
    updated_user = await db.update("users", user_id, update_dict)
    
    # Invalidate caches
    await cache.delete(f"user:{user_id}")
    await cache.invalidate_pattern("users:list:")
    
    logger.info("User fully updated", user_id=user_id)
    return UserResponse(**updated_user)


@crud_router.patch(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Update user (partial update)",
    description="Update specific user fields (PATCH method example)"
)
async def update_user_partial(
    user_id: int = Path(..., description="User ID", ge=1),
    user: UserUpdate = None
) -> UserResponse:
    """
    Partial user update (PATCH method).
    
    This demonstrates:
    - PATCH for partial resource update
    - Optional field updates
    - Efficient cache invalidation
    
    Args:
        user_id: User ID from path
        user: Partial user data (only fields to update)
        
    Returns:
        Updated user data
        
    Raises:
        HTTPException: If user not found
    """
    db = get_db()
    cache = get_cache()
    
    # Check if user exists
    existing_user = await db.read_by_id("users", user_id)
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    # Update only provided fields
    update_dict = user.model_dump(exclude_unset=True)
    if not update_dict:
        # No fields to update
        return UserResponse(**existing_user)
    
    updated_user = await db.update("users", user_id, update_dict)
    
    # Invalidate caches
    await cache.delete(f"user:{user_id}")
    await cache.invalidate_pattern("users:list:")
    
    logger.info("User partially updated", user_id=user_id, fields=list(update_dict.keys()))
    return UserResponse(**updated_user)


@crud_router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user",
    description="Remove a user (DELETE method example)"
)
async def delete_user(
    user_id: int = Path(..., description="User ID", ge=1)
) -> None:
    """
    Delete user (DELETE method).
    
    This demonstrates:
    - DELETE request handling
    - 204 No Content response
    - Cache invalidation
    
    Args:
        user_id: User ID from path
        
    Raises:
        HTTPException: If user not found
    """
    db = get_db()
    cache = get_cache()
    
    # Delete user
    deleted = await db.delete("users", user_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    # Invalidate caches
    await cache.delete(f"user:{user_id}")
    await cache.invalidate_pattern("users:list:")
    
    logger.info("User deleted", user_id=user_id)


@crud_router.head(
    "/users/{user_id}",
    summary="Check if user exists",
    description="Get user metadata without body (HEAD method example)"
)
async def check_user_exists(
    user_id: int = Path(..., description="User ID", ge=1),
    response: Response = None
) -> None:
    """
    Check if user exists (HEAD method).
    
    This demonstrates:
    - HEAD request (returns headers only, no body)
    - Efficient existence checks
    - Custom headers
    
    Args:
        user_id: User ID from path
        response: FastAPI Response object
        
    Returns:
        Empty response with appropriate status code
    """
    db = get_db()
    
    user = await db.read_by_id("users", user_id)
    
    if user:
        response.status_code = status.HTTP_200_OK
        response.headers["X-User-Exists"] = "true"
        response.headers["X-User-Email"] = user.get("email", "")
        logger.debug("User exists check - found", user_id=user_id)
    else:
        response.status_code = status.HTTP_404_NOT_FOUND
        response.headers["X-User-Exists"] = "false"
        logger.debug("User exists check - not found", user_id=user_id)


@crud_router.options(
    "/users/{user_id}",
    summary="Get supported methods",
    description="Get allowed HTTP methods for user endpoint (OPTIONS method example)"
)
async def user_options(response: Response) -> dict:
    """
    Get allowed methods (OPTIONS method).
    
    This demonstrates:
    - OPTIONS request for CORS preflight
    - Advertising supported methods
    - API capability discovery
    
    Returns:
        Dictionary with allowed methods and capabilities
    """
    response.headers["Allow"] = "GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE"
    
    return {
        "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
        "description": "User management endpoint",
        "version": "1.0"
    }


# ==================== PRODUCT ENDPOINTS ====================

@crud_router.post(
    "/products",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new product"
)
async def create_product(product: ProductCreate) -> ProductResponse:
    """Create a new product."""
    db = get_db()
    cache = get_cache()
    
    product_dict = product.model_dump()
    created_product = await db.create("products", product_dict)
    
    await cache.invalidate_pattern("products:list:")
    
    logger.info("Product created", product_id=created_product["id"])
    return ProductResponse(**created_product)


@crud_router.get(
    "/products/{product_id}",
    response_model=ProductResponse,
    summary="Get product by ID"
)
async def get_product(product_id: int = Path(..., ge=1)) -> ProductResponse:
    """Get product by ID."""
    db = get_db()
    
    product = await db.read_by_id("products", product_id)
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found"
        )
    
    logger.info("Product retrieved", product_id=product_id)
    return ProductResponse(**product)


@crud_router.get(
    "/products",
    response_model=List[ProductResponse],
    summary="List products with filters"
)
async def list_products(
    category: Optional[str] = Query(None, description="Filter by category"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price"),
    in_stock: Optional[bool] = Query(None, description="Only in-stock items"),
    limit: int = Query(50, ge=1, le=100, description="Max items to return")
) -> List[ProductResponse]:
    """
    List products with query parameter filters.
    
    Demonstrates complex query parameter filtering.
    """
    db = get_db()
    
    def product_filter(product: dict) -> bool:
        if category and product.get("category") != category:
            return False
        if min_price is not None and product.get("price", 0) < min_price:
            return False
        if max_price is not None and product.get("price", float('inf')) > max_price:
            return False
        if in_stock is not None:
            if in_stock and product.get("stock", 0) <= 0:
                return False
        return True
    
    products = await db.read_all("products", filter_fn=product_filter, limit=limit)
    
    logger.info("Products listed", count=len(products), filters={"category": category})
    return [ProductResponse(**p) for p in products]


@crud_router.patch(
    "/products/{product_id}",
    response_model=ProductResponse,
    summary="Update product fields"
)
async def update_product(
    product_id: int = Path(..., ge=1),
    product: ProductUpdate = None
) -> ProductResponse:
    """Update specific product fields (PATCH example)."""
    db = get_db()
    cache = get_cache()
    
    existing_product = await db.read_by_id("products", product_id)
    if not existing_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found"
        )
    
    update_dict = product.model_dump(exclude_unset=True)
    if not update_dict:
        return ProductResponse(**existing_product)
    
    updated_product = await db.update("products", product_id, update_dict)
    
    await cache.invalidate_pattern("products:list:")
    
    logger.info("Product updated", product_id=product_id)
    return ProductResponse(**updated_product)


@crud_router.delete(
    "/products/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete product"
)
async def delete_product(product_id: int = Path(..., ge=1)) -> None:
    """Delete a product."""
    db = get_db()
    cache = get_cache()
    
    deleted = await db.delete("products", product_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found"
        )
    
    await cache.invalidate_pattern("products:list:")
    
    logger.info("Product deleted", product_id=product_id)
