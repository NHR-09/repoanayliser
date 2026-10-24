"""
Database module for ARCHITECH.
Provides relational persistence via SQLite with WAL mode, foreign keys, and migration tracking.
"""

from .connection import get_db_connection, init_db

__all__ = ["get_db_connection", "init_db"]
