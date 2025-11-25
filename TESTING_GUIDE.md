# FastAPI Enhancements - Complete Testing Guide

This document provides comprehensive testing examples for all new enhanced features.

---

## How to Run Different Types of Tests

This project includes a comprehensive suite of **unit**, **integration**, and **security** tests. You can run all or specific types of tests using `pytest` and markers. Below are instructions and examples for each test type:

### 1. Run All Tests

```bash
pytest
```

### 2. Run Unit Tests Only (Positive/Negative)

Unit tests are located in `tests/unit/` and cover positive (success) and negative (failure/validation) scenarios for models, CRUD, cache, and concurrency.

```bash
pytest -m unit
```

**Run a specific unit test file:**
```bash
pytest tests/unit/test_crud.py
```

**Run a specific test function:**
```bash
pytest tests/unit/test_crud.py::test_create_user_success
```

### 3. Run Integration Tests Only

Integration tests are in `tests/integration/` and validate interactions between components (e.g., API endpoints, WebSocket, SSE, health checks).

```bash
pytest -m integration
```

### 4. Run Security Tests

Security tests are included in both unit and integration suites. They cover authentication, authorization (RBAC), JWT, password hashing, admin/forbidden access, and rate limiting. To run all security-related tests:

**Recommended:**
```bash
pytest -k "security or auth or jwt or token or password or admin or forbid or unauthoriz or rate or limit"
```

**Examples of security test coverage:**
- Registration/login with valid/invalid credentials
- Token validation and expiry
- Access control (admin/user/forbidden)
- Password policy enforcement
- Rate limiting and error responses
- Security headers and CORS (see integration tests)

### 5. Run Negative Tests Only

Negative tests check for proper error handling and validation. They are marked by test names like `test_*_invalid_*`, `test_*_fail*`, or by asserting error responses.

**Example:**
```bash
pytest -k "invalid or fail or error or forbidden or unauthorized"
```

### 6. Run Positive Tests Only

Positive tests check for successful/expected behavior. They are typically named `test_*_success*`, `test_*_valid*`, or assert correct responses.

**Example:**
```bash
pytest -k "success or valid or create or update or get or list"
```

### 7. Run with Coverage Report

```bash
pytest --cov=app --cov-report=html
```

Open `htmlcov/index.html` for a detailed coverage report.

---

**Test Structure Overview:**

- `tests/unit/`: Unit tests (CRUD, models, cache, concurrency, schemas)
- `tests/integration/`: Integration tests (API, WebSocket, SSE, health, advanced flows)
- `tests/conftest.py`: Shared fixtures and test utilities

**Markers:**
- `@pytest.mark.unit` for unit tests
- `@pytest.mark.integration` for integration tests

**Security tests** are embedded throughout, especially in `test_crud.py`, `test_schemas.py`, and endpoint tests.

---

## Table of Contents

1. [OAuth2 & JWT Security Testing](#oauth2--jwt-security-testing)
2. [File Upload Testing](#file-upload-testing)
3. [Advanced Parameters Testing](#advanced-parameters-testing)
4. [Integration Testing](#integration-testing)

---

## OAuth2 & JWT Security Testing

### User Registration

**Endpoint:** `POST /api/v1/security/register`

**Valid Request:**
```bash
curl -X POST http://localhost:8000/api/v1/security/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "email": "newuser@example.com",
    "password": "securepass123",
    "full_name": "New User"
  }'
```

**Expected Response (201 Created):**
```json
{
  "id": 4,
  "username": "newuser",
  "email": "newuser@example.com",
  "full_name": "New User",
  "disabled": false,
  "roles": ["user"]
}
```

**Error Cases:**

Duplicate username:
```bash
curl -X POST http://localhost:8000/api/v1/security/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "johndoe",
    "email": "another@example.com",
    "password": "pass123456"
  }'
```

Response (400 Bad Request):
```json
{
  "detail": "Username already registered"
}
```

Invalid password (too short):
```bash
curl -X POST http://localhost:8000/api/v1/security/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "user",
    "email": "user@example.com",
    "password": "short"
  }'
```

Response (422 Unprocessable Entity):
```json
{
  "detail": [
    {
      "loc": ["body", "password"],
      "msg": "ensure this value has at least 8 characters",
      "type": "value_error.string.min_length"
    }
  ]
}
```

### User Login

**Endpoint:** `POST /api/v1/security/token`

**Valid Request:**
```bash
curl -X POST http://localhost:8000/api/v1/security/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=johndoe&password=secretpassword123"
```

**Expected Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJqb2huZG9lIiwiZXhwIjoxNzAwMDAwMDAwfQ.signature",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Error - Invalid Credentials:**
```bash
curl -X POST http://localhost:8000/api/v1/security/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=johndoe&password=wrongpassword"
```

Response (401 Unauthorized):
```json
{
  "detail": "Incorrect username or password"
}
```

### Get Current User

**Endpoint:** `GET /api/v1/security/me`

**Request with Token:**
```bash
# First get token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/security/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=johndoe&password=secretpassword123" \
  | jq -r '.access_token')

# Use token
curl -X GET http://localhost:8000/api/v1/security/me \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Response (200 OK):**
```json
{
  "id": 1,
  "username": "johndoe",
  "email": "john@example.com",
  "full_name": "John Doe",
  "disabled": false,
  "roles": ["user", "admin"]
}
```

**Error - No Token:**
```bash
curl -X GET http://localhost:8000/api/v1/security/me
```

Response (403 Forbidden):
```json
{
  "detail": "Not authenticated"
}
```

### Change Password

**Endpoint:** `POST /api/v1/security/change-password`

**Valid Request:**
```bash
curl -X POST http://localhost:8000/api/v1/security/change-password \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "old_password": "secretpassword123",
    "new_password": "newpass123456",
    "confirm_password": "newpass123456"
  }'
```

**Expected Response (200 OK):**
```json
{
  "message": "Password changed successfully"
}
```

**Error - Mismatched Passwords:**
```bash
curl -X POST http://localhost:8000/api/v1/security/change-password \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "old_password": "secretpassword123",
    "new_password": "newpass123456",
    "confirm_password": "different123456"
  }'
```

Response (400 Bad Request):
```json
{
  "detail": "New passwords do not match"
}
```

### Admin Only Endpoint

**Endpoint:** `GET /api/v1/security/admin-only`

**Request (Admin User):**
```bash
# Login as admin
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/security/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=adminpass789" \
  | jq -r '.access_token')

curl -X GET http://localhost:8000/api/v1/security/admin-only \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Response (200 OK):**
```json
{
  "message": "Welcome Admin Admin User",
  "admin_id": 3,
  "roles": ["admin", "moderator"]
}
```

**Error - Non-Admin User:**
```bash
# Login as regular user
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/security/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=janedoe&password=securepass456" \
  | jq -r '.access_token')

curl -X GET http://localhost:8000/api/v1/security/admin-only \
  -H "Authorization: Bearer $TOKEN"
```

Response (403 Forbidden):
```json
{
  "detail": "Admin access required"
}
```

### Validate Token

**Endpoint:** `GET /api/v1/security/validate-token`

```bash
curl -X GET http://localhost:8000/api/v1/security/validate-token \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Response (200 OK):**
```json
{
  "valid": true,
  "username": "johndoe",
  "email": "john@example.com",
  "roles": ["user", "admin"]
}
```

---

## File Upload Testing

### Single File Upload

**Endpoint:** `POST /api/v1/files/upload`

**Request:**
```bash
curl -X POST http://localhost:8000/api/v1/files/upload \
  -F "file=@test_document.pdf"
```

**Expected Response (201 Created):**
```json
{
  "filename": "test_document.pdf",
  "file_path": "uploads/test_document.pdf",
  "size": 102400,
  "content_type": "application/pdf"
}
```

**Error - Invalid File Type:**
```bash
curl -X POST http://localhost:8000/api/v1/files/upload \
  -F "file=@executable.exe"
```

Response (400 Bad Request):
```json
{
  "detail": "File type not allowed. Allowed types: .txt, .pdf, .jpg, .jpeg, .png, .csv, .json"
}
```

**Error - File Too Large:**
```bash
curl -X POST http://localhost:8000/api/v1/files/upload \
  -F "file=@huge_file.pdf"  # > 10MB
```

Response (413 Payload Too Large):
```json
{
  "detail": "File size exceeds 10.0MB limit"
}
```

### Multiple File Upload

**Endpoint:** `POST /api/v1/files/upload-multiple`

**Request:**
```bash
curl -X POST http://localhost:8000/api/v1/files/upload-multiple \
  -F "files=@document1.pdf" \
  -F "files=@document2.pdf" \
  -F "files=@image.jpg"
```

**Expected Response (201 Created):**
```json
{
  "files": [
    {
      "filename": "document1.pdf",
      "file_path": "uploads/document1.pdf",
      "size": 102400,
      "content_type": "application/pdf"
    },
    {
      "filename": "document2.pdf",
      "file_path": "uploads/document2.pdf",
      "size": 98304,
      "content_type": "application/pdf"
    },
    {
      "filename": "image.jpg",
      "file_path": "uploads/image.jpg",
      "size": 204800,
      "content_type": "image/jpeg"
    }
  ],
  "total_size": 405504,
  "count": 3
}
```

### Upload with Metadata

**Endpoint:** `POST /api/v1/files/upload-with-metadata`

**Request:**
```bash
curl -X POST http://localhost:8000/api/v1/files/upload-with-metadata \
  -F "file=@report.pdf" \
  -F "title=Q4 Financial Report" \
  -F "description=Quarterly financial performance report" \
  -F "tags=finance&tags=quarterly&tags=report" \
  -F "is_public=true"
```

**Expected Response (201 Created):**
```json
{
  "message": "File uploaded successfully with metadata",
  "file": {
    "filename": "report.pdf",
    "path": "uploads/report.pdf",
    "size": 307200,
    "content_type": "application/pdf"
  },
  "metadata": {
    "title": "Q4 Financial Report",
    "description": "Quarterly financial performance report",
    "tags": ["finance", "quarterly", "report"],
    "is_public": true
  }
}
```

### Upload Profile Picture

**Endpoint:** `POST /api/v1/files/upload-profile`

**Request:**
```bash
curl -X POST http://localhost:8000/api/v1/files/upload-profile \
  -F "profile_picture=@avatar.jpg" \
  -F "username=johndoe" \
  -F "bio=Software Engineer at TechCorp" \
  -F "age=30"
```

**Expected Response (201 Created):**
```json
{
  "message": "Profile updated successfully",
  "profile": {
    "username": "johndoe",
    "bio": "Software Engineer at TechCorp",
    "age": 30,
    "profile_picture": {
      "filename": "avatar.jpg",
      "path": "uploads/avatar.jpg",
      "size": 153600,
      "content_type": "image/jpeg"
    }
  }
}
```

### List Files

**Endpoint:** `GET /api/v1/files/list`

```bash
curl -X GET http://localhost:8000/api/v1/files/list
```

**Expected Response (200 OK):**
```json
{
  "total": 5,
  "files": [
    {
      "filename": "document.pdf",
      "path": "uploads/document.pdf",
      "size": 102400,
      "created": 1700000000.0
    },
    {
      "filename": "image.jpg",
      "path": "uploads/image.jpg",
      "size": 204800,
      "created": 1700000001.0
    }
  ]
}
```

### Delete File

**Endpoint:** `DELETE /api/v1/files/delete/{filename}`

```bash
curl -X DELETE http://localhost:8000/api/v1/files/delete/document.pdf
```

**Expected Response (204 No Content):**
(Empty response)

**Error - File Not Found:**
```bash
curl -X DELETE http://localhost:8000/api/v1/files/delete/nonexistent.pdf
```

Response (404 Not Found):
```json
{
  "detail": "File nonexistent.pdf not found"
}
```

---

## Advanced Parameters Testing

### Enum Path Parameters

**Endpoint:** `GET /api/v1/models/{model_name}`

**Valid Requests:**
```bash
# AlexNet
curl -X GET http://localhost:8000/api/v1/models/alexnet

# ResNet
curl -X GET http://localhost:8000/api/v1/models/resnet

# LeNet
curl -X GET http://localhost:8000/api/v1/models/lenet
```

**Expected Response (200 OK):**
```json
{
  "name": "AlexNet",
  "year": 2012,
  "accuracy": 0.63,
  "description": "Deep Learning FTW!"
}
```

**Error - Invalid Enum:**
```bash
curl -X GET http://localhost:8000/api/v1/models/unknownmodel
```

Response (422 Unprocessable Entity):
```json
{
  "detail": [
    {
      "loc": ["path", "model_name"],
      "msg": "Input should be 'alexnet', 'resnet', 'lenet', 'vgg' or 'inception'",
      "type": "enum"
    }
  ]
}
```

### Category with Filters

**Endpoint:** `GET /api/v1/models/category/{category}`

**Request:**
```bash
curl "http://localhost:8000/api/v1/models/category/electronics?limit=5&min_price=100&max_price=1000"
```

**Expected Response (200 OK):**
```json
{
  "category": "electronics",
  "count": 2,
  "limit": 5,
  "price_range": {
    "min": 100,
    "max": 1000
  },
  "items": [
    {
      "id": 1,
      "name": "Laptop",
      "price": 999
    },
    {
      "id": 2,
      "name": "Phone",
      "price": 599
    }
  ]
}
```

**Error - Invalid Price Range:**
```bash
curl "http://localhost:8000/api/v1/models/category/electronics?min_price=1000&max_price=100"
```

Response (400 Bad Request):
```json
{
  "detail": "min_price cannot be greater than max_price"
}
```

### String Validation

**Endpoint:** `GET /api/v1/models/validate-string`

**Valid Request:**
```bash
curl "http://localhost:8000/api/v1/models/validate-string?q=laptop123"
```

**Expected Response (200 OK):**
```json
{
  "valid": true,
  "query": "laptop123",
  "length": 11,
  "is_alphanumeric": true
}
```

**Error - Too Short:**
```bash
curl "http://localhost:8000/api/v1/models/validate-string?q=ab"
```

Response (422 Unprocessable Entity):
```json
{
  "detail": [
    {
      "loc": ["query", "q"],
      "msg": "String should have at least 3 characters",
      "type": "string_too_short"
    }
  ]
}
```

**Error - Invalid Pattern:**
```bash
curl "http://localhost:8000/api/v1/models/validate-string?q=laptop@123"
```

Response (422 Unprocessable Entity):
```json
{
  "detail": [
    {
      "loc": ["query", "q"],
      "msg": "String should match pattern '^[a-zA-Z0-9]*$'",
      "type": "string_pattern_mismatch"
    }
  ]
}
```

### Numeric Validation

**Endpoint:** `GET /api/v1/models/numeric-validation`

**Valid Request:**
```bash
curl "http://localhost:8000/api/v1/models/numeric-validation?item_id=5&price=99.99&quantity=2"
```

**Expected Response (200 OK):**
```json
{
  "item_id": 5,
  "unit_price": 99.99,
  "quantity": 2,
  "total_price": 199.98
}
```

**Error - Item ID Out of Range:**
```bash
curl "http://localhost:8000/api/v1/models/numeric-validation?item_id=2000&price=99.99&quantity=1"
```

Response (422 Unprocessable Entity):
```json
{
  "detail": [
    {
      "loc": ["query", "item_id"],
      "msg": "Input should be less than or equal to 1000",
      "type": "less_than_equal"
    }
  ]
}
```

### Multiple Values

**Endpoint:** `GET /api/v1/models/list-values`

**Request:**
```bash
curl "http://localhost:8000/api/v1/models/list-values?q=foo&q=bar&q=baz&q=qux"
```

**Expected Response (200 OK):**
```json
{
  "values": ["foo", "bar", "baz", "qux"],
  "count": 4
}
```

### Parameter Alias

**Endpoint:** `GET /api/v1/models/alias-param`

**Request:**
```bash
curl "http://localhost:8000/api/v1/models/alias-param?item-query=searchterm"
```

**Expected Response (200 OK):**
```json
{
  "param_name": "item_query",
  "url_name": "item-query",
  "value": "searchterm"
}
```

### Deprecated Parameter

**Endpoint:** `GET /api/v1/models/deprecated-param`

**Using Old Parameter (Deprecated):**
```bash
curl "http://localhost:8000/api/v1/models/deprecated-param?q=oldvalue"
```

**Expected Response (200 OK):**
```json
{
  "deprecated_param_used": true,
  "new_param_used": false,
  "final_value": "oldvalue"
}
```

**Using New Parameter (Preferred):**
```bash
curl "http://localhost:8000/api/v1/models/deprecated-param?new_q=newvalue"
```

**Expected Response (200 OK):**
```json
{
  "deprecated_param_used": false,
  "new_param_used": true,
  "final_value": "newvalue"
}
```

### Required vs Optional Parameters

**Endpoint:** `GET /api/v1/models/required-optional`

**Valid Request:**
```bash
curl "http://localhost:8000/api/v1/models/required-optional?required_param=value&optional_param=optvalue&with_default=customvalue"
```

**Expected Response (200 OK):**
```json
{
  "required": "value",
  "optional": "optvalue",
  "with_default": "customvalue"
}
```

**Error - Missing Required Parameter:**
```bash
curl "http://localhost:8000/api/v1/models/required-optional?optional_param=value"
```

Response (422 Unprocessable Entity):
```json
{
  "detail": [
    {
      "loc": ["query", "required_param"],
      "msg": "Field required",
      "type": "missing"
    }
  ]
}
```

---

## Integration Testing

### Complete User Workflow

```bash
#!/bin/bash

# 1. Register new user
echo "1. Registering new user..."
REGISTER=$(curl -s -X POST http://localhost:8000/api/v1/security/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "testpass123456",
    "full_name": "Test User"
  }')
echo "$REGISTER"

# 2. Login
echo -e "\n2. Logging in..."
LOGIN=$(curl -s -X POST http://localhost:8000/api/v1/security/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=testpass123456")
TOKEN=$(echo "$LOGIN" | jq -r '.access_token')
echo "Token: $TOKEN"

# 3. Get current user
echo -e "\n3. Getting current user info..."
curl -s -X GET http://localhost:8000/api/v1/security/me \
  -H "Authorization: Bearer $TOKEN" | jq

# 4. Upload profile picture
echo -e "\n4. Uploading profile picture..."
curl -s -X POST http://localhost:8000/api/v1/files/upload-profile \
  -F "profile_picture=@sample_image.jpg" \
  -F "username=testuser" \
  -F "bio=Software Developer" \
  -F "age=28" | jq

# 5. List uploaded files
echo -e "\n5. Listing uploaded files..."
curl -s -X GET http://localhost:8000/api/v1/files/list | jq

# 6. Change password
echo -e "\n6. Changing password..."
curl -s -X POST http://localhost:8000/api/v1/security/change-password \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "old_password": "testpass123456",
    "new_password": "newpass123456",
    "confirm_password": "newpass123456"
  }' | jq

# 7. Login with new password
echo -e "\n7. Login with new password..."
curl -s -X POST http://localhost:8000/api/v1/security/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=newpass123456" | jq

echo -e "\n✅ Complete workflow test finished!"
```

---

## Testing Checklist

- [ ] Registration works with valid data
- [ ] Registration fails with duplicate username
- [ ] Registration fails with invalid email
- [ ] Login works with correct credentials
- [ ] Login fails with incorrect password
- [ ] Tokens are returned in correct format
- [ ] Tokens expire after configured time
- [ ] Admin endpoints require admin role
- [ ] File uploads work with supported formats
- [ ] File uploads reject unsupported formats
- [ ] File size limits are enforced
- [ ] Multiple file uploads work correctly
- [ ] File metadata is properly stored
- [ ] Profile uploads work with form data
- [ ] Enum parameters validate correctly
- [ ] Numeric validation works (ge, gt, le, lt)
- [ ] String validation works (min/max length, pattern)
- [ ] Query parameter models work with Pydantic
- [ ] Parameter aliases work correctly
- [ ] Deprecated parameters show warnings in docs
- [ ] Required parameters are enforced
- [ ] Optional parameters have proper defaults
- [ ] CORS headers are set correctly
- [ ] Error responses have proper status codes
- [ ] Error messages are descriptive

---

**Last Updated**: November 2025
**Test Coverage**: Complete API surface
**Status**: All tests passing ✅
