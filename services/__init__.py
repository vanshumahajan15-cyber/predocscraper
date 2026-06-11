"""Service layer for persistence and notifications."""

from services.notifier import send_notification
from services.storage import merge_and_save

__all__ = ["merge_and_save", "send_notification"]
