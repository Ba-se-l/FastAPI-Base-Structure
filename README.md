# 🚀 Enterprise FastAPI Base Structure Foundation (v1.0.0)

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141+-009688.svg)](https://fastapi.tiangolo.com)
[![SQLAlchemy 2.0](https://img.shields.io/badge/SQLAlchemy-2.0+-red.svg)](https://www.sqlalchemy.org/)
[![Alembic](https://img.shields.io/badge/Alembic-Async-orange.svg)](https://alembic.sqlalchemy.org/)
[![Pydantic v2](https://img.shields.io/badge/Pydantic-V2-green.svg)](https://docs.pydantic.dev/)
[![Code Style: PEP 8](https://img.shields.io/badge/code%20style-PEP%208-black.svg)](https://peps.python.org/pep-0008/)

A battle-tested, high-performance, and modular backend foundation built with **FastAPI**, **SQLAlchemy 2.0 (Async)**, and **Pydantic V2**. Designed following Domain-Driven Design (DDD-lite) principles, the Orchestrator/Specialist architectural pattern, and strict enterprise coding constitutions.

> 📖 **[انقر هنا لقراءة التوثيق الشامل باللغة العربية (README_AR.md)](README_AR.md)**

---

## 📑 Table of Contents

- [🚀 Enterprise FastAPI Base Structure Foundation (v1.0.0)](#-enterprise-fastapi-base-structure-foundation-v100)
  - [📑 Table of Contents](#-table-of-contents)
  - [🏛 Architectural Philosophy](#-architectural-philosophy)
  - [📂 Directory Structure](#-directory-structure)
  - [⚡ Core Features \& Subsystems](#-core-features--subsystems)
    - [1. Authentication \& JWT Lifecycle](#1-authentication--jwt-lifecycle)
    - [2. Role-Based Access Control (RBAC)](#2-role-based-access-control-rbac)
    - [3. Database \& Async Alembic Migrations](#3-database--async-alembic-migrations)
    - [4. Audit Logging \& Telemetry](#4-audit-logging--telemetry)
    - [5. Unified API Envelopes](#5-unified-api-envelopes)
  - [🚀 Quickstart Guide](#-quickstart-guide)
    - [Prerequisites](#prerequisites)
    - [Installation](#installation)
    - [Environment Configuration](#environment-configuration)
    - [Database Migrations](#database-migrations)
    - [Running the Application](#running-the-application)
  - [🧪 Testing Suite](#-testing-suite)
  - [🛠 Developer Guide: Adding a New Domain Module](#-developer-guide-adding-a-new-domain-module)
    - [Step 1: Create the Directory](#step-1-create-the-directory)
    - [Step 2: Define the Model (`src/modules/products/model.py`)](#step-2-define-the-model-srcmodulesproductsmodelpy)
    - [Step 3: Define Schemas \& Repository](#step-3-define-schemas--repository)
    - [Step 4: Implement Service \& Router](#step-4-implement-service--router)
    - [Step 5: Mount Router \& Register Migration](#step-5-mount-router--register-migration)
  - [📄 License](#-license)

---

## 🏛 Architectural Philosophy

1. **Domain Modular Architecture:** Business logic is segmented into self-contained domain modules under `src/modules/` (`auth`, `user`, `audit`). Each module encapsulates its own models, repositories, schemas, services, and routers.
2. **Orchestrator-Specialist Pattern:** 
   * **Routers (Orchestrators):** Delegate state and HTTP concerns without embedding raw SQL or business logic.
   * **Services (Maestros):** Coordinate atomic domain operations.
   * **Repositories (Specialists):** Reusable generic async CRUD operations adhering strictly to the Single Responsibility Principle (SRP).
3. **Pydantic-First Data Contracts:** Boundary data crossing HTTP or database boundaries is strictly typed using Pydantic V2 models.
4. **Strict Typing (Python 3.10+):** Exclusively uses modern union pipes `|`, `StrEnum` for finite state sets, and structural types (`Sequence`, `Mapping`).
5. **Fail-Safe & Observable:** Correlation IDs (`X-Request-ID`) injected across every request and unified error response envelopes guarantee clean telemetry.

---

## 📂 Directory Structure

```
fastapi-base-structure/
├── main.py                     # Application entry point, lifespan, middleware & exception handlers
├── pyproject.toml              # Project metadata & dependencies (uv managed)
├── alembic.ini                 # Alembic migration configuration
├── .env.example                # Documented environment variable template
├── migrations/                 # Alembic async migration environment
│   ├── env.py                  # Migration runner connected to settings & models
│   ├── script.py.mako          # Async revision template
│   └── versions/               # Timestamped/hashed migration versions
├── src/
│   ├── database/               # Async database infrastructure
│   │   ├── __init__.py         # Public facade
│   │   ├── base.py             # DeclarativeBase with standard naming conventions
│   │   ├── base_repo.py        # Generic BaseRepository[Model] (Async CRUD)
│   │   ├── engine.py           # AsyncEngine & connection verifier
│   │   ├── mixin.py            # DateTimeMixin (created_at, updated_at)
│   │   └── session.py          # Session dependency provider (get_session)
│   ├── exc/                    # Domain and base exceptions
│   │   ├── __init__.py         # Exported exception classes
│   │   └── base.py             # AppException hierarchy
│   ├── modules/                # Domain-Driven modules
│   │   ├── __init__.py         # Master API router consolidating all domains
│   │   ├── auth/               # Authentication & token lifecycle
│   │   │   ├── dependencies.py # get_current_user, require_role
│   │   │   ├── model.py        # RefreshSession ORM
│   │   │   ├── repo.py         # RefreshSessionRepository
│   │   │   ├── router.py       # Auth endpoints (/login, /register, /refresh, /logout)
│   │   │   ├── schemas.py      # Request/response contracts (EmailStr, TokenResponse)
│   │   │   └── service.py      # Auth business logic & token issuance
│   │   ├── user/               # User management
│   │   │   ├── model.py        # User ORM model
│   │   │   ├── repo.py         # UserRepository
│   │   │   ├── router.py       # User endpoints (/me, /{id}, list)
│   │   │   ├── schemas.py      # UserResponse, UserUpdate
│   │   │   └── service.py      # User CRUD business operations
│   │   └── audit/              # Security audit logging subsystem
│   │       ├── enum.py         # Severity & action enums
│   │       ├── formatters.py   # Single-line NDJSON, Text, and Markdown formatters
│   │       ├── model.py        # AuditLog ORM model with composite indexes
│   │       ├── repo.py         # AuditLogRepository
│   │       ├── router.py       # Audit query and export endpoints
│   │       ├── schemas.py      # LogEvent, LogResponse, LogQueryFilter
│   │       └── service.py      # Multi-sink maestro (DB + disk file logging)
│   ├── security/               # Cryptography and token security
│   │   ├── __init__.py         # Public facade
│   │   └── security.py         # Password hashing & JWT encode/decode
│   ├── settings/               # Environment & configuration management
│   │   ├── __init__.py         # Public facade
│   │   └── settings.py         # Settings class with Environment StrEnum & production guards
│   └── share/                  # Cross-cutting primitives
│       ├── __init__.py         # Public facade
│       ├── enum.py             # Roles (StrEnum) & TokenType
│       ├── responses.py        # ErrorResponse, SuccessResponse, PaginatedResponse
│       └── schemas.py          # TokenPayload schema
└── tests/                      # Automated test suite
    ├── conftest.py             # In-memory SQLite async test fixtures
    ├── test_security.py        # Cryptography & JWT unit tests
    ├── test_auth_flow.py       # End-to-end registration, login, refresh, logout
    ├── test_user_rbac.py       # RBAC role validation & pagination
    ├── test_user_crud.py       # User CRUD & authorization boundaries
    ├── test_validation_envelope.py # 422 error wrapping validation
    ├── test_pagination_edges.py    # Pagination edge cases
    ├── test_audit_logging.py   # Audit query, filter, and export
    ├── test_audit_db_disabled.py # Resilience verification when DB logging is off
    ├── test_health.py          # Liveness & readiness probe tests
    ├── README.md               # Test documentation (English)
    └── README_AR.md            # Test documentation (Arabic)
```

---

## ⚡ Core Features & Subsystems

### 1. Authentication & JWT Lifecycle
- **Dual Token Architecture:** Issues short-lived access tokens (30 minutes) and revocable long-lived refresh tokens (30 days).
- **Cryptographic JTI Tracking:** Every refresh token carries a unique JWT ID (`jti`) persisted in the database (`refresh_sessions` table).
- **Session Revocation:** Logout revokes the specific refresh session. Supports instant device sign-out.
- **Enterprise Password Hashing:** Uses `bcrypt` with optional SHA-256 pre-hashing to eliminate the 72-byte password truncation limit.

### 2. Role-Based Access Control (RBAC)
- **Typed Roles:** Strict `Roles(StrEnum)` containing `USER` and `ADMIN`.
- **Dependency Factory:** Clean declarator `require_role(Roles.ADMIN)` applied seamlessly on endpoints:
  ```python
  @router.get("", dependencies=[Depends(require_role(Roles.ADMIN))])
  async def list_users(...):
      ...
  ```

### 3. Database & Async Alembic Migrations
- **SQLAlchemy 2.0 Async Native:** Built around `AsyncEngine` and `async_sessionmaker`.
- **Constraint Naming Conventions:** Standardized naming (`ix_`, `uq_`, `ck_`, `fk_`, `pk_`) ensures 100% reliable automated migration generation across SQLite and PostgreSQL.
- **Zero Lifespan Table Generation in Production:** Database evolution is handled exclusively via version-controlled Alembic migrations.

### 4. Audit Logging & Telemetry
- **Multi-Sink Architecture:** Simultaneously logs critical actions to the relational database and disk storage.
- **Strict NDJSON Compliance:** File output writes one self-contained JSON record per physical line for zero-friction ingestion by log shippers (`jq`, Filebeat, Loki).
- **Transport-Agnostic Context (`AuditContext`):** High-performance `@dataclass(frozen=True, slots=True)` capturing client IP (with `X-Forwarded-For` reverse proxy support), User-Agent, and correlation `request_id` via FastAPI's `Depends(get_audit_context)`.
- **Zero-Credential Leakage Guarantee:** Strict sanitization ensures passwords and credentials are never stored in audit logs (`exclude={"password"}`).
- **State Change Diff Tracking:** `get_extra_dict_for_updates` captures granular `old` vs `new` field modifications before applying database updates.
- **Resilient Execution:** If database persistence is disabled (`LOG_TO_DB=false`), the subsystem continues file logging safely without crashing.
- **Export Capabilities:** Multi-format export endpoints supporting `JSON`, `TXT`, and `MARKDOWN`.

### 5. Unified API Envelopes
All responses adhere to standardized Pydantic envelopes:
* **Success Envelope:**
  ```json
  { "success": true, "data": { ... } }
  ```
* **Paginated Envelope:**
  ```json
  {
    "success": true,
    "data": [ ... ],
    "pagination": { "page": 1, "page_size": 20, "total": 100, "pages": 5 }
  }
  ```
* **Error Envelope (AppException, 500, and 422 Validation Errors):**
  ```json
  {
    "success": false,
    "error": {
      "code": "VALIDATION_ERROR",
      "message": "Invalid request payload.",
      "details": [ ... ]
    },
    "request_id": "9a4f6d8c0b2e4f..."
  }
  ```

---

## 🚀 Quickstart Guide

### Prerequisites
- Python 3.13 or higher
- [`uv`](https://docs.astral.sh/uv/) (ultra-fast Python package and project manager)

### Installation
Clone the repository and install dependencies:
```bash
git clone <repository-url>
cd fastapi-base-structure
uv sync
```

### Environment Configuration
Copy the sample environment file and configure variables:
```bash
cp .env.example .env
```
Key configuration parameters:
| Parameter | Default | Description |
|---|---|---|
| `ENVIRONMENT` | `dev` | Runtime environment (`dev`, `test`, `staging`, `pro`) |
| `DATABASE_URL` | `sqlite+aiosqlite:///./database.db` | Async database connection string |
| `ACCESS_SECRET_KEY` | `placeholder-...` | JWT access token HMAC secret |
| `REFRESH_SECRET_KEY` | `placeholder-...` | JWT refresh token HMAC secret |
| `LOG_TO_DB` | `true` | Enable/disable audit log persistence in database |
| `LOG_TO_FILE` | `true` | Enable/disable audit log writing to disk |

> [!CAUTION]
> If `ENVIRONMENT=pro`, the application automatically validates that secret keys are not placeholder strings and that CORS is not configured with wildcard `*`.

### Database Migrations
Apply all migrations to initialize the database schema:
```bash
uv run alembic upgrade head
```

To create a new automated migration after modifying ORM models:
```bash
uv run alembic revision --autogenerate -m "describe_changes"
uv run alembic upgrade head
```

Verify migration synchronization:
```bash
uv run alembic check
```

### Running the Application
Start the development server with live reload:
```bash
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000
```
Interactive Swagger API documentation will be available at:
- **Swagger UI:** `http://127.0.0.1:8000/docs`
- **ReDoc:** `http://127.0.0.1:8000/redoc`

---

## 🧪 Testing Suite

The project includes 100% automated tests running against an isolated in-memory SQLite database:
```bash
uv run pytest -v
```

To run a specific test suite:
```bash
uv run pytest tests/test_auth_flow.py -v
uv run pytest tests/test_user_crud.py -v
```
Detailed test documentation and scenario contracts are available in [`tests/README.md`](tests/README.md) and [`tests/README_AR.md`](tests/README_AR.md).

---

## 🛠 Developer Guide: Adding a New Domain Module

Follow this 5-step process to add a new domain (e.g., `products`):

### Step 1: Create the Directory
```bash
mkdir src/modules/products
```

### Step 2: Define the Model (`src/modules/products/model.py`)
```python
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from src.database.base import BaseModel
from src.database.mixin import DateTimeMixin

class Product(BaseModel, DateTimeMixin):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
```

### Step 3: Define Schemas & Repository
* Create `schemas.py` using Pydantic V2 models (`ProductResponse`, `ProductCreate`).
* Create `repo.py` inheriting from `BaseRepository[Product]`:
  ```python
  from src.database.base_repo import BaseRepository
  from .model import Product

  class ProductRepository(BaseRepository[Product]):
      def __init__(self, session):
          super().__init__(model=Product, session=session)
  ```

### Step 4: Implement Service & Router
* Create `service.py` with atomic business functions.
* Create `router.py` with FastAPI endpoints and dependency injection (`get_session`, `require_role`).

### Step 5: Mount Router & Register Migration
* Include the new router in `src/modules/__init__.py`.
* Import the model in `migrations/env.py`.
* Generate and apply migration:
  ```bash
  uv run alembic revision --autogenerate -m "add_products_table"
  uv run alembic upgrade head
  ```

---

## 📄 License
This project is open-source and distributed under the [MIT License](LICENSE).
