import json
import uuid
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from src.db.connection import get_db_connection
from src.services.question_generation_service import QuestionGenerationService

logger = logging.getLogger(__name__)

VALID_COMPETENCIES = [
    'CODE_COMPREHENSION',
    'DEPENDENCY_TRACING',
    'ARCHITECTURE_REASONING',
    'DEBUGGING',
    'CHANGE_IMPACT'
]

VALID_FORMATS = ['SINGLE_SELECT', 'MULTI_SELECT', 'TRUE_FALSE', 'TEXT', 'CODE_TASK']
VALID_DIFFICULTIES = ['BEGINNER', 'INTERMEDIATE', 'ADVANCED']
VALID_REVIEW_STATUSES = ['NEEDS_REVIEW', 'APPROVED', 'PUBLISHED', 'ARCHIVED']
VALID_VALIDATION_STATUSES = ['PENDING', 'VALIDATED', 'REJECTED']

class HRQuestionBankService:
    def __init__(self):
        pass

    def get_organization_questions(
        self,
        organization_id: str,
        search: Optional[str] = None,
        skill: Optional[str] = None,
        competency: Optional[str] = None,
        difficulty: Optional[str] = None,
        response_format: Optional[str] = None,
        source_type: Optional[str] = None,
        repository_id: Optional[str] = None,
        validation_status: Optional[str] = None,
        review_status: Optional[str] = None,
        is_archived: bool = False,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """
        Search, filter, and paginate organization questions with server-side queries.
        Ensures strict tenant isolation on organization_id.
        """
        page = max(1, page)
        page_size = min(max(1, page_size), 100)
        offset = (page - 1) * page_size

        allowed_sort_cols = {
            "created_at": "q.created_at",
            "updated_at": "q.updated_at",
            "difficulty": "q.difficulty",
            "competency": "q.competency",
            "review_status": "q.review_status",
            "validation_status": "q.validation_status"
        }
        order_col = allowed_sort_cols.get(sort_by, "q.created_at")
        order_dir = "ASC" if sort_order.lower() == "asc" else "DESC"

        conditions = ["q.organization_id = ?", "q.is_archived = ?"]
        params: List[Any] = [organization_id, 1 if is_archived else 0]

        if search and search.strip():
            term = f"%{search.strip()}%"
            conditions.append("(q.question_text LIKE ? OR q.skill_tags LIKE ? OR q.explanation LIKE ?)")
            params.extend([term, term, term])

        if skill and skill.strip():
            conditions.append("q.skill_tags LIKE ?")
            params.append(f"%{skill.strip()}%")

        if competency and competency in VALID_COMPETENCIES:
            conditions.append("q.competency = ?")
            params.append(competency)

        if difficulty and difficulty in VALID_DIFFICULTIES:
            conditions.append("q.difficulty = ?")
            params.append(difficulty)

        if response_format and response_format in VALID_FORMATS:
            conditions.append("q.response_format = ?")
            params.append(response_format)

        if source_type and source_type in ('SKILL_BASED', 'REPOSITORY_BASED'):
            conditions.append("q.source_type = ?")
            params.append(source_type)

        if repository_id and repository_id.strip():
            conditions.append("q.repository_id = ?")
            params.append(repository_id.strip())

        if validation_status and validation_status in VALID_VALIDATION_STATUSES:
            conditions.append("q.validation_status = ?")
            params.append(validation_status)

        if review_status and review_status in VALID_REVIEW_STATUSES:
            conditions.append("q.review_status = ?")
            params.append(review_status)

        where_clause = " WHERE " + " AND ".join(conditions)

        with get_db_connection() as conn:
            # 1. Total count query
            count_sql = f"SELECT COUNT(*) as total FROM questions q {where_clause}"
            total = conn.execute(count_sql, params).fetchone()["total"]

            # 2. Paginated items query
            data_sql = f"""
                SELECT q.*, u.full_name as author_name, r.display_name as repo_name
                FROM questions q
                LEFT JOIN users u ON u.id = q.created_by
                LEFT JOIN repositories r ON r.id = q.repository_id
                {where_clause}
                ORDER BY {order_col} {order_dir}
                LIMIT ? OFFSET ?
            """
            item_params = list(params) + [page_size, offset]
            rows = conn.execute(data_sql, item_params).fetchall()

            items = []
            for r in rows:
                item = dict(r)
                item["options"] = json.loads(item["options"]) if item.get("options") else []
                item["answer_key"] = json.loads(item["answer_key"]) if item.get("answer_key") else []
                item["skill_tags"] = json.loads(item["skill_tags"]) if item.get("skill_tags") else []
                item["evidence_references"] = json.loads(item["evidence_references"]) if item.get("evidence_references") else []
                items.append(item)

            total_pages = (total + page_size - 1) // page_size if total > 0 else 1

            return {
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages
            }

    def get_question_by_id(self, organization_id: str, question_id: str) -> Dict[str, Any]:
        """Fetch question by ID, verifying organizational ownership."""
        with get_db_connection() as conn:
            row = conn.execute("""
                SELECT q.*, u.full_name as author_name, rev.full_name as reviewer_name,
                       r.display_name as repo_name, r.repo_url
                FROM questions q
                LEFT JOIN users u ON u.id = q.created_by
                LEFT JOIN users rev ON rev.id = q.reviewed_by
                LEFT JOIN repositories r ON r.id = q.repository_id
                WHERE q.id = ? AND q.organization_id = ?
            """, (question_id, organization_id)).fetchone()

            if not row:
                raise ValueError("Question not found or access denied for this organization.")

            item = dict(row)
            item["options"] = json.loads(item["options"]) if item.get("options") else []
            item["answer_key"] = json.loads(item["answer_key"]) if item.get("answer_key") else []
            item["skill_tags"] = json.loads(item["skill_tags"]) if item.get("skill_tags") else []
            item["evidence_references"] = json.loads(item["evidence_references"]) if item.get("evidence_references") else []
            return item

    def validate_question_data(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate question fields, option formats, and answer key consistency."""
        text = str(data.get("question_text", "")).strip()
        if not text or len(text) < 15:
            return False, "Question text must be at least 15 characters."

        fmt = str(data.get("response_format", "")).upper()
        if fmt not in VALID_FORMATS:
            return False, f"Invalid response format '{fmt}'."

        comp = str(data.get("competency", "")).upper()
        if comp not in VALID_COMPETENCIES:
            return False, f"Invalid competency '{comp}'."

        diff = str(data.get("difficulty", "")).upper()
        if diff not in VALID_DIFFICULTIES:
            return False, f"Invalid difficulty '{diff}'."

        explanation = str(data.get("explanation", "")).strip()
        if not explanation or len(explanation) < 10:
            return False, "Explanation must be at least 10 characters."

        # Validate options and answer keys for multiple choice / true-false
        if fmt in ('SINGLE_SELECT', 'MULTI_SELECT', 'TRUE_FALSE'):
            options = data.get("options", [])
            if not isinstance(options, list) or len(options) == 0:
                return False, "Options list cannot be empty."

            option_ids = set()
            option_texts = set()
            for opt in options:
                if not isinstance(opt, dict):
                    return False, "Each option must be an object."
                oid = str(opt.get("id") or opt.get("key") or "").strip().upper()
                otext = str(opt.get("text") or "").strip()
                if not oid:
                    return False, "Each option must contain 'id' or 'key'."
                if not otext:
                    return False, "Option text cannot be empty."
                if oid in option_ids:
                    return False, f"Duplicate option key '{oid}'."
                if otext.lower() in option_texts:
                    return False, f"Duplicate option text '{otext}'."
                option_ids.add(oid)
                option_texts.add(otext.lower())

            raw_answers = data.get("answer_key", [])
            if isinstance(raw_answers, str):
                raw_answers = [raw_answers]
            if not isinstance(raw_answers, list) or len(raw_answers) == 0:
                return False, "Answer key cannot be empty."

            answers = [str(a).strip().upper() for a in raw_answers]
            for a in answers:
                if a not in option_ids:
                    return False, f"Answer key choice '{a}' does not match any available option."

            if fmt == 'SINGLE_SELECT':
                if len(options) < 2 or len(options) > 6:
                    return False, f"SINGLE_SELECT requires between 2 and 6 options, found {len(options)}."
                if len(answers) != 1:
                    return False, "SINGLE_SELECT requires exactly one keyed answer."

            elif fmt == 'MULTI_SELECT':
                if len(options) < 3 or len(options) > 6:
                    return False, f"MULTI_SELECT requires between 3 and 6 options, found {len(options)}."
                if len(answers) < 2:
                    return False, "MULTI_SELECT requires at least two keyed answers."

            elif fmt == 'TRUE_FALSE':
                if len(options) != 2:
                    return False, "TRUE_FALSE requires exactly 2 options ('True' / 'False')."
                if len(answers) != 1:
                    return False, "TRUE_FALSE requires exactly one keyed answer."
                valid_tf = {'TRUE', 'FALSE', 'T', 'F', 'A', 'B'}
                if answers[0] not in valid_tf:
                    return False, "TRUE_FALSE answer key must be True or False."

        return True, "Valid"

    def create_question(
        self,
        organization_id: str,
        author_id: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Manually author a question for an organization."""
        is_valid, reason = self.validate_question_data(data)
        if not is_valid:
            raise ValueError(reason)

        q_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        skill_tags = data.get("skill_tags") or ["General"]
        if isinstance(skill_tags, str):
            skill_tags = [skill_tags]

        normalized_options = []
        for opt in data.get("options", []):
            oid = str(opt.get("id") or opt.get("key") or "").strip().upper()
            otext = str(opt.get("text") or "").strip()
            normalized_options.append({"id": oid, "key": oid, "text": otext})
        options_json = json.dumps(normalized_options)

        answer_key = data.get("answer_key", [])
        if isinstance(answer_key, str):
            answer_key = [answer_key]
        answer_key_json = json.dumps([str(a).strip().upper() for a in answer_key])
        evidence_json = json.dumps(data.get("evidence_references", []))

        with get_db_connection() as conn:
            conn.execute("""
                INSERT INTO questions (
                    id, organization_id, created_by, source_type, repository_id,
                    neo4j_repo_id, analysis_version, skill_tags, competency,
                    response_format, difficulty, question_text, options, answer_key,
                    explanation, evidence_references, validation_status, review_status,
                    version, is_archived, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'VALIDATED', 'NEEDS_REVIEW', 1, 0, ?, ?)
            """, (
                q_id,
                organization_id,
                author_id,
                data.get("source_type", "SKILL_BASED"),
                data.get("repository_id"),
                data.get("neo4j_repo_id"),
                data.get("analysis_version"),
                json.dumps(skill_tags),
                data["competency"],
                data["response_format"],
                data["difficulty"],
                data["question_text"],
                options_json,
                answer_key_json,
                data["explanation"],
                evidence_json,
                now,
                now
            ))

            # Create immutable version 1 snapshot
            v_id = str(uuid.uuid4())
            conn.execute("""
                INSERT INTO question_versions (
                    id, question_id, version, organization_id, author_id,
                    source_type, repository_id, neo4j_repo_id, analysis_version,
                    skill_tags, competency, response_format, difficulty,
                    question_text, options, answer_key, explanation,
                    evidence_references, validation_status, review_status, created_at
                )
                VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'VALIDATED', 'NEEDS_REVIEW', ?)
            """, (
                v_id,
                q_id,
                organization_id,
                author_id,
                data.get("source_type", "SKILL_BASED"),
                data.get("repository_id"),
                data.get("neo4j_repo_id"),
                data.get("analysis_version"),
                json.dumps(skill_tags),
                data["competency"],
                data["response_format"],
                data["difficulty"],
                data["question_text"],
                options_json,
                answer_key_json,
                data["explanation"],
                evidence_json,
                now
            ))

            # Audit log
            conn.execute("""
                INSERT INTO audit_logs (id, organization_id, user_id, action, resource_type, resource_id, details, timestamp)
                VALUES (?, ?, ?, 'CREATE_QUESTION', 'QUESTION', ?, 'Created manual question', ?)
            """, (str(uuid.uuid4()), organization_id, author_id, q_id, now))

        return self.get_question_by_id(organization_id, q_id)

    def update_question(
        self,
        organization_id: str,
        user_id: str,
        question_id: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update an existing question.
        If question was APPROVED or PUBLISHED, editing increments version and resets review status.
        """
        existing = self.get_question_by_id(organization_id, question_id)
        merged_data = dict(existing)
        for k, v in data.items():
            if v is not None:
                merged_data[k] = v

        is_valid, reason = self.validate_question_data(merged_data)
        if not is_valid:
            raise ValueError(reason)

        was_published = existing["review_status"] in ("PUBLISHED", "APPROVED")
        new_version = existing["version"] + 1 if was_published else existing["version"]
        new_review_status = "NEEDS_REVIEW" if was_published else existing["review_status"]
        now = datetime.utcnow().isoformat()

        skill_tags = merged_data.get("skill_tags", existing["skill_tags"])

        raw_options = data.get("options")
        if raw_options is not None:
            normalized_options = []
            for opt in raw_options:
                oid = str(opt.get("id") or opt.get("key") or "").strip().upper()
                otext = str(opt.get("text") or "").strip()
                normalized_options.append({"id": oid, "key": oid, "text": otext})
            options_json = json.dumps(normalized_options)
        else:
            options_json = json.dumps(existing.get("options", []))

        raw_answer_key = data.get("answer_key")
        if raw_answer_key is not None:
            if isinstance(raw_answer_key, str):
                raw_answer_key = [raw_answer_key]
            answer_key_json = json.dumps([str(a).strip().upper() for a in raw_answer_key])
        else:
            answer_key_json = json.dumps(existing.get("answer_key", []))

        evidence_json = json.dumps(data.get("evidence_references", existing["evidence_references"]))

        with get_db_connection() as conn:
            conn.execute("""
                UPDATE questions
                SET question_text = ?,
                    response_format = ?,
                    competency = ?,
                    difficulty = ?,
                    skill_tags = ?,
                    options = ?,
                    answer_key = ?,
                    explanation = ?,
                    evidence_references = ?,
                    version = ?,
                    review_status = ?,
                    validation_status = 'VALIDATED',
                    updated_at = ?
                WHERE id = ? AND organization_id = ?
            """, (
                merged_data["question_text"],
                merged_data["response_format"],
                merged_data["competency"],
                merged_data["difficulty"],
                json.dumps(skill_tags),
                options_json,
                answer_key_json,
                merged_data["explanation"],
                evidence_json,
                new_version,
                new_review_status,
                now,
                question_id,
                organization_id
            ))

            # Record question version
            v_id = str(uuid.uuid4())
            conn.execute("""
                INSERT INTO question_versions (
                    id, question_id, version, organization_id, author_id,
                    source_type, repository_id, neo4j_repo_id, analysis_version,
                    skill_tags, competency, response_format, difficulty,
                    question_text, options, answer_key, explanation,
                    evidence_references, validation_status, review_status, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'VALIDATED', ?, ?)
                ON CONFLICT(question_id, version) DO UPDATE SET
                    question_text = excluded.question_text,
                    options = excluded.options,
                    answer_key = excluded.answer_key,
                    explanation = excluded.explanation,
                    evidence_references = excluded.evidence_references,
                    skill_tags = excluded.skill_tags,
                    competency = excluded.competency,
                    response_format = excluded.response_format,
                    difficulty = excluded.difficulty,
                    validation_status = excluded.validation_status,
                    review_status = excluded.review_status
            """, (
                v_id,
                question_id,
                new_version,
                organization_id,
                user_id,
                existing["source_type"],
                existing.get("repository_id"),
                existing.get("neo4j_repo_id"),
                existing.get("analysis_version"),
                json.dumps(skill_tags),
                merged_data["competency"],
                merged_data["response_format"],
                merged_data["difficulty"],
                merged_data["question_text"],
                options_json,
                answer_key_json,
                merged_data["explanation"],
                evidence_json,
                new_review_status,
                now
            ))

            # Audit log
            conn.execute("""
                INSERT INTO audit_logs (id, organization_id, user_id, action, resource_type, resource_id, details, timestamp)
                VALUES (?, ?, ?, 'UPDATE_QUESTION', 'QUESTION', ?, ?, ?)
            """, (str(uuid.uuid4()), organization_id, user_id, question_id, f"Updated question to version {new_version}", now))

        return self.get_question_by_id(organization_id, question_id)

    def transition_question_status(
        self,
        organization_id: str,
        reviewer_id: str,
        question_id: str,
        action: str,
        reviewer_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transition review and publication lifecycle:
        - SUBMIT_REVIEW: Draft -> NEEDS_REVIEW
        - APPROVE: NEEDS_REVIEW -> APPROVED (requires VALIDATED)
        - REJECT: NEEDS_REVIEW -> REJECTED (sets validation_status = 'REJECTED')
        - PUBLISH: APPROVED -> PUBLISHED
        - ARCHIVE: any -> ARCHIVED
        - RESTORE: ARCHIVED -> NEEDS_REVIEW
        """
        question = self.get_question_by_id(organization_id, question_id)
        current_review = question["review_status"]
        current_validation = question["validation_status"]
        now = datetime.utcnow().isoformat()

        action_upper = action.strip().upper()
        target_review = current_review
        target_validation = current_validation
        is_archived = question.get("is_archived", 0)

        if action_upper == "SUBMIT_REVIEW":
            target_review = "NEEDS_REVIEW"

        elif action_upper == "APPROVE":
            if current_validation == "REJECTED":
                raise ValueError("Cannot approve a question in REJECTED validation status.")
            target_review = "APPROVED"
            target_validation = "VALIDATED"

        elif action_upper == "REJECT":
            target_review = "NEEDS_REVIEW"
            target_validation = "REJECTED"

        elif action_upper == "PUBLISH":
            if current_review not in ("APPROVED", "PUBLISHED"):
                raise ValueError("Only APPROVED questions can be published.")
            target_review = "PUBLISHED"

        elif action_upper == "ARCHIVE":
            target_review = "ARCHIVED"
            is_archived = 1

        elif action_upper == "RESTORE":
            target_review = "NEEDS_REVIEW"
            is_archived = 0

        else:
            raise ValueError(f"Unknown lifecycle transition action '{action}'.")

        with get_db_connection() as conn:
            conn.execute("""
                UPDATE questions
                SET review_status = ?,
                    validation_status = ?,
                    is_archived = ?,
                    reviewed_by = ?,
                    reviewed_at = ?,
                    reviewer_notes = ?,
                    updated_at = ?
                WHERE id = ? AND organization_id = ?
            """, (
                target_review,
                target_validation,
                is_archived,
                reviewer_id,
                now,
                reviewer_notes or question.get("reviewer_notes"),
                now,
                question_id,
                organization_id
            ))

            # Record version snapshot with updated status
            v_id = str(uuid.uuid4())
            conn.execute("""
                INSERT INTO question_versions (
                    id, question_id, version, organization_id, author_id, reviewed_by,
                    source_type, repository_id, neo4j_repo_id, analysis_version,
                    skill_tags, competency, response_format, difficulty,
                    question_text, options, answer_key, explanation,
                    evidence_references, validation_status, review_status, reviewer_notes, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(question_id, version) DO UPDATE SET
                    review_status = excluded.review_status,
                    validation_status = excluded.validation_status,
                    reviewed_by = excluded.reviewed_by,
                    reviewer_notes = excluded.reviewer_notes
            """, (
                v_id,
                question_id,
                question["version"],
                organization_id,
                question.get("created_by"),
                reviewer_id,
                question["source_type"],
                question.get("repository_id"),
                question.get("neo4j_repo_id"),
                question.get("analysis_version"),
                json.dumps(question["skill_tags"]),
                question["competency"],
                question["response_format"],
                question["difficulty"],
                question["question_text"],
                json.dumps(question["options"]),
                json.dumps(question["answer_key"]),
                question["explanation"],
                json.dumps(question["evidence_references"]),
                target_validation,
                target_review,
                reviewer_notes,
                now
            ))

            # Audit log
            conn.execute("""
                INSERT INTO audit_logs (id, organization_id, user_id, action, resource_type, resource_id, details, timestamp)
                VALUES (?, ?, ?, ?, 'QUESTION', ?, ?, ?)
            """, (
                str(uuid.uuid4()),
                organization_id,
                reviewer_id,
                f"QUESTION_{action_upper}",
                question_id,
                f"Transitioned to {target_review} ({reviewer_notes or 'No notes'})",
                now
            ))

        return self.get_question_by_id(organization_id, question_id)

    def get_question_versions(self, organization_id: str, question_id: str) -> List[Dict[str, Any]]:
        """Retrieve complete immutable revision history for a question."""
        # Ensure org ownership
        self.get_question_by_id(organization_id, question_id)

        with get_db_connection() as conn:
            rows = conn.execute("""
                SELECT qv.*, u.full_name as author_name, rev.full_name as reviewer_name
                FROM question_versions qv
                LEFT JOIN users u ON u.id = qv.author_id
                LEFT JOIN users rev ON rev.id = qv.reviewed_by
                WHERE qv.question_id = ? AND qv.organization_id = ?
                ORDER BY qv.version DESC
            """, (question_id, organization_id)).fetchall()

            history = []
            for r in rows:
                item = dict(r)
                item["options"] = json.loads(item["options"]) if item.get("options") else []
                item["answer_key"] = json.loads(item["answer_key"]) if item.get("answer_key") else []
                item["skill_tags"] = json.loads(item["skill_tags"]) if item.get("skill_tags") else []
                item["evidence_references"] = json.loads(item["evidence_references"]) if item.get("evidence_references") else []
                history.append(item)
            return history

    def preview_question_candidate_mode(self, organization_id: str, question_id: str) -> Dict[str, Any]:
        """Candidate-style preview redacting answer keys and reviewer metadata."""
        question = self.get_question_by_id(organization_id, question_id)
        return QuestionGenerationService.serialize_for_candidate(question)
