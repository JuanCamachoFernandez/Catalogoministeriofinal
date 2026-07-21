"""Canonical mail adapter exposed by the MVC package."""

from .email_service import BrevoEmailService, EmailDeliveryError

__all__ = ["BrevoEmailService", "EmailDeliveryError"]
