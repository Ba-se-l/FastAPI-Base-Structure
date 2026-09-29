# 🧪 Test Suite Documentation & Architecture Reference

This directory contains the comprehensive automated testing suite for the **FastAPI Base Structure** foundation. It provides isolated unit tests, end-to-end integration workflows, and role-based access control (RBAC) security verification.

---

## Table of Contents
1. [Architecture & Testing Philosophy](#1-architecture--testing-philosophy)
2. [Prerequisites & Environment Setup](#2-prerequisites--environment-setup)
3. [Configuration & Global Fixtures (`conftest.py`)](#3-configuration--global-fixtures-conftestpy)
4. [File-by-File Technical Deep Dive](#4-file-by-file-technical-deep-dive)
   - [`test_security.py`](#test_securitypy--cryptography--jwt-tokens)
   - [`test_health.py`](#test_healthpy--system-probes)
   - [`test_auth_flow.py`](#test_auth_flowpy--authentication-lifecycle)
   - [`test_user_rbac.py`](#test_user_rbacpy--rbac--pagination)
5. [CLI Execution Guide](#5-cli-execution-guide)
6. [Data Contracts & Payload Reference (Positive vs. Negative)](#6-data-contracts--payload-reference-positive-vs-negative)
7. [Troubleshooting & Best Practices](#7-troubleshooting--best-practices)

---

## 1. Architecture & Testing Philosophy

The test suite is built on four core principles:

1. **Complete Database Isolation (In-Memory SQLite):**
   * Tests run against `sqlite+aiosqlite:///:memory:`.
   * **Zero contamination:** The physical development database (`database.db`) is never touched during test runs.
   * Tables are created and dropped per test run to guarantee clean state.

2. **Zero Network Overhead (`ASGITransport`):**
   * All HTTP requests are executed in-process using `httpx.AsyncClient` with `ASGITransport(app=app)`.
   * No actual TCP sockets or web servers are opened, resulting in sub-millisecond request cycles and ultra-fast execution (~3 seconds for the full suite).

3. **Dependency Injection Overrides:**
   * FastAPI's `dependency_overrides` mechanism is leveraged to dynamically replace the production database session dependency `get_session` with an isolated test transaction generator.

4. **100% Asynchronous Native Flow:**
   * All test cases are executed within native `asyncio` event loops using `pytest-asyncio` in strict mode.

---

## 2. Prerequisites & Environment Setup

The test suite requires development dependencies:
* `pytest` (>= 9.0)
* `pytest-asyncio` (>= 1.4)
* `httpx` (>= 0.28)
* `aiosqlite` (>= 0.22)

To sync and install all required testing dependencies using `uv`:

```bash
uv sync --extra dev
```

Alternatively, if managing packages manually:

```bash
uv add --dev pytest pytest-asyncio
```

---

## 3. Configuration & Global Fixtures (`conftest.py`)

File: [`tests/conftest.py`](file:///d:/_Python%20Projects-27-05-2026/fastapi-base-structure-dev/tests/conftest.py)

This file sets up the async database engine and defines the core fixtures shared across all tests:

### Key Components

* `TEST_DATABASE_URL = 'sqlite+aiosqlite:///:memory:'`:
  In-memory async connection string.
* `test_engine`:
  Dedicated `create_async_engine` instance configured with `echo=False`.
* `TestSessionLocal`:
  `async_sessionmaker` configured with `autoflush=False` and `expire_on_commit=False`.

### Core Fixtures

| Fixture Name | Scope | Description |
|---|---|---|
| `init_test_database` | Function (`autouse=True`) | Automatically creates all tables (`BaseModel.metadata.create_all`) before each test runs and drops them (`drop_all`) afterwards. |
| `db_session` | Function | Yields an active `AsyncSession` bound to the in-memory test database for direct seed data insertions. |
| `client` | Function | Yields an `httpx.AsyncClient` wired to the FastAPI application with `app.dependency_overrides[get_session]` active, cleaning overrides up upon teardown. |

---

## 4. File-by-File Technical Deep Dive

### `test_security.py` — Cryptography & JWT Tokens
File: [`tests/test_security.py`](file:///d:/_Python%20Projects-27-05-2026/fastapi-base-structure-dev/tests/test_security.py)

Pure unit tests verifying the cryptographic primitives and token encoding/decoding mechanics in `src/security`:

* **`test_password_hashing_and_verification`**:
  * Asserts that `hash_password(raw)` returns a salted bcrypt hash distinct from the plain text.
  * Asserts that `verify_password` returns `True` for the correct password and `False` for incorrect inputs.
* **`test_access_token_creation_and_decoding`**:
  * Asserts that `create_access_token(user_id)` generates a valid JWT with claims: `sub`, `type=TokenType.ACCESS`, and expiration `exp`.
* **`test_refresh_token_creation_and_decoding`**:
  * Asserts that `create_refresh_token(user_id)` produces a tuple `(token, jti)`.
  * Verifies that the token decodes to `type=TokenType.REFRESH` and matches the 32-character hexadecimal `jti`.
* **`test_access_token_type_mismatch`**:
  * Ensures that decoding a refresh token using `decode_access_token()` raises `InvalidCredentialsException` (preventing token type substitution attacks).

---

### `test_health.py` — System Probes
File: [`tests/test_health.py`](file:///d:/_Python%20Projects-27-05-2026/fastapi-base-structure-dev/tests/test_health.py)

Integration tests verifying operational monitoring endpoints in `main.py`:

* **`test_health_endpoints`**:
  * **Liveness Probe (`GET /health`)**: Verifies that the endpoint returns `200 OK` with JSON `{ "status": "ok", "version": "...", "environment": "..." }`.
  * **Readiness Probe (`GET /health/ready`)**: Verifies that the endpoint executes an async SQL probe `SELECT 1` against the database engine and returns `200 OK` with `{ "status": "ok", "checks": { "database": "ok" } }`.

---

### `test_auth_flow.py` — Authentication Lifecycle
File: [`tests/test_auth_flow.py`](file:///d:/_Python%20Projects-27-05-2026/fastapi-base-structure-dev/tests/test_auth_flow.py)

Comprehensive end-to-end integration test executing the complete user authentication lifecycle:

1. **User Registration (`POST /api/v1/auth/register`)**:
   * Registers a new user account with hashed password and returns `201 Created` with a `UserResponse` schema.
2. **Duplicate Email Rejection (Negative)**:
   * Submits the same email again; expects `409 Conflict` with `ErrorResponse` (`code="USER_ALREADY_EXISTS"`).
3. **Weak Password Rejection (Negative)**:
   * Submits a password lacking required uppercase/digit/special characters; expects `422 Unprocessable Entity`.
4. **User Login (`POST /api/v1/auth/login`)**:
   * Submits valid credentials; returns `200 OK` with `TokenResponse` (`access_token` and `refresh_token`).
5. **Token Refresh & Rotation (`POST /api/v1/auth/refresh`)**:
   * Exchanges the refresh token for a brand new token pair; asserts that `new_access_token != access_token` and `new_refresh_token != refresh_token`.
6. **Replay Attack Prevention (Negative)**:
   * Re-submits the old (already rotated) refresh token; expects `401 Unauthorized` with `ErrorResponse` (`code="TOKEN_REVOKED"`).
7. **Single Device Logout (`POST /api/v1/auth/logout`)**:
   * Revokes the current active refresh token; returns `200 OK` with `MessageResponse`.

---

### `test_user_rbac.py` — RBAC & Pagination
File: [`tests/test_user_rbac.py`](file:///d:/_Python%20Projects-27-05-2026/fastapi-base-structure-dev/tests/test_user_rbac.py)

Integration tests verifying authorization boundaries and pagination:

* **Setup**: Seeds one Admin (`role=Roles.ADMIN`) and one Normal User (`role=Roles.USER`).
* **Current Profile (`GET /api/v1/users/me`)**:
  * Authenticates as normal user; returns `200 OK` with matching email and role.
* **Privilege Guard (`GET /api/v1/users`) (Negative)**:
  * Normal user requests admin-only user list; expects `403 Forbidden` with `ErrorResponse` (`code="ACCESS_DENIED"`).
* **Admin Paginated List (`GET /api/v1/users?page=1&page_size=10`) (Positive)**:
  * Admin requests user list; expects `200 OK` with `PaginatedResponse[UserResponse]`.
  * Verifies pagination metadata: `total=2`, `page=1`, `pages=1`.

---

### `test_audit_logging.py` — Audit Trail & Portable Logging
File: [`tests/test_audit_logging.py`](file:///d:/_Python%20Projects-27-05-2026/fastapi-base-structure-dev/tests/test_audit_logging.py)

Integration and service-level unit tests for the portable audit logging module:

* **Service Operations (`test_audit_service_operations`)**:
  * Asserts `save_success_event` and `save_failed_event` persist records correctly to the `audit_logs` table.
  * Verifies user-specific query filtering via `get_user_audit_logs`.
  * Verifies multi-format export generation across **JSON**, **TXT**, and **Markdown** formats.
* **API Endpoints & RBAC (`test_audit_api_endpoints_and_rbac`)**:
  * Verifies normal users are rejected with `403 Forbidden` (`ACCESS_DENIED`) on `/api/v1/audit/logs`.
  * Verifies administrators can query paginated logs, query user-specific logs, and download file exports.

---

## 5. CLI Execution Guide

### Run All Tests
To execute the entire test suite with standard output:
```powershell
uv run pytest
```

### Run with Verbose Reporting (`-v`)
Displays the status and duration of every individual test function:
```powershell
uv run pytest -v
```

### Run with Output Capture Disabled (`-s`)
Displays `print()` statements and application logs during test execution:
```powershell
uv run pytest -v -s
```

### Run a Specific Test File
```powershell
uv run pytest tests/test_security.py -v
uv run pytest tests/test_health.py -v
uv run pytest tests/test_auth_flow.py -v
uv run pytest tests/test_user_rbac.py -v
```

### Run a Specific Test Function
```powershell
uv run pytest tests/test_auth_flow.py::test_auth_full_lifecycle -v
uv run pytest tests/test_user_rbac.py::test_rbac_and_user_endpoints -v
```

### Run Tests Matching a Pattern (`-k`)
```powershell
uv run pytest -k "token" -v
uv run pytest -k "rbac" -v
```

---

## 6. Data Contracts & Payload Reference (Positive vs. Negative)

### A. Registration (`POST /api/v1/auth/register`)

#### Positive Scenario (Success)
* **Request JSON:**
  ```json
  {
    "name": "Test Engineer",
    "email": "engineer@enterprise.io",
    "password": "StrongP@ssw0rd!"
  }
  ```
* **Response Status:** `201 Created`
* **Response Body (`UserResponse`):**
  ```json
  {
    "id": 1,
    "name": "Test Engineer",
    "email": "engineer@enterprise.io",
    "role": "user",
    "is_active": true,
    "created_at": "2026-09-28T19:58:44.519000Z",
    "updated_at": "2026-09-28T19:58:44.519000Z"
  }
  ```

#### Negative Scenario 1: Duplicate Email Conflict
* **Request JSON:** Same email as an existing account.
* **Response Status:** `409 Conflict`
* **Response Body (`ErrorResponse`):**
  ```json
  {
    "success": false,
    "error": {
      "code": "USER_ALREADY_EXISTS",
      "message": "User with email 'engineer@enterprise.io' already exists.",
      "details": null
    },
    "request_id": "201d8bc8badf49f2b89a1b796adeb897"
  }
  ```

#### Negative Scenario 2: Weak Password Violation
* **Request JSON:**
  ```json
  {
    "name": "Test Engineer",
    "email": "engineer2@enterprise.io",
    "password": "simple"
  }
  ```
* **Response Status:** `422 Unprocessable Entity`
* **Response Body (`ErrorResponse` Envelope):**
  ```json
  {
    "success": false,
    "error": {
      "code": "VALIDATION_ERROR",
      "message": "Invalid request payload.",
      "details": [
        {
          "type": "value_error",
          "loc": ["body", "password"],
          "msg": "Value error, Password must contain at least one uppercase letter."
        }
      ]
    },
    "request_id": "201d8bc8badf49f2b89a1b796adeb897"
  }
  ```
        "type": "value_error",
        "loc": ["body", "password"],
        "msg": "Value error, Password must contain at least one uppercase letter.",
        "input": "simple"
      }
    ]
  }
  ```

---

### B. Login (`POST /api/v1/auth/login`)

#### Positive Scenario (Success)
* **Request JSON:**
  ```json
  {
    "email": "engineer@enterprise.io",
    "password": "StrongP@ssw0rd!"
  }
  ```
* **Response Status:** `200 OK`
* **Response Body (`TokenResponse`):**
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
  }
  ```

#### Negative Scenario: Wrong Password or Email
* **Request JSON:**
  ```json
  {
    "email": "engineer@enterprise.io",
    "password": "WrongPassword123!"
  }
  ```
* **Response Status:** `401 Unauthorized`
* **Response Body (`ErrorResponse`):**
  ```json
  {
    "success": false,
    "error": {
      "code": "INVALID_CREDENTIALS",
      "message": "Invalid email or password.",
      "details": null
    },
    "request_id": "9b12f6a73c1d42a8b9821f5e8e3a2014"
  }
  ```

---

### C. Refresh Token (`POST /api/v1/auth/refresh`)

#### Positive Scenario (Success with Rotation)
* **Request JSON:**
  ```json
  {
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
  ```
* **Response Status:** `200 OK`
* **Response Body (`TokenResponse`):**
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...<NEW>",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...<NEW>",
    "token_type": "bearer"
  }
  ```

#### Negative Scenario: Replaying an Already-Rotated/Revoked Token
* **Request JSON:** Submitting the old refresh token after rotation.
* **Response Status:** `401 Unauthorized`
* **Response Body (`ErrorResponse`):**
  ```json
  {
    "success": false,
    "error": {
      "code": "TOKEN_REVOKED",
      "message": "Refresh token has been revoked or is invalid.",
      "details": null
    },
    "request_id": "3f8e12cb5d2a45a689b1c7820e14a519"
  }
  ```

---

### D. RBAC Protected User List (`GET /api/v1/users`)

#### Positive Scenario (Admin Access with Pagination)
* **Headers:** `Authorization: Bearer <ADMIN_ACCESS_TOKEN>`
* **Query Parameters:** `?page=1&page_size=10`
* **Response Status:** `200 OK`
* **Response Body (`PaginatedResponse[UserResponse]`):**
  ```json
  {
    "success": true,
    "data": [
      {
        "id": 1,
        "name": "Root Admin",
        "email": "admin@enterprise.io",
        "role": "admin",
        "is_active": true,
        "created_at": "2026-09-28T20:00:00.000000Z",
        "updated_at": "2026-09-28T20:00:00.000000Z"
      },
      {
        "id": 2,
        "name": "Normal User",
        "email": "user@enterprise.io",
        "role": "user",
        "is_active": true,
        "created_at": "2026-09-28T20:00:00.000000Z",
        "updated_at": "2026-09-28T20:00:00.000000Z"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 10,
      "total": 2,
      "pages": 1
    }
  }
  ```

#### Negative Scenario: Normal User Access Denied
* **Headers:** `Authorization: Bearer <NORMAL_USER_ACCESS_TOKEN>`
* **Response Status:** `403 Forbidden`
* **Response Body (`ErrorResponse`):**
  ```json
  {
    "success": false,
    "error": {
      "code": "ACCESS_DENIED",
      "message": "Operation requires one of the following roles: ['admin'].",
      "details": null
    },
    "request_id": "e42d7a19c8f341b590e6a1278b30f452"
  }
  ```

---

## 7. Troubleshooting & Best Practices

### JTI Token Collisions
* **Issue:** Generating tokens within the same second for the same user id could yield identical JWT signatures if only `sub`, `iat`, and `exp` are encoded.
* **Resolution:** Every access token and refresh token automatically receives a unique `jti = uuid.uuid4().hex` in its payload, guaranteeing cryptographic uniqueness.

### Writing New Tests
When adding new endpoints to the project, follow this pattern:

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_my_new_endpoint(client: AsyncClient):
    response = await client.get("/api/v1/my-path")
    assert response.status_code == 200
    assert response.json()["success"] is True
```

The `client` fixture handles database isolation, schema initialization, and teardown automatically.
