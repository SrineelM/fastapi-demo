# FastAPI Development Guidelines

## Table of Contents

1. [Code Style](#code-style)
2. [Project Structure](#project-structure)
3. [Naming Conventions](#naming-conventions)
4. [API Design](#api-design)
5. [Error Handling](#error-handling)
6. [Testing](#testing)
7. [Security](#security)
8. [Performance](#performance)
9. [Documentation](#documentation)
10. [Git Workflow](#git-workflow)

---

## Code Style

### Python Standards

Follow **PEP 8** with these specific conventions:

```python
# ✅ Good
async def get_user_by_id(user_id: int) -> UserResponse:
    """Retrieve user by ID from database.
    
    Args:
        user_id: Unique identifier for the user
        
    Returns:
        UserResponse object with user data
        
    Raises:
        HTTPException: 404 if user not found
    """
    user = await db.read("users", user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(**user)

# ❌ Bad
def getUserById(userId):
    user = db.read("users", userId)
    return user
```

### Type Hints

**Always** use type hints for function parameters and return values:

```python
# ✅ Good
from typing import List, Optional

async def list_users(
    page: int = 1,
    page_size: int = 10,
    role: Optional[str] = None
) -> List[UserResponse]:
    pass

# ❌ Bad
async def list_users(page=1, page_size=10, role=None):
    pass
```

### Imports Organization

Order imports as follows:

```python
# 1. Standard library
import asyncio
import logging
from typing import List, Optional

# 2. Third-party packages
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

# 3. Local imports
from app.core.config import get_settings
from app.db.memory import get_db
from app.schemas.models import UserResponse
```

### Code Formatting

Use **Black** for automatic formatting:

```bash
black app/ tests/ --line-length 100
```

Use **isort** for import sorting:

```bash
isort app/ tests/ --profile black
```

---

## Project Structure

### Directory Organization

```
app/
├── api/              # API endpoints
│   └── routes/       # Route handlers grouped by feature
├── core/             # Core functionality (config, logging, security)
├── db/               # Database layer
├── middleware/       # Custom middleware
├── schemas/          # Pydantic models
├── services/         # Business logic services
└── utils/            # Utility functions
```

### File Naming

- **Files**: `snake_case.py`
- **Classes**: `PascalCase`
- **Functions/Variables**: `snake_case`
- **Constants**: `UPPER_SNAKE_CASE`

### Module Guidelines

- Keep modules focused on single responsibility
- Maximum file length: 500 lines
- Extract common functionality to utilities

---

## Naming Conventions

### Endpoints

Use RESTful conventions:

```python
# ✅ Good
@router.post("/users")              # Create
@router.get("/users/{user_id}")     # Read one
@router.get("/users")               # Read many
@router.put("/users/{user_id}")     # Full update
@router.patch("/users/{user_id}")   # Partial update
@router.delete("/users/{user_id}")  # Delete

# ❌ Bad
@router.post("/create_user")
@router.get("/get_user")
@router.post("/user/update")
```

### Route Functions

Name route functions descriptively:

```python
# ✅ Good
@router.post("/users", status_code=201)
async def create_user(user: UserCreate) -> UserResponse:
    pass

@router.get("/users/{user_id}")
async def get_user(user_id: int) -> UserResponse:
    pass

# ❌ Bad
@router.post("/users")
async def user_post(data: dict):
    pass
```

### Database Functions

Use CRUD naming:

```python
# ✅ Good
async def create_user(data: dict) -> dict:
    pass

async def read_user(user_id: int) -> Optional[dict]:
    pass

async def update_user(user_id: int, data: dict) -> dict:
    pass

async def delete_user(user_id: int) -> bool:
    pass
```

---

## API Design

### Request/Response Models

Always use Pydantic models:

```python
# ✅ Good
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    age: Optional[int] = None

@router.post("/users")
async def create_user(user: UserCreate) -> UserResponse:
    pass

# ❌ Bad
@router.post("/users")
async def create_user(data: dict):
    pass
```

### Path vs Query Parameters

```python
# Path parameters: Required identifiers
@router.get("/users/{user_id}")
async def get_user(user_id: int):
    pass

# Query parameters: Optional filters/pagination
@router.get("/users")
async def list_users(
    page: int = 1,
    page_size: int = 10,
    role: Optional[str] = None
):
    pass
```

### Status Codes

Use appropriate HTTP status codes:

```python
# ✅ Good
@router.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate):
    pass

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int):
    pass

# Common codes:
# 200 OK - Successful GET, PUT, PATCH
# 201 Created - Successful POST
# 204 No Content - Successful DELETE
# 400 Bad Request - Validation error
# 401 Unauthorized - Authentication required
# 403 Forbidden - Not allowed
# 404 Not Found - Resource doesn't exist
# 500 Internal Server Error - Server error
```

### Pagination

Standardize pagination:

```python
class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int
    pages: int

@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100)
) -> PaginatedResponse:
    pass
```

---

## Error Handling

### HTTP Exceptions

Use FastAPI's HTTPException:

```python
from fastapi import HTTPException, status

# ✅ Good
@router.get("/users/{user_id}")
async def get_user(user_id: int):
    user = await db.read("users", user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )
    return user

# ❌ Bad
@router.get("/users/{user_id}")
async def get_user(user_id: int):
    user = await db.read("users", user_id)
    if not user:
        return {"error": "Not found"}  # Wrong!
```

### Custom Exception Handlers

```python
from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)}
    )
```

### Validation Errors

Let Pydantic handle validation:

```python
class UserCreate(BaseModel):
    email: EmailStr  # Validates email format
    age: int = Field(ge=18, le=120)  # Age constraints
    
    @field_validator('name')
    def validate_name(cls, v):
        if len(v) < 2:
            raise ValueError("Name must be at least 2 characters")
        return v
```

---

## Testing

### Test Organization

```
tests/
├── unit/              # Unit tests (fast, isolated)
│   ├── test_crud.py
│   ├── test_database.py
│   └── test_schemas.py
├── integration/       # Integration tests
│   └── test_advanced.py
└── conftest.py        # Shared fixtures
```

### Test Naming

```python
# ✅ Good
def test_create_user_success():
    pass

def test_create_user_duplicate_email():
    pass

def test_get_user_not_found():
    pass

# ❌ Bad
def test_user_creation():
    pass

def test1():
    pass
```

### Test Structure (AAA Pattern)

```python
@pytest.mark.asyncio
async def test_create_user_success(async_client, sample_user_data):
    # Arrange
    user_data = sample_user_data
    
    # Act
    response = await async_client.post("/api/v1/users", json=user_data)
    
    # Assert
    assert response.status_code == 201
    assert response.json()["email"] == user_data["email"]
```

### Fixtures

Use fixtures for reusable test data:

```python
@pytest.fixture
async def create_test_user(async_client):
    """Factory fixture for creating test users."""
    async def _create(name="Test User", **kwargs):
        data = {"name": name, "email": f"{name.lower()}@test.com", **kwargs}
        response = await async_client.post("/api/v1/users", json=data)
        return response.json()
    return _create
```

### Coverage Requirements

- Minimum coverage: **90%**
- Critical paths: **100%**

```bash
pytest --cov=app --cov-report=html --cov-report=term-missing
```

---

## Security

### Authentication

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def get_current_user(token: str = Depends(security)):
    """Verify JWT token and return user."""
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

### Password Handling

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ✅ Good
hashed_password = pwd_context.hash(plain_password)
is_valid = pwd_context.verify(plain_password, hashed_password)

# ❌ Bad - Never store plain text passwords
user.password = plain_password  # Wrong!
```

### Input Validation

```python
# ✅ Good - Use Pydantic validators
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    
    @field_validator('password')
    def validate_password(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain digit")
        return v
```

### Sensitive Data

```python
# ✅ Good - Exclude sensitive fields
class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    
    model_config = ConfigDict(from_attributes=True)
    # password is NOT included

# ❌ Bad
class User(BaseModel):
    id: int
    name: str
    password: str  # Don't expose!
```

---

## Performance

### Async/Await

```python
# ✅ Good - Use async for I/O operations
@router.get("/users/{user_id}")
async def get_user(user_id: int):
    user = await db.read("users", user_id)  # Non-blocking
    return user

# ❌ Bad - Blocking in async context
@router.get("/users/{user_id}")
async def get_user(user_id: int):
    user = db.read_sync("users", user_id)  # Blocks event loop!
    return user
```

### Database Queries

```python
# ✅ Good - Single query with filter
users = await db.find_by_field("users", "role", "admin")

# ❌ Bad - Multiple queries
all_users = await db.read_all("users")
admin_users = [u for u in all_users if u["role"] == "admin"]
```

### Caching

```python
from app.services.cache import cache_result

# ✅ Good - Cache expensive operations
@cache_result(ttl=300)
async def get_user_stats(user_id: int):
    # Expensive calculation
    return stats

# Cache invalidation
@router.patch("/users/{user_id}")
async def update_user(user_id: int, data: UserUpdate):
    await cache.delete(f"user:{user_id}")
    await cache.delete_pattern(f"user:{user_id}:*")
    return updated_user
```

### Background Tasks

```python
from fastapi import BackgroundTasks

@router.post("/users")
async def create_user(user: UserCreate, background_tasks: BackgroundTasks):
    # Create user immediately
    created_user = await db.create("users", user.model_dump())
    
    # Send welcome email in background
    background_tasks.add_task(send_welcome_email, created_user["email"])
    
    return created_user
```

---

## Documentation

### Docstrings

Use Google-style docstrings:

```python
async def create_user(user: UserCreate) -> UserResponse:
    """Create a new user in the database.
    
    Args:
        user: User creation data including name, email, password
        
    Returns:
        UserResponse: Created user with generated ID and timestamps
        
    Raises:
        HTTPException: 400 if email already exists
        
    Example:
        >>> user = UserCreate(name="John", email="john@example.com", password="Pass123!")
        >>> created = await create_user(user)
        >>> print(created.id)
        1
    """
    pass
```

### API Documentation

Add descriptions and examples:

```python
@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new user",
    description="Create a new user with email and password. Email must be unique.",
    response_description="Created user object with generated ID"
)
async def create_user(
    user: UserCreate = Body(
        ...,
        example={
            "name": "John Doe",
            "email": "john@example.com",
            "password": "SecurePass123!",
            "age": 30
        }
    )
):
    pass
```

### Comments

```python
# ✅ Good - Explain WHY, not WHAT
# Use thread pool for blocking I/O to prevent blocking event loop
result = await run_in_thread_pool(blocking_function)

# ❌ Bad - Obvious comment
# Create a user
user = await db.create("users", data)
```

---

## Git Workflow

### Commit Messages

Follow conventional commits:

```
feat: add user authentication endpoint
fix: resolve cache invalidation bug
docs: update API documentation
test: add tests for user CRUD operations
refactor: extract validation logic to utility
perf: optimize database queries
chore: update dependencies
```

### Branch Naming

```
feature/user-authentication
bugfix/cache-invalidation
hotfix/security-vulnerability
refactor/database-layer
```

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No new warnings
```

---

## Best Practices Summary

### DO ✅

- Use type hints everywhere
- Write async functions for I/O operations
- Validate input with Pydantic
- Handle errors with HTTPException
- Write tests for all endpoints
- Document with docstrings
- Use dependency injection
- Cache expensive operations
- Log structured data
- Use environment variables for config

### DON'T ❌

- Block the event loop with sync operations
- Use `dict` instead of Pydantic models
- Store passwords in plain text
- Expose sensitive data in responses
- Write functions longer than 50 lines
- Use global mutable state
- Commit without tests
- Hard-code configuration
- Ignore type errors
- Skip error handling

---

## Code Review Checklist

Before submitting code for review:

- [ ] All tests pass
- [ ] Type checking passes (`mypy app/`)
- [ ] Linting passes (`flake8 app/`)
- [ ] Code is formatted (`black app/`)
- [ ] Coverage is maintained or improved
- [ ] Documentation is updated
- [ ] No sensitive data in code
- [ ] Error handling is comprehensive
- [ ] Logging is appropriate
- [ ] Performance is acceptable

---

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [PEP 8 Style Guide](https://pep8.org/)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [Async/Await Guide](https://docs.python.org/3/library/asyncio.html)

---

**Last Updated:** November 16, 2025
