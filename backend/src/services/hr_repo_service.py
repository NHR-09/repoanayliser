import uuid
import hashlib
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from src.db.connection import get_db_connection
from src.analysis_engine import AnalysisEngine
from src.services.candidate_repo_service import CandidateRepositoryService

logger = logging.getLogger(__name__)

CORE_COMPETENCIES = [
    'CODE_COMPREHENSION',
    'DEPENDENCY_TRACING',
    'ARCHITECTURE_REASONING',
    'DEBUGGING',
    'CHANGE_IMPACT'
]

class HRRepositoryLibraryService:
    def __init__(self, engine: Optional[AnalysisEngine] = None):
        self._engine = engine
        self._cand_service = CandidateRepositoryService(engine=engine)

    @property
    def engine(self) -> AnalysisEngine:
        if self._engine is None:
            self._engine = AnalysisEngine()
        return self._engine

    def register_repository_for_org(
        self,
        organization_id: str,
        user_id: str,
        repo_url: str,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        intended_evaluations: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Register a verified GitHub repository in the Organization Repository Library.
        Enforces SSRF validation, links to organization, and sets approval_status='REGISTERED'.
        """
        validated = self._cand_service.validate_github_url(repo_url)
        canonical_url = validated["canonical_url"]
        owner = validated["owner"]
        repo_name = validated["repo_name"]

        neo4j_repo_id = hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()[:16]
        disp_name = display_name.strip() if display_name else f"{owner}/{repo_name}"
        now = datetime.utcnow().isoformat()

        with get_db_connection() as conn:
            # Check if this repository already exists in database
            existing = conn.execute(
                "SELECT * FROM repositories WHERE neo4j_repo_id = ? OR repo_url = ?",
                (neo4j_repo_id, canonical_url)
            ).fetchone()

            if existing:
                repo_id = existing["id"]
                # Update organization metadata and description
                conn.execute("""
                    UPDATE repositories
                    SET organization_id = COALESCE(organization_id, ?),
                        display_name = COALESCE(display_name, ?),
                        description = COALESCE(description, ?),
                        intended_evaluations = COALESCE(intended_evaluations, ?),
                        approval_status = CASE WHEN approval_status IS NULL THEN 'REGISTERED' ELSE approval_status END,
                        updated_at = ?
                    WHERE id = ?
                """, (organization_id, disp_name, description, intended_evaluations, now, repo_id))

                # Ensure organization access grant exists
                grant = conn.execute(
                    "SELECT id FROM repository_access_grants WHERE repository_id = ? AND organization_id = ?",
                    (repo_id, organization_id)
                ).fetchone()

                if not grant:
                    conn.execute("""
                        INSERT INTO repository_access_grants (id, repository_id, organization_id, permission, created_at)
                        VALUES (?, ?, ?, 'ADMIN', ?)
                    """, (str(uuid.uuid4()), repo_id, organization_id, now))

            else:
                repo_id = str(uuid.uuid4())
                conn.execute("""
                    INSERT INTO repositories (
                        id, neo4j_repo_id, organization_id, display_name, repo_url,
                        default_branch, is_public, analysis_status, approval_status,
                        description, intended_evaluations, is_archived, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, 'main', 1, 'PENDING', 'REGISTERED', ?, ?, 0, ?, ?)
                """, (
                    repo_id,
                    neo4j_repo_id,
                    organization_id,
                    disp_name,
                    canonical_url,
                    description,
                    intended_evaluations,
                    now,
                    now
                ))

                conn.execute("""
                    INSERT INTO repository_access_grants (id, repository_id, organization_id, permission, created_at)
                    VALUES (?, ?, ?, 'ADMIN', ?)
                """, (str(uuid.uuid4()), repo_id, organization_id, now))

            # Audit log
            conn.execute("""
                INSERT INTO audit_logs (id, organization_id, user_id, action, resource_type, resource_id, details, timestamp)
                VALUES (?, ?, ?, 'REGISTER_REPOSITORY', 'REPOSITORY', ?, ?, ?)
            """, (str(uuid.uuid4()), organization_id, user_id, repo_id, f"Registered {canonical_url} in library", now))

            row = conn.execute("SELECT * FROM repositories WHERE id = ?", (repo_id,)).fetchone()
            return dict(row)

    def check_org_repo_access(self, organization_id: str, repo_id: str) -> bool:
        """Verify repository belongs to or is granted to organization."""
        with get_db_connection() as conn:
            row = conn.execute("""
                SELECT r.id FROM repositories r
                LEFT JOIN repository_access_grants g ON g.repository_id = r.id AND g.organization_id = ?
                WHERE r.id = ? AND (r.organization_id = ? OR g.id IS NOT NULL)
            """, (organization_id, repo_id, organization_id)).fetchone()
            return row is not None

    def get_org_repositories(
        self,
        organization_id: str,
        approval_filter: Optional[str] = None,
        include_archived: bool = False
    ) -> List[Dict[str, Any]]:
        """List repositories in organization's approved library."""
        with get_db_connection() as conn:
            query = """
                SELECT DISTINCT r.*,
                       u.full_name as approved_by_name,
                       (SELECT COUNT(*) FROM questions q WHERE q.repository_id = r.id AND q.organization_id = ? AND q.is_archived = 0) as total_questions,
                       (SELECT COUNT(*) FROM questions q WHERE q.repository_id = r.id AND q.organization_id = ? AND q.review_status = 'PUBLISHED') as published_questions
                FROM repositories r
                LEFT JOIN repository_access_grants g ON g.repository_id = r.id AND g.organization_id = ?
                LEFT JOIN users u ON u.id = r.approved_by
                WHERE (r.organization_id = ? OR g.id IS NOT NULL)
            """
            params: List[Any] = [organization_id, organization_id, organization_id, organization_id]

            if not include_archived:
                query += " AND (r.is_archived = 0 OR r.is_archived IS NULL)"

            if approval_filter and approval_filter.strip():
                query += " AND r.approval_status = ?"
                params.append(approval_filter.strip())

            query += " ORDER BY r.created_at DESC"
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def get_org_repository_details(self, organization_id: str, repo_id: str) -> Dict[str, Any]:
        """Fetch complete repository details with approval status and question statistics."""
        if not self.check_org_repo_access(organization_id, repo_id):
            raise PermissionError("Access denied: repository not authorized for this organization.")

        with get_db_connection() as conn:
            row = conn.execute("""
                SELECT r.*,
                       u.full_name as approved_by_name,
                       (SELECT COUNT(*) FROM questions q WHERE q.repository_id = r.id AND q.organization_id = ? AND q.is_archived = 0) as total_questions,
                       (SELECT COUNT(*) FROM questions q WHERE q.repository_id = r.id AND q.organization_id = ? AND q.review_status = 'PUBLISHED') as published_questions
                FROM repositories r
                LEFT JOIN users u ON u.id = r.approved_by
                WHERE r.id = ?
            """, (organization_id, organization_id, repo_id)).fetchone()

            if not row:
                raise ValueError("Repository not found.")
            return dict(row)

    def transition_repo_approval(
        self,
        organization_id: str,
        user_id: str,
        repo_id: str,
        action: str
    ) -> Dict[str, Any]:
        """
        Transition repository lifecycle:
        - APPROVE: -> APPROVED (requires analysis_status == 'COMPLETED')
        - ARCHIVE: -> ARCHIVED (is_archived = 1)
        - RESTORE: -> APPROVED (is_archived = 0)
        """
        repo = self.get_org_repository_details(organization_id, repo_id)
        now = datetime.utcnow().isoformat()
        act = action.strip().upper()

        if act == "APPROVE":
            if repo.get("analysis_status") != "COMPLETED":
                raise ValueError("Cannot approve repository before static code analysis completes successfully.")
            new_approval = "APPROVED"
            is_archived = 0

            with get_db_connection() as conn:
                conn.execute("""
                    UPDATE repositories
                    SET approval_status = ?,
                        approved_by = ?,
                        approved_at = ?,
                        is_archived = ?,
                        updated_at = ?
                    WHERE id = ?
                """, (new_approval, user_id, now, is_archived, now, repo_id))

        elif act == "ARCHIVE":
            new_approval = "ARCHIVED"
            with get_db_connection() as conn:
                conn.execute("""
                    UPDATE repositories
                    SET approval_status = ?,
                        is_archived = 1,
                        updated_at = ?
                    WHERE id = ?
                """, (new_approval, now, repo_id))

        elif act == "RESTORE":
            new_approval = "APPROVED"
            with get_db_connection() as conn:
                conn.execute("""
                    UPDATE repositories
                    SET approval_status = ?,
                        is_archived = 0,
                        updated_at = ?
                    WHERE id = ?
                """, (new_approval, now, repo_id))

        else:
            raise ValueError(f"Unknown repository action '{action}'.")

        # Record audit log
        with get_db_connection() as conn:
            conn.execute("""
                INSERT INTO audit_logs (id, organization_id, user_id, action, resource_type, resource_id, details, timestamp)
                VALUES (?, ?, ?, ?, 'REPOSITORY', ?, ?, ?)
            """, (str(uuid.uuid4()), organization_id, user_id, f"REPO_{act}", repo_id, f"Transitioned repository to {new_approval}", now))

        return self.get_org_repository_details(organization_id, repo_id)

    def get_repository_question_coverage(self, organization_id: str, repo_id: str) -> Dict[str, Any]:
        """
        Compute genuine question coverage metrics for this repository across competencies,
        difficulties, and publication statuses. Never fabricates statistics.
        """
        repo = self.get_org_repository_details(organization_id, repo_id)

        with get_db_connection() as conn:
            # 1. Total questions
            total_row = conn.execute("""
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN review_status = 'PUBLISHED' THEN 1 ELSE 0 END) as published,
                       SUM(CASE WHEN review_status = 'APPROVED' THEN 1 ELSE 0 END) as approved,
                       SUM(CASE WHEN review_status = 'NEEDS_REVIEW' THEN 1 ELSE 0 END) as needs_review,
                       SUM(CASE WHEN is_archived = 1 THEN 1 ELSE 0 END) as archived
                FROM questions
                WHERE repository_id = ? AND organization_id = ?
            """, (repo_id, organization_id)).fetchone()

            # 2. Competency breakdown
            comp_rows = conn.execute("""
                SELECT competency,
                       COUNT(*) as count,
                       SUM(CASE WHEN review_status = 'PUBLISHED' THEN 1 ELSE 0 END) as published_count,
                       SUM(CASE WHEN review_status = 'APPROVED' THEN 1 ELSE 0 END) as approved_count
                FROM questions
                WHERE repository_id = ? AND organization_id = ? AND (is_archived = 0 OR is_archived IS NULL)
                GROUP BY competency
            """, (repo_id, organization_id)).fetchall()

            # 3. Difficulty breakdown
            diff_rows = conn.execute("""
                SELECT difficulty, COUNT(*) as count
                FROM questions
                WHERE repository_id = ? AND organization_id = ? AND (is_archived = 0 OR is_archived IS NULL)
                GROUP BY difficulty
            """, (repo_id, organization_id)).fetchall()

            # 4. Response format breakdown
            fmt_rows = conn.execute("""
                SELECT response_format, COUNT(*) as count
                FROM questions
                WHERE repository_id = ? AND organization_id = ? AND (is_archived = 0 OR is_archived IS NULL)
                GROUP BY response_format
            """, (repo_id, organization_id)).fetchall()

        comp_stats = {c: {"total": 0, "published": 0, "approved": 0} for c in CORE_COMPETENCIES}
        for r in comp_rows:
            comp_stats[r["competency"]] = {
                "total": r["count"],
                "published": r["published_count"] or 0,
                "approved": r["approved_count"] or 0
            }

        diff_stats = {r["difficulty"]: r["count"] for r in diff_rows}
        fmt_stats = {r["response_format"]: r["count"] for r in fmt_rows}

        # Identify missing coverage
        gaps = []
        for c in CORE_COMPETENCIES:
            if comp_stats[c]["published"] == 0:
                gaps.append(c)

        return {
            "repository_id": repo_id,
            "display_name": repo["display_name"],
            "analysis_version": repo.get("last_analyzed_commit") or "HEAD",
            "approval_status": repo.get("approval_status", "REGISTERED"),
            "totals": {
                "total_questions": total_row["total"] or 0,
                "published": total_row["published"] or 0,
                "approved": total_row["approved"] or 0,
                "needs_review": total_row["needs_review"] or 0,
                "archived": total_row["archived"] or 0
            },
            "by_competency": comp_stats,
            "by_difficulty": diff_stats,
            "by_response_format": fmt_stats,
            "coverage_gaps": gaps,
            "is_ready_for_assessments": repo.get("approval_status") == "APPROVED" and (total_row["published"] or 0) >= 5
        }
