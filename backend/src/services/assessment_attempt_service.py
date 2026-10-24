import json
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from src.db.connection import get_db_connection

logger = logging.getLogger(__name__)

class AssessmentAttemptService:
    """
    Manages timed candidate assessment attempts, server-authoritative deadlines,
    autosave durability, and objective evaluation.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    def start_attempt(
        self,
        candidate_user: Dict[str, Any],
        assignment_id: str,
    ) -> Dict[str, Any]:
        """
        Start an assessment attempt.
        Validates assignment eligibility, calculates server deadline, and creates an immutable attempt.
        If an attempt is already IN_PROGRESS, resumes it idempotently.
        """
        user_id = candidate_user["id"]
        user_email = candidate_user["email"].strip().lower()
        now = datetime.now(timezone.utc)

        with get_db_connection(self.db_path) as conn:
            # 1. Fetch and validate assignment
            assignment = conn.execute(
                """
                SELECT aa.*, a.status as assessment_status, a.duration_minutes, a.passing_score_pct,
                       a.result_release_policy, a.repository_id, a.availability_start, a.availability_end,
                       a.published_version_id
                FROM assessment_assignments aa
                JOIN assessments a ON aa.assessment_id = a.id
                WHERE aa.id = ?
                """,
                (assignment_id,),
            ).fetchone()

            if not assignment:
                raise ValueError("Assignment not found.")

            # Verify candidate ownership
            if assignment["candidate_id"] and assignment["candidate_id"] != user_id:
                raise ValueError("Unauthorized. This assignment belongs to another candidate.")
            if not assignment["candidate_id"] and assignment["candidate_email"].strip().lower() != user_email:
                raise ValueError("Unauthorized. Email does not match assignment invitation.")

            if assignment["status"] == "REVOKED" or assignment["revoked_at"] is not None:
                raise ValueError("This assessment assignment has been revoked by the recruiting organization.")

            expires_at = assignment["expires_at"]
            if expires_at and datetime.fromisoformat(expires_at.replace("Z", "+00:00")) < now:
                raise ValueError("This assessment invitation has expired.")

            # Availability window checks
            if assignment["availability_start"]:
                start_dt = datetime.fromisoformat(assignment["availability_start"].replace("Z", "+00:00"))
                if now < start_dt:
                    raise ValueError(f"Assessment is not available yet. Starts at {assignment['availability_start']}.")
            if assignment["availability_end"]:
                end_dt = datetime.fromisoformat(assignment["availability_end"].replace("Z", "+00:00"))
                if now > end_dt:
                    raise ValueError(f"Assessment window closed at {assignment['availability_end']}.")

            # Check attempt limit
            max_attempts = assignment["max_attempts"] or 1
            attempts_used = assignment["attempts_used"] or 0

            # 2. Check for active IN_PROGRESS attempt
            existing_active = conn.execute(
                """
                SELECT * FROM assessment_attempts
                WHERE assignment_id = ? AND user_id = ? AND status = 'IN_PROGRESS'
                ORDER BY created_at DESC LIMIT 1
                """,
                (assignment_id, user_id),
            ).fetchone()

            if existing_active:
                deadline_dt = datetime.fromisoformat(existing_active["deadline_at"].replace("Z", "+00:00"))
                if now <= deadline_dt:
                    # Resume existing active attempt safely
                    return self._build_candidate_attempt_view(conn, dict(existing_active), now)
                else:
                    # Deadline passed while inactive: auto-submit and grade
                    logger.info(f"Attempt {existing_active['id']} expired. Finalizing.")
                    self._finalize_and_grade_attempt(conn, dict(existing_active))

            # Verify remaining attempts
            if attempts_used >= max_attempts:
                raise ValueError(f"Maximum attempt limit reached ({max_attempts}/{max_attempts}).")

            # 3. Load immutable assessment version and questions snapshot
            version_id = assignment["assessment_version_id"] or assignment["published_version_id"]
            if not version_id:
                raise ValueError("Assessment has no published version available.")

            av_row = conn.execute(
                """
                SELECT id, assessment_id, version, questions_snapshot, duration_minutes,
                       passing_score_pct, result_release_policy, repository_id, neo4j_repo_id,
                       analysis_commit
                FROM assessment_versions
                WHERE id = ?
                """,
                (version_id,),
            ).fetchone()

            if not av_row:
                raise ValueError("Published assessment version snapshot not found.")

            duration_mins = av_row["duration_minutes"] or 60
            deadline_at = (now + timedelta(minutes=duration_mins)).isoformat()
            attempt_id = str(uuid.uuid4())
            questions_snapshot = av_row["questions_snapshot"]

            # Calculate total max possible score from snapshot
            parsed_questions = json.loads(questions_snapshot)
            max_score = sum(float(q.get("points", 1.0)) for q in parsed_questions)

            # 4. Insert new attempt
            conn.execute(
                """
                INSERT INTO assessment_attempts (
                    id, assignment_id, user_id, assessment_id, organization_id, assessment_version_id,
                    candidate_email, started_at, deadline_at, snapshot_questions, max_possible_score,
                    status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'IN_PROGRESS')
                """,
                (
                    attempt_id,
                    assignment_id,
                    user_id,
                    assignment["assessment_id"],
                    assignment["organization_id"],
                    version_id,
                    user_email,
                    now.isoformat(),
                    deadline_at,
                    questions_snapshot,
                    max_score,
                ),
            )

            # Update assignment status
            conn.execute(
                "UPDATE assessment_assignments SET status = 'IN_PROGRESS', candidate_id = ? WHERE id = ?",
                (user_id, assignment_id),
            )

            # Record event
            conn.execute(
                """
                INSERT INTO attempt_events (id, attempt_id, event_type, event_payload)
                VALUES (?, ?, 'START', ?)
                """,
                (str(uuid.uuid4()), attempt_id, json.dumps({"started_at": now.isoformat(), "deadline_at": deadline_at})),
            )

            new_attempt = conn.execute("SELECT * FROM assessment_attempts WHERE id = ?", (attempt_id,)).fetchone()
            return self._build_candidate_attempt_view(conn, dict(new_attempt), now)

    def autosave_answer(
        self,
        candidate_user: Dict[str, Any],
        attempt_id: str,
        question_id: str,
        candidate_response: Any,
    ) -> Dict[str, Any]:
        """
        Autosave candidate answer.
        Enforces server-authoritative deadline and validates question belongs to the attempt.
        """
        user_id = candidate_user["id"]
        now = datetime.now(timezone.utc)

        with get_db_connection(self.db_path) as conn:
            attempt = conn.execute(
                "SELECT * FROM assessment_attempts WHERE id = ? AND user_id = ?",
                (attempt_id, user_id),
            ).fetchone()

            if not attempt:
                raise ValueError("Attempt not found or unauthorized.")
            if attempt["status"] != "IN_PROGRESS":
                raise ValueError(f"Attempt is already {attempt['status']} and cannot accept answers.")

            # Check server-authoritative deadline
            deadline_dt = datetime.fromisoformat(attempt["deadline_at"].replace("Z", "+00:00"))
            if now > deadline_dt:
                # Expire and finalize
                self._finalize_and_grade_attempt(conn, dict(attempt))
                raise ValueError("Assessment deadline has expired. Your attempt has been finalized.")

            # Validate question exists in attempt snapshot
            questions = json.loads(attempt["snapshot_questions"])
            matched_q = next((q for q in questions if (q.get("id") or q.get("question_id")) == question_id), None)
            if not matched_q:
                raise ValueError(f"Question {question_id} does not exist in this assessment.")

            # Format response
            response_json = json.dumps(candidate_response)

            # Upsert into attempt_answers
            answer_id = str(uuid.uuid4())
            conn.execute(
                """
                INSERT INTO attempt_answers (id, attempt_id, question_id, candidate_response, selected_options, answered_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(attempt_id, question_id) DO UPDATE SET
                    candidate_response = excluded.candidate_response,
                    selected_options = excluded.selected_options,
                    answered_at = CURRENT_TIMESTAMP
                """,
                (answer_id, attempt_id, question_id, response_json, response_json),
            )

            # Record event
            conn.execute(
                """
                INSERT INTO attempt_events (id, attempt_id, event_type, event_payload)
                VALUES (?, ?, 'AUTOSAVE', ?)
                """,
                (str(uuid.uuid4()), attempt_id, json.dumps({"question_id": question_id, "timestamp": now.isoformat()})),
            )

        return {
            "status": "SAVED",
            "question_id": question_id,
            "saved_at": now.isoformat(),
        }

    def submit_attempt(
        self,
        candidate_user: Dict[str, Any],
        attempt_id: str,
    ) -> Dict[str, Any]:
        """
        Finalize and grade an assessment attempt.
        Calculates objective scores, skill/competency breakdowns, and enforces result release policy.
        """
        user_id = candidate_user["id"]

        with get_db_connection(self.db_path) as conn:
            attempt = conn.execute(
                "SELECT * FROM assessment_attempts WHERE id = ? AND user_id = ?",
                (attempt_id, user_id),
            ).fetchone()

            if not attempt:
                raise ValueError("Attempt not found or unauthorized.")
            if attempt["status"] != "IN_PROGRESS":
                return self.get_attempt_result_for_candidate(candidate_user, attempt_id)

            graded_attempt = self._finalize_and_grade_attempt(conn, dict(attempt))
            return self.get_attempt_result_for_candidate(candidate_user, attempt_id)

    def _finalize_and_grade_attempt(self, conn, attempt: Dict[str, Any]) -> Dict[str, Any]:
        """Internal objective grading and status transition for an attempt."""
        attempt_id = attempt["id"]
        assignment_id = attempt["assignment_id"]
        now = datetime.now(timezone.utc)

        questions = json.loads(attempt["snapshot_questions"])
        saved_answers_rows = conn.execute(
            "SELECT question_id, candidate_response, selected_options FROM attempt_answers WHERE attempt_id = ?",
            (attempt_id,),
        ).fetchall()
        answers_map = {row["question_id"]: row for row in saved_answers_rows}

        total_awarded = 0.0
        total_possible = 0.0

        skill_scores: Dict[str, Dict[str, float]] = {}
        comp_scores: Dict[str, Dict[str, float]] = {}
        diff_scores: Dict[str, Dict[str, float]] = {}

        for q in questions:
            qid = q.get("id") or q.get("question_id")
            fmt = q.get("response_format", "SINGLE_SELECT").upper()
            max_points = float(q.get("points", 1.0))
            total_possible += max_points

            # Parse candidate response
            ans_record = answers_map.get(qid)
            cand_resp = None
            if ans_record and ans_record["candidate_response"]:
                try:
                    cand_resp = json.loads(ans_record["candidate_response"])
                except Exception:
                    cand_resp = ans_record["candidate_response"]

            # Parse answer key safely across formats:
            # Format 1: dict {"correct_option": "A"} or {"correct_options": ["A", "B"]} or {"correct_value": "True"}
            # Format 2: list ["A"] or ["A", "B"] or ["True"]
            # Format 3: scalar string/number
            ak = q.get("answer_key", {})
            if isinstance(ak, str):
                try:
                    ak = json.loads(ak)
                except Exception:
                    pass

            awarded = 0.0
            is_correct = 0
            feedback = ""

            if fmt in ("SINGLE_SELECT", "TRUE_FALSE"):
                if isinstance(ak, dict):
                    correct_key = ak.get("correct_option") or ak.get("correct_value")
                elif isinstance(ak, list) and ak:
                    correct_key = ak[0]
                else:
                    correct_key = ak

                # Normalize candidate selection (can be string "A" or list ["A"])
                selected_val = cand_resp[0] if isinstance(cand_resp, list) and cand_resp else cand_resp
                if selected_val is not None and correct_key is not None and str(selected_val).strip().upper() == str(correct_key).strip().upper():
                    awarded = max_points
                    is_correct = 1
                    feedback = "Correct"
                else:
                    feedback = "Incorrect"

            elif fmt == "MULTI_SELECT":
                if isinstance(ak, dict):
                    correct_keys = [str(k).upper() for k in ak.get("correct_options", [])]
                elif isinstance(ak, list):
                    correct_keys = [str(k).upper() for k in ak]
                else:
                    correct_keys = [str(ak).upper()] if ak else []

                selected_keys = [str(k).upper() for k in (cand_resp if isinstance(cand_resp, list) else [cand_resp])] if cand_resp else []

                if correct_keys:
                    points_per_correct = max_points / len(correct_keys)
                    options_count = len(q.get("options", [])) or 4
                    penalty_per_wrong = max_points / options_count

                    correct_selected = sum(1 for k in selected_keys if k in correct_keys)
                    incorrect_selected = sum(1 for k in selected_keys if k not in correct_keys)

                    raw_score = (correct_selected * points_per_correct) - (incorrect_selected * penalty_per_wrong)
                    awarded = max(0.0, min(max_points, round(raw_score, 2)))
                    is_correct = 1 if awarded == max_points else (2 if awarded > 0 else 0)
                    feedback = f"Partial credit: {awarded}/{max_points}" if awarded > 0 and awarded < max_points else ("Correct" if is_correct == 1 else "Incorrect")

            total_awarded += awarded

            # Upsert detailed grading into attempt_answers
            conn.execute(
                """
                INSERT INTO attempt_answers (id, attempt_id, question_id, is_correct, partial_score, max_score, feedback)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(attempt_id, question_id) DO UPDATE SET
                    is_correct = excluded.is_correct,
                    partial_score = excluded.partial_score,
                    max_score = excluded.max_score,
                    feedback = excluded.feedback
                """,
                (str(uuid.uuid4()), attempt_id, qid, is_correct, awarded, max_points, feedback),
            )

            # Skill tracking
            q_tags = q.get("skill_tags", [])
            if isinstance(q_tags, str):
                try:
                    q_tags = json.loads(q_tags)
                except Exception:
                    q_tags = [q_tags]
            for tag in q_tags:
                tag_name = tag.capitalize()
                if tag_name not in skill_scores:
                    skill_scores[tag_name] = {"earned": 0.0, "total": 0.0}
                skill_scores[tag_name]["earned"] += awarded
                skill_scores[tag_name]["total"] += max_points

            # Competency tracking
            comp = q.get("competency", "GENERAL")
            if comp not in comp_scores:
                comp_scores[comp] = {"earned": 0.0, "total": 0.0}
            comp_scores[comp]["earned"] += awarded
            comp_scores[comp]["total"] += max_points

            # Difficulty tracking
            diff = q.get("difficulty", "INTERMEDIATE")
            if diff not in diff_scores:
                diff_scores[diff] = {"earned": 0.0, "total": 0.0}
            diff_scores[diff]["earned"] += awarded
            diff_scores[diff]["total"] += max_points

        # Calculate final percentage & pass/fail
        pct = (total_awarded / total_possible * 100) if total_possible > 0 else 0.0
        pct = round(pct, 2)

        # Get passing threshold
        av_row = conn.execute(
            "SELECT passing_score_pct FROM assessment_versions WHERE id = ?",
            (attempt["assessment_version_id"],),
        ).fetchone()
        passing_threshold = av_row["passing_score_pct"] if av_row else 70.0
        passed = 1 if pct >= passing_threshold else 0

        # Update attempt
        conn.execute(
            """
            UPDATE assessment_attempts
            SET status = 'GRADED', submitted_at = ?, total_score = ?, max_possible_score = ?,
                percentage_score = ?, passed = ?, skill_breakdown = ?, competency_breakdown = ?,
                difficulty_breakdown = ?
            WHERE id = ?
            """,
            (
                now.isoformat(),
                total_awarded,
                total_possible,
                pct,
                passed,
                json.dumps(skill_scores),
                json.dumps(comp_scores),
                json.dumps(diff_scores),
                attempt_id,
            ),
        )

        # Update assignment
        conn.execute(
            """
            UPDATE assessment_assignments
            SET attempts_used = attempts_used + 1, status = 'COMPLETED'
            WHERE id = ?
            """,
            (assignment_id,),
        )

        # Event log
        conn.execute(
            """
            INSERT INTO attempt_events (id, attempt_id, event_type, event_payload)
            VALUES (?, ?, 'SUBMIT', ?)
            """,
            (str(uuid.uuid4()), attempt_id, json.dumps({"score": total_awarded, "max": total_possible, "pct": pct})),
        )

        return conn.execute("SELECT * FROM assessment_attempts WHERE id = ?", (attempt_id,)).fetchone()

    def _build_candidate_attempt_view(
        self,
        conn,
        attempt: Dict[str, Any],
        now: datetime,
    ) -> Dict[str, Any]:
        """
        Builds the candidate assessment workspace view.
        CRITICAL: Completely redacts answer_key, explanation, and reviewer notes!
        """
        deadline_dt = datetime.fromisoformat(attempt["deadline_at"].replace("Z", "+00:00"))
        remaining_seconds = max(0, int((deadline_dt - now).total_seconds()))

        # Parse questions snapshot and redact
        questions = json.loads(attempt["snapshot_questions"])
        candidate_questions = []
        for q in questions:
            # Parse options if string
            opts = q.get("options", [])
            if isinstance(opts, str):
                try:
                    opts = json.loads(opts)
                except Exception:
                    pass

            q_view = {
                "id": q.get("id") or q.get("question_id"),
                "question_text": q.get("question_text"),
                "options": opts,
                "response_format": q.get("response_format"),
                "competency": q.get("competency"),
                "difficulty": q.get("difficulty"),
                "points": q.get("points", 1.0),
                "evidence_references": q.get("evidence_references"),
            }
            # Strictly do NOT include answer_key, explanation, reviewer_notes!
            candidate_questions.append(q_view)

        # Load existing answers
        saved_rows = conn.execute(
            "SELECT question_id, candidate_response FROM attempt_answers WHERE attempt_id = ?",
            (attempt["id"],),
        ).fetchall()
        saved_answers = {}
        for r in saved_rows:
            try:
                saved_answers[r["question_id"]] = json.loads(r["candidate_response"])
            except Exception:
                saved_answers[r["question_id"]] = r["candidate_response"]

        # Load assessment & repository metadata
        av_row = conn.execute(
            """
            SELECT av.title, av.instructions, av.repository_id, av.neo4j_repo_id, av.analysis_commit,
                   r.display_name as repo_name, r.repo_url
            FROM assessment_versions av
            LEFT JOIN repositories r ON av.repository_id = r.id
            WHERE av.id = ?
            """,
            (attempt["assessment_version_id"],),
        ).fetchone()

        repo_info = None
        if av_row and av_row["repository_id"]:
            repo_info = {
                "repository_id": av_row["repository_id"],
                "neo4j_repo_id": av_row["neo4j_repo_id"],
                "commit_sha": av_row["analysis_commit"],
                "display_name": av_row["repo_name"],
            }

        return {
            "attempt_id": attempt["id"],
            "assessment_id": attempt["assessment_id"],
            "title": av_row["title"] if av_row else "Technical Assessment",
            "instructions": av_row["instructions"] if av_row else None,
            "started_at": attempt["started_at"],
            "deadline_at": attempt["deadline_at"],
            "remaining_seconds": remaining_seconds,
            "status": attempt["status"],
            "questions": candidate_questions,
            "saved_answers": saved_answers,
            "repository": repo_info,
        }

    def get_attempt_result_for_candidate(
        self,
        candidate_user: Dict[str, Any],
        attempt_id: str,
    ) -> Dict[str, Any]:
        """
        Retrieve assessment result for candidate respecting result_release_policy.
        """
        user_id = candidate_user["id"]

        with get_db_connection(self.db_path) as conn:
            attempt = conn.execute(
                """
                SELECT a.*, av.result_release_policy, av.title as assessment_title
                FROM assessment_attempts a
                JOIN assessment_versions av ON a.assessment_version_id = av.id
                WHERE a.id = ? AND a.user_id = ?
                """,
                (attempt_id, user_id),
            ).fetchone()

            if not attempt:
                raise ValueError("Attempt not found or unauthorized.")

            status = attempt["status"]
            policy = attempt["result_release_policy"]
            is_released = bool(attempt["result_released"]) or (policy == "IMMEDIATE")

            if not is_released and policy == "WITHHOLD_PENDING_REVIEW":
                return {
                    "attempt_id": attempt_id,
                    "assessment_title": attempt["assessment_title"],
                    "status": status,
                    "result_released": False,
                    "message": "Your assessment has been submitted successfully and is pending recruiter review. You will be notified once results are released.",
                }

            # Released or score-only policy
            response: Dict[str, Any] = {
                "attempt_id": attempt_id,
                "assessment_title": attempt["assessment_title"],
                "status": status,
                "result_released": True,
                "total_score": attempt["total_score"],
                "max_possible_score": attempt["max_possible_score"],
                "percentage_score": attempt["percentage_score"],
                "passed": bool(attempt["passed"]),
                "submitted_at": attempt["submitted_at"],
            }

            if attempt["skill_breakdown"]:
                try:
                    response["skill_breakdown"] = json.loads(attempt["skill_breakdown"])
                except Exception:
                    pass
            if attempt["competency_breakdown"]:
                try:
                    response["competency_breakdown"] = json.loads(attempt["competency_breakdown"])
                except Exception:
                    pass

            # If full explanations allowed
            if policy == "IMMEDIATE" or (policy == "WITHHOLD_PENDING_REVIEW" and attempt["result_released"]):
                # Provide explanations and question results
                answers = conn.execute(
                    """
                    SELECT question_id, candidate_response, is_correct, partial_score, max_score, feedback
                    FROM attempt_answers
                    WHERE attempt_id = ?
                    """,
                    (attempt_id,),
                ).fetchall()
                response["question_results"] = [dict(a) for a in answers]

            return response
