import hashlib
import secrets
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from src.db.connection import get_db_connection

logger = logging.getLogger(__name__)

class AssessmentAssignmentService:
    """
    Manages candidate assessment invitations, cryptographically secure token generation,
    candidate assignment claims, status transitions, and revocations.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    @staticmethod
    def hash_token(raw_token: str) -> str:
        """Hash token using SHA-256 to ensure raw tokens are never persisted."""
        return hashlib.sha256(raw_token.strip().encode("utf-8")).hexdigest()

    def create_assignments(
        self,
        organization_id: str,
        assessment_id: str,
        candidate_emails: List[str],
        expires_days: int = 7,
        max_attempts: int = 1,
    ) -> List[Dict[str, Any]]:
        """
        Create assignments and secure invitation tokens for candidate emails.
        Only published assessments can be assigned.
        """
        if not candidate_emails:
            raise ValueError("At least one candidate email is required.")

        with get_db_connection(self.db_path) as conn:
            assessment = conn.execute(
                """
                SELECT id, status, published_version_id, max_attempts_per_candidate
                FROM assessments
                WHERE id = ? AND organization_id = ?
                """,
                (assessment_id, organization_id),
            ).fetchone()

            if not assessment:
                raise ValueError("Assessment not found or unauthorized.")
            if assessment["status"] != "PUBLISHED" or not assessment["published_version_id"]:
                raise ValueError("Cannot assign an unpublished assessment. Please publish the assessment first.")

            version_id = assessment["published_version_id"]
            configured_max_attempts = max_attempts or assessment["max_attempts_per_candidate"] or 1
            expires_at = (datetime.now(timezone.utc) + timedelta(days=expires_days)).isoformat()

            results = []
            for email in candidate_emails:
                clean_email = email.strip().lower()
                if not clean_email or "@" not in clean_email:
                    continue

                raw_token = secrets.token_urlsafe(32)
                token_hash = self.hash_token(raw_token)
                assignment_id = str(uuid.uuid4())

                # Check if candidate user already exists
                user_row = conn.execute(
                    "SELECT id FROM users WHERE email = ? COLLATE NOCASE", (clean_email,)
                ).fetchone()
                candidate_id = user_row["id"] if user_row else None

                conn.execute(
                    """
                    INSERT INTO assessment_assignments (
                        id, assessment_id, organization_id, assessment_version_id, candidate_id,
                        candidate_email, invitation_token_hash, expires_at, max_attempts,
                        attempts_used, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 'PENDING')
                    """,
                    (
                        assignment_id,
                        assessment_id,
                        organization_id,
                        version_id,
                        candidate_id,
                        clean_email,
                        token_hash,
                        expires_at,
                        configured_max_attempts,
                    ),
                )

                results.append({
                    "assignment_id": assignment_id,
                    "candidate_email": clean_email,
                    "invitation_token": raw_token,
                    "invitation_url": f"/assessment/invite/{raw_token}",
                    "expires_at": expires_at,
                    "status": "AVAILABLE" if candidate_id else "PENDING",
                })

            return results

    def list_assignments_for_assessment(
        self,
        organization_id: str,
        assessment_id: str,
    ) -> List[Dict[str, Any]]:
        """List all assignments for an assessment for HR review."""
        with get_db_connection(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT aa.*, u.full_name as candidate_name,
                    (SELECT COUNT(*) FROM assessment_attempts WHERE assignment_id = aa.id) as attempts_count,
                    (SELECT status FROM assessment_attempts WHERE assignment_id = aa.id ORDER BY created_at DESC LIMIT 1) as latest_attempt_status,
                    (SELECT percentage_score FROM assessment_attempts WHERE assignment_id = aa.id ORDER BY created_at DESC LIMIT 1) as latest_attempt_score
                FROM assessment_assignments aa
                LEFT JOIN users u ON aa.candidate_id = u.id
                WHERE aa.assessment_id = ? AND aa.organization_id = ?
                ORDER BY aa.created_at DESC
                """,
                (assessment_id, organization_id),
            ).fetchall()

            return [dict(r) for r in rows]

    def revoke_assignment(
        self,
        organization_id: str,
        user_id: str,
        assignment_id: str,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Revoke a candidate assignment."""
        with get_db_connection(self.db_path) as conn:
            res = conn.execute(
                """
                UPDATE assessment_assignments
                SET status = 'EXPIRED', revoked_at = CURRENT_TIMESTAMP, revoked_by = ?, revoked_reason = ?
                WHERE id = ? AND organization_id = ? AND revoked_at IS NULL AND status != 'COMPLETED'
                """,
                (user_id, reason or "Revoked by recruiter", assignment_id, organization_id),
            )
            if res.rowcount == 0:
                raise ValueError("Assignment not found, unauthorized, or cannot be revoked.")

            return {"assignment_id": assignment_id, "status": "REVOKED"}

    def claim_invitation(
        self,
        raw_token: str,
        candidate_user: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Candidate claims an assignment invitation using raw token.
        Verifies token validity, expiry, and that user email matches intended recipient.
        """
        token_hash = self.hash_token(raw_token)
        user_email = candidate_user["email"].strip().lower()
        user_id = candidate_user["id"]

        with get_db_connection(self.db_path) as conn:
            assignment = conn.execute(
                """
                SELECT aa.*, a.title as assessment_title, a.duration_minutes
                FROM assessment_assignments aa
                JOIN assessments a ON aa.assessment_id = a.id
                WHERE aa.invitation_token_hash = ?
                """,
                (token_hash,),
            ).fetchone()

            if not assignment:
                raise ValueError("Invalid invitation link.")

            if assignment["status"] == "REVOKED" or assignment["revoked_at"]:
                raise ValueError("This invitation has been revoked by the recruiting organization.")

            expires_at = assignment["expires_at"]
            if expires_at and datetime.fromisoformat(expires_at.replace("Z", "+00:00")) < datetime.now(timezone.utc):
                raise ValueError("This invitation has expired.")

            # Email identity check
            intended_email = assignment["candidate_email"].strip().lower()
            if intended_email != user_email:
                raise ValueError(
                    f"Invitation is addressed to '{intended_email}', but you are signed in as '{user_email}'."
                )

            # Bind candidate
            conn.execute(
                """
                UPDATE assessment_assignments
                SET candidate_id = ?, claimed_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (user_id, assignment["id"]),
            )

            return {
                "assignment_id": assignment["id"],
                "assessment_id": assignment["assessment_id"],
                "assessment_title": assignment["assessment_title"],
                "duration_minutes": assignment["duration_minutes"],
                "status": "AVAILABLE",
            }

    def list_candidate_assigned_assessments(
        self,
        candidate_user: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """List assessments assigned to the authenticated candidate."""
        user_id = candidate_user["id"]
        user_email = candidate_user["email"].strip().lower()

        with get_db_connection(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT aa.id as assignment_id, aa.assessment_id, aa.assessment_version_id,
                       aa.expires_at, aa.max_attempts, aa.attempts_used, aa.status as assignment_status,
                       a.title, a.description, a.instructions, a.duration_minutes, a.passing_score_pct,
                       a.result_release_policy, o.name as organization_name,
                       (SELECT id FROM assessment_attempts WHERE assignment_id = aa.id AND status = 'IN_PROGRESS' LIMIT 1) as active_attempt_id,
                       (SELECT status FROM assessment_attempts WHERE assignment_id = aa.id ORDER BY created_at DESC LIMIT 1) as latest_attempt_status,
                       (SELECT percentage_score FROM assessment_attempts WHERE assignment_id = aa.id AND (result_released = 1 OR a.result_release_policy = 'IMMEDIATE') ORDER BY created_at DESC LIMIT 1) as released_score
                FROM assessment_assignments aa
                JOIN assessments a ON aa.assessment_id = a.id
                JOIN organizations o ON aa.organization_id = o.id
                WHERE (aa.candidate_id = ? OR aa.candidate_email = ?)
                  AND aa.status != 'REVOKED'
                ORDER BY aa.created_at DESC
                """,
                (user_id, user_email),
            ).fetchall()

            return [dict(r) for r in rows]
