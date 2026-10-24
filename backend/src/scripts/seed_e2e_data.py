"""
ARCHITECH - Phase 5 Synthetic E2E Test Fixture Seeder
Deterministic, isolated test data for Playwright browser automation & CI.
"""

import json
import uuid
import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.db.connection import get_db_connection, init_db
from src.security.passwords import hash_password

def seed_e2e_data(db_path=None):
    init_db(db_path)
    
    with get_db_connection(db_path) as conn:
        pw_hash = hash_password("StrongPass123!")
        
        # 1. Seed Synthetic Organizations
        orgs = [
            ("org-acme-e2e", "Acme Corp", "acme-corp"),
            ("org-beta-e2e", "Beta Tech", "beta-tech"),
        ]
        for org_id, name, slug in orgs:
            conn.execute(
                """
                INSERT INTO organizations (id, name, slug)
                VALUES (?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET name = excluded.name, slug = excluded.slug
                """,
                (org_id, name, slug)
            )
            
        # 2. Seed Synthetic Users
        users = [
            ("user-hr-acme", "hr_org_a@example.com", "HR Alice", "HR", "org-acme-e2e"),
            ("user-hr-beta", "hr_org_b@example.com", "HR Bob", "HR", "org-beta-e2e"),
            ("user-candidate-e2e", "candidate_e2e@example.com", "Charlie Candidate", "USER", None),
        ]
        for uid, email, name, role, org_id in users:
            conn.execute(
                """
                INSERT INTO users (id, email, password_hash, full_name, role, is_active)
                VALUES (?, ?, ?, ?, ?, 1)
                ON CONFLICT(id) DO UPDATE SET 
                    email = excluded.email, 
                    password_hash = excluded.password_hash,
                    full_name = excluded.full_name,
                    role = excluded.role,
                    is_active = 1
                """,
                (uid, email, pw_hash, name, role)
            )
            if org_id:
                conn.execute(
                    """
                    INSERT INTO organization_memberships (id, organization_id, user_id, org_role)
                    VALUES (?, ?, ?, 'OWNER')
                    ON CONFLICT(organization_id, user_id) DO UPDATE SET org_role = 'OWNER'
                    """,
                    (str(uuid.uuid4()), org_id, uid)
                )

        # 3. Seed Sample Approved Repository for Org A
        repo_id = "repo-acme-e2e"
        conn.execute(
            """
            INSERT INTO repositories (
                id, neo4j_repo_id, organization_id, display_name, repo_url,
                default_branch, approval_status, description, analysis_status
            )
            VALUES (?, ?, ?, ?, ?, 'main', 'APPROVED', 'Synthetic Core Repo for Testing', 'COMPLETED')
            ON CONFLICT(id) DO UPDATE SET approval_status = 'APPROVED', analysis_status = 'COMPLETED'
            """,
            (repo_id, "neo4j-acme-core", "org-acme-e2e", "Acme Core Repo", "https://github.com/acme/core-service")
        )

        # 4. Seed Questions for Org A and Org B
        options_a = [
            {"key": "A", "text": "Decoupling high-level policy from low-level implementation details"},
            {"key": "B", "text": "Eliminating the need for unit testing entirely"},
            {"key": "C", "text": "Guaranteeing 100% database query cache hit rates"},
            {"key": "D", "text": "Requiring all classes to inherit from a single god object"}
        ]
        answer_key_a = {"correct_options": ["A"]}
        
        conn.execute(
            """
            INSERT INTO questions (
                id, organization_id, created_by, source_type, repository_id, skill_tags,
                competency, response_format, difficulty, question_text, options, answer_key,
                explanation, review_status, validation_status, version, is_archived
            )
            VALUES (?, ?, ?, 'SKILL_BASED', NULL, ?, 'ARCHITECTURE_REASONING', 'SINGLE_SELECT',
                    'INTERMEDIATE', ?, ?, ?, ?, 'PUBLISHED', 'VALIDATED', 1, 0)
            ON CONFLICT(id) DO UPDATE SET
                review_status = 'PUBLISHED',
                validation_status = 'VALIDATED'
            """,
            (
                "q-acme-e2e-1",
                "org-acme-e2e",
                "user-hr-acme",
                json.dumps(["Architecture", "Clean Code"]),
                "What is the primary architectural benefit of Dependency Inversion?",
                json.dumps(options_a),
                json.dumps(answer_key_a),
                "Dependency inversion inverts ownership so high-level modules depend on abstractions."
            )
        )
        conn.execute(
            """
            INSERT INTO question_versions (
                id, question_id, version, organization_id, author_id, source_type,
                skill_tags, competency, response_format, difficulty, question_text,
                options, answer_key, explanation, validation_status, review_status
            )
            VALUES (?, ?, 1, ?, ?, 'SKILL_BASED', ?, 'ARCHITECTURE_REASONING', 'SINGLE_SELECT',
                    'INTERMEDIATE', ?, ?, ?, ?, 'VALIDATED', 'PUBLISHED')
            ON CONFLICT(question_id, version) DO NOTHING
            """,
            (
                "qv-acme-e2e-1",
                "q-acme-e2e-1",
                "org-acme-e2e",
                "user-hr-acme",
                json.dumps(["Architecture", "Clean Code"]),
                "What is the primary architectural benefit of Dependency Inversion?",
                json.dumps(options_a),
                json.dumps(answer_key_a),
                "Dependency inversion inverts ownership so high-level modules depend on abstractions."
            )
        )

        # Question for Org B (to test multi-tenant cross-org isolation)
        conn.execute(
            """
            INSERT INTO questions (
                id, organization_id, created_by, source_type, repository_id, skill_tags,
                competency, response_format, difficulty, question_text, options, answer_key,
                explanation, review_status, validation_status, version, is_archived
            )
            VALUES (?, ?, ?, 'SKILL_BASED', NULL, ?, 'CODE_COMPREHENSION', 'TRUE_FALSE',
                    'BEGINNER', ?, ?, ?, ?, 'PUBLISHED', 'VALIDATED', 1, 0)
            ON CONFLICT(id) DO UPDATE SET
                review_status = 'PUBLISHED',
                validation_status = 'VALIDATED'
            """,
            (
                "q-beta-e2e-1",
                "org-beta-e2e",
                "user-hr-beta",
                json.dumps(["Python", "Basics"]),
                "In Python, integers and strings are immutable objects.",
                json.dumps([{"key": "T", "text": "True"}, {"key": "F", "text": "False"}]),
                json.dumps({"correct_options": ["T"]}),
                "Integers, floats, tuples, and strings are immutable in Python."
            )
        )

        # 5. Seed Assessment for Org A
        conn.execute(
            """
            INSERT INTO assessments (
                id, organization_id, title, description, job_role,
                mode, duration_minutes, passing_score_pct, status, version
            )
            VALUES (?, ?, ?, ?, ?, 'CURATED', 30, 70.0, 'PUBLISHED', 1)
            ON CONFLICT(id) DO UPDATE SET status = 'PUBLISHED'
            """,
            (
                "asm-acme-e2e-1",
                "org-acme-e2e",
                "Acme Architecture Assessment",
                "Baseline assessment for enterprise software architects.",
                "Senior Software Engineer"
            )
        )
        conn.execute(
            """
            INSERT INTO assessment_questions (
                id, assessment_id, question_id, question_version, order_index, points
            )
            VALUES (?, ?, ?, 1, 0, 10.0)
            ON CONFLICT(assessment_id, question_id) DO NOTHING
            """,
            ("aq-acme-e2e-1", "asm-acme-e2e-1", "q-acme-e2e-1")
        )
        
        snapshot = [{
            "id": "q-acme-e2e-1",
            "version": 1,
            "competency": "ARCHITECTURE_REASONING",
            "response_format": "SINGLE_SELECT",
            "difficulty": "INTERMEDIATE",
            "question_text": "What is the primary architectural benefit of Dependency Inversion?",
            "options": options_a,
            "answer_key": answer_key_a,
            "points": 10.0
        }]
        
        conn.execute(
            """
            INSERT INTO assessment_versions (
                id, assessment_id, version, organization_id, title, description,
                mode, duration_minutes, passing_score_pct, result_release_policy,
                questions_snapshot, total_points, created_by
            )
            VALUES (?, ?, 1, ?, ?, ?, 'CURATED', 30, 70.0, 'WITHHOLD_PENDING_REVIEW', ?, 10.0, ?)
            ON CONFLICT(assessment_id, version) DO NOTHING
            """,
            (
                "av-acme-e2e-1",
                "asm-acme-e2e-1",
                "org-acme-e2e",
                "Acme Architecture Assessment",
                "Baseline assessment for enterprise software architects.",
                json.dumps(snapshot),
                "user-hr-acme"
            )
        )

        conn.commit()
        print("✓ Synthetic E2E test data seeded successfully:")
        print("  - Org A: Acme Corp (org-acme-e2e), HR: hr_org_a@example.com (StrongPass123!)")
        print("  - Org B: Beta Tech (org-beta-e2e), HR: hr_org_b@example.com (StrongPass123!)")
        print("  - Candidate: candidate_e2e@example.com (StrongPass123!)")
        print("  - Published Assessment: asm-acme-e2e-1 with question q-acme-e2e-1")

if __name__ == "__main__":
    seed_e2e_data()
