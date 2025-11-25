"""
Unit Tests for CRUD Endpoints

Tests all HTTP verbs (GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS)
with various scenarios including success and error cases.

Test Coverage:
- User CRUD operations
- Product CRUD operations
- Query parameter filtering
- Path parameter validation
- Error handling
- Cache behavior
"""

import pytest
from fastapi import status


# ==================== USER CREATE TESTS ====================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_user_success(async_client, sample_user_data):
    """Test successful user creation."""
    response = await async_client.post("/api/v1/users", json=sample_user_data)
    
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == sample_user_data["name"]
    assert data["email"] == sample_user_data["email"]
    assert data["age"] == sample_user_data["age"]
    assert "id" in data
    assert "created_at" in data
    assert "password" not in data  # Password should not be in response


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_user_duplicate_email(async_client, sample_user_data):
    """Test creating user with duplicate email fails."""
    # Create first user
    await async_client.post("/api/v1/users", json=sample_user_data)
    
    # Try to create second user with same email
    response = await async_client.post("/api/v1/users", json=sample_user_data)
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "email already registered" in response.json()["detail"].lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_user_invalid_email(async_client, sample_user_data):
    """Test creating user with invalid email fails validation."""
    sample_user_data["email"] = "invalid-email"
    response = await async_client.post("/api/v1/users", json=sample_user_data)
    
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_user_weak_password(async_client, sample_user_data):
    """Test creating user with weak password fails validation."""
    sample_user_data["password"] = "weak"
    response = await async_client.post("/api/v1/users", json=sample_user_data)
    
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ==================== USER READ TESTS ====================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_user_by_id_success(async_client, create_test_user):
    """Test retrieving user by ID."""
    user = await create_test_user(name="John Doe", email="john@example.com")
    
    response = await async_client.get(f"/api/v1/users/{user['id']}")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == user["id"]
    assert data["name"] == "John Doe"
    assert data["email"] == "john@example.com"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_user_not_found(async_client):
    """Test retrieving non-existent user returns 404."""
    response = await async_client.get("/api/v1/users/999")
    
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_user_invalid_id(async_client):
    """Test retrieving user with invalid ID fails validation."""
    response = await async_client.get("/api/v1/users/0")
    
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_user_uses_cache(async_client, create_test_user, cache):
    """Test that user retrieval uses cache."""
    user = await create_test_user(name="Cached User")
    
    # First request - should hit database
    response1 = await async_client.get(f"/api/v1/users/{user['id']}")
    assert response1.status_code == status.HTTP_200_OK
    
    # Check cache has the user
    cache_key = f"user:{user['id']}"
    cached_user = await cache.get(cache_key)
    assert cached_user is not None
    assert cached_user["name"] == "Cached User"
    
    # Second request - should hit cache
    response2 = await async_client.get(f"/api/v1/users/{user['id']}")
    assert response2.status_code == status.HTTP_200_OK


# ==================== USER LIST TESTS ====================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_users_empty(async_client):
    """Test listing users when database is empty."""
    response = await async_client.get("/api/v1/users")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["users"] == []
    assert data["total"] == 0
    assert data["page"] == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_users_with_data(async_client, sample_users_data):
    """Test listing users with data."""
    # Create multiple users
    for user_data in sample_users_data:
        await async_client.post("/api/v1/users", json=user_data)
    
    response = await async_client.get("/api/v1/users")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["users"]) == len(sample_users_data)
    assert data["total"] == len(sample_users_data)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_users_pagination(async_client, create_test_user):
    """Test user list pagination."""
    # Create 25 users
    for i in range(25):
        await create_test_user(name=f"User {i}", email=f"user{i}@example.com")
    
    # Page 1
    response1 = await async_client.get("/api/v1/users?page=1&page_size=10")
    assert response1.status_code == status.HTTP_200_OK
    data1 = response1.json()
    assert len(data1["users"]) == 10
    assert data1["total"] == 25
    assert data1["page"] == 1
    
    # Page 2
    response2 = await async_client.get("/api/v1/users?page=2&page_size=10")
    data2 = response2.json()
    assert len(data2["users"]) == 10
    assert data2["page"] == 2
    
    # Page 3 (remaining 5)
    response3 = await async_client.get("/api/v1/users?page=3&page_size=10")
    data3 = response3.json()
    assert len(data3["users"]) == 5


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_users_filter_by_role(async_client, sample_users_data):
    """Test filtering users by role."""
    # Create users
    for user_data in sample_users_data:
        await async_client.post("/api/v1/users", json=user_data)
    
    response = await async_client.get("/api/v1/users?role=admin")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert all(user["role"] == "admin" for user in data["users"])


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_users_filter_by_active_status(async_client, sample_users_data):
    """Test filtering users by active status."""
    # Create users
    for user_data in sample_users_data:
        await async_client.post("/api/v1/users", json=user_data)
    
    response = await async_client.get("/api/v1/users?is_active=false")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert all(user["is_active"] is False for user in data["users"])


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_users_search(async_client, create_test_user):
    """Test searching users by name or email."""
    await create_test_user(name="Alice Smith", email="alice@example.com")
    await create_test_user(name="Bob Johnson", email="bob@example.com")
    await create_test_user(name="Charlie Brown", email="charlie@example.com")
    
    # Search by name
    response = await async_client.get("/api/v1/users?search=alice")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["users"]) == 1
    assert "alice" in data["users"][0]["name"].lower()


# ==================== USER UPDATE TESTS ====================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_user_full(async_client, create_test_user, sample_user_data):
    """Test full user update (PUT)."""
    user = await create_test_user(name="Old Name", email="old@example.com")
    
    update_data = sample_user_data.copy()
    update_data["name"] = "New Name"
    update_data["email"] = "new@example.com"
    
    response = await async_client.put(f"/api/v1/users/{user['id']}", json=update_data)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "New Name"
    assert data["email"] == "new@example.com"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_user_partial(async_client, create_test_user):
    """Test partial user update (PATCH)."""
    user = await create_test_user(name="Original Name", age=25)
    
    update_data = {"age": 26}
    response = await async_client.patch(f"/api/v1/users/{user['id']}", json=update_data)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["age"] == 26
    assert data["name"] == "Original Name"  # Name unchanged


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_user_not_found(async_client):
    """Test updating non-existent user returns 404."""
    update_data = {"name": "New Name"}
    response = await async_client.patch("/api/v1/users/999", json=update_data)
    
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_user_invalidates_cache(async_client, create_test_user, cache):
    """Test that updating user invalidates cache."""
    user = await create_test_user(name="Test User")
    
    # Get user to populate cache
    await async_client.get(f"/api/v1/users/{user['id']}")
    
    # Update user
    await async_client.patch(f"/api/v1/users/{user['id']}", json={"name": "Updated"})
    
    # Cache should be invalidated
    cache_key = f"user:{user['id']}"
    cached_user = await cache.get(cache_key)
    assert cached_user is None


# ==================== USER DELETE TESTS ====================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_user_success(async_client, create_test_user):
    """Test successful user deletion."""
    user = await create_test_user(name="To Delete")
    
    response = await async_client.delete(f"/api/v1/users/{user['id']}")
    
    assert response.status_code == status.HTTP_204_NO_CONTENT
    
    # Verify user is deleted
    get_response = await async_client.get(f"/api/v1/users/{user['id']}")
    assert get_response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_user_not_found(async_client):
    """Test deleting non-existent user returns 404."""
    response = await async_client.delete("/api/v1/users/999")
    
    assert response.status_code == status.HTTP_404_NOT_FOUND


# ==================== USER HEAD TESTS ====================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_head_user_exists(async_client, create_test_user):
    """Test HEAD request for existing user."""
    user = await create_test_user(name="Test", email="test@example.com")
    
    response = await async_client.head(f"/api/v1/users/{user['id']}")
    
    assert response.status_code == status.HTTP_200_OK
    assert response.headers.get("X-User-Exists") == "true"
    assert "test@example.com" in response.headers.get("X-User-Email", "")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_head_user_not_exists(async_client):
    """Test HEAD request for non-existent user."""
    response = await async_client.head("/api/v1/users/999")
    
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.headers.get("X-User-Exists") == "false"


# ==================== USER OPTIONS TESTS ====================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_options_user_endpoint(async_client):
    """Test OPTIONS request returns allowed methods."""
    response = await async_client.options("/api/v1/users/1")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "methods" in data
    assert "GET" in data["methods"]
    assert "POST" in data["methods"]
    assert "PUT" in data["methods"]
    assert "PATCH" in data["methods"]
    assert "DELETE" in data["methods"]


# ==================== PRODUCT TESTS (Basic Coverage) ====================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_product_success(async_client, sample_product_data):
    """Test successful product creation."""
    response = await async_client.post("/api/v1/products", json=sample_product_data)
    
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == sample_product_data["name"]
    assert data["price"] == sample_product_data["price"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_product_by_id(async_client, create_test_product):
    """Test retrieving product by ID."""
    product = await create_test_product(name="Test Product", price=99.99)
    
    response = await async_client.get(f"/api/v1/products/{product['id']}")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == product["id"]
    assert data["name"] == "Test Product"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_products_with_filters(async_client, sample_products_data):
    """Test listing products with filters."""
    # Create products
    for product_data in sample_products_data:
        await async_client.post("/api/v1/products", json=product_data)
    
    # Filter by category
    response = await async_client.get("/api/v1/products?category=Electronics")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert all(product["category"] == "Electronics" for product in data)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_product(async_client, create_test_product):
    """Test updating product."""
    product = await create_test_product(name="Old Product", price=50.00)
    
    update_data = {"price": 75.00}
    response = await async_client.patch(f"/api/v1/products/{product['id']}", json=update_data)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["price"] == 75.00
    assert data["name"] == "Old Product"  # Name unchanged


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_product(async_client, create_test_product):
    """Test deleting product."""
    product = await create_test_product(name="To Delete")
    
    response = await async_client.delete(f"/api/v1/products/{product['id']}")
    
    assert response.status_code == status.HTTP_204_NO_CONTENT
