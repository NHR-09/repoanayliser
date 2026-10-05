from __future__ import annotations

import json
import sqlite3
import threading
import zlib
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


class StateStore:
    """Small local delta store. Source remains in the repository; parse JSON is compressed."""

    def __init__(self, path: str | Path, checkpoint_retention: int = 30):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.checkpoint_retention = checkpoint_retention
        self._lock = threading.RLock()
        self._initialize()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            connection = sqlite3.connect(self.path, timeout=30)
            connection.row_factory = sqlite3.Row
            try:
                yield connection
                connection.commit()
            finally:
                connection.close()

    def _initialize(self) -> None:
        with self.connection() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=NORMAL")
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS repositories (
                    repo_id TEXT PRIMARY KEY,
                    root TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS files (
                    repo_id TEXT NOT NULL,
                    path TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    language TEXT NOT NULL,
                    parsed BLOB NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (repo_id, path)
                );
                CREATE TABLE IF NOT EXISTS checkpoints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    repo_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    delta BLOB NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_checkpoint_repo
                    ON checkpoints(repo_id, id DESC);
                """
            )

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _pack(value: Any) -> bytes:
        raw = json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        return zlib.compress(raw, level=6)

    @staticmethod
    def _unpack(value: bytes) -> Any:
        return json.loads(zlib.decompress(value).decode("utf-8"))

    def set_repository(self, repo_id: str, root: str) -> None:
        with self.connection() as db:
            db.execute(
                """INSERT INTO repositories(repo_id, root, updated_at) VALUES(?, ?, ?)
                   ON CONFLICT(repo_id) DO UPDATE SET root=excluded.root, updated_at=excluded.updated_at""",
                (repo_id, str(Path(root).resolve()), self._now()),
            )

    def hashes(self, repo_id: str) -> dict[str, str]:
        with self.connection() as db:
            rows = db.execute(
                "SELECT path, content_hash FROM files WHERE repo_id=?", (repo_id,)
            ).fetchall()
        return {row["path"]: row["content_hash"] for row in rows}

    def put_file(self, repo_id: str, path: str, content_hash: str, language: str, parsed: dict[str, Any]) -> None:
        with self.connection() as db:
            db.execute(
                """INSERT INTO files(repo_id, path, content_hash, language, parsed, updated_at)
                   VALUES(?, ?, ?, ?, ?, ?)
                   ON CONFLICT(repo_id, path) DO UPDATE SET
                     content_hash=excluded.content_hash,
                     language=excluded.language,
                     parsed=excluded.parsed,
                     updated_at=excluded.updated_at""",
                (repo_id, path, content_hash, language, self._pack(parsed), self._now()),
            )

    def delete_files(self, repo_id: str, paths: list[str]) -> None:
        if not paths:
            return
        with self.connection() as db:
            db.executemany(
                "DELETE FROM files WHERE repo_id=? AND path=?",
                [(repo_id, path) for path in paths],
            )

    def parsed_files(self, repo_id: str) -> list[dict[str, Any]]:
        with self.connection() as db:
            rows = db.execute(
                "SELECT parsed FROM files WHERE repo_id=? ORDER BY path", (repo_id,)
            ).fetchall()
        return [self._unpack(row["parsed"]) for row in rows]

    def add_checkpoint(self, repo_id: str, delta: dict[str, Any]) -> int:
        with self.connection() as db:
            cursor = db.execute(
                "INSERT INTO checkpoints(repo_id, created_at, delta) VALUES(?, ?, ?)",
                (repo_id, self._now(), self._pack(delta)),
            )
            checkpoint_id = int(cursor.lastrowid)
            db.execute(
                """DELETE FROM checkpoints WHERE repo_id=? AND id NOT IN (
                       SELECT id FROM checkpoints WHERE repo_id=? ORDER BY id DESC LIMIT ?
                   )""",
                (repo_id, repo_id, self.checkpoint_retention),
            )
        return checkpoint_id

    def stats(self, repo_id: str) -> dict[str, int]:
        with self.connection() as db:
            file_count = db.execute(
                "SELECT count(*) FROM files WHERE repo_id=?", (repo_id,)
            ).fetchone()[0]
            checkpoint_count = db.execute(
                "SELECT count(*) FROM checkpoints WHERE repo_id=?", (repo_id,)
            ).fetchone()[0]
        return {"cached_files": file_count, "ephemeral_checkpoints": checkpoint_count}
