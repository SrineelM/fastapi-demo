# Prompt for FastAPI Comprehensive Guide Project

## Role
Act as a senior Python 3.14 developer and architect.

## Goal
Create a FastAPI project that serves as a comprehensive guide for both beginners and advanced users, demonstrating modern best practices (2023-2025).

## Tasks
- Create a basic project structure and Python virtual environment (venv)
- Implement endpoints for all HTTP verbs (GET, POST, PUT, PATCH, DELETE, OPTIONS, HEAD)
- Show examples of path, query, and body parameters
- Include at least one example each of:
  - Blocking and non-blocking (async) calls
  - GraphQL endpoint
  - WebSocket
  - Event-driven and stream-based implementations
- Demonstrate concurrency, thread safety, and async programming
- Create a dummy in-memory database for CRUD operations
- Provide examples using Pydantic, numpy, and other popular Python libraries (no deep dives)
- Implement caching (decorator-based, in-memory, TTL)
- Show how to run effectively in distributed systems (AWS, Kubernetes, Docker)
- Demonstrate best practices for performance, fault tolerance, resilience, observability, and scalability
- Add any other best practices from your own experience

## Outcome
- A project that runs successfully with proper indentation and structure
- Uses modern build tools and venv
- Complete unit test cases with high coverage, low cyclomatic complexity, and best practices for testability
- Ample comments to illustrate what is done and why (for both beginners and advanced users)
- Suitable as a backend for UI apps (e.g., Angular)
- Runs locally on a laptop with 8GB RAM, with guidance for AWS/on-prem Kubernetes deployment
- Includes README.md, Guidelines.md, Architecture.md
- Provides copilot-instructions.md
- Shares test data and Postman collection for API testing
- Complete API documentation
- No unnecessary markdown files

## Instructions
- Think step by step, plan, and execute
- Do not assume anything; clarify if in doubt
- Refer to https://fastapi.tiangolo.com/tutorial/ for high-quality code
- Target both beginners and advanced users with clear explanations and best practices
