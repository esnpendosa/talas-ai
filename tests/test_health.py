"""
TALAS AI — Test Health Check Endpoints
"""
import pytest


class TestHealthEndpoints:
    """Test health check dan ping endpoints."""

    @pytest.mark.asyncio
    async def test_ping(self, client):
        """Endpoint /api/ping harus merespons."""
        response = await client.get("/api/ping")
        assert response.status_code == 200
        data = response.json()
        assert data["ping"] == "pong"
        assert "app" in data
        assert data["app"] == "TALAS AI"

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Endpoint /api/health harus merespons dengan status."""
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ("healthy", "degraded")
        assert "database" in data
        assert "version" in data

    @pytest.mark.asyncio
    async def test_health_check_database_info(self, client):
        """Health check harus menyertakan info database."""
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert "database" in data
        db_info = data["database"]
        assert "status" in db_info

    @pytest.mark.asyncio
    async def test_root_endpoint(self, client):
        """Root endpoint / harus merespons dengan 200."""
        response = await client.get("/")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_security_headers(self, client):
        """Response harus mengandung security headers."""
        response = await client.get("/api/ping")
        assert "x-content-type-options" in response.headers
        assert response.headers["x-content-type-options"] == "nosniff"
        assert "x-frame-options" in response.headers
        assert response.headers["x-frame-options"] == "DENY"

    @pytest.mark.asyncio
    async def test_404_response_format(self, client):
        """Response 404 harus dalam format standar tanpa stack trace."""
        response = await client.get("/api/endpoint-yang-tidak-ada")
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
        assert "message" in data
        # Pastikan tidak ada stack trace
        assert "traceback" not in str(data).lower()
        assert "exception" not in data
