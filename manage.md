# Architecture & Operations Guide: `manage.py`
## FastAPI Base Structure Administrative CLI Reference Manual

> **The definitive operational reference for out-of-band system administration, permission policy seeding, role provisioning, and administrative bootstrapping.**  
> 🌐 **[النسخة العربية (manage_ar.md)](manage_ar.md)**

---

## Table of Contents
1. [Architectural Philosophy: Why `manage.py` Exists](#1-architectural-philosophy-why-managepy-exists)
   - [The Chicken-and-Egg Bootstrap Paradox](#the-chicken-and-egg-bootstrap-paradox)
   - [Out-of-Band Administrative Control](#out-of-band-administrative-control)
   - [Asynchronous Engine & Connection Pool Hygiene](#asynchronous-engine--connection-pool-hygiene)
2. [Code Anatomy & Architectural Patterns](#2-code-anatomy--architectural-patterns)
   - [The Maestro / Dispatcher Pattern](#the-maestro--dispatcher-pattern)
   - [Pre-Execution Validation Guards](#pre-execution-validation-guards)
   - [Fail-Safe Admin Lockout Prevention](#fail-safe-admin-lockout-prevention)
3. [Comprehensive Command Reference](#3-comprehensive-command-reference)
   - [1. `seed-policies` — Baseline Policy Ingestion](#1-seed-policies--baseline-policy-ingestion)
   - [2. `create-admin` — Interactive & Direct Admin Provisioning](#2-create-admin--interactive--direct-admin-provisioning)
   - [3. `promote-admin` — Existing User Role Escalation](#3-promote-admin--existing-user-role-escalation)
   - [4. `grant` — Assign Resource Actions to Roles](#4-grant--assign-resource-actions-to-roles)
   - [5. `revoke` — Strip Resource Actions from Roles](#5-revoke--strip-resource-actions-from-roles)
   - [6. `assign-role` — Bind User Subject to Role](#6-assign-role--bind-user-subject-to-role)
   - [7. `unassign-role` — Detach Role from User Subject](#7-unassign-role--detach-role-from-user-subject)
   - [8. `list-policies` — Inspect Active Authorization Matrix](#8-list-policies--inspect-active-authorization-matrix)
4. [Real-World Production Scenarios](#4-real-world-production-scenarios)
   - [Scenario A: Fresh Environment Bootstrap (Day 0)](#scenario-a-fresh-environment-bootstrap-day-0)
   - [Scenario B: Custom Role Onboarding (`auditor` Role)](#scenario-b-custom-role-onboarding-auditor-role)
   - [Scenario C: Break-Glass Emergency Recovery](#scenario-c-break-glass-emergency-recovery)
5. [CI/CD & Container Automation (Docker Entrypoint)](#5-cicd--container-automation-docker-entrypoint)
6. [Troubleshooting & Common Pitfalls](#6-troubleshooting--common-pitfalls)
7. [Security & Operational Best Practices](#7-security--operational-best-practices)

---

## 1. Architectural Philosophy: Why `manage.py` Exists

In modern enterprise backends built on **FastAPI**, authorization is enforced at the perimeter through dynamic Role-Based Access Control (**PyCasbin**). This design guarantees defense-in-depth, but introduces an operational requirement:

```
  +-------------------------------------------------------------+
  |              API Endpoints (FastAPI Application)            |
  |  - Requires valid JWT                                       |
  |  - Requires RBAC check (Users:Read, Users:Write)            |
  |  - FAILS CLOSED (Denies access if no admin/policies exist)   |
  +-------------------------------------------------------------+
                                 ^
                                 |  (Blocked! No admin exists yet)
                                 x
  +-------------------------------------------------------------+
  |                      manage.py (CLI Tool)                   |
  |  - Direct database access via AsyncEngineLocal              |
  |  - Out-of-band administrative execution                     |
  |  - Seeds policies, bootstraps root admin, assigns roles      |
  +-------------------------------------------------------------+
```

### The Chicken-and-Egg Bootstrap Paradox
When deploying a clean database for the first time:
1. All administrative endpoints (such as `/api/v1/users` or `/api/v1/audit/logs`) are guarded by `require_permission`.
2. The authorization engine follows a strict **Fail-Closed** rule: if no matching policy exists in the database, the operation is denied (`403 Forbidden`).
3. Exposing a public, unauthenticated HTTP endpoint to register an administrator would represent an unacceptable security vulnerability.
4. Consequently, the initial system state cannot be provisioned via HTTP. **`manage.py` solves this paradox** by serving as an out-of-band CLI tool that operates directly against the local persistence layer.

### Out-of-Band Administrative Control
`manage.py` empowers system engineers, site reliability engineers (SREs), and deployment pipelines to:
* Seed and synchronize authorization policies into the `casbin_rule` table without writing raw SQL.
* Create, promote, or restore superuser accounts during emergencies without deploying code changes.
* Inspect the active permission matrix at runtime for auditing and compliance verifications.

### Asynchronous Engine & Connection Pool Hygiene
Because the application stack is natively asynchronous (SQLAlchemy 2.0 AsyncIO + `aiosqlite`/`asyncpg`), running standalone scripts that open connection pools can leave uncollected sockets if terminated abruptly. `manage.py` enforces connection hygiene by disposing of the engine within a guaranteed `finally` block:
```python
try:
    asyncio.run(handler())
finally:
    asyncio.run(AsyncEngineLocal.dispose())
```

---

## 2. Code Anatomy & Architectural Patterns

`manage.py` is engineered in accordance with the repository's **Enterprise Python Architecture Constitution**:

### The Maestro / Dispatcher Pattern
The entry point `main()` contains zero business logic. It serves purely as an orchestrator:
1. Configures the command parser via `build_parser()`.
2. Maps subcommands to specialized handler coroutines via an immutable dispatch map (`command_handlers`).
3. Catches operational exceptions (`ValueError`, `RuntimeError`), routes error messages to `sys.stderr`, and exits with standard POSIX status codes (`0` for success, `1` for error).

### Pre-Execution Validation Guards
Before touching the database or mutating Casbin policies, all parameters undergo deterministic validation:
* **`validate_role_name(role)`**:
  * Prevents collision with reserved user subjects by rejecting names starting with `user:`.
  * Enforces the naming regex pattern `^[a-z][a-z0-9_]{1,49}$` (2 to 50 lowercase alphanumeric characters with underscores).
* **`validate_resource(resource)`**:
  * Ensures the resource token strictly matches known members of `Resource` (e.g., `users`, `audit`) or the wildcard character `*`.
* **`validate_action(action)`**:
  * Ensures the action token strictly matches known members of `Action` (e.g., `create`, `read`, `update`, `delete`, `export`) or the wildcard character `*`.
* **Pydantic Validation via `RegisterRequest`**:
  * In `create-admin`, administrator credentials pass through the application's domain `RegisterRequest` schema to guarantee enterprise password complexity and email format standards before database insertion.

### Fail-Safe Admin Lockout Prevention
To safeguard production environments from catastrophic human error, revoking the root administrator rule `(admin, *, *)` is explicitly blocked:
```python
if args.role == 'admin' and args.resource == '*' and args.action == '*' and not args.force:
    print("Safety Warning: Revoking (admin, *, *) will lock out all administrators...\n"
          "If you really intend to do this, pass the --force flag.", file=sys.stderr)
    sys.exit(1)
```
Only an explicit `--force` flag overrides this safeguard.

---

## 3. Comprehensive Command Reference

Execute all commands through the `uv` toolchain to ensure environment isolation and dependency alignment:

```bash
uv run python manage.py <command> [options]
```

---

### 1. `seed-policies` — Baseline Policy Ingestion

* **Purpose:** Seeds the foundational authorization rules into the `casbin_rule` table. The operation is completely **idempotent**; existing rules are not duplicated.
* **Rules Ingested:**
  1. `(admin, *, *)` — Unrestricted access for users with the `admin` role across all resources and actions.
  2. `(user, users, read)` — Baseline permission for regular users to read profile records.
* **Syntax:**
  ```bash
  uv run python manage.py seed-policies
  ```
* **Output:**
  ```text
  Successfully seeded default policies (2 new rule(s) added).
  ```
  *(If already seeded, prints `0 new rule(s) added` without altering state).*

---

### 2. `create-admin` — Interactive & Direct Admin Provisioning

* **Purpose:** Provisions a new superuser account (`role=Roles.ADMIN`, `security_version=1`, `is_active=True`) hashed with Argon2id.
* **Arguments:**
  * `--email` (*required*): Administrator email address.
  * `--name` (*required*): Administrator full display name.
  * `--password` (*optional*): Account password. If omitted, the CLI enters **interactive hidden input mode** using `getpass`.
* **Interactive Mode (Recommended for human operators):**
  ```bash
  uv run python manage.py create-admin --email "root@enterprise.io" --name "Root Admin"
  ```
  ```text
  Enter admin password: 
  Confirm admin password: 
  Admin user successfully created with ID 1 (email: root@enterprise.io).
  ```
* **Non-Interactive Mode (For automated provisioning / CI scripts):**
  ```bash
  uv run python manage.py create-admin --email "root@enterprise.io" --name "Root Admin" --password "SuperSecretPass123!"
  ```

---

### 3. `promote-admin` — Existing User Role Escalation

* **Purpose:** Elevates an existing standard user (`role='user'`) directly to the administrator role (`role='admin'`) in the persistence store.
* **Invariants Enforced:**
  * The user must exist in the database.
  * The user account must be active (`is_active=True`). Deactivated accounts cannot be promoted.
* **Arguments:**
  * `--email` (*required*): Email address of the user to promote.
* **Syntax:**
  ```bash
  uv run python manage.py promote-admin --email "alice@enterprise.io"
  ```
* **Output:**
  ```text
  User 'alice@enterprise.io' (ID: 3) successfully promoted to Admin.
  ```

---

### 4. `grant` — Assign Resource Actions to Roles

* **Purpose:** Registers a dynamic permission policy (`p`) granting a role access to perform an action on a resource.
* **Positional Arguments:**
  1. `role`: Lowercase role name (e.g., `auditor`, `manager`, `support`).
  2. `resource`: Target resource token (e.g., `users`, `audit`, or `*`).
  3. `action`: Target action token (e.g., `read`, `export`, `create`, or `*`).
* **Examples:**
  ```bash
  # Grant auditor role permission to read audit logs
  uv run python manage.py grant auditor audit read

  # Grant auditor role permission to export audit records
  uv run python manage.py grant auditor audit export

  # Grant support role permission to read any resource
  uv run python manage.py grant support * read
  ```
* **Output:**
  ```text
  Successfully granted: (auditor, audit, read).
  ```

---

### 5. `revoke` — Strip Resource Actions from Roles

* **Purpose:** Removes an existing permission policy (`p`) from persistent storage. Changes take effect on the next incoming HTTP request.
* **Positional Arguments & Options:**
  1. `role`: Target role name.
  2. `resource`: Target resource token.
  3. `action`: Target action token.
  4. `--force` (*flag*): Mandatory when revoking `(admin, *, *)`.
* **Examples:**
  ```bash
  # Revoke export permission from the auditor role
  uv run python manage.py revoke auditor audit export

  # Attempting to revoke root admin without force fails safely:
  uv run python manage.py revoke admin * *
  # Safety Warning: Revoking (admin, *, *) will lock out all administrators.
  # If you really intend to do this, pass the --force flag.

  # Revoke with explicit confirmation:
  uv run python manage.py revoke admin * * --force
  ```

---

### 6. `assign-role` — Bind User Subject to Role

* **Purpose:** Creates a grouping policy (`g`) binding a specific user integer identifier to an authorization role (`user:<id> -> role`).
* **Positional Arguments:**
  1. `user_id`: Target user integer ID.
  2. `role`: Role name to bind to the user.
* **Safety Check:** Verifies that the user exists in `UserRepository` prior to creating the mapping.
* **Example:**
  ```bash
  # Assign the auditor role to user with ID 2
  uv run python manage.py assign-role 2 auditor
  ```
* **Output:**
  ```text
  Successfully assigned role 'auditor' to user 2 (user:2).
  ```

---

### 7. `unassign-role` — Detach Role from User Subject

* **Purpose:** Deletes the grouping policy (`g`) linking a user subject to a role, immediately removing the inherited permissions.
* **Positional Arguments:**
  1. `user_id`: Target user integer ID.
  2. `role`: Role name to detach.
* **Example:**
  ```bash
  uv run python manage.py unassign-role 2 auditor
  ```
* **Output:**
  ```text
  Successfully removed role 'auditor' from user 2.
  ```

---

### 8. `list-policies` — Inspect Active Authorization Matrix

* **Purpose:** Renders a clean tabular summary of all active permission policies (`p`) and role groupings (`g`).
* **Syntax:**
  ```bash
  uv run python manage.py list-policies
  ```
* **Example Output:**
  ```text
  --- Active Permission Policies ('p') ---
    ROLE / SUBJECT       RESOURCE        ACTION         
    --------------------------------------------------
    admin                *               *              
    user                 users           read           
    auditor              audit           read           
    auditor              audit           export         

  --- Active Role Groupings ('g') ---
    MEMBER               ROLE                
    ----------------------------------------
    user:2               auditor             
  ```

---

## 4. Real-World Production Scenarios

### Scenario A: Fresh Environment Bootstrap (Day 0)
When initializing a new staging or production environment, execute this exact sequence:

```bash
# 1. Apply database migrations to create tables
uv run alembic upgrade head

# 2. Seed default RBAC rules into Casbin storage
uv run python manage.py seed-policies

# 3. Create the initial administrator account
uv run python manage.py create-admin --email "root@enterprise.io" --name "Root Admin"

# 4. Verify policy alignment
uv run python manage.py list-policies
```

---

### Scenario B: Custom Role Onboarding (`auditor` Role)
Assume an organization requires a compliance officer (`compliance@enterprise.io`, user `ID = 5`) who must access `/api/v1/audit/logs` and `/api/v1/audit/export` without receiving full administrator privileges:

```bash
# Step 1: Define permissions for the 'auditor' role
uv run python manage.py grant auditor audit read
uv run python manage.py grant auditor audit export

# Step 2: Bind the user ID to the new role
uv run python manage.py assign-role 5 auditor

# Step 3: Inspect active bindings
uv run python manage.py list-policies
```
* **Runtime Impact:** On the user's next API request, `require_permission(Resource.AUDIT, Action.READ)` evaluates to `True` immediately. No server restart or code deployment is required.

---

### Scenario C: Break-Glass Emergency Recovery
If an administrator account is locked out or credential compromise requires emergency access restoration:

```bash
# 1. Promote an active existing account to superuser
uv run python manage.py promote-admin --email "recovery@enterprise.io"

# 2. Re-establish root wildcard policy if stripped
uv run python manage.py grant admin * *
```

---

## 5. CI/CD & Container Automation (Docker Entrypoint)

In containerized deployments (Docker, Kubernetes Init-Containers), automate initialization with an entrypoint script:

### Production `entrypoint.sh` Example:
```bash
#!/usr/bin/env bash
set -e

echo "==> [DB] Applying migrations..."
uv run alembic upgrade head

echo "==> [RBAC] Seeding default authorization policies..."
uv run python manage.py seed-policies

# Conditionally bootstrap administrator if environment variables are provided
if [ -n "$BOOTSTRAP_ADMIN_EMAIL" ] && [ -n "$BOOTSTRAP_ADMIN_PASSWORD" ]; then
    echo "==> [AUTH] Provisioning initial administrator..."
    uv run python manage.py create-admin \
        --email "$BOOTSTRAP_ADMIN_EMAIL" \
        --name "${BOOTSTRAP_ADMIN_NAME:-Root Admin}" \
        --password "$BOOTSTRAP_ADMIN_PASSWORD" || true
fi

echo "==> [SERVER] Launching FastAPI via Uvicorn..."
exec uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## 6. Troubleshooting & Common Pitfalls

| Error Message / Symptom | Root Cause | Remediation |
| :--- | :--- | :--- |
| `Role names cannot begin with the reserved prefix 'user:'.` | The role string begins with `user:` (e.g., `user:auditor`). | The `user:` prefix is reserved for user subject identifiers. Use standalone names like `auditor` or `manager`. |
| `Invalid role name '...'. Must be 2-50 characters...` | Role contains uppercase letters, spaces, or hyphens. | Role names must be lowercase alphanumeric with underscores matching `^[a-z][a-z0-9_]{1,49}$` (e.g., `auditor_team`). |
| `Unknown resource 'analytics'. Allowed values: ['audit', 'users', '*']` | The resource token is not registered in the `Resource` enum. | Add the resource to `src/share/enum.py` and run migrations if corresponding tables are created. |
| `Unknown action 'download'. Allowed values: ['*', 'create', 'delete', 'export', 'read', 'update']` | The action token is not registered in the `Action` enum. | Use one of the standardized application action verbs. |
| `Error: User with ID 99 does not exist.` | Attempting to assign a role to a nonexistent database ID. | Verify the user ID in the database before invoking `assign-role`. |
| `Error: User '...' is deactivated and cannot be promoted.` | The target account has `is_active=False`. | Reactivate the account before promoting it to administrator. |

---

## 7. Security & Operational Best Practices

1. **Avoid Passing Passwords in Plain Shell Arguments:**
   * In interactive sessions, omit the `--password` parameter when running `create-admin`. The CLI uses `getpass` to prompt for input without echoing characters to terminal history (`~/.bash_history` or PowerShell logs).
2. **Follow the Principle of Least Privilege (PoLP):**
   * Never grant `* *` permissions to non-administrator roles. Explicitly scope grants to exact resource and action pairs.
3. **Conduct Regular Authorization Audits:**
   * Periodically execute `uv run python manage.py list-policies` to identify orphaned permissions or stale role groupings.
4. **Restrict Direct Server Execution:**
   * Access to `manage.py` in production environments must be restricted to authorized operations personnel via authenticated SSH or secure deployment runners.
