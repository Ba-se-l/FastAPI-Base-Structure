import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_validation_error_envelope(client: AsyncClient):
    """Verifies that 422 RequestValidationError returns unified ErrorResponse envelope."""
    # 1. Invalid payload: invalid email format and weak password
    invalid_payload = {
        'name': 'Invalid User',
        'email': 'not-an-email',
        'password': 'short',
    }

    response = await client.post('/api/v1/auth/register', json=invalid_payload)
    assert response.status_code == 422

    data = response.json()
    # Verify ErrorResponse structure
    assert data['success'] is False
    assert 'error' in data
    assert data['error']['code'] == 'VALIDATION_ERROR'
    assert data['error']['message'] == 'Invalid request payload.'
    assert isinstance(data['error']['details'], list)
    assert len(data['error']['details']) > 0

    # Verify request_id correlation
    assert 'request_id' in data
    assert data['request_id'] is not None
    assert response.headers.get('X-Request-ID') == data['request_id']


@pytest.mark.asyncio
async def test_validation_error_missing_body(client: AsyncClient):
    """Verifies that empty request body triggers 422 with ErrorResponse envelope."""
    response = await client.post('/api/v1/auth/login', json={})
    assert response.status_code == 422

    data = response.json()
    assert data['success'] is False
    assert data['error']['code'] == 'VALIDATION_ERROR'
    assert len(data['error']['details']) >= 2  # email and password missing


@pytest.mark.asyncio
async def test_validation_error_custom_validator_value_error(client: AsyncClient):
    """Verifies that custom @field_validator ValueError exceptions are serialized cleanly."""
    payload = {
        'name': 'Valid Name',
        'email': 'valid@enterprise.io',
        'password': 'weakpassword123',
    }
    response = await client.post('/api/v1/auth/register', json=payload)
    assert response.status_code == 422

    data = response.json()
    assert data['success'] is False
    assert data['error']['code'] == 'VALIDATION_ERROR'
    assert 'Password must contain at least one uppercase letter' in str(data['error']['details'])

