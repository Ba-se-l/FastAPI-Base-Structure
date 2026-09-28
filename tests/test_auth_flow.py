import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_auth_full_lifecycle(client: AsyncClient):
    """Tests registration, login, token refresh, and logout flow."""
    user_payload = {
        'name': 'Test Engineer',
        'email': 'engineer@enterprise.io',
        'password': 'StrongP@ssw0rd!',
        'device_fingerprint': 'test-runner-agent-1',
    }

    # 1. Register new user
    reg_response = await client.post('/api/v1/auth/register', json=user_payload)
    assert reg_response.status_code == 201
    data = reg_response.json()
    assert data['email'] == user_payload['email']
    assert data['name'] == user_payload['name']
    assert data['role'] == 'user'
    assert 'id' in data

    # 2. Reject duplicate email with 409 Conflict
    dup_response = await client.post('/api/v1/auth/register', json=user_payload)
    assert dup_response.status_code == 409
    dup_data = dup_response.json()
    assert dup_data['success'] is False
    assert dup_data['error']['code'] == 'USER_ALREADY_EXISTS'

    # 3. Reject weak password with 422 Unprocessable Entity
    weak_payload = dict(user_payload)
    weak_payload['email'] = 'other@enterprise.io'
    weak_payload['password'] = 'simple'
    weak_response = await client.post('/api/v1/auth/register', json=weak_payload)
    assert weak_response.status_code == 422

    # 4. Login with valid credentials
    login_response = await client.post(
        '/api/v1/auth/login',
        json={'email': user_payload['email'], 'password': user_payload['password']},
    )
    assert login_response.status_code == 200
    tokens = login_response.json()
    access_token = tokens['access_token']
    refresh_token = tokens['refresh_token']
    assert access_token is not None
    assert refresh_token is not None

    # 5. Refresh token rotation
    refresh_response = await client.post(
        '/api/v1/auth/refresh',
        json={'refresh_token': refresh_token},
    )
    assert refresh_response.status_code == 200
    new_tokens = refresh_response.json()
    new_access_token = new_tokens['access_token']
    new_refresh_token = new_tokens['refresh_token']
    assert new_access_token != access_token
    assert new_refresh_token != refresh_token

    # 6. Old refresh token should now be revoked (replay attack prevention)
    stale_response = await client.post(
        '/api/v1/auth/refresh',
        json={'refresh_token': refresh_token},
    )
    assert stale_response.status_code == 401
    stale_data = stale_response.json()
    assert stale_data['error']['code'] == 'TOKEN_REVOKED'

    # 7. Logout endpoint
    logout_response = await client.post(
        '/api/v1/auth/logout',
        json={'refresh_token': new_refresh_token},
    )
    assert logout_response.status_code == 200
    assert logout_response.json()['success'] is True
