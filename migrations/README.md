# 🗄️ Database Migrations Architecture & Alembic CLI Reference

This directory contains the database schema migration scripts and environment configuration powered by **Alembic** and **SQLAlchemy 2.0 (Async)**. It serves as the single source of truth for the physical evolution of the application's database schema.

---

## 📑 Table of Contents

1. [Architecture & Design Principles](#1-architecture--design-principles)
2. [First-Time Developer Setup (Zero to Running DB)](#2-first-time-developer-setup-zero-to-running-db)
3. [Essential Alembic CLI Commands](#3-essential-alembic-cli-commands)
   - [`upgrade head`](#alembic-upgrade-head--apply-all-pending-migrations)
   - [`downgrade`](#alembic-downgrade--roll-back-migrations)
   - [`revision --autogenerate`](#alembic-revision---autogenerate--generate-migrations)
   - [`check`](#alembic-check--verify-schema-synchronization)
   - [`current`](#alembic-current--view-active-revision)
   - [`history`](#alembic-history--view-migration-timeline)
   - [`heads`](#alembic-heads--inspect-branch-heads)
   - [`merge`](#alembic-merge--resolve-branching-conflicts)
   - [`stamp`](#alembic-stamp--re-align-migration-state)
4. [Internal Plumbing & Architectural Wiring (`env.py`)](#4-internal-plumbing--architectural-wiring-envpy)
   - [Dynamic Settings & Connection Pool](#dynamic-settings--connection-pool)
   - [Target Metadata Registration](#target-metadata-registration)
   - [Constraint Naming Conventions](#constraint-naming-conventions)
   - [SQLite Batch Mode (`render_as_batch=True`)](#sqlite-batch-mode-render_as_batchtrue)
5. [Step-by-Step Developer Workflows](#5-step-by-step-developer-workflows)
   - [Workflow A: Adding a New Column to an Existing Table](#workflow-a-adding-a-new-column-to-an-existing-table)
   - [Workflow B: Creating a New Domain Model & Table](#workflow-b-creating-a-new-domain-model--table)
   - [Workflow C: Writing a Custom Data Migration](#workflow-c-writing-a-custom-data-migration)
6. [Troubleshooting & Common Pitfalls](#6-troubleshooting--common-pitfalls)

---

## 1. Architecture & Design Principles

In production enterprise backends, invoking `BaseModel.metadata.create_all()` at startup is an **anti-pattern**:
* `create_all()` only creates tables that do **not** yet exist; it cannot alter existing columns, rename tables, drop unused indexes, or enforce new constraints.
* Schema changes become untracked, unreproducible, and prone to silent data drift across team members and deployment stages.

### How Alembic Solves This:
1. **Version-Controlled DDL:** Every schema alteration is written into an immutable Python script in `migrations/versions/`.
2. **Reversible Changes:** Every migration defines both an `upgrade()` function (applying forward changes) and a `downgrade()` function (rolling back changes cleanly).
3. **100% Async Native:** Configured using `async_engine_from_config` and `AsyncConnection`, fully integrated with `aiosqlite` (development default) and `asyncpg` (PostgreSQL production target).
4. **Zero-Configuration URLs:** The connection string is never hardcoded in `alembic.ini`; it is dynamically injected from `src.settings.settings.database_url`.

---

## 2. First-Time Developer Setup (Zero to Running DB)

When cloning this repository for the first time, your local environment will not have a database file initialized. Follow these 3 steps to get up and running:

### Step 1: Ensure Virtual Environment is Active
```bash
uv sync
```

### Step 2: Configure Environment Variables
Copy the template configuration file:
```bash
cp .env.example .env
```
Ensure `DATABASE_URL` is configured (defaults to SQLite: `sqlite+aiosqlite:///./database.db`).

### Step 3: Apply All Migrations
Run the upgrade command to execute all migrations up to the latest revision:
```bash
uv run alembic upgrade head
```

**Expected Terminal Output:**
```text
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 023d924aba69, initial_schema
```

### Step 4: Verify Database State
```bash
uv run alembic current
```
**Expected Output:**
```text
023d924aba69 (head)
```

Your database is now fully initialized with all tables (`users`, `refresh_sessions`, `audit_logs`), primary keys, indexes, and foreign keys.

---

## 3. Essential Alembic CLI Commands

Always run Alembic through the project's dependency manager (`uv run alembic <command>`).

### `alembic upgrade head` — Apply All Pending Migrations
Applies all unapplied migration scripts in chronological order up to the latest revision (`head`).
```bash
uv run alembic upgrade head
```
* **When to use:** On initial project setup, after pulling new code (`git pull`), or before launching the web server.
* **Targeting specific versions:** You can upgrade to an explicit revision hash:
  ```bash
  uv run alembic upgrade 023d924aba69
  ```

---

### `alembic downgrade` — Roll Back Migrations
Reverts applied migrations in reverse chronological order.

* **Revert the last single migration:**
  ```bash
  uv run alembic downgrade -1
  ```
* **Revert all migrations (completely blank database):**
  ```bash
  uv run alembic downgrade base
  ```
* **Revert to a specific revision:**
  ```bash
  uv run alembic downgrade <revision_id>
  ```
* **When to use:** When testing migration reversibility, reverting a flawed schema change during local feature development, or recovering from a failed deployment.

---

### `alembic revision --autogenerate` — Generate Migrations
Compares your current SQLAlchemy ORM models (`BaseModel.metadata`) against the physical database schema and generates a new migration script containing the differences.
```bash
uv run alembic revision --autogenerate -m "add_phone_number_to_users"
```
* **When to use:** Immediately after adding, modifying, or removing fields/relationships in any ORM model.
* **Result:** A new timestamped/hashed file created in `migrations/versions/`.

> [!IMPORTANT]
> **Always inspect generated migrations!** While Alembic autogenerates DDL accurately, you must review the generated file to ensure it matches your architectural intent (especially column renames or nullability).

---

### `alembic check` — Verify Schema Synchronization
Verifies whether the physical database schema matches the SQLAlchemy ORM models.
```bash
uv run alembic check
```
* **If in sync:** Outputs `No new upgrade operations detected.` and exits with code `0`.
* **If uncommitted changes exist:** Outputs detected differences and exits with code `11`.
* **When to use:** In pre-commit hooks or CI/CD pipelines to block pull requests that modified ORM models without committing a corresponding migration script.

---

### `alembic current` — View Active Revision
Displays the exact revision hash currently stamped on the connected database.
```bash
uv run alembic current
```
* **Optional verbose mode:**
  ```bash
  uv run alembic current -v
  ```

---

### `alembic history` — View Migration Timeline
Lists all migrations in the repository in chronological order.
```bash
uv run alembic history --verbose
```
* **Shows:** Revision hash, parent revision, author, date, and descriptive commit message.

---

### `alembic heads` — Inspect Branch Heads
Shows the latest revision(s) across all branches.
```bash
uv run alembic heads
```
* In a clean repository, this should display exactly **one** revision ending with `(head)`.
* If two developers create migrations concurrently on separate git branches, `alembic heads` will display **two** heads, indicating a merge is required.

---

### `alembic merge` — Resolve Branching Conflicts
Merges two diverging migration revisions into a single unified head.
```bash
uv run alembic merge -m "merge_user_and_order_branches" <rev1> <rev2>
```
* **When to use:** When merging git branches that each contain independent migration files.

---

### `alembic stamp` — Re-Align Migration State
Updates the database's `alembic_version` tracking table to a specific revision **without executing any SQL DDL**.
```bash
uv run alembic stamp head
```
* **When to use:** When attaching Alembic to an existing database that already has tables created, or recovering from a manually resolved schema conflict.

---

## 4. Internal Plumbing & Architectural Wiring (`env.py`)

The migration environment is driven by [`migrations/env.py`](file:///d:/_Python%20Projects-27-05-2026/fastapi-base-structure-dev/migrations/env.py). Here is how it is structured:

### Dynamic Settings & Connection Pool
Instead of hardcoding database credentials in `alembic.ini`, `env.py` reads directly from application settings:
```python
from src.settings import settings

# Dynamically synchronize database URL with application settings
config.set_main_option("sqlalchemy.url", settings.database_url)
```
This guarantees that whether running locally with SQLite or in staging/production with PostgreSQL, Alembic always uses the active environment configuration from `.env`.

### Target Metadata Registration
For Alembic's `--autogenerate` engine to discover models, they **must** be imported into `env.py`:
```python
from src.database.base import BaseModel
from src.modules.user.model import User           # noqa: F401
from src.modules.auth.model import RefreshSession # noqa: F401
from src.modules.audit.model import AuditLog      # noqa: F401

target_metadata = BaseModel.metadata
```

> [!WARNING]
> If you create a new ORM model in a new module and forget to import it in `migrations/env.py`, Alembic will **not** detect the table during `--autogenerate`!

### Constraint Naming Conventions
Alembic requires predictable constraint names to drop or alter foreign keys, unique constraints, and indexes. In [`src/database/base.py`](file:///d:/_Python%20Projects-27-05-2026/fastapi-base-structure-dev/src/database/base.py), `BaseModel` defines:
```python
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
```
This guarantees that all generated migrations contain explicit, reproducible constraint identifiers.

### SQLite Batch Mode (`render_as_batch=True`)
SQLite does not natively support standard `ALTER TABLE DROP COLUMN` or altering column constraints. Alembic resolves this via **batch mode**, which automatically:
1. Creates a temporary table with the new schema.
2. Copies all existing data over.
3. Drops the old table.
4. Renames the temporary table.

In `env.py`, batch mode is enabled by default:
```python
context.configure(
    connection=connection,
    target_metadata=target_metadata,
    render_as_batch=True,  # Critical for SQLite compatibility
)
```

---

## 5. Step-by-Step Developer Workflows

### Workflow A: Adding a New Column to an Existing Table

1. **Edit the ORM Model:**
   Open `src/modules/user/model.py` and add the new column:
   ```python
   phone_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
   ```

2. **Generate the Migration Script:**
   ```bash
   uv run alembic revision --autogenerate -m "add_phone_number_to_user"
   ```

3. **Inspect the Generated File:**
   Open the newly created file in `migrations/versions/`. Verify the `upgrade()` and `downgrade()` functions:
   ```python
   def upgrade() -> None:
       with op.batch_alter_table('users', schema=None) as batch_op:
           batch_op.add_column(sa.Column('phone_number', sa.String(length=20), nullable=True))

   def downgrade() -> None:
       with op.batch_alter_table('users', schema=None) as batch_op:
           batch_op.drop_column('phone_number')
   ```

4. **Apply the Migration:**
   ```bash
   uv run alembic upgrade head
   ```

5. **Verify Synchronization:**
   ```bash
   uv run alembic check
   ```

---

### Workflow B: Creating a New Domain Model & Table

1. **Define the Model:**
   Create `src/modules/billing/model.py`:
   ```python
   from sqlalchemy import String, Numeric
   from sqlalchemy.orm import Mapped, mapped_column
   from src.database.base import BaseModel
   from src.database.mixin import DateTimeMixin

   class Invoice(BaseModel, DateTimeMixin):
       __tablename__ = "invoices"

       id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
       amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
   ```

2. **Register the Model in `migrations/env.py`:**
   Add the import:
   ```python
   from src.modules.billing.model import Invoice  # noqa: F401
   ```

3. **Generate & Apply Migration:**
   ```bash
   uv run alembic revision --autogenerate -m "create_invoices_table"
   uv run alembic upgrade head
   ```

---

### Workflow C: Writing a Custom Data Migration

Sometimes you need to seed default roles or transform existing data rather than just changing schema structure:

1. **Generate an Empty Revision:**
   ```bash
   uv run alembic revision -m "seed_initial_roles"
   ```

2. **Write Raw SQL or Bulk Inserts in `upgrade()`:**
   ```python
   from alembic import op
   import sqlalchemy as sa

   def upgrade() -> None:
       # Execute bulk SQL or data transform
       op.execute("UPDATE users SET is_active = 1 WHERE is_active IS NULL")

   def downgrade() -> None:
       pass
   ```

3. **Apply:**
   ```bash
   uv run alembic upgrade head
   ```

---

## 6. Troubleshooting & Common Pitfalls

### Pitfall 1: "Target database is not up to date"
* **Symptom:** `alembic check` fails or `upgrade` errors with revision mismatches.
* **Fix:** Run `uv run alembic upgrade head` to bring the database to the current head revision before generating new revisions.

### Pitfall 2: Autogenerate did not detect my changes
* **Cause:** The modified or new model class was not imported into `migrations/env.py`.
* **Fix:** Add `from src.modules.<module>.model import <ModelClass> # noqa: F401` to `migrations/env.py`.

### Pitfall 3: Multiple heads detected (`MultipleHeadException`)
* **Symptom:** Two different migration files have `down_revision = '<same_parent>'`.
* **Fix:** Merge the heads:
  ```bash
  uv run alembic merge -m "resolve_conflicts" head1 head2
  uv run alembic upgrade head
  ```

### Pitfall 4: Adding a `NOT NULL` column to an existing table with rows
* **Symptom:** In SQLite, adding a non-nullable column to a table with existing rows fails with `Cannot add a NOT NULL column with default value NULL`.
* **Fix:** Either:
  1. Make the column nullable (`nullable=True`).
  2. Or provide a server default:
     ```python
     status: Mapped[str] = mapped_column(String(50), nullable=False, server_default="active")
     ```
