"""
Advanced Parameter Handling Routes Module

Demonstrates:
- Path parameters with Enum values (predefined choices)
- Complex query parameter validation
- Query parameter models with Pydantic
- Numeric validation constraints
- String pattern validation
- Multiple query parameters
- Required vs optional parameters

This module showcases advanced parameter handling patterns from FastAPI documentation.
"""

from enum import Enum  # For defining enumerations (enums) used in path/query parameters
from typing import Annotated, List  # Annotated for parameter metadata, List for type hints

from fastapi import APIRouter, Query, Path, HTTPException, status  # FastAPI core imports for routing, parameter validation, and HTTP errors
from pydantic import BaseModel, Field  # Pydantic for data validation and schema generation

from app.core.logging import get_logger  # Project's custom logger for structured logging

logger = get_logger(__name__)

# Create router
advanced_params_router = APIRouter(prefix="/models", tags=["Advanced Parameters"])


# ==================== ENUM DEFINITIONS ====================

class ModelName(str, Enum):
    """Available ML models"""
    alexnet = "alexnet"
    resnet = "resnet"
    lenet = "lenet"
    vgg = "vgg"
    inception = "inception"


class SortOrder(str, Enum):
    """Sort order options"""
    asc = "ascending"
    desc = "descending"


class ItemCategory(str, Enum):
    """Product categories"""
    electronics = "electronics"
    clothing = "clothing"
    books = "books"
    home = "home"
    sports = "sports"


class FilterParams(BaseModel):
    """Complex query parameter model"""
    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of items to return"
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Number of items to skip"
    )
    sort_by: str = Field(
        default="created_at",
        description="Field to sort by"
    )
    sort_order: SortOrder = Field(
        default=SortOrder.desc,
        description="Sort in ascending or descending order"
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Filter by tags"
    )
    search: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Search query string"
    )


# ==================== ENDPOINTS ====================

@advanced_params_router.get(
    "/{model_name}",
    summary="Get ML model by name",
    description="Retrieve ML model details by predefined enum value"
)
async def get_model(
    model_name: Annotated[
        ModelName,
        Path(title="Model name", description="One of: alexnet, resnet, lenet, vgg, inception")
    ]
) -> dict:
    """
    Get ML model by enumerated name.
    
    Demonstrates path parameter with Enum validation.
    FastAPI automatically validates and shows available options in docs.
    
    Args:
        model_name: ML model name (enum value)
        
    Returns:
        Model information
    """
    model_info = {
        ModelName.alexnet: {
            "name": "AlexNet",
            "year": 2012,
            "accuracy": 0.63,
            "description": "Deep Learning FTW!"
        },
        ModelName.resnet: {
            "name": "ResNet",
            "year": 2015,
            "accuracy": 0.776,
            "description": "Have some residuals"
        },
        ModelName.lenet: {
            "name": "LeNet",
            "year": 1998,
            "accuracy": 0.99,
            "description": "LeCNN all the images"
        },
        ModelName.vgg: {
            "name": "VGG",
            "year": 2014,
            "accuracy": 0.928,
            "description": "Very deep networks"
        },
        ModelName.inception: {
            "name": "Inception",
            "year": 2014,
            "accuracy": 0.936,
            "description": "Going deeper with convolutions"
        }
    }
    
    logger.info("Model retrieved", model=model_name.value)
    return model_info[model_name]


@advanced_params_router.get(
    "/category/{category}",
    summary="Get items by category",
    description="Filter items by product category enum"
)
async def get_items_by_category(
    category: Annotated[
        ItemCategory,
        Path(description="Product category")
    ],
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="Max items to return")
    ] = 10,
    min_price: Annotated[
        float,
        Query(ge=0, description="Minimum price filter")
    ] = 0.0,
    max_price: Annotated[
        float,
        Query(ge=0, description="Maximum price filter")
    ] = 10000.0
) -> dict:
    """
    Get items filtered by category and price range.
    
    Demonstrates:
    - Enum path parameter
    - Numeric query parameter validation (ge, le)
    - Multiple query parameters
    
    Args:
        category: Product category
        limit: Maximum items to return
        min_price: Minimum price filter
        max_price: Maximum price filter
        
    Returns:
        Filtered items
    """
    if min_price > max_price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="min_price cannot be greater than max_price"
        )
    
    # Mock data
    items = {
        ItemCategory.electronics: [
            {"id": 1, "name": "Laptop", "price": 999},
            {"id": 2, "name": "Phone", "price": 599},
            {"id": 3, "name": "Headphones", "price": 99},
        ],
        ItemCategory.clothing: [
            {"id": 4, "name": "T-Shirt", "price": 29},
            {"id": 5, "name": "Jeans", "price": 79},
            {"id": 6, "name": "Jacket", "price": 199},
        ],
        ItemCategory.books: [
            {"id": 7, "name": "Python Guide", "price": 45},
            {"id": 8, "name": "FastAPI Docs", "price": 35},
            {"id": 9, "name": "Web Development", "price": 55},
        ]
    }
    
    # Get category items
    category_items = items.get(category, [])
    
    # Filter by price
    filtered = [
        item for item in category_items
        if min_price <= item["price"] <= max_price
    ]
    
    # Limit results
    result = filtered[:limit]
    
    logger.info(
        "Items retrieved",
        category=category.value,
        count=len(result),
        min_price=min_price,
        max_price=max_price
    )
    
    return {
        "category": category.value,
        "count": len(result),
        "limit": limit,
        "price_range": {"min": min_price, "max": max_price},
        "items": result
    }


@advanced_params_router.get(
    "/search/advanced",
    summary="Advanced search with query model",
    description="Search with complex query parameter validation"
)
async def advanced_search(
    filter_query: Annotated[FilterParams, Query()]
) -> dict:
    """
    Advanced search with Pydantic query model.
    
    Demonstrates:
    - Pydantic model for query parameters
    - Field validation (min, max, length)
    - Multiple parameters with defaults
    - Type conversion and validation
    
    Args:
        filter_query: Filter parameters (from Pydantic model)
        
    Returns:
        Search results with applied filters
    """
    logger.info(
        "Search executed",
        limit=filter_query.limit,
        offset=filter_query.offset,
        sort_by=filter_query.sort_by,
        search=filter_query.search
    )
    
    return {
        "status": "success",
        "query": {
            "limit": filter_query.limit,
            "offset": filter_query.offset,
            "sort_by": filter_query.sort_by,
            "sort_order": filter_query.sort_order.value,
            "tags": filter_query.tags,
            "search": filter_query.search
        },
        "results": [
            {"id": 1, "name": "Item 1", "tags": filter_query.tags},
            {"id": 2, "name": "Item 2", "tags": filter_query.tags}
        ]
    }


@advanced_params_router.get(
    "/validate-string",
    summary="String validation",
    description="Demonstrate string parameter validation"
)
async def validate_string(
    q: Annotated[
        str | None,
        Query(
            min_length=3,
            max_length=50,
            pattern="^[a-zA-Z0-9]*$",
            title="Query string",
            description="Query string with alphanumeric validation"
        )
    ] = None
) -> dict:
    """
    Validate string query parameter.
    
    Demonstrates:
    - Min and max length validation
    - Regex pattern matching
    - Optional parameter with None default
    
    Args:
        q: Query string
        
    Returns:
        Validation result
    """
    if q:
        logger.info("String validated", query=q)
        return {
            "valid": True,
            "query": q,
            "length": len(q),
            "is_alphanumeric": q.isalnum()
        }
    else:
        return {
            "valid": True,
            "query": None,
            "message": "No query provided"
        }


@advanced_params_router.get(
    "/numeric-validation",
    summary="Numeric validation",
    description="Demonstrate numeric parameter constraints"
)
async def numeric_validation(
    item_id: Annotated[
        int,
        Query(ge=1, le=1000, title="Item ID")
    ],
    price: Annotated[
        float,
        Query(gt=0, lt=10000, title="Price")
    ],
    quantity: Annotated[
        int,
        Query(ge=0, le=100, title="Quantity")
    ] = 1
) -> dict:
    """
    Validate numeric parameters.
    
    Demonstrates:
    - Greater than/equal (ge, gt)
    - Less than/equal (le, lt)
    - Integer and float validation
    
    Args:
        item_id: Item ID (1-1000)
        price: Price (0 exclusive to 10000 exclusive)
        quantity: Quantity (0-100, default 1)
        
    Returns:
        Validated values
    """
    total_price = price * quantity
    
    logger.info(
        "Numeric validation passed",
        item_id=item_id,
        price=price,
        quantity=quantity,
        total=total_price
    )
    
    return {
        "item_id": item_id,
        "unit_price": price,
        "quantity": quantity,
        "total_price": total_price
    }


@advanced_params_router.get(
    "/list-values",
    summary="Multiple query values",
    description="Query parameter with multiple values"
)
async def list_values(
    q: Annotated[
        List[str],
        Query(description="Multiple values for q parameter")
    ] = None
) -> dict:
    """
    Accept multiple values for same query parameter.
    
    URL: /list-values?q=foo&q=bar&q=baz
    
    Demonstrates:
    - List of values from same parameter
    - Multiple occurrences in URL
    
    Args:
        q: List of query values
        
    Returns:
        Received values
    """
    if not q:
        q = []
    
    logger.info("List values received", count=len(q), values=q)
    
    return {
        "values": q,
        "count": len(q)
    }


@advanced_params_router.get(
    "/alias-param",
    summary="Query parameter alias",
    description="Query parameter with different name in URL"
)
async def alias_param(
    item_query: Annotated[
        str | None,
        Query(
            alias="item-query",
            description="Query using alias 'item-query' in URL"
        )
    ] = None
) -> dict:
    """
    Query parameter with URL alias.
    
    Parameter name: item_query
    URL query name: item-query
    
    Demonstrates parameter aliasing for URL compatibility.
    
    Args:
        item_query: Query parameter (accessed via ?item-query=value)
        
    Returns:
        Received value
    """
    return {
        "param_name": "item_query",
        "url_name": "item-query",
        "value": item_query
    }


@advanced_params_router.get(
    "/deprecated-param",
    summary="Deprecated parameter example",
    description="Show how to mark parameters as deprecated"
)
async def deprecated_param(
    q: Annotated[
        str | None,
        Query(
            deprecated=True,
            description="This parameter is deprecated. Use 'new_q' instead."
        )
    ] = None,
    new_q: Annotated[
        str | None,
        Query(description="New parameter replacing 'q'")
    ] = None
) -> dict:
    """
    Demonstrate deprecated parameter handling.
    
    Shows old parameter as deprecated in OpenAPI docs,
    while supporting new parameter name.
    
    Args:
        q: Old parameter (deprecated)
        new_q: New parameter (preferred)
        
    Returns:
        Value from either parameter (new_q takes precedence)
    """
    # Prefer new_q if provided
    actual_value = new_q or q
    
    return {
        "deprecated_param_used": q is not None and new_q is None,
        "new_param_used": new_q is not None,
        "final_value": actual_value
    }


@advanced_params_router.get(
    "/required-optional",
    summary="Required vs optional parameters",
    description="Demonstrate required and optional query parameters"
)
async def required_optional(
    required_param: Annotated[
        str,
        Query(description="This parameter is required")
    ],
    optional_param: Annotated[
        str | None,
        Query(description="This parameter is optional")
    ] = None,
    with_default: Annotated[
        str,
        Query(description="This has a default value")
    ] = "default_value"
) -> dict:
    """
    Demonstrate parameter requirement levels.
    
    Args:
        required_param: Required (no default value)
        optional_param: Optional (default is None)
        with_default: Optional with specific default
        
    Returns:
        All parameter values
    """
    return {
        "required": required_param,
        "optional": optional_param,
        "with_default": with_default
    }
