import json
import uuid
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from src.db.connection import get_db_connection
from src.services.question_generation_service import QuestionGenerationService

logger = logging.getLogger(__name__)

class HRQuestionGenerationService:
    def __init__(self, generation_service: Optional[QuestionGenerationService] = None):
        self._gen_service = generation_service

    @property
    def gen_service(self) -> QuestionGenerationService:
        if self._gen_service is None:
            self._gen_service = QuestionGenerationService()
        return self._gen_service

    def generate_questions_for_organization(
        self,
        organization_id: str,
        user_id: str,
        mode: str,
        skill_name: Optional[str] = None,
        repo_id: Optional[str] = None,
        difficulty: str = "INTERMEDIATE",
        competencies: Optional[List[str]] = None,
        requested_count: int = 5,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate questions for an organization using Phase 2 generation & validation pipeline.
        Ensures all generated questions are scoped to organization_id and default to NEEDS_REVIEW.
        """
        if mode == "REPOSITORY_BASED":
            if not repo_id:
                raise ValueError("Repository ID is required for repository question generation.")

            # Validate that repository belongs to or is granted to this organization
            with get_db_connection() as conn:
                repo = conn.execute("""
                    SELECT r.* FROM repositories r
                    LEFT JOIN repository_access_grants g ON g.repository_id = r.id AND g.organization_id = ?
                    WHERE r.id = ? AND (r.organization_id = ? OR g.id IS NOT NULL)
                """, (organization_id, repo_id, organization_id)).fetchone()

                if not repo:
                    raise PermissionError(f"Access denied: repository '{repo_id}' is not authorized for organization '{organization_id}'.")

                if repo["analysis_status"] != "COMPLETED":
                    raise ValueError(f"Repository analysis is {repo['analysis_status'].lower()}. An analyzed repository revision is required.")

        # Call underlying generation & validation engine
        raw_validated_questions, gen_note = self.gen_service.generate_quiz_questions(
            mode=mode,
            skill_name=skill_name,
            repo_id=repo_id,
            difficulty=difficulty,
            competencies=competencies,
            requested_count=requested_count
        )

        saved_org_questions = []
        now = datetime.utcnow().isoformat()

        with get_db_connection() as conn:
            for q in raw_validated_questions:
                q_id = q.get("id")
                if not q_id:
                    q_id = str(uuid.uuid4())
                    q["id"] = q_id

                exists = conn.execute("SELECT id FROM questions WHERE id = ?", (q_id,)).fetchone()
                if exists:
                    conn.execute("""
                        UPDATE questions
                        SET organization_id = ?,
                            created_by = ?,
                            review_status = 'NEEDS_REVIEW',
                            validation_status = 'VALIDATED',
                            reviewer_notes = ?,
                            updated_at = ?
                        WHERE id = ?
                    """, (
                        organization_id,
                        user_id,
                        notes or "Generated via AI assessment engine; pending human HR review",
                        now,
                        q_id
                    ))
                else:
                    opt_json = json.dumps(q.get("options", []))
                    raw_ak = q.get("answer_key", [])
                    if isinstance(raw_ak, str):
                        raw_ak = [raw_ak]
                    ak_json = json.dumps([str(a).strip().upper() for a in raw_ak])
                    ev_json = json.dumps(q.get("evidence_references", []))
                    st_json = json.dumps(q.get("skill_tags", []))
                    conn.execute("""
                        INSERT INTO questions (
                            id, organization_id, created_by, source_type, repository_id,
                            neo4j_repo_id, analysis_version, skill_tags, competency,
                            response_format, difficulty, question_text, options, answer_key,
                            explanation, evidence_references, validation_status, review_status,
                            reviewer_notes, version, is_archived, created_at, updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'VALIDATED', 'NEEDS_REVIEW', ?, 1, 0, ?, ?)
                    """, (
                        q_id,
                        organization_id,
                        user_id,
                        q.get("source_type", "SKILL_BASED"),
                        q.get("repository_id"),
                        q.get("neo4j_repo_id"),
                        q.get("analysis_version"),
                        st_json,
                        q.get("competency", "CODE_COMPREHENSION"),
                        q.get("response_format", "SINGLE_SELECT"),
                        q.get("difficulty", "INTERMEDIATE"),
                        q.get("question_text", ""),
                        opt_json,
                        ak_json,
                        q.get("explanation", ""),
                        ev_json,
                        notes or "Generated via AI assessment engine; pending human HR review",
                        now,
                        now
                    ))

                # Create version 1 snapshot in question_versions
                v_id = str(uuid.uuid4())
                options_json = json.dumps(q.get("options", []))
                answer_key = q.get("answer_key", [])
                if isinstance(answer_key, str):
                    answer_key = [answer_key]
                answer_key_json = json.dumps([str(a).strip().upper() for a in answer_key])
                evidence_json = json.dumps(q.get("evidence_references", []))
                skill_tags_json = json.dumps(q.get("skill_tags", []))

                conn.execute("""
                    INSERT INTO question_versions (
                        id, question_id, version, organization_id, author_id,
                        source_type, repository_id, neo4j_repo_id, analysis_version,
                        skill_tags, competency, response_format, difficulty,
                        question_text, options, answer_key, explanation,
                        evidence_references, validation_status, review_status, reviewer_notes, created_at
                    )
                    VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'VALIDATED', 'NEEDS_REVIEW', ?, ?)
                    ON CONFLICT(question_id, version) DO UPDATE SET
                        organization_id = excluded.organization_id,
                        author_id = excluded.author_id,
                        review_status = 'NEEDS_REVIEW',
                        validation_status = 'VALIDATED'
                """, (
                    v_id,
                    q_id,
                    organization_id,
                    user_id,
                    q.get("source_type", "SKILL_BASED"),
                    q.get("repository_id"),
                    q.get("neo4j_repo_id"),
                    q.get("analysis_version"),
                    skill_tags_json,
                    q["competency"],
                    q["response_format"],
                    q["difficulty"],
                    q["question_text"],
                    options_json,
                    answer_key_json,
                    q["explanation"],
                    evidence_json,
                    notes or "Initial generated draft",
                    now
                ))

                # Fetch updated full item
                row = conn.execute("SELECT * FROM questions WHERE id = ?", (q_id,)).fetchone()
                item = dict(row)
                item["options"] = json.loads(item["options"]) if item.get("options") else []
                item["answer_key"] = json.loads(item["answer_key"]) if item.get("answer_key") else []
                item["skill_tags"] = json.loads(item["skill_tags"]) if item.get("skill_tags") else []
                item["evidence_references"] = json.loads(item["evidence_references"]) if item.get("evidence_references") else []
                saved_org_questions.append(item)

            # Record audit log
            conn.execute("""
                INSERT INTO audit_logs (id, organization_id, user_id, action, resource_type, resource_id, details, timestamp)
                VALUES (?, ?, ?, 'GENERATE_QUESTIONS', 'QUESTION_BANK', ?, ?, ?)
            """, (
                str(uuid.uuid4()),
                organization_id,
                user_id,
                repo_id or "SKILL_MODE",
                f"Generated {len(saved_org_questions)} validated questions in {mode}",
                now
            ))

        return {
            "requested_count": requested_count,
            "generated_count": len(saved_org_questions),
            "questions": saved_org_questions,
            "note": gen_note or f"Successfully produced {len(saved_org_questions)} question drafts for review."
        }
