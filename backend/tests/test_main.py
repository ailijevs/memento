"""Tests for the main FastAPI application."""
import pytest
from fastapi.testclient import TestClient

from app.main import app, create_app


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    @pytest.fixture
    def client(self):
        """Create a test client for the app."""
        return TestClient(app)

    def test_root_endpoint(self, client):
        """Test the root endpoint returns OK status."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "service" in data

    def test_health_endpoint(self, client):
        """Test the health endpoint returns healthy status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"


class TestAppCreation:
    """Tests for app factory function."""

    def test_create_app_returns_fastapi_instance(self):
        """Test that create_app returns a FastAPI instance."""
        from fastapi import FastAPI

        test_app = create_app()
        assert isinstance(test_app, FastAPI)

    def test_app_has_required_routers(self):
        """Test that the app includes all required routers."""
        test_app = create_app()
        routes = [route.path for route in test_app.routes]

        # Check that API routes are registered
        assert any("/api/v1/profiles" in str(route) for route in routes)
        assert any("/api/v1/events" in str(route) for route in routes)
        assert any("/api/v1/memberships" in str(route) for route in routes)
        assert any("/api/v1/consents" in str(route) for route in routes)

    def test_app_has_cors_middleware(self):
        """Test that CORS middleware is configured."""
        test_app = create_app()
        middleware_classes = [m.cls.__name__ for m in test_app.user_middleware]
        assert "CORSMiddleware" in middleware_classes
