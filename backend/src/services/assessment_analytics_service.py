import csv
import io
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from src.db.connection import get_db_connection

logger = logging.getLogger(__name__)

class AssessmentAnalyticsService:
    """
    Manages HR assessment reporting, candidate scorecards, manual score overrides,
    result release transitions, and sanitized CSV exports.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    @staticmethod
    def sanitize_csv_field(val: Any) -> str:
        """Protect against CSV formula injection by quoting dangerous leading characters."""
        if val is None:
            return ""
        s = str(val).strip()
        if s.startswith(("=", "+", "-", "@")):
            return f"'{s}"
        return s

    def list_assessment_attempts(
        self,
        organization_id: str,
        assessment_id: str,
    ) -> List[Dict[str, Any]]:
        """List all candidate attempts for an assessment belonging to the organization."""
        with get_db_connection(self.db_path) as conn:
            # Verify org ownership of assessment
            a_check = conn.execute(
                "SELECT id FROM assessments WHERE id = ? AND organization_id = ?",
                (assessment_id, organization_id),
            ).fetchone()
            if not a_check:
                raise ValueError("Assessment not found or unauthorized.")

            rows = conn.execute(
                """
                SELECT att.*, u.full_name as candidate_name, u.email as user_email
                FROM assessment_attempts att
                LEFT JOIN users u ON att.user_id = u.id
                WHERE att.assessment_id = ? AND att.organization_id = ?
                ORDER BY att.created_at DESC
                """,
                (assessment_id, organization_id),
            ).fetchall()

            results = []
            for r in rows:
                item = dict(r)
                # Compute duration used
                if item["started_at"] and item["submitted_at"]:
                    try:
                        s_dt = datetime.fromisoformat(item["started_at"].replace("Z", "+00:00"))
                        e_dt = datetime.fromisoformat(item["submitted_at"].replace("Z", "+00:00"))
                        item["duration_seconds_used"] = int((e_dt - s_dt).total_seconds())
                    except Exception:
                        item["duration_seconds_used"] = None
                else:
                    item["duration_seconds_used"] = None

                # Exclude large snapshot_questions from listing
                item.pop("snapshot_questions", None)
                results.append(item)

            return results

    def get_candidate_scorecard(
        self,
        organization_id: str,
        attempt_id: str,
    ) -> Dict[str, Any]:
        """
        Retrieve full candidate scorecard including question-level details,
        correct answer key, evidence citations, and manual overrides for authorized HR.
        """
        with get_db_connection(self.db_path) as conn:
            attempt_row = conn.execute(
                """
                SELECT att.*, u.full_name as candidate_name, u.email as candidate_user_email,
                       a.title as assessment_title, av.version as assessment_version,
                       av.passing_score_pct, av.result_release_policy,
                       r.display_name as repo_name, r.last_analyzed_commit as repo_commit
                FROM assessment_attempts att
                JOIN assessments a ON att.assessment_id = a.id
                LEFT JOIN assessment_versions av ON att.assessment_version_id = av.id
                LEFT JOIN users u ON att.user_id = u.id
                LEFT JOIN repositories r ON av.repository_id = r.id
                WHERE att.id = ? AND att.organization_id = ?
                """,
                (attempt_id, organization_id),
            ).fetchone()

            if not attempt_row:
                raise ValueError("Assessment attempt not found or access denied.")

            attempt = dict(attempt_row)

            # Parse questions snapshot and answers
            questions = json.loads(attempt["snapshot_questions"])
            ans_rows = conn.execute(
                "SELECT * FROM attempt_answers WHERE attempt_id = ?",
                (attempt_id,),
            ).fetchall()
            answers_map = {row["question_id"]: dict(row) for row in ans_rows}

            question_details = []
            for q in questions:
                qid = q.get("id") or q.get("question_id")
                ans = answers_map.get(qid, {})

                cand_resp = None
                if ans.get("candidate_response"):
                    try:
                        cand_resp = json.loads(ans["candidate_response"])
                    except Exception:
                        cand_resp = ans["candidate_response"]

                opts = q.get("options", [])
                if isinstance(opts, str):
                    try:
                        opts = json.loads(opts)
                    except Exception:
                        pass

                ak = q.get("answer_key", {})
                if isinstance(ak, str):
                    try:
                        ak = json.loads(ak)
                    except Exception:
                        pass

                question_details.append({
                    "question_id": qid,
                    "question_text": q.get("question_text"),
                    "options": opts,
                    "competency": q.get("competency"),
                    "response_format": q.get("response_format"),
                    "difficulty": q.get("difficulty"),
                    "points": float(q.get("points", 1.0)),
                    "candidate_response": cand_resp,
                    "answer_key": ak,
                    "explanation": q.get("explanation"),
                    "evidence_references": q.get("evidence_references"),
                    "is_correct": ans.get("is_correct", 0),
                    "awarded_points": ans.get("partial_score", 0.0),
                    "feedback": ans.get("feedback"),
                })

            attempt["questions"] = question_details
            attempt.pop("snapshot_questions", None)

            if attempt.get("skill_breakdown"):
                try:
                    attempt["skill_breakdown"] = json.loads(attempt["skill_breakdown"])
                except Exception:
                    pass
            if attempt.get("competency_breakdown"):
                try:
                    attempt["competency_breakdown"] = json.loads(attempt["competency_breakdown"])
                except Exception:
                    pass
            if attempt.get("difficulty_breakdown"):
                try:
                    attempt["difficulty_breakdown"] = json.loads(attempt["difficulty_breakdown"])
                except Exception:
                    pass

            return attempt

    def manual_score_override(
        self,
        organization_id: str,
        user_id: str,
        attempt_id: str,
        new_score: float,
        reason: str,
    ) -> Dict[str, Any]:
        """
        Authorized HR manual score override with audit trail.
        """
        if not reason or len(reason.strip()) < 5:
            raise ValueError("A clear reason (at least 5 characters) is required for manual score overrides.")

        with get_db_connection(self.db_path) as conn:
            attempt = conn.execute(
                """
                SELECT att.*, av.passing_score_pct
                FROM assessment_attempts att
                LEFT JOIN assessment_versions av ON att.assessment_version_id = av.id
                WHERE att.id = ? AND att.organization_id = ?
                """,
                (attempt_id, organization_id),
            ).fetchone()

            if not attempt:
                raise ValueError("Attempt not found or unauthorized.")

            max_score = attempt["max_possible_score"] or 1.0
            if new_score < 0.0 or new_score > max_score:
                raise ValueError(f"Overridden score must be between 0.0 and {max_score}.")

            new_pct = round((new_score / max_score * 100), 2)
            passing_thresh = attempt["passing_score_pct"] if attempt["passing_score_pct"] is not None else 70.0
            passed = 1 if new_pct >= passing_thresh else 0
            now = datetime.now(timezone.utc)

            conn.execute(
                """
                UPDATE assessment_attempts
                SET total_score = ?, percentage_score = ?, passed = ?,
                    manual_override_score = ?, manual_override_by = ?,
                    manual_override_reason = ?, manual_override_at = ?
                WHERE id = ?
                """,
                (new_score, new_pct, passed, new_score, user_id, reason.strip(), now.isoformat(), attempt_id),
            )

            # Record event
            conn.execute(
                """
                INSERT INTO attempt_events (id, attempt_id, event_type, event_payload)
                VALUES (?, ?, 'SCORE_OVERRIDE', ?)
                """,
                (
                    str(uuid.uuid4()),
                    attempt_id,
                    json.dumps({
                        "original_score": attempt["total_score"],
                        "new_score": new_score,
                        "reason": reason,
                        "override_by": user_id,
                    }),
                ),
            )

            return self.get_candidate_scorecard(organization_id, attempt_id)

    def release_attempt_result(
        self,
        organization_id: str,
        user_id: str,
        attempt_id: str,
    ) -> Dict[str, Any]:
        """Release assessment result to the candidate."""
        now = datetime.now(timezone.utc)
        with get_db_connection(self.db_path) as conn:
            res = conn.execute(
                """
                UPDATE assessment_attempts
                SET result_released = 1, result_released_at = ?, result_released_by = ?
                WHERE id = ? AND organization_id = ?
                """,
                (now.isoformat(), user_id, attempt_id, organization_id),
            )
            if res.rowcount == 0:
                raise ValueError("Attempt not found or unauthorized.")

            return {"attempt_id": attempt_id, "result_released": True, "released_at": now.isoformat()}

    def export_results_csv(
        self,
        organization_id: str,
        assessment_id: str,
    ) -> str:
        """
        Generate CSV export of candidate results with formula injection sanitization.
        """
        attempts = self.list_assessment_attempts(organization_id, assessment_id)

        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            "Candidate Email",
            "Candidate Name",
            "Status",
            "Total Score",
            "Max Possible Score",
            "Percentage Score",
            "Result",
            "Result Released",
            "Started At",
            "Submitted At",
            "Duration (Seconds)",
        ])

        for a in attempts:
            writer.writerow([
                self.sanitize_csv_field(a.get("candidate_email") or a.get("user_email")),
                self.sanitize_csv_field(a.get("candidate_name") or "Candidate"),
                self.sanitize_csv_field(a.get("status")),
                self.sanitize_csv_field(a.get("total_score")),
                self.sanitize_csv_field(a.get("max_possible_score")),
                self.sanitize_csv_field(a.get("percentage_score")),
                "PASS" if a.get("passed") == 1 else "FAIL",
                "YES" if a.get("result_released") == 1 else "NO",
                self.sanitize_csv_field(a.get("started_at")),
                self.sanitize_csv_field(a.get("submitted_at")),
                self.sanitize_csv_field(a.get("duration_seconds_used")),
            ])

        return output.getvalue()
