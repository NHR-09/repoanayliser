"""
Security module for ARCHITECH.
Provides password hashing (PBKDF2-HMAC-SHA256), session token management, and FastAPI auth dependencies.
"""

from .passwords import hash_password, verify_password
from .sessions import create_session, validate_session, revoke_session
from .dependencies import get_current_user, require_user, require_hr, require_org_hr

__all__ = [
    "hash_password",
    "verify_password",
    "create_session",
    "validate_session",
    "revoke_session",
    "get_current_user",
    "require_user",
    "require_hr",
    "require_org_hr"
]
