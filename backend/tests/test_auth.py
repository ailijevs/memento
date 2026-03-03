"""Tests for authentication endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create a test client for the app."""
    return TestClient(app)


def test_auth_me_requires_authentication(client):
    """GET /api/v1/auth/me should return 401 without Bearer token."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert "not authenticated" in response.json()["detail"].lower()


def test_auth_verify_requires_token(client):
    """POST /api/v1/auth/verify should return 401 when no token provided."""
    response = client.post("/api/v1/auth/verify")
    assert response.status_code == 401
    assert "no token" in response.json()["detail"].lower()


def test_auth_verify_with_invalid_token(client):
    """POST /api/v1/auth/verify with invalid token should return valid=False."""
    response = client.post(
        "/api/v1/auth/verify",
        json={"token": "invalid.jwt.token"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert data["user"] is None
