"""
Memento API - FastAPI application entry point.

This API provides endpoints for:
- User profiles management
- Event creation and management
- Event memberships (joining/leaving events)
- Consent management for privacy controls
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    consents_router,
    events_router,
    memberships_router,
    profiles_router,
    recognition_router,
)
from app.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events."""
    # Startup: validate settings are loadable
    settings = get_settings()
    print(f"Starting {settings.app_name}...")
    yield
    # Shutdown
    print("Shutting down...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description=(
            "Memento API for event-scoped networking with privacy controls.\n\n"
            "## Features\n"
            "- **Profiles**: Manage user profiles with customizable visibility\n"
            "- **Events**: Create and manage networking events\n"
            "- **Memberships**: Join/leave events with role management\n"
            "- **Consents**: Fine-grained privacy controls per event\n"
            "- **Recognition**: Face detection and identification via MentraOS glasses\n\n"
            "## Authentication\n"
            "All endpoints require a valid Supabase JWT in the Authorization header. "
            "Use `Bearer <token>` format.\n\n"
            "## Privacy\n"
            "User profiles are only visible to other users who:\n"
            "1. Share at least one event membership\n"
            "2. Have consent from the profile owner for that event"
        ),
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS middleware - configure for your frontend domain
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",  # Local development
            "http://localhost:5173",  # Vite default
            # Add production URLs here
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    app.include_router(profiles_router, prefix="/api/v1")
    app.include_router(events_router, prefix="/api/v1")
    app.include_router(memberships_router, prefix="/api/v1")
    app.include_router(consents_router, prefix="/api/v1")
    app.include_router(recognition_router, prefix="/api/v1")

    @app.get("/")
    async def root():
        """Health check endpoint."""
        return {"status": "ok", "service": settings.app_name}

    @app.get("/health")
    async def health():
        """Detailed health check."""
        return {
            "status": "healthy",
            "service": settings.app_name,
            "version": "1.0.0",
        }

    return app


# Create the app instance
app = create_app()
