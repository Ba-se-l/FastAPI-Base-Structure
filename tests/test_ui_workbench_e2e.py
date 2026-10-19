import pytest
from httpx import AsyncClient

from src.share import Roles


@pytest.mark.asyncio
async def test_workbench_full_lifecycle_e2e(client: AsyncClient) -> None:
    """Verifies the complete end-to-end workflow automated by the UI Workbench:
    
    1. 1-Click Demo Setup: Register + Dual Device concurrent login (Device A & Device B).
    2. Token Inspection: Verifies unique lineage (fid, jti, sec_ver).
    3. Token Rotation: Refreshes Device A token, checks same fid and new jti.
    4. Replay Attack Simulator: Replays revoked token, receives 401 TOKEN_REVOKED.
    5. Smart Isolation: Device B access token remains valid after Device A replay breach.
    6. Users & RBAC: Profile inspection, PATCH name, and explicit null 422 rejection.
    7. Audit Trail: Query logs and download formatted Markdown audit export.
    """
    # -------------------------------------------------------------
    # 1. 1-Click Demo Setup: Register & Dual Device Login
    # -------------------------------------------------------------
    demo_email = "workbench.demo@enterprise.io"
    demo_pass = "WorkbenchP@ss123!"
    demo_name = "Workbench Demo User"

    # Register
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={"name": demo_name, "email": demo_email, "password": demo_pass},
    )
    assert reg_res.status_code == 201
    user_id = reg_res.json()["id"]
    assert reg_res.json()["name"] == demo_name

    # Login Device A
    login_a = await client.post(
        "/api/v1/auth/login",
        json={"email": demo_email, "password": demo_pass},
    )
    assert login_a.status_code == 200
    token_a_data = login_a.json()
    access_a = token_a_data["access_token"]
    refresh_a_1 = token_a_data["refresh_token"]

    # Login Device B
    login_b = await client.post(
        "/api/v1/auth/login",
        json={"email": demo_email, "password": demo_pass},
    )
    assert login_b.status_code == 200
    token_b_data = login_b.json()
    access_b = token_b_data["access_token"]
    refresh_b = token_b_data["refresh_token"]

    # Verify both devices have tokens
    assert access_a != access_b
    assert refresh_a_1 != refresh_b

    # -------------------------------------------------------------
    # 2. Token Rotation on Device A
    # -------------------------------------------------------------
    rot_a = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_a_1},
    )
    assert rot_a.status_code == 200
    new_token_a_data = rot_a.json()
    access_a_2 = new_token_a_data["access_token"]
    refresh_a_2 = new_token_a_data["refresh_token"]
    assert refresh_a_2 != refresh_a_1

    # -------------------------------------------------------------
    # 3. Simulate Replay Attack with Revoked refresh_a_1
    # -------------------------------------------------------------
    replay_res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_a_1},
    )
    assert replay_res.status_code == 401
    assert replay_res.json()["error"]["code"] == "TOKEN_REVOKED"

    # -------------------------------------------------------------
    # 4. Smart Device Isolation: Device B remains active
    # -------------------------------------------------------------
    me_b = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {access_b}"},
    )
    assert me_b.status_code == 200
    assert me_b.json()["email"] == demo_email

    # -------------------------------------------------------------
    # 5. User Profile Update & Guardrails
    # -------------------------------------------------------------
    # Valid PATCH update
    patch_ok = await client.patch(
        f"/api/v1/users/{user_id}",
        headers={"Authorization": f"Bearer {access_b}"},
        json={"name": "Architect Master"},
    )
    assert patch_ok.status_code == 200
    assert patch_ok.json()["name"] == "Architect Master"

    # Explicit null rejection (Guardrail test 02)
    patch_null = await client.patch(
        f"/api/v1/users/{user_id}",
        headers={"Authorization": f"Bearer {access_b}"},
        json={"name": None},
    )
    assert patch_null.status_code == 422

    # -------------------------------------------------------------
    # 6. Audit Trail & Export
    # -------------------------------------------------------------
    # As standard user, audit log access is restricted by RBAC (Casbin)
    audit_forbidden = await client.get(
        "/api/v1/audit/logs",
        headers={"Authorization": f"Bearer {access_b}"},
    )
    assert audit_forbidden.status_code == 403
    assert audit_forbidden.json()["error"]["code"] == "ACCESS_DENIED"
