"""
Authentication API router.
Provides endpoints for signup, signin, session validation, and token verification.
"""

import base64
import hashlib
import secrets
from typing import Annotated
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.dependencies import CurrentUser, get_current_user, verify_jwt
from app.auth.schemas import (
    AuthResponse,
    OAuthCallbackRequest,
    OAuthUrlResponse,
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


# =============================================================================
# OAuth Endpoints (Google & Apple)
# =============================================================================

SUPPORTED_OAUTH_PROVIDERS = {"google", "apple"}


def generate_pkce_pair() -> tuple[str, str]:
    """Generate PKCE code_verifier and code_challenge pair."""
    # Generate a random code_verifier (43-128 characters)
    code_verifier = secrets.token_urlsafe(32)

    # Create code_challenge using S256 method
    code_challenge_digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(code_challenge_digest).rstrip(b"=").decode()

    return code_verifier, code_challenge


@router.get("/oauth/{provider}", response_model=OAuthUrlResponse)
async def get_oauth_url(
    provider: str,
    redirect_to: str | None = None,
) -> OAuthUrlResponse:
    """
    Get the OAuth authorization URL for the specified provider.
    Redirect the user to this URL to start the OAuth flow.

    IMPORTANT: Save the returned code_verifier - you must send it back
    when calling /oauth/callback with the authorization code.

    Supported providers: google, apple

    Args:
        provider: The OAuth provider (google or apple)
        redirect_to: Optional URL to redirect to after successful auth.
    """
    provider_lower = provider.lower()
    if provider_lower not in SUPPORTED_OAUTH_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported provider: {provider}. "
                f"Supported: {', '.join(SUPPORTED_OAUTH_PROVIDERS)}"
            ),
        )

    settings = get_settings()

    try:
        # Generate PKCE pair
        code_verifier, code_challenge = generate_pkce_pair()

        # Build the OAuth URL manually to include our PKCE challenge
        params = {
            "provider": provider_lower,
            "code_challenge": code_challenge,
            "code_challenge_method": "s256",
        }
        if redirect_to:
            params["redirect_to"] = redirect_to

        oauth_url = f"{settings.supabase_url}/auth/v1/authorize?{urlencode(params)}"

        return OAuthUrlResponse(
            url=oauth_url,
            provider=provider_lower,
            code_verifier=code_verifier,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OAuth initialization failed: {str(e)}",
        )


@router.post("/oauth/callback", response_model=AuthResponse)
async def oauth_callback(data: OAuthCallbackRequest) -> AuthResponse:
    """
    Exchange OAuth authorization code for session tokens.
    Call this after the user is redirected back from the provider with a code.

    You must provide the code_verifier that was returned from the /oauth/{provider} endpoint.

    Works for both Google and Apple OAuth.

    Automatically creates a user profile on first sign-in using OAuth metadata.
    """
    import httpx

    settings = get_settings()

    try:
        # Exchange code for session using Supabase's token endpoint
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.supabase_url}/auth/v1/token?grant_type=pkce",
                json={
                    "auth_code": data.code,
                    "code_verifier": data.code_verifier,
                },
                headers={
                    "apikey": settings.supabase_anon_key,
                    "Content-Type": "application/json",
                },
            )

        if response.status_code != 200:
            error_detail = response.json().get("error_description", response.text)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Failed to exchange code for session: {error_detail}",
            )

        token_data = response.json()
        user_id = token_data["user"]["id"]
        user_metadata = token_data["user"].get("user_metadata", {})

        # Auto-create profile if it doesn't exist
        await _ensure_profile_exists(
            user_id=user_id,
            email=token_data["user"].get("email"),
            user_metadata=user_metadata,
        )

        return AuthResponse(
            user=UserInfo(
                id=UUID(user_id),
                email=token_data["user"].get("email"),
            ),
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            expires_in=token_data.get("expires_in", 3600),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"OAuth callback failed: {str(e)}",
        )


async def _ensure_profile_exists(
    user_id: str,
    email: str | None,
    user_metadata: dict,
) -> None:
    """
    Check if a profile exists for the user, and create one if not.
    Uses admin client to bypass RLS during auth flow.

    Extracts name and photo from OAuth provider metadata.
    """
    import logging

    from app.db.supabase import get_admin_client

    logger = logging.getLogger(__name__)

    try:
        admin_client = get_admin_client()

        # Log the metadata we received
        logger.info(f"OAuth user_metadata for {user_id}: {user_metadata}")

        # Check if profile already exists
        existing = admin_client.table("profiles").select("user_id").eq("user_id", user_id).execute()

        if existing.data and len(existing.data) > 0:
            # Profile already exists, nothing to do
            logger.info(f"Profile already exists for user {user_id}")
            return

        # Extract name from OAuth metadata (Google provides these fields)
        full_name = (
            user_metadata.get("full_name")
            or user_metadata.get("name")
            or (email.split("@")[0] if email else "Unknown User")
        )

        # Extract photo URL from OAuth metadata
        photo_url = user_metadata.get("picture") or user_metadata.get("avatar_url")

        # Create the profile
        profile_data = {
            "user_id": user_id,
            "full_name": full_name,
            "photo_path": photo_url,
        }

        logger.info(f"Creating profile for user {user_id}: {profile_data}")

        result = admin_client.table("profiles").insert(profile_data).execute()
        logger.info(f"Profile created successfully: {result.data}")

    except Exception as e:
        logger.error(f"Failed to create profile for user {user_id}: {e}")
        # Don't raise - profile creation failure shouldn't block auth
