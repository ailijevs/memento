"""API routers for the Memento application."""
from .profiles import router as profiles_router
from .events import router as events_router
from .memberships import router as memberships_router
from .consents import router as consents_router

__all__ = [
    "profiles_router",
    "events_router",
    "memberships_router",
    "consents_router",
]
