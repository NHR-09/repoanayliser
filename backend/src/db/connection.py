import sqlite3
import os
from pathlib import Path
from contextlib import contextmanager
from typing import Generator, Optional
import logging

from ..config import settings

logger = logging.getLogger(__name__)

def resolve_db_path(custom_path: Optional[str] = None) -> Path:
    """Resolve the SQLite database path ensuring parent directory exists."""
    path_str = custom_path or settings.db_path
    db_file = Path(path_str)
    if not db_file.is_absolute():
        # Resolve relative to backend root (parent of src)
        backend_root = Path(__file__).resolve().parent.parent.parent
        db_file = backend_root / db_file
    db_file.parent.mkdir(parents=True, exist_ok=True)
    return db_file

@contextmanager
def get_db_connection(custom_path: Optional[str] = None) -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager yielding a thread-safe SQLite connection.
    Enforces foreign keys, WAL mode, synchronous normal, and row_factory = sqlite3.Row.
    Commits on success, rolls back on exception.
    """
    db_file = resolve_db_path(custom_path)
    conn = sqlite3.connect(
        str(db_file),
        timeout=30.0,
        check_same_thread=False
    )
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def init_db(custom_path: Optional[str] = None):
    """Run all schema migrations on the database."""
    from .migrations import run_migrations
    run_migrations(custom_path)
