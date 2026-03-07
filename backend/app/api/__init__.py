"""API routers for the Memento application."""

from .consents import router as consents_router
from .events import router as events_router
from .memberships import router as memberships_router
from .profiles import router as profiles_router
from .recognition import router as recognition_router

__all__ = [
    "consents_router",
    "events_router",
    "memberships_router",
    "profiles_router",
    "recognition_router",
]
