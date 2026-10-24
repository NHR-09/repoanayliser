"""
API package for ARCHITECH.
"""
from .auth import router as auth_router
from .practice import router as practice_router
from .hr import router as hr_router

__all__ = ["auth_router", "practice_router", "hr_router"]
