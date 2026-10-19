import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_ui_redirect(client: AsyncClient) -> None:
    """Verifies that GET /ui redirects to /ui/."""
    response = await client.get("/ui", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/ui/"


@pytest.mark.asyncio
async def test_ui_mount_serves_html(client: AsyncClient) -> None:
    """Verifies that GET /ui/ serves static index.html with text/html content-type."""
    response = await client.get("/ui/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Enterprise API Workbench" in response.text
    assert '<base href="/ui/">' in response.text
