from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


MCP_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = MCP_ROOT.parent
BACKEND_ROOT = PROJECT_ROOT / "backend"
DATA_ROOT = MCP_ROOT / ".data"

load_dotenv(BACKEND_ROOT / ".env", override=False)


@dataclass(frozen=True)
class Config:
    neo4j_uri: str = os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687")
    neo4j_user: str = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password: str = os.getenv("NEO4J_PASSWORD", "")
    database: str | None = os.getenv("NEO4J_DATABASE") or None
    state_db: Path = Path(os.getenv("ARCHITECH_MCP_STATE_DB", DATA_ROOT / "state.sqlite3"))
    backend_python: Path = Path(os.getenv(
        "ARCHITECH_BACKEND_PYTHON",
        BACKEND_ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python"),
    ))
    max_page_size: int = 100
    default_page_size: int = 20
    max_response_chars: int = 20_000
    max_source_lines: int = 240
    checkpoint_retention: int = 30


config = Config()
