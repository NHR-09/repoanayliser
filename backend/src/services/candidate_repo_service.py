import os
import re
import uuid
import hashlib
import urllib.parse
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from src.db.connection import get_db_connection
from src.analysis_engine import AnalysisEngine

logger = logging.getLogger(__name__)

# Strict GitHub URL pattern: https://github.com/owner/repo or https://github.com/owner/repo.git
GITHUB_URL_REGEX = re.compile(
    r"^https://github\.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+?)(?:\.git)?/?$"
)

# SSRF and blocked host checks
BLOCKED_HOST_PATTERNS = [
    r"^localhost$",
    r"^127\.",
    r"^10\.",
    r"^172\.(1[6-9]|2[0-9]|3[01])\.",
    r"^192\.168\.",
    r"^169\.254\.",
    r"^0\.",
    r"^::1$",
    r"^fc00:",
    r"^fe80:",
]

class CandidateRepositoryService:
    def __init__(self, engine: Optional[AnalysisEngine] = None):
        self._engine = engine

    @property
    def engine(self) -> AnalysisEngine:
        if self._engine is None:
            self._engine = AnalysisEngine()
        return self._engine

    def validate_github_url(self, repo_url: str) -> Dict[str, str]:
        """
        Strictly validate GitHub URL against SSRF, internal IP ranges,
        credentials in URLs, unexpected ports, and malformed paths.
        """
        if not repo_url or not isinstance(repo_url, str):
            raise ValueError("Repository URL is required.")

        clean_url = repo_url.strip()
        parsed = urllib.parse.urlparse(clean_url)

        # 1. Enforce HTTPS scheme
        if parsed.scheme.lower() != "https":
            raise ValueError("Invalid URL scheme. Only secure 'https://' URLs are permitted.")

        # 2. Reject credentials in URL (e.g., https://user:pass@github.com)
        if parsed.username or parsed.password:
            raise ValueError("Embedded credentials in repository URLs are strictly prohibited.")

        # 3. Reject non-standard ports
        if parsed.port and parsed.port != 443:
            raise ValueError(f"Unexpected port {parsed.port}. Only standard HTTPS (port 443) is allowed.")

        # 4. Hostname check - must be strictly github.com
        hostname = (parsed.hostname or "").lower()
        if hostname != "github.com":
            raise ValueError("Invalid host. Only official 'github.com' repositories are currently supported.")

        # 5. Regex match for owner and repository name
        match = GITHUB_URL_REGEX.match(clean_url)
        if not match:
            raise ValueError("Invalid GitHub repository format. Expected: 'https://github.com/<owner>/<repo>'.")

        owner, repo_name = match.groups()
        # Ensure no path traversal in owner or repo name
        if ".." in owner or ".." in repo_name or "/" in owner or "/" in repo_name:
            raise ValueError("Malformed repository path detected.")

        canonical_url = f"https://github.com/{owner}/{repo_name}"
        return {
            "owner": owner,
            "repo_name": repo_name,
            "canonical_url": canonical_url
        }

    def register_repository(
        self,
        user_id: str,
        repo_url: str,
        display_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Register a validated GitHub repository in user's workspace,
        compute neo4j_repo_id, record ownership and access grants.
        """
        validated = self.validate_github_url(repo_url)
        canonical_url = validated["canonical_url"]
        repo_name = validated["repo_name"]
        owner = validated["owner"]

        # Derive 16-character SHA-256 repo_id matching AnalysisEngine convention
        neo4j_repo_id = hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()[:16]
        disp_name = display_name.strip() if display_name else f"{owner}/{repo_name}"

        now = datetime.utcnow().isoformat()

        with get_db_connection() as conn:
            # Check if this repository already exists in SQLite
            existing = conn.execute(
                "SELECT * FROM repositories WHERE neo4j_repo_id = ? OR repo_url = ?",
                (neo4j_repo_id, canonical_url)
            ).fetchone()

            if existing:
                repo_id = existing["id"]
                # Ensure current user has access grant
                grant_exists = conn.execute(
                    "SELECT id FROM repository_access_grants WHERE repository_id = ? AND user_id = ?",
                    (repo_id, user_id)
                ).fetchone()

                if not grant_exists:
                    grant_id = str(uuid.uuid4())
                    conn.execute("""
                        INSERT INTO repository_access_grants (id, repository_id, user_id, permission, created_at)
                        VALUES (?, ?, ?, 'ADMIN', ?)
                    """, (grant_id, repo_id, user_id, now))

                return dict(existing)

            # Insert new repository record
            repo_id = str(uuid.uuid4())
            conn.execute("""
                INSERT INTO repositories (
                    id, neo4j_repo_id, owner_user_id, display_name, repo_url,
                    default_branch, is_public, analysis_status, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, 'main', 1, 'PENDING', ?, ?)
            """, (
                repo_id,
                neo4j_repo_id,
                user_id,
                disp_name,
                canonical_url,
                now,
                now
            ))

            # Grant candidate ADMIN permission on their personal repo
            grant_id = str(uuid.uuid4())
            conn.execute("""
                INSERT INTO repository_access_grants (id, repository_id, user_id, permission, created_at)
                VALUES (?, ?, ?, 'ADMIN', ?)
            """, (grant_id, repo_id, user_id, now))

            row = conn.execute("SELECT * FROM repositories WHERE id = ?", (repo_id,)).fetchone()
            return dict(row)

    def check_user_access(self, user_id: str, repo_id: str) -> bool:
        """Verify user is owner or has active grant on repository."""
        with get_db_connection() as conn:
            row = conn.execute("""
                SELECT r.id FROM repositories r
                LEFT JOIN repository_access_grants g ON g.repository_id = r.id AND g.user_id = ?
                WHERE r.id = ? AND (r.owner_user_id = ? OR g.id IS NOT NULL)
            """, (user_id, repo_id, user_id)).fetchone()
            return row is not None

    def get_user_repositories(self, user_id: str) -> List[Dict[str, Any]]:
        """List all repositories the user has access to."""
        with get_db_connection() as conn:
            rows = conn.execute("""
                SELECT DISTINCT r.id, r.neo4j_repo_id, r.display_name, r.repo_url,
                                r.analysis_status, r.last_analyzed_commit, r.last_analyzed_at,
                                r.analysis_error, r.created_at
                FROM repositories r
                LEFT JOIN repository_access_grants g ON g.repository_id = r.id AND g.user_id = ?
                WHERE r.owner_user_id = ? OR g.id IS NOT NULL
                ORDER BY r.created_at DESC
            """, (user_id, user_id)).fetchall()
            return [dict(r) for r in rows]

    def get_repository_details(self, user_id: str, repo_id: str) -> Dict[str, Any]:
        """Fetch repository details, checking access."""
        if not self.check_user_access(user_id, repo_id):
            raise PermissionError("Access denied to repository.")

        with get_db_connection() as conn:
            row = conn.execute("SELECT * FROM repositories WHERE id = ?", (repo_id,)).fetchone()
            if not row:
                raise ValueError("Repository not found.")
            return dict(row)

    def run_repository_analysis_task(self, repo_id: str):
        """
        Background task to execute ARCHITECH's analysis engine,
        building Tree-sitter AST, Neo4j code graph, NetworkX coupling, and patterns.
        """
        with get_db_connection() as conn:
            row = conn.execute("SELECT * FROM repositories WHERE id = ?", (repo_id,)).fetchone()
            if not row:
                return

            repo_url = row["repo_url"]
            conn.execute(
                "UPDATE repositories SET analysis_status = 'RUNNING', analysis_error = NULL WHERE id = ?",
                (repo_id,)
            )

        try:
            logger.info(f"🚀 Starting ARCHITECH repository analysis for {repo_url} (ID: {repo_id})")
            result = self.engine.analyze_repository(repo_url)
            commit_hash = result.get("commit_hash") or result.get("commit") or "HEAD"
            now = datetime.utcnow().isoformat()

            with get_db_connection() as conn:
                conn.execute("""
                    UPDATE repositories
                    SET analysis_status = 'COMPLETED',
                        last_analyzed_commit = ?,
                        last_analyzed_at = ?,
                        analysis_error = NULL,
                        updated_at = ?
                    WHERE id = ?
                """, (commit_hash, now, now, repo_id))
            logger.info(f"✅ Repository analysis completed successfully for {repo_url}")

        except Exception as e:
            logger.error(f"❌ Repository analysis failed for {repo_url}: {e}", exc_info=True)
            now = datetime.utcnow().isoformat()
            with get_db_connection() as conn:
                conn.execute("""
                    UPDATE repositories
                    SET analysis_status = 'FAILED',
                        analysis_error = ?,
                        updated_at = ?
                    WHERE id = ?
                """, (str(e), now, repo_id))
