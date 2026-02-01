"""Tests for the main FastAPI application."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create a test client for the app."""
    return TestClient(app)


def test_root_endpoint_returns_greeting(client):
    """Root endpoint should return the welcome string."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == "Hello world, welcome to Memento"
