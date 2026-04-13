"""Tests for password reset and sign-out endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import CurrentUser, get_current_user
from app.main import app

FAKE_USER = CurrentUser(
    id=UUID("00000000-0000-0000-0000-000000000001"),
    email="test@example.com",
    access_token="fake-token",
)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def authed_client():
    """Client with auth dependency overridden."""
    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    c = TestClient(app)
    yield c
    app.dependency_overrides.pop(get_current_user, None)


# ─── Sign-Out ──────────────────────────────────────────────────────────────────


class TestSignOut:
    """Tests for POST /api/v1/auth/signout."""

    def test_signout_requires_authentication(self, client):
        response = client.post("/api/v1/auth/signout")
        assert response.status_code == 401

    @patch("app.auth.router.create_client")
    def test_signout_success(self, mock_create_client, authed_client):
        mock_supabase = MagicMock()
        mock_create_client.return_value = mock_supabase

        response = authed_client.post("/api/v1/auth/signout")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Signed out successfully"
        mock_supabase.auth.admin.sign_out.assert_called_once_with("fake-token")

    @patch("app.auth.router.create_client")
    def test_signout_succeeds_even_if_supabase_fails(self, mock_create_client, authed_client):
        """Sign-out should not fail even if Supabase throws an error."""
        mock_supabase = MagicMock()
        mock_supabase.auth.admin.sign_out.side_effect = Exception("Supabase down")
        mock_create_client.return_value = mock_supabase

        response = authed_client.post("/api/v1/auth/signout")

        assert response.status_code == 200
        assert response.json()["message"] == "Signed out successfully"


# ─── Password Reset Request ───────────────────────────────────────────────────


class TestPasswordResetRequest:
    """Tests for POST /api/v1/auth/reset-password."""

    @patch("app.auth.router.create_client")
    def test_reset_password_sends_email(self, mock_create_client, client):
        mock_supabase = MagicMock()
        mock_create_client.return_value = mock_supabase

        response = client.post(
            "/api/v1/auth/reset-password",
            json={"email": "test@example.com"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "reset link" in data["message"].lower()
        mock_supabase.auth.reset_password_email.assert_called_once()

    @patch("app.auth.router.create_client")
    def test_reset_password_with_redirect(self, mock_create_client, client):
        mock_supabase = MagicMock()
        mock_create_client.return_value = mock_supabase

        response = client.post(
            "/api/v1/auth/reset-password",
            json={
                "email": "test@example.com",
                "redirect_to": "https://example.com/reset",
            },
        )

        assert response.status_code == 200
        call_args = mock_supabase.auth.reset_password_email.call_args
        assert call_args[1]["options"]["redirect_to"] == "https://example.com/reset"

    @patch("app.auth.router.create_client")
    def test_reset_password_always_succeeds_for_unknown_email(self, mock_create_client, client):
        """Prevents email enumeration — always returns success."""
        mock_supabase = MagicMock()
        mock_supabase.auth.reset_password_email.side_effect = Exception("User not found")
        mock_create_client.return_value = mock_supabase

        response = client.post(
            "/api/v1/auth/reset-password",
            json={"email": "nobody@example.com"},
        )

        assert response.status_code == 200
        assert "reset link" in response.json()["message"].lower()

    def test_reset_password_validates_email_format(self, client):
        response = client.post(
            "/api/v1/auth/reset-password",
            json={"email": "not-an-email"},
        )

        assert response.status_code == 422

    def test_reset_password_requires_email(self, client):
        response = client.post(
            "/api/v1/auth/reset-password",
            json={},
        )

        assert response.status_code == 422


# ─── Password Reset Confirm ───────────────────────────────────────────────────


class TestPasswordResetConfirm:
    """Tests for POST /api/v1/auth/reset-password/confirm."""

    @patch("app.auth.router.httpx.AsyncClient")
    def test_confirm_reset_success(self, mock_async_client_cls, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "user-123"}

        mock_http_client = AsyncMock()
        mock_http_client.put.return_value = mock_response

        mock_async_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_async_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)

        response = client.post(
            "/api/v1/auth/reset-password/confirm",
            json={
                "access_token": "valid-reset-token",
                "new_password": "newpassword123",
            },
        )

        assert response.status_code == 200
        assert response.json()["message"] == "Password updated successfully"

    @patch("app.auth.router.httpx.AsyncClient")
    def test_confirm_reset_invalid_token(self, mock_async_client_cls, client):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"message": "Invalid or expired token"}

        mock_http_client = AsyncMock()
        mock_http_client.put.return_value = mock_response

        mock_async_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_async_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)

        response = client.post(
            "/api/v1/auth/reset-password/confirm",
            json={
                "access_token": "expired-token",
                "new_password": "newpassword123",
            },
        )

        assert response.status_code == 400

    def test_confirm_reset_requires_both_fields(self, client):
        response = client.post(
            "/api/v1/auth/reset-password/confirm",
            json={"access_token": "some-token"},
        )
        assert response.status_code == 422

        response = client.post(
            "/api/v1/auth/reset-password/confirm",
            json={"new_password": "some-password"},
        )
        assert response.status_code == 422

    def test_confirm_reset_empty_body(self, client):
        response = client.post(
            "/api/v1/auth/reset-password/confirm",
            json={},
        )
        assert response.status_code == 422
