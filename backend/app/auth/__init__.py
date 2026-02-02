"""Authentication module for Supabase JWT verification."""

from .dependencies import CurrentUser, get_current_user, get_current_user_optional
from .router import router as auth_router
from .schemas import (
    AuthResponse,
    SignInRequest,
    SignUpRequest,
    TokenVerifyRequest,
    TokenVerifyResponse,
    UserInfo,
)

__all__ = [
    "AuthResponse",
    "CurrentUser",
    "SignInRequest",
    "SignUpRequest",
    "auth_router",
    "get_current_user",
    "get_current_user_optional",
    "TokenVerifyRequest",
    "TokenVerifyResponse",
    "UserInfo",
]
