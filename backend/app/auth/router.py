"""
Authentication API router.
Provides endpoints for signup, signin, session validation, and token verification.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.dependencies import CurrentUser, get_current_user, verify_jwt
from app.auth.schemas import (
    AuthResponse,
    SignInRequest,
    SignUpRequest,
    TokenVerifyRequest,
    TokenVerifyResponse,
    UserInfo,
)
from app.config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)


@router.get("/me", response_model=UserInfo)
async def get_me(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> UserInfo:
    """
    Return the current authenticated user's info from the JWT.
    Use this to validate a session or check if the token is still valid.
    """
    return UserInfo(id=current_user.id, email=current_user.email)


@router.post("/verify", response_model=TokenVerifyResponse)
async def verify_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    body: TokenVerifyRequest | None = Body(default=None),
) -> TokenVerifyResponse:
    """
    Verify a Supabase JWT and return user info if valid.
    Token can be provided via Authorization header (Bearer) or in request body.
    Useful for token refresh validation and client-side session checks.
    """
    token: str | None = None
    if credentials:
        token = credentials.credentials
    elif body and body.token:
        token = body.token

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No token provided. Use Authorization: Bearer <token> or pass token in body.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = verify_jwt(token)
        user_id = payload.get("sub")
        if not user_id:
            return TokenVerifyResponse(valid=False, user=None)

        return TokenVerifyResponse(
            valid=True,
            user=UserInfo(
                id=UUID(user_id),
                email=payload.get("email"),
            ),
        )
    except HTTPException:
        return TokenVerifyResponse(valid=False, user=None)  # Invalid or expired token


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(data: SignUpRequest) -> AuthResponse:
    """
    Create a new user account with email and password.
    Returns access and refresh tokens on success.
    """
    from supabase import create_client

    settings = get_settings()
    supabase = create_client(settings.supabase_url, settings.supabase_anon_key)

    try:
        # Sign up the user
        response = supabase.auth.sign_up(
            {
                "email": data.email,
                "password": data.password,
                "options": {
                    "data": {"full_name": data.full_name} if data.full_name else {},
                },
            }
        )

        if response.user is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create account. Email may already be registered.",
            )

        if response.session is None:
            # Email confirmation required
            raise HTTPException(
                status_code=status.HTTP_202_ACCEPTED,
                detail="Account created. Please check your email to confirm.",
            )

        return AuthResponse(
            user=UserInfo(
                id=UUID(response.user.id),
                email=response.user.email,
            ),
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            expires_in=response.session.expires_in or 3600,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Signup failed: {str(e)}",
        )


@router.post("/signin", response_model=AuthResponse)
async def signin(data: SignInRequest) -> AuthResponse:
    """
    Sign in with email and password.
    Returns access and refresh tokens on success.
    """
    from supabase import create_client

    settings = get_settings()
    supabase = create_client(settings.supabase_url, settings.supabase_anon_key)

    try:
        response = supabase.auth.sign_in_with_password(
            {
                "email": data.email,
                "password": data.password,
            }
        )

        if response.user is None or response.session is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )

        return AuthResponse(
            user=UserInfo(
                id=UUID(response.user.id),
                email=response.user.email,
            ),
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            expires_in=response.session.expires_in or 3600,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Sign in failed: {str(e)}",
        )
