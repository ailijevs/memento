"""Tests for the main FastAPI application."""

from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

# Ensure the backend package is importable whether tests are run from repo root or backend/
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

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
