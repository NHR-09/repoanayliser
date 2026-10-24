import json
import uuid
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from src.db.connection import get_db_connection
from src.services.question_generation_service import QuestionGenerationService

logger = logging.getLogger(__name__)

class PracticeService:
    def __init__(self, generation_service: Optional[QuestionGenerationService] = None):
        self._gen_service = generation_service

    @property
    def gen_service(self) -> QuestionGenerationService:
        if self._gen_service is None:
            self._gen_service = QuestionGenerationService()
        return self._gen_service

    def start_quiz(
        self,
        user_id: str,
        mode: str,
        skill_name: Optional[str] = None,
        repo_id: Optional[str] = None,
        difficulty: str = "INTERMEDIATE",
        competencies: Optional[List[str]] = None,
        question_count: int = 5
    ) -> Dict[str, Any]:
        """
        Configure and start a new practice quiz.
        Returns candidate-safe quiz payload (strictly redacting answer keys).
        """
        # If repository mode, verify access and fetch neo4j_repo_id
        neo4j_repo_id = None
        if mode == "REPOSITORY_BASED":
            if not repo_id:
                raise ValueError("Repository ID is required for repository practice.")
            with get_db_connection() as conn:
                repo_row = conn.execute("SELECT * FROM repositories WHERE id = ?", (repo_id,)).fetchone()
                if not repo_row:
                    raise ValueError("Repository not found.")
                neo4j_repo_id = repo_row["neo4j_repo_id"]

        # Generate and validate questions
        questions, note = self.gen_service.generate_quiz_questions(
            mode=mode,
            skill_name=skill_name,
            repo_id=repo_id,
            difficulty=difficulty,
            competencies=competencies,
            requested_count=question_count
        )

        if not questions:
            raise ValueError("Unable to generate validated questions for the selected configuration. Try general skill practice or re-analyze the repository.")

        quiz_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        comps_json = json.dumps(competencies or ["CODE_COMPREHENSION"])

        with get_db_connection() as conn:
            conn.execute("""
                INSERT INTO practice_quizzes (
                    id, user_id, mode, skill_name, repository_id, neo4j_repo_id,
                    difficulty, competencies, question_count, status,
                    total_score, max_score, percentage_score, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'IN_PROGRESS', 0.0, ?, 0.0, ?)
            """, (
                quiz_id,
                user_id,
                mode,
                skill_name,
                repo_id,
                neo4j_repo_id,
                difficulty,
                comps_json,
                len(questions),
                float(len(questions)),
                now
            ))

            # Link questions to quiz
            for idx, q in enumerate(questions):
                conn.execute("""
                    INSERT INTO practice_quiz_questions (quiz_id, question_id, order_index)
                    VALUES (?, ?, ?)
                """, (quiz_id, q["id"], idx))

        # Return candidate-safe serialization
        safe_questions = [self.gen_service.serialize_for_candidate(q) for q in questions]

        return {
            "quiz_id": quiz_id,
            "mode": mode,
            "skill_name": skill_name,
            "repository_id": repo_id,
            "difficulty": difficulty,
            "question_count": len(safe_questions),
            "status": "IN_PROGRESS",
            "questions": safe_questions,
            "generation_note": note,
            "created_at": now
        }

    def get_quiz_for_candidate(self, user_id: str, quiz_id: str) -> Dict[str, Any]:
        """Fetch active or completed quiz. Redacts answer key if in progress."""
        with get_db_connection() as conn:
            quiz_row = conn.execute(
                "SELECT * FROM practice_quizzes WHERE id = ? AND user_id = ?",
                (quiz_id, user_id)
            ).fetchone()
            if not quiz_row:
                raise ValueError("Practice quiz not found or access denied.")

            quiz = dict(quiz_row)

            # Fetch linked questions
            q_rows = conn.execute("""
                SELECT q.*
                FROM questions q
                JOIN practice_quiz_questions pq ON pq.question_id = q.id
                WHERE pq.quiz_id = ?
                ORDER BY pq.order_index ASC
            """, (quiz_id,)).fetchall()

            questions = [dict(r) for r in q_rows]

            if quiz["status"] == "IN_PROGRESS":
                safe_questions = [self.gen_service.serialize_for_candidate(q) for q in questions]
                quiz["questions"] = safe_questions
            else:
                # Include answers and feedback if completed
                return self.get_quiz_results(user_id, quiz_id)

            return quiz

    def submit_quiz_answers(
        self,
        user_id: str,
        quiz_id: str,
        answers: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """
        Evaluate candidate submissions against protected answer keys using objective scoring.
        Supports precision-sensitive partial credit for multi-select.
        """
        with get_db_connection() as conn:
            quiz_row = conn.execute(
                "SELECT * FROM practice_quizzes WHERE id = ? AND user_id = ?",
                (quiz_id, user_id)
            ).fetchone()

            if not quiz_row:
                raise ValueError("Practice quiz not found or access denied.")

            quiz = dict(quiz_row)
            if quiz["status"] == "COMPLETED":
                # Already submitted - return existing results
                return self.get_quiz_results(user_id, quiz_id)

            q_rows = conn.execute("""
                SELECT q.*
                FROM questions q
                JOIN practice_quiz_questions pq ON pq.question_id = q.id
                WHERE pq.quiz_id = ?
                ORDER BY pq.order_index ASC
            """, (quiz_id,)).fetchall()

            questions = [dict(r) for r in q_rows]

            total_awarded = 0.0
            max_possible = float(len(questions))
            now = datetime.utcnow().isoformat()

            for q in questions:
                q_id = q["id"]
                fmt = q["response_format"]
                raw_ans_key = json.loads(q["answer_key"]) if isinstance(q["answer_key"], str) else q["answer_key"]
                answer_key = [str(a).strip().upper() for a in raw_ans_key]
                options = json.loads(q["options"]) if isinstance(q["options"], str) else q["options"]
                all_option_ids = {str(opt["id"]).strip().upper() for opt in options}

                # Candidate's submitted choice for this question
                raw_sub = answers.get(q_id, [])
                if isinstance(raw_sub, str):
                    raw_sub = [raw_sub]
                selected = [str(s).strip().upper() for s in raw_sub if str(s).strip().upper() in all_option_ids]

                awarded = 0.0
                is_correct = 0

                # Scoring rules
                if fmt in ("SINGLE_SELECT", "TRUE_FALSE"):
                    if selected and selected == answer_key:
                        awarded = 1.0
                        is_correct = 1
                    else:
                        awarded = 0.0
                        is_correct = 0

                elif fmt == "MULTI_SELECT":
                    correct_set = set(answer_key)
                    selected_set = set(selected)
                    incorrect_options = all_option_ids - correct_set

                    true_positives = len(selected_set & correct_set)
                    false_positives = len(selected_set - correct_set)

                    penalty_per_fp = (1.0 / len(incorrect_options)) if incorrect_options else 1.0
                    raw_score = (true_positives / len(correct_set)) - (false_positives * penalty_per_fp)
                    awarded = max(0.0, min(1.0, round(raw_score, 2)))
                    is_correct = 1 if awarded >= 0.99 else 0

                total_awarded += awarded

                # Record answer
                ans_id = str(uuid.uuid4())
                conn.execute("""
                    INSERT INTO practice_answers (
                        id, quiz_id, question_id, user_id, selected_options,
                        is_correct, awarded_points, max_points, explanation, answered_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1.0, ?, ?)
                    ON CONFLICT(quiz_id, question_id) DO UPDATE SET
                        selected_options = excluded.selected_options,
                        is_correct = excluded.is_correct,
                        awarded_points = excluded.awarded_points,
                        explanation = excluded.explanation,
                        answered_at = excluded.answered_at
                """, (
                    ans_id,
                    quiz_id,
                    q_id,
                    user_id,
                    json.dumps(selected),
                    is_correct,
                    awarded,
                    q["explanation"],
                    now
                ))

            # Finalize quiz score
            pct = round((total_awarded / max_possible * 100.0), 1) if max_possible > 0 else 0.0
            conn.execute("""
                UPDATE practice_quizzes
                SET status = 'COMPLETED',
                    total_score = ?,
                    max_score = ?,
                    percentage_score = ?,
                    completed_at = ?
                WHERE id = ?
            """, (total_awarded, max_possible, pct, now, quiz_id))

        return self.get_quiz_results(user_id, quiz_id)

    def get_quiz_results(self, user_id: str, quiz_id: str) -> Dict[str, Any]:
        """Fetch complete graded results, competency breakdowns, and recommendations."""
        with get_db_connection() as conn:
            quiz_row = conn.execute(
                "SELECT * FROM practice_quizzes WHERE id = ? AND user_id = ?",
                (quiz_id, user_id)
            ).fetchone()

            if not quiz_row:
                raise ValueError("Quiz not found.")

            quiz = dict(quiz_row)

            # Fetch questions and candidate answers
            rows = conn.execute("""
                SELECT q.*,
                       a.selected_options, a.is_correct, a.awarded_points, a.answered_at
                FROM questions q
                JOIN practice_quiz_questions pq ON pq.question_id = q.id
                LEFT JOIN practice_answers a ON a.question_id = q.id AND a.quiz_id = pq.quiz_id
                WHERE pq.quiz_id = ?
                ORDER BY pq.order_index ASC
            """, (quiz_id,)).fetchall()

            detailed_questions = []
            competency_stats = {}
            missed_topics = []

            for r in rows:
                item = dict(r)
                item["options"] = json.loads(item["options"]) if isinstance(item["options"], str) else item["options"]
                item["answer_key"] = json.loads(item["answer_key"]) if isinstance(item["answer_key"], str) else item["answer_key"]
                item["skill_tags"] = json.loads(item["skill_tags"]) if isinstance(item["skill_tags"], str) else item["skill_tags"]
                item["evidence_references"] = json.loads(item["evidence_references"]) if isinstance(item["evidence_references"], str) else item["evidence_references"]
                item["selected_options"] = json.loads(item["selected_options"]) if item.get("selected_options") else []

                comp = item["competency"]
                if comp not in competency_stats:
                    competency_stats[comp] = {"awarded": 0.0, "max": 0.0, "count": 0}
                competency_stats[comp]["awarded"] += item.get("awarded_points") or 0.0
                competency_stats[comp]["max"] += 1.0
                competency_stats[comp]["count"] += 1

                if (item.get("awarded_points") or 0.0) < 0.99:
                    missed_topics.append({
                        "competency": comp,
                        "question": item["question_text"],
                        "skills": item["skill_tags"]
                    })

                detailed_questions.append(item)

            # Compute breakdown percentages
            breakdown = {}
            for comp, stats in competency_stats.items():
                pct = round((stats["awarded"] / stats["max"] * 100.0), 1) if stats["max"] > 0 else 0.0
                breakdown[comp] = {
                    "awarded": stats["awarded"],
                    "max": stats["max"],
                    "question_count": stats["count"],
                    "percentage": pct
                }

            # Recommendations
            recommendations = []
            for missed in missed_topics[:4]:
                skill = missed["skills"][0] if missed["skills"] else "General"
                recommendations.append(
                    f"Review {missed['competency'].replace('_', ' ').title()} in {skill} to strengthen conceptual grounding."
                )

            quiz["questions"] = detailed_questions
            quiz["competency_breakdown"] = breakdown
            quiz["recommendations"] = recommendations
            return quiz

    def get_user_practice_history(self, user_id: str) -> Dict[str, Any]:
        """Summary of user's practice sessions, scores, and competency totals."""
        with get_db_connection() as conn:
            quizzes_rows = conn.execute("""
                SELECT q.*, r.display_name as repo_name
                FROM practice_quizzes q
                LEFT JOIN repositories r ON r.id = q.repository_id
                WHERE q.user_id = ?
                ORDER BY q.created_at DESC
            """, (user_id,)).fetchall()

            quizzes = [dict(r) for r in quizzes_rows]

            # Aggregate competency stats across all completed attempts
            comp_rows = conn.execute("""
                SELECT q.competency,
                       COUNT(a.id) as total_answers,
                       SUM(a.awarded_points) as total_awarded,
                       SUM(a.max_points) as total_max
                FROM practice_answers a
                JOIN questions q ON q.id = a.question_id
                JOIN practice_quizzes pq ON pq.id = a.quiz_id
                WHERE a.user_id = ? AND pq.status = 'COMPLETED'
                GROUP BY q.competency
            """, (user_id,)).fetchall()

            competencies = {}
            for r in comp_rows:
                awarded = r["total_awarded"] or 0.0
                max_pts = r["total_max"] or 0.0
                pct = round((awarded / max_pts * 100.0), 1) if max_pts > 0 else 0.0
                competencies[r["competency"]] = {
                    "question_count": r["total_answers"],
                    "awarded_points": awarded,
                    "max_points": max_pts,
                    "accuracy_pct": pct
                }

            total_quizzes = len(quizzes)
            completed_quizzes = [q for q in quizzes if q["status"] == "COMPLETED"]
            avg_score = round(sum(q["percentage_score"] for q in completed_quizzes) / len(completed_quizzes), 1) if completed_quizzes else 0.0
            total_questions = sum(q["question_count"] for q in completed_quizzes)

            return {
                "total_quizzes": total_quizzes,
                "completed_quizzes_count": len(completed_quizzes),
                "total_questions_answered": total_questions,
                "average_score_pct": avg_score,
                "competency_progress": competencies,
                "recent_quizzes": quizzes
            }
