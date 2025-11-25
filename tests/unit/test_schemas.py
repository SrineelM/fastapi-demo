"""
Unit Tests for Pydantic Schemas

Tests data validation, serialization, and custom validators.
"""

import pytest
from pydantic import ValidationError
from app.schemas.models import (
    UserCreate, UserUpdate, UserResponse,
    ProductCreate, ProductUpdate, ProductResponse,
    OrderCreate, OrderItem, OrderResponse
)


# ==================== USER SCHEMA TESTS ====================

@pytest.mark.unit
def test_user_create_valid():
    """Test creating valid user."""
    user = UserCreate(
        name="John Doe",
        email="john@example.com",
        password="SecurePass123!",
        age=30
    )
    
    assert user.name == "John Doe"
    assert user.email == "john@example.com"
    assert user.age == 30


@pytest.mark.unit
def test_user_create_invalid_email():
    """Test user creation with invalid email fails."""
    with pytest.raises(ValidationError) as exc_info:
        UserCreate(
            name="John Doe",
            email="invalid-email",
            password="SecurePass123!",
            age=30
        )
    
    errors = exc_info.value.errors()
    assert any(error["loc"] == ("email",) for error in errors)


@pytest.mark.unit
def test_user_create_weak_password():
    """Test user creation with weak password fails."""
    with pytest.raises(ValidationError) as exc_info:
        UserCreate(
            name="John Doe",
            email="john@example.com",
            password="weak",
            age=30
        )
    
    errors = exc_info.value.errors()
    assert any("password" in str(error) for error in errors)


@pytest.mark.unit
def test_user_create_age_validation():
    """Test age validation."""
    # Too young
    with pytest.raises(ValidationError):
        UserCreate(
            name="Child",
            email="child@example.com",
            password="SecurePass123!",
            age=5
        )
    
    # Too old
    with pytest.raises(ValidationError):
        UserCreate(
            name="Ancient",
            email="ancient@example.com",
            password="SecurePass123!",
            age=200
        )


@pytest.mark.unit
def test_user_create_default_values():
    """Test default values are applied."""
    user = UserCreate(
        name="John Doe",
        email="john@example.com",
        password="SecurePass123!"
    )
    
    assert user.is_active is True
    assert user.role == "user"


@pytest.mark.unit
def test_user_update_partial():
    """Test partial user update."""
    update = UserUpdate(name="New Name")
    
    assert update.name == "New Name"
    assert update.email is None
    assert update.age is None


@pytest.mark.unit
def test_user_response_excludes_password():
    """Test user response doesn't include password."""
    user_data = {
        "id": 1,
        "name": "John Doe",
        "email": "john@example.com",
        "age": 30,
        "is_active": True,
        "role": "user",
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00"
    }
    
    user = UserResponse(**user_data)
    
    # Verify password field doesn't exist
    assert not hasattr(user, 'password')


# ==================== PRODUCT SCHEMA TESTS ====================

@pytest.mark.unit
def test_product_create_valid():
    """Test creating valid product."""
    product = ProductCreate(
        name="Laptop",
        description="High-performance laptop",
        price=999.99,
        stock=50,
        category="Electronics"
    )
    
    assert product.name == "Laptop"
    assert product.price == 999.99
    assert product.stock == 50


@pytest.mark.unit
def test_product_create_negative_price():
    """Test product with negative price fails."""
    with pytest.raises(ValidationError) as exc_info:
        ProductCreate(
            name="Product",
            price=-10.00,
            stock=10
        )
    
    errors = exc_info.value.errors()
    assert any(error["loc"] == ("price",) for error in errors)


@pytest.mark.unit
def test_product_create_negative_stock():
    """Test product with negative stock fails."""
    with pytest.raises(ValidationError):
        ProductCreate(
            name="Product",
            price=10.00,
            stock=-5
        )


@pytest.mark.unit
def test_product_create_default_values():
    """Test product default values."""
    product = ProductCreate(
        name="Product",
        price=10.00
    )
    
    assert product.stock == 0
    assert product.is_available is True


@pytest.mark.unit
def test_product_update_partial():
    """Test partial product update."""
    update = ProductUpdate(price=19.99)
    
    assert update.price == 19.99
    assert update.name is None
    assert update.stock is None


@pytest.mark.unit
def test_product_response():
    """Test product response schema."""
    product_data = {
        "id": 1,
        "name": "Laptop",
        "description": "High-performance laptop",
        "price": 999.99,
        "stock": 50,
        "category": "Electronics",
        "is_available": True,
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00"
    }
    
    product = ProductResponse(**product_data)
    
    assert product.id == 1
    assert product.name == "Laptop"
    assert product.price == 999.99


# ==================== ORDER SCHEMA TESTS ====================

@pytest.mark.unit
def test_order_item_valid():
    """Test creating valid order item."""
    item = OrderItem(
        product_id=1,
        quantity=2,
        price=99.99
    )
    
    assert item.product_id == 1
    assert item.quantity == 2
    assert item.price == 99.99


@pytest.mark.unit
def test_order_item_invalid_quantity():
    """Test order item with invalid quantity fails."""
    with pytest.raises(ValidationError):
        OrderItem(
            product_id=1,
            quantity=0,  # Must be at least 1
            price=99.99
        )


@pytest.mark.unit
def test_order_create_valid():
    """Test creating valid order."""
    order = OrderCreate(
        user_id=1,
        items=[
            OrderItem(product_id=1, quantity=2, price=99.99),
            OrderItem(product_id=2, quantity=1, price=49.99)
        ]
    )
    
    assert order.user_id == 1
    assert len(order.items) == 2
    assert order.items[0].quantity == 2


@pytest.mark.unit
def test_order_create_empty_items():
    """Test order with empty items fails."""
    with pytest.raises(ValidationError):
        OrderCreate(
            user_id=1,
            items=[]  # Must have at least one item
        )


@pytest.mark.unit
def test_order_create_calculates_total():
    """Test order total is calculated correctly."""
    order = OrderCreate(
        user_id=1,
        items=[
            OrderItem(product_id=1, quantity=2, price=99.99),
            OrderItem(product_id=2, quantity=1, price=49.99)
        ]
    )
    
    expected_total = (2 * 99.99) + (1 * 49.99)
    assert order.total == expected_total


@pytest.mark.unit
def test_order_response():
    """Test order response schema."""
    order_data = {
        "id": 1,
        "user_id": 1,
        "items": [
            {"product_id": 1, "quantity": 2, "price": 99.99},
            {"product_id": 2, "quantity": 1, "price": 49.99}
        ],
        "total": 249.97,
        "status": "pending",
        "created_at": "2024-01-01T00:00:00"
    }
    
    order = OrderResponse(**order_data)
    
    assert order.id == 1
    assert order.user_id == 1
    assert len(order.items) == 2
    assert order.total == 249.97


# ==================== FIELD VALIDATION TESTS ====================

@pytest.mark.unit
def test_string_length_validation():
    """Test string length constraints."""
    # Name too short
    with pytest.raises(ValidationError):
        UserCreate(
            name="A",  # Min length is 2
            email="user@example.com",
            password="SecurePass123!"
        )
    
    # Name too long
    with pytest.raises(ValidationError):
        UserCreate(
            name="A" * 101,  # Max length is 100
            email="user@example.com",
            password="SecurePass123!"
        )


@pytest.mark.unit
def test_email_normalization():
    """Test email is normalized to lowercase."""
    user = UserCreate(
        name="John Doe",
        email="John.Doe@EXAMPLE.COM",
        password="SecurePass123!"
    )
    
    assert user.email == "john.doe@example.com"


@pytest.mark.unit
def test_enum_validation():
    """Test enum field validation."""
    # Valid role
    user = UserCreate(
        name="Admin User",
        email="admin@example.com",
        password="SecurePass123!",
        role="admin"
    )
    assert user.role == "admin"
    
    # Invalid role
    with pytest.raises(ValidationError):
        UserCreate(
            name="Invalid User",
            email="invalid@example.com",
            password="SecurePass123!",
            role="superuser"  # Not in allowed roles
        )


@pytest.mark.unit
def test_optional_fields():
    """Test optional fields can be omitted."""
    product = ProductCreate(
        name="Product",
        price=10.00
    )
    
    assert product.description is None
    assert product.category is None


@pytest.mark.unit
def test_immutable_fields():
    """Test certain fields cannot be updated."""
    update = UserUpdate()
    
    # ID and timestamps should not be updatable
    assert not hasattr(update, 'id')
    assert not hasattr(update, 'created_at')


# ==================== SERIALIZATION TESTS ====================

@pytest.mark.unit
def test_model_to_dict():
    """Test converting model to dictionary."""
    user = UserCreate(
        name="John Doe",
        email="john@example.com",
        password="SecurePass123!",
        age=30
    )
    
    user_dict = user.model_dump()
    
    assert isinstance(user_dict, dict)
    assert user_dict["name"] == "John Doe"
    assert user_dict["email"] == "john@example.com"


@pytest.mark.unit
def test_model_to_json():
    """Test converting model to JSON."""
    user = UserCreate(
        name="John Doe",
        email="john@example.com",
        password="SecurePass123!",
        age=30
    )
    
    user_json = user.model_dump_json()
    
    assert isinstance(user_json, str)
    assert "John Doe" in user_json


@pytest.mark.unit
def test_nested_model_serialization():
    """Test serializing nested models."""
    order = OrderCreate(
        user_id=1,
        items=[
            OrderItem(product_id=1, quantity=2, price=99.99),
            OrderItem(product_id=2, quantity=1, price=49.99)
        ]
    )
    
    order_dict = order.model_dump()
    
    assert isinstance(order_dict["items"], list)
    assert isinstance(order_dict["items"][0], dict)
    assert order_dict["items"][0]["product_id"] == 1


@pytest.mark.unit
def test_exclude_fields_in_serialization():
    """Test excluding fields during serialization."""
    user_data = {
        "id": 1,
        "name": "John Doe",
        "email": "john@example.com",
        "age": 30,
        "is_active": True,
        "role": "user",
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00"
    }
    
    user = UserResponse(**user_data)
    
    # Exclude email from serialization
    user_dict = user.model_dump(exclude={"email"})
    
    assert "email" not in user_dict
    assert "name" in user_dict
