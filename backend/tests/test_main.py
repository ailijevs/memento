"""Tests for the main FastAPI application."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create a test client for the app."""
    return TestClient(app)


def test_root_endpoint_returns_status(client):
    """Root endpoint should return status ok."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "service" in data


def test_health_endpoint(client):
    """Health endpoint should return healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
