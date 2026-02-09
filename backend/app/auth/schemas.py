"""
Pydantic schemas for authentication API requests and responses.
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class UserInfo(BaseModel):
    """Minimal user info returned by auth endpoints."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    email: str | None = None


class SignUpRequest(BaseModel):
    """Request body for POST /auth/signup."""

    email: EmailStr
    password: str
    full_name: str | None = None


class SignInRequest(BaseModel):
    """Request body for POST /auth/signin."""

    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    """Response from signup/signin endpoints."""

    user: UserInfo
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenVerifyRequest(BaseModel):
    """Request body for POST /auth/verify - optionally pass token in body."""

    token: str | None = None


class TokenVerifyResponse(BaseModel):
    """Response from token verification endpoint."""

    valid: bool
    user: UserInfo | None = None


class OAuthUrlResponse(BaseModel):
    """Response containing the OAuth authorization URL and code verifier for PKCE."""

    url: str
    provider: str
    code_verifier: str  # Client must store this and send it back with the code


class OAuthCallbackRequest(BaseModel):
    """Request body for OAuth callback - exchange code for session."""

    code: str
    code_verifier: str  # The code_verifier from the initial OAuth URL response
