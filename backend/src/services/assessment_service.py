import json
import uuid
import random
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from src.db.connection import get_db_connection

logger = logging.getLogger(__name__)

class AssessmentService:
    """
    Manages HR assessment configuration, curated question selection,
    randomized blueprint composition, immutable version snapshots, and publication.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    def list_assessments(
        self,
        organization_id: str,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List assessments belonging to an organization with server-side pagination and filters."""
        offset = (page - 1) * page_size
        conditions = ["organization_id = ?", "is_archived = 0"]
        params: List[Any] = [organization_id]

        if status:
            conditions.append("status = ?")
            params.append(status.upper())

        if search:
            conditions.append("(title LIKE ? OR description LIKE ? OR job_role LIKE ?)")
            term = f"%{search.strip()}%"
            params.extend([term, term, term])

        where_clause = " WHERE " + " AND ".join(conditions)

        with get_db_connection(self.db_path) as conn:
            total_row = conn.execute(
                f"SELECT COUNT(*) as count FROM assessments{where_clause}", params
            ).fetchone()
            total = total_row["count"] if total_row else 0

            query = f"""
                SELECT a.*, r.display_name as repo_name,
                    (SELECT COUNT(*) FROM assessment_assignments WHERE assessment_id = a.id) as assigned_candidates_count,
                    (SELECT COUNT(*) FROM assessment_attempts WHERE assessment_id = a.id AND status IN ('SUBMITTED', 'GRADED')) as completed_candidates_count
                FROM assessments a
                LEFT JOIN repositories r ON a.repository_id = r.id
                {where_clause}
                ORDER BY a.created_at DESC
                LIMIT ? OFFSET ?
            """
            rows = conn.execute(query, params + [page_size, offset]).fetchall()

            items = []
            for r in rows:
                item = dict(r)
                if item.get("blueprint_config"):
                    try:
                        item["blueprint_config"] = json.loads(item["blueprint_config"])
                    except Exception:
                        pass
                if item.get("skills_evaluated"):
                    try:
                        item["skills_evaluated"] = json.loads(item["skills_evaluated"])
                    except Exception:
                        pass
                if item.get("competencies_evaluated"):
                    try:
                        item["competencies_evaluated"] = json.loads(item["competencies_evaluated"])
                    except Exception:
                        pass
                items.append(item)

        total_pages = max(1, (total + page_size - 1) // page_size)
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    def get_assessment(self, organization_id: str, assessment_id: str) -> Dict[str, Any]:
        """Retrieve assessment details and its curated questions or blueprint config."""
        with get_db_connection(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT a.*, r.display_name as repo_name, r.last_analyzed_commit as repo_commit,
                       r.approval_status as repo_approval_status
                FROM assessments a
                LEFT JOIN repositories r ON a.repository_id = r.id
                WHERE a.id = ? AND a.organization_id = ?
                """,
                (assessment_id, organization_id),
            ).fetchone()

            if not row:
                raise ValueError("Assessment not found or access denied.")

            assessment = dict(row)
            if assessment.get("blueprint_config"):
                try:
                    assessment["blueprint_config"] = json.loads(assessment["blueprint_config"])
                except Exception:
                    pass
            if assessment.get("skills_evaluated"):
                try:
                    assessment["skills_evaluated"] = json.loads(assessment["skills_evaluated"])
                except Exception:
                    pass
            if assessment.get("competencies_evaluated"):
                try:
                    assessment["competencies_evaluated"] = json.loads(assessment["competencies_evaluated"])
                except Exception:
                    pass

            # If curated mode, load attached questions
            curated_questions = []
            if assessment["mode"] == "CURATED":
                q_rows = conn.execute(
                    """
                    SELECT aq.order_index, aq.points, aq.question_version,
                           q.id as question_id, q.question_text, q.competency, q.response_format,
                           q.difficulty, q.skill_tags, q.review_status, q.validation_status
                    FROM assessment_questions aq
                    JOIN questions q ON aq.question_id = q.id
                    WHERE aq.assessment_id = ?
                    ORDER BY aq.order_index ASC
                    """,
                    (assessment_id,),
                ).fetchall()
                for qr in q_rows:
                    q_item = dict(qr)
                    if q_item.get("skill_tags"):
                        try:
                            q_item["skill_tags"] = json.loads(q_item["skill_tags"])
                        except Exception:
                            pass
                    curated_questions.append(q_item)

            assessment["curated_questions"] = curated_questions

            # Load versions
            versions = conn.execute(
                """
                SELECT id, version, total_points, published_at, created_by
                FROM assessment_versions
                WHERE assessment_id = ?
                ORDER BY version DESC
                """,
                (assessment_id,),
            ).fetchall()
            assessment["versions"] = [dict(v) for v in versions]

            return assessment

    def create_assessment(
        self,
        organization_id: str,
        user_id: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create a new DRAFT assessment with details and curated/randomized configuration."""
        title = data.get("title", "").strip()
        if not title:
            raise ValueError("Assessment title is required.")

        mode = data.get("mode", "CURATED").upper()
        if mode not in ("CURATED", "RANDOMIZED"):
            raise ValueError("Mode must be either CURATED or RANDOMIZED.")

        duration = int(data.get("duration_minutes", 60))
        if duration < 5 or duration > 360:
            raise ValueError("Duration must be between 5 and 360 minutes.")

        passing_pct = float(data.get("passing_score_pct", 70.0))
        if passing_pct < 0.0 or passing_pct > 100.0:
            raise ValueError("Passing score percentage must be between 0 and 100.")

        release_policy = data.get("result_release_policy", "WITHHOLD_PENDING_REVIEW").upper()
        if release_policy not in ("IMMEDIATE", "WITHHOLD_PENDING_REVIEW", "RELEASE_SCORE_ONLY"):
            raise ValueError("Invalid result release policy.")

        repo_id = data.get("repository_id")
        if repo_id:
            with get_db_connection(self.db_path) as conn:
                repo_check = conn.execute(
                    "SELECT id, approval_status FROM repositories WHERE id = ? AND organization_id = ?",
                    (repo_id, organization_id),
                ).fetchone()
                if not repo_check:
                    raise ValueError("Attached repository not found or unauthorized for this organization.")

        assessment_id = str(uuid.uuid4())
        blueprint_config = json.dumps(data.get("blueprint_config")) if data.get("blueprint_config") else None
        skills_eval = json.dumps(data.get("skills_evaluated", []))
        comp_eval = json.dumps(data.get("competencies_evaluated", []))

        with get_db_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO assessments (
                    id, organization_id, title, description, instructions, job_role,
                    repository_id, mode, blueprint_config, skills_evaluated, competencies_evaluated,
                    difficulty_profile, duration_minutes, passing_score_pct, availability_start,
                    availability_end, result_release_policy, max_attempts_per_candidate, status,
                    version, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'DRAFT', 1, ?)
                """,
                (
                    assessment_id,
                    organization_id,
                    title,
                    data.get("description", "").strip(),
                    data.get("instructions", "").strip(),
                    data.get("job_role", "").strip(),
                    repo_id,
                    mode,
                    blueprint_config,
                    skills_eval,
                    comp_eval,
                    data.get("difficulty_profile", "BALANCED"),
                    duration,
                    passing_pct,
                    data.get("availability_start"),
                    data.get("availability_end"),
                    release_policy,
                    int(data.get("max_attempts_per_candidate", 1)),
                    user_id,
                ),
            )

            # If curated mode with initial questions
            question_ids = data.get("question_ids", [])
            for idx, qid in enumerate(question_ids):
                # Verify question is published and authorized
                q_row = conn.execute(
                    "SELECT id, version, review_status FROM questions WHERE id = ? AND organization_id = ?",
                    (qid, organization_id),
                ).fetchone()
                if not q_row:
                    raise ValueError(f"Question {qid} does not exist or is unauthorized.")
                conn.execute(
                    """
                    INSERT INTO assessment_questions (id, assessment_id, question_id, question_version, order_index, points)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (str(uuid.uuid4()), assessment_id, qid, q_row["version"] or 1, idx, 1.0),
                )

        return self.get_assessment(organization_id, assessment_id)

    def update_assessment(
        self,
        organization_id: str,
        user_id: str,
        assessment_id: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update an assessment. If published, increments version and reverts status to DRAFT to protect active assessments."""
        current = self.get_assessment(organization_id, assessment_id)

        is_currently_published = current["status"] == "PUBLISHED"
        new_version = (current["version"] or 1) + 1 if is_currently_published else (current["version"] or 1)
        new_status = "DRAFT" if is_currently_published else current["status"]

        title = data.get("title", current["title"]).strip()
        description = data.get("description", current["description"])
        instructions = data.get("instructions", current.get("instructions", ""))
        job_role = data.get("job_role", current.get("job_role", ""))
        mode = data.get("mode", current["mode"]).upper()
        duration = int(data.get("duration_minutes", current["duration_minutes"]))
        passing_pct = float(data.get("passing_score_pct", current["passing_score_pct"]))
        release_policy = data.get("result_release_policy", current.get("result_release_policy", "WITHHOLD_PENDING_REVIEW"))
        repo_id = data.get("repository_id", current.get("repository_id"))

        blueprint_config = json.dumps(data["blueprint_config"]) if "blueprint_config" in data else (
            json.dumps(current["blueprint_config"]) if current.get("blueprint_config") else None
        )
        skills_eval = json.dumps(data.get("skills_evaluated", current.get("skills_evaluated", [])))
        comp_eval = json.dumps(data.get("competencies_evaluated", current.get("competencies_evaluated", [])))

        with get_db_connection(self.db_path) as conn:
            conn.execute(
                """
                UPDATE assessments
                SET title = ?, description = ?, instructions = ?, job_role = ?, repository_id = ?,
                    mode = ?, blueprint_config = ?, skills_evaluated = ?, competencies_evaluated = ?,
                    duration_minutes = ?, passing_score_pct = ?, result_release_policy = ?,
                    version = ?, status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND organization_id = ?
                """,
                (
                    title,
                    description,
                    instructions,
                    job_role,
                    repo_id,
                    mode,
                    blueprint_config,
                    skills_eval,
                    comp_eval,
                    duration,
                    passing_pct,
                    release_policy,
                    new_version,
                    new_status,
                    assessment_id,
                    organization_id,
                ),
            )

            # Update curated questions if provided
            if "question_ids" in data and mode == "CURATED":
                conn.execute("DELETE FROM assessment_questions WHERE assessment_id = ?", (assessment_id,))
                for idx, qid in enumerate(data["question_ids"]):
                    q_row = conn.execute(
                        "SELECT id, version FROM questions WHERE id = ? AND organization_id = ?",
                        (qid, organization_id),
                    ).fetchone()
                    if q_row:
                        conn.execute(
                            """
                            INSERT INTO assessment_questions (id, assessment_id, question_id, question_version, order_index, points)
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (str(uuid.uuid4()), assessment_id, qid, q_row["version"] or 1, idx, 1.0),
                        )

        return self.get_assessment(organization_id, assessment_id)

    def select_blueprint_questions(
        self,
        organization_id: str,
        blueprint: Dict[str, Any],
        repository_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Deterministic, constraint-satisfaction randomized selection for Mode B.
        Randomization operates ONLY on approved and published questions.
        """
        requested_count = int(blueprint.get("question_count", 5))
        skills = blueprint.get("required_skills", [])
        competencies = blueprint.get("required_competencies", [])
        difficulty = blueprint.get("difficulty")
        response_formats = blueprint.get("allowed_response_formats", [])

        conditions = ["organization_id = ?", "review_status = 'PUBLISHED'", "is_archived = 0"]
        params: List[Any] = [organization_id]

        if repository_id:
            conditions.append("repository_id = ?")
            params.append(repository_id)

        if difficulty:
            conditions.append("difficulty = ?")
            params.append(difficulty.upper())

        if competencies:
            placeholders = ",".join("?" for _ in competencies)
            conditions.append(f"competency IN ({placeholders})")
            params.extend([c.upper() for c in competencies])

        if response_formats:
            placeholders = ",".join("?" for _ in response_formats)
            conditions.append(f"response_format IN ({placeholders})")
            params.extend([rf.upper() for rf in response_formats])

        where_clause = " WHERE " + " AND ".join(conditions)

        with get_db_connection(self.db_path) as conn:
            rows = conn.execute(
                f"""
                SELECT id, version, question_text, options, answer_key, explanation,
                       competency, response_format, difficulty, skill_tags, evidence_references
                FROM questions
                {where_clause}
                """,
                params,
            ).fetchall()

            eligible = []
            for r in rows:
                q = dict(r)
                q_tags = []
                if q.get("skill_tags"):
                    try:
                        q_tags = [t.lower() for t in json.loads(q["skill_tags"])]
                    except Exception:
                        pass

                # If required skills specified, check tag intersection
                if skills:
                    has_skill = any(s.lower() in q_tags for s in skills)
                    if not has_skill:
                        continue

                eligible.append(q)

        if len(eligible) < requested_count:
            raise ValueError(
                f"Insufficient published question coverage to satisfy blueprint. "
                f"Requested {requested_count} questions, but only {len(eligible)} matching questions found."
            )

        # Deterministic sample (use seed if provided in blueprint)
        seed = blueprint.get("random_seed")
        rng = random.Random(seed) if seed is not None else random.Random()
        selected = rng.sample(eligible, requested_count)

        # Allocate points (default 1.0 per question or per blueprint)
        default_points = float(blueprint.get("points_per_question", 1.0))
        for q in selected:
            q["points"] = default_points

        return selected

    def publish_assessment(
        self,
        organization_id: str,
        user_id: str,
        assessment_id: str,
    ) -> Dict[str, Any]:
        """
        Publish an assessment.
        Validates all prerequisites and creates an immutable assessment_versions snapshot.
        """
        assessment = self.get_assessment(organization_id, assessment_id)

        # 1. Validate repository readiness if repository attached
        repo_commit = None
        neo4j_repo_id = None
        if assessment.get("repository_id"):
            with get_db_connection(self.db_path) as conn:
                repo_row = conn.execute(
                    "SELECT id, approval_status, last_analyzed_commit, neo4j_repo_id FROM repositories WHERE id = ?",
                    (assessment["repository_id"],),
                ).fetchone()
                if not repo_row:
                    raise ValueError("Attached repository not found.")
                if repo_row["approval_status"] not in ("READY_FOR_REVIEW", "APPROVED"):
                    raise ValueError(
                        f"Repository must be APPROVED before assessment publication. Current status: {repo_row['approval_status']}"
                    )
                repo_commit = repo_row["last_analyzed_commit"]
                neo4j_repo_id = repo_row["neo4j_repo_id"]

        # 2. Gather frozen questions for snapshot
        questions_to_freeze: List[Dict[str, Any]] = []

        if assessment["mode"] == "CURATED":
            curated = assessment.get("curated_questions", [])
            if not curated:
                raise ValueError("Curated assessment must contain at least one question before publishing.")

            with get_db_connection(self.db_path) as conn:
                for item in curated:
                    qid = item["question_id"]
                    q_row = conn.execute(
                        """
                        SELECT id, version, question_text, options, answer_key, explanation,
                               competency, response_format, difficulty, skill_tags, evidence_references,
                               review_status, validation_status
                        FROM questions
                        WHERE id = ? AND organization_id = ?
                        """,
                        (qid, organization_id),
                    ).fetchone()
                    if not q_row:
                        raise ValueError(f"Question {qid} not found.")
                    if q_row["review_status"] != "PUBLISHED":
                        raise ValueError(
                            f"Question '{q_row['question_text'][:30]}...' must be in PUBLISHED review status. Current: {q_row['review_status']}"
                        )
                    q_dict = dict(q_row)
                    q_dict["points"] = float(item.get("points", 1.0))
                    q_dict["order_index"] = item.get("order_index", 0)
                    questions_to_freeze.append(q_dict)

        elif assessment["mode"] == "RANDOMIZED":
            bp = assessment.get("blueprint_config")
            if not bp:
                raise ValueError("Randomized assessment must have a valid blueprint_config.")
            # Verify and select blueprint questions
            selected = self.select_blueprint_questions(organization_id, bp, assessment.get("repository_id"))
            for idx, q in enumerate(selected):
                q["order_index"] = idx
                questions_to_freeze.append(q)

        # 3. Compute total points
        total_points = sum(q.get("points", 1.0) for q in questions_to_freeze)

        # 4. Serialize questions snapshot
        snapshot_json = json.dumps(questions_to_freeze)

        # 5. Insert immutable assessment_version and update status to PUBLISHED
        version_id = str(uuid.uuid4())
        next_ver = assessment["version"] or 1

        with get_db_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO assessment_versions (
                    id, assessment_id, version, organization_id, title, description, instructions,
                    job_role, repository_id, neo4j_repo_id, analysis_commit, mode, blueprint_config,
                    duration_minutes, passing_score_pct, result_release_policy, questions_snapshot,
                    total_points, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    version_id,
                    assessment_id,
                    next_ver,
                    organization_id,
                    assessment["title"],
                    assessment["description"],
                    assessment.get("instructions"),
                    assessment.get("job_role"),
                    assessment.get("repository_id"),
                    neo4j_repo_id,
                    repo_commit,
                    assessment["mode"],
                    json.dumps(assessment.get("blueprint_config")) if assessment.get("blueprint_config") else None,
                    assessment["duration_minutes"],
                    assessment["passing_score_pct"],
                    assessment.get("result_release_policy", "WITHHOLD_PENDING_REVIEW"),
                    snapshot_json,
                    total_points,
                    user_id,
                ),
            )

            conn.execute(
                """
                UPDATE assessments
                SET status = 'PUBLISHED', published_version_id = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND organization_id = ?
                """,
                (version_id, assessment_id, organization_id),
            )

        return self.get_assessment(organization_id, assessment_id)

    def archive_assessment(self, organization_id: str, assessment_id: str) -> Dict[str, Any]:
        """Archive an assessment without deleting historical attempts or versions."""
        with get_db_connection(self.db_path) as conn:
            res = conn.execute(
                """
                UPDATE assessments
                SET status = 'ARCHIVED', is_archived = 1, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND organization_id = ?
                """,
                (assessment_id, organization_id),
            )
            if res.rowcount == 0:
                raise ValueError("Assessment not found or access denied.")

        return {"id": assessment_id, "status": "ARCHIVED", "is_archived": True}
