"""Data Access Layers for Supabase tables."""

from .analytics_dal import AnalyticsDAL
from .consent_dal import ConsentDAL
from .event_dal import EventDAL
from .membership_dal import MembershipDAL
from .notification_dal import NotificationDAL
from .profile_dal import ProfileDAL

__all__ = [
    "AnalyticsDAL",
    "ConsentDAL",
    "EventDAL",
    "MembershipDAL",
    "ProfileDAL",
    "NotificationDAL",
]
