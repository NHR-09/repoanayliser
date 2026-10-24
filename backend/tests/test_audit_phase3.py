import os
import json
import uuid
import tempfile
import unittest
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from main import app
from src.config import settings
from src.db.connection import get_db_connection, init_db
from src.security.sessions import create_session
from src.services.hr_question_service import HRQuestionBankService
from src.services.hr_repo_service import HRRepositoryLibraryService
from src.services.hr_question_generation_service import HRQuestionGenerationService


class TestAuditPhase3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.test_db_path = os.path.join(cls.temp_dir.name, "test_audit_phase3.db")
        cls.orig_db_path = settings.db_path
        settings.db_path = cls.test_db_path
        os.environ["DATABASE_PATH"] = cls.test_db_path

        init_db(cls.test_db_path)
        cls.client = TestClient(app)
        cls.question_service = HRQuestionBankService()
        cls.repo_service = HRRepositoryLibraryService()
        cls.gen_service = HRQuestionGenerationService()

    @classmethod
    def tearDownClass(cls):
        settings.db_path = cls.orig_db_path
        cls.temp_dir.cleanup()

    def setUp(self):
        settings.db_path = self.test_db_path
        self.client.cookies.clear()

    def _setup_org_and_hr(self, org_name: str, email_prefix: str) -> Dict[str, Any]:
        """Helper to set up an organization with an authorized HR user and session token."""
        org_id = f"org_{uuid.uuid4().hex[:6]}"
        user_id = f"hr_{uuid.uuid4().hex[:6]}"
        email = f"{email_prefix}_{uuid.uuid4().hex[:4]}@company.com"

        with get_db_connection(self.test_db_path) as conn:
            conn.execute(
                "INSERT INTO organizations (id, name, slug) VALUES (?, ?, ?)",
                (org_id, org_name, org_id)
            )
            conn.execute(
                "INSERT INTO users (id, email, password_hash, full_name, role) VALUES (?, ?, 'h', 'HR Manager', 'HR')",
                (user_id, email)
            )
            conn.execute(
                "INSERT INTO organization_memberships (id, organization_id, user_id, org_role) VALUES (?, ?, ?, 'RECRUITER')",
                (str(uuid.uuid4()), org_id, user_id)
            )

        sess = create_session(user_id, db_path=self.test_db_path)
        headers = {"Authorization": f"Bearer {sess['token']}"}
        return {
            "org_id": org_id,
            "user_id": user_id,
            "email": email,
            "token": sess["token"],
            "headers": headers
        }

    def _setup_candidate_user(self) -> Dict[str, Any]:
        """Helper to set up a regular candidate USER."""
        user_id = f"cand_{uuid.uuid4().hex[:6]}"
        email = f"cand_{uuid.uuid4().hex[:4]}@candidate.com"
        with get_db_connection(self.test_db_path) as conn:
            conn.execute(
                "INSERT INTO users (id, email, password_hash, full_name, role) VALUES (?, ?, 'h', 'Regular Candidate', 'USER')",
                (user_id, email)
            )
        sess = create_session(user_id, db_path=self.test_db_path)
        return {
            "user_id": user_id,
            "email": email,
            "token": sess["token"],
            "headers": {"Authorization": f"Bearer {sess['token']}"}
        }

    # =============================================================
    # TEST GROUP 3A: Question Bank Authorization & CRUD (P3-01 to P3-10)
    # =============================================================

    def test_p3_01_hr_create_valid_question(self):
        hr_ctx = self._setup_org_and_hr("Acme Corp", "hr_p3_01")
        payload = {
            "question_text": "What is the primary benefit of Python generators over standard lists?",
            "response_format": "SINGLE_SELECT",
            "competency": "CODE_COMPREHENSION",
            "difficulty": "INTERMEDIATE",
            "skill_tags": ["Python", "Memory Management"],
            "options": [
                {"id": "A", "text": "They allow faster indexing by integer index."},
                {"id": "B", "text": "They produce values lazily on demand, reducing memory usage."},
                {"id": "C", "text": "They guarantee multi-core thread parallelism."}
            ],
            "answer_key": ["B"],
            "explanation": "Generators compute items lazily using yield, consuming constant memory regardless of stream size."
        }
        res = self.client.post(
            f"/api/hr/questions?organization_id={hr_ctx['org_id']}",
            json=payload,
            headers=hr_ctx["headers"]
        )
        self.assertEqual(res.status_code, 201)
        data = res.json()["question"]
        self.assertEqual(data["organization_id"], hr_ctx["org_id"])
        self.assertEqual(data["review_status"], "NEEDS_REVIEW")
        self.assertEqual(data["version"], 1)

    def test_p3_02_hr_submit_invalid_question(self):
        hr_ctx = self._setup_org_and_hr("Beta Corp", "hr_p3_02")
        payload = {
            "question_text": "Short",  # < 15 chars
            "response_format": "SINGLE_SELECT",
            "competency": "INVALID_COMPETENCY",
            "difficulty": "INTERMEDIATE",
            "options": [{"id": "A", "text": "Option A"}],
            "answer_key": ["A"],
            "explanation": "Valid explanation."
        }
        res = self.client.post(
            f"/api/hr/questions?organization_id={hr_ctx['org_id']}",
            json=payload,
            headers=hr_ctx["headers"]
        )
        self.assertIn(res.status_code, (400, 422))

    def test_p3_03_candidate_user_cannot_create_hr_question(self):
        cand_ctx = self._setup_candidate_user()
        payload = {
            "question_text": "Unauthorized attempt to create a question in bank?",
            "response_format": "SINGLE_SELECT",
            "competency": "CODE_COMPREHENSION",
            "difficulty": "BEGINNER",
            "options": [{"id": "A", "text": "A"}, {"id": "B", "text": "B"}],
            "answer_key": ["A"],
            "explanation": "Not permitted."
        }
        res = self.client.post(
            "/api/hr/questions",
            json=payload,
            headers=cand_ctx["headers"]
        )
        self.assertEqual(res.status_code, 403)

    def test_p3_04_hr_cross_organization_access_denied(self):
        hr_a = self._setup_org_and_hr("Org A", "hr_a")
        hr_b = self._setup_org_and_hr("Org B", "hr_b")

        # HR A creates question in Org A
        q_payload = {
            "question_text": "Org A Confidential Technical Assessment Question?",
            "response_format": "SINGLE_SELECT",
            "competency": "CODE_COMPREHENSION",
            "difficulty": "INTERMEDIATE",
            "options": [{"id": "A", "text": "A"}, {"id": "B", "text": "B"}],
            "answer_key": ["A"],
            "explanation": "Explanation for Org A question."
        }
        create_res = self.client.post(
            f"/api/hr/questions?organization_id={hr_a['org_id']}",
            json=q_payload,
            headers=hr_a["headers"]
        )
        self.assertEqual(create_res.status_code, 201)
        q_id = create_res.json()["question"]["id"]

        # HR B attempts to access Org A's question
        # 1. By claiming Org A in parameter
        res_claimed_org = self.client.get(
            f"/api/hr/questions/{q_id}?organization_id={hr_a['org_id']}",
            headers=hr_b["headers"]
        )
        self.assertEqual(res_claimed_org.status_code, 403)

        # 2. By using Org B's id with Org A's question id
        res_cross_id = self.client.get(
            f"/api/hr/questions/{q_id}?organization_id={hr_b['org_id']}",
            headers=hr_b["headers"]
        )
        self.assertEqual(res_cross_id.status_code, 404)

    def test_p3_05_hr_tampering_question_id_denied(self):
        hr_a = self._setup_org_and_hr("Org Alpha", "hr_alpha")
        hr_b = self._setup_org_and_hr("Org Beta", "hr_beta")

        q_b = self.question_service.create_question(
            organization_id=hr_b["org_id"],
            author_id=hr_b["user_id"],
            data={
                "question_text": "What is dependency inversion principle in OOP?",
                "response_format": "SINGLE_SELECT",
                "competency": "ARCHITECTURE_REASONING",
                "difficulty": "ADVANCED",
                "skill_tags": ["Architecture"],
                "options": [{"id": "A", "text": "High level modules depend on abstractions."}, {"id": "B", "text": "Concrete classes"}],
                "answer_key": ["A"],
                "explanation": "High level modules should not depend on low level details."
            }
        )

        # HR Alpha attempts to approve Org Beta's question
        res = self.client.post(
            f"/api/hr/questions/{q_b['id']}/transition?organization_id={hr_a['org_id']}",
            json={"action": "APPROVE"},
            headers=hr_a["headers"]
        )
        self.assertEqual(res.status_code, 404)

    def test_p3_06_hr_search_and_filter(self):
        hr = self._setup_org_and_hr("Search Corp", "hr_search")
        org_id = hr["org_id"]

        # Insert 3 questions with different skills and competencies
        self.question_service.create_question(
            organization_id=org_id,
            author_id=hr["user_id"],
            data={
                "question_text": "How does React virtual DOM diffing algorithm function?",
                "response_format": "SINGLE_SELECT",
                "competency": "CODE_COMPREHENSION",
                "difficulty": "INTERMEDIATE",
                "skill_tags": ["React", "JavaScript"],
                "options": [{"id": "A", "text": "Tree comparison in O(n)"}, {"id": "B", "text": "O(n^3)"}],
                "answer_key": ["A"],
                "explanation": "React uses heuristic O(n) diffing."
            }
        )

        self.question_service.create_question(
            organization_id=org_id,
            author_id=hr["user_id"],
            data={
                "question_text": "What is the purpose of foreign key cascade constraints in SQL databases?",
                "response_format": "SINGLE_SELECT",
                "competency": "DEPENDENCY_TRACING",
                "difficulty": "BEGINNER",
                "skill_tags": ["SQL", "Database"],
                "options": [{"id": "A", "text": "Maintain relational integrity"}, {"id": "B", "text": "Index speed"}],
                "answer_key": ["A"],
                "explanation": "Cascades keep dependent child records synchronized."
            }
        )

        # Search for 'React'
        res_search = self.client.get(
            f"/api/hr/questions?organization_id={org_id}&search=React",
            headers=hr["headers"]
        )
        self.assertEqual(res_search.status_code, 200)
        items = res_search.json()["items"]
        self.assertEqual(len(items), 1)
        self.assertIn("React", items[0]["question_text"])

        # Filter by competency
        res_comp = self.client.get(
            f"/api/hr/questions?organization_id={org_id}&competency=DEPENDENCY_TRACING",
            headers=hr["headers"]
        )
        self.assertEqual(res_comp.status_code, 200)
        self.assertEqual(len(res_comp.json()["items"]), 1)
        self.assertIn("SQL", res_comp.json()["items"][0]["question_text"])

    def test_p3_07_hr_archive_question(self):
        hr = self._setup_org_and_hr("Archive Corp", "hr_arch")
        org_id = hr["org_id"]

        q = self.question_service.create_question(
            organization_id=org_id,
            author_id=hr["user_id"],
            data={
                "question_text": "Legacy question slated for formal archiving and retirement?",
                "response_format": "SINGLE_SELECT",
                "competency": "DEBUGGING",
                "difficulty": "BEGINNER",
                "skill_tags": ["Legacy"],
                "options": [{"id": "A", "text": "A"}, {"id": "B", "text": "B"}],
                "answer_key": ["A"],
                "explanation": "Archiving test."
            }
        )

        # Archive it via transition
        res_arch = self.client.post(
            f"/api/hr/questions/{q['id']}/transition?organization_id={org_id}",
            json={"action": "ARCHIVE"},
            headers=hr["headers"]
        )
        self.assertEqual(res_arch.status_code, 200)

        # Excluded from active question list
        res_list = self.client.get(
            f"/api/hr/questions?organization_id={org_id}",
            headers=hr["headers"]
        )
        ids = [item["id"] for item in res_list.json()["items"]]
        self.assertNotIn(q["id"], ids)

        # Included when is_archived=true is requested
        res_arch_list = self.client.get(
            f"/api/hr/questions?organization_id={org_id}&is_archived=true",
            headers=hr["headers"]
        )
        arch_ids = [item["id"] for item in res_arch_list.json()["items"]]
        self.assertIn(q["id"], arch_ids)

    def test_p3_08_candidate_cannot_read_confidential_answer_keys(self):
        hr = self._setup_org_and_hr("Security Bank Corp", "hr_sec")
        cand = self._setup_candidate_user()

        # HR questions list cannot be read by candidate
        res = self.client.get(
            f"/api/hr/questions?organization_id={hr['org_id']}",
            headers=cand["headers"]
        )
        self.assertEqual(res.status_code, 403)

    # =============================================================
    # TEST GROUP 3B & 3C: Question Correctness, Lifecycle & Versioning
    # =============================================================

    def test_p3_09_question_lifecycle_and_immutable_versioning(self):
        hr = self._setup_org_and_hr("Lifecycle Corp", "hr_life")
        org_id = hr["org_id"]
        headers = hr["headers"]

        # 1. Create (NEEDS_REVIEW, version 1)
        create_res = self.client.post(
            f"/api/hr/questions?organization_id={org_id}",
            json={
                "question_text": "Original Version 1: What is ACID compliance in database transactions?",
                "response_format": "SINGLE_SELECT",
                "competency": "ARCHITECTURE_REASONING",
                "difficulty": "INTERMEDIATE",
                "skill_tags": ["Databases"],
                "options": [{"id": "A", "text": "Atomicity, Consistency, Isolation, Durability"}, {"id": "B", "text": "Wrong"}],
                "answer_key": ["A"],
                "explanation": "ACID guarantees transactional safety."
            },
            headers=headers
        )
        self.assertEqual(create_res.status_code, 201)
        q_id = create_res.json()["question"]["id"]
        self.assertEqual(create_res.json()["question"]["review_status"], "NEEDS_REVIEW")
        self.assertEqual(create_res.json()["question"]["version"], 1)

        # 2. Cannot publish directly before approval
        pub_fail = self.client.post(
            f"/api/hr/questions/{q_id}/transition?organization_id={org_id}",
            json={"action": "PUBLISH"},
            headers=headers
        )
        self.assertEqual(pub_fail.status_code, 400)
        self.assertIn("approved", pub_fail.json()["detail"].lower())

        # 3. Approve question
        app_res = self.client.post(
            f"/api/hr/questions/{q_id}/transition?organization_id={org_id}",
            json={"action": "APPROVE"},
            headers=headers
        )
        self.assertEqual(app_res.status_code, 200)
        self.assertEqual(app_res.json()["question"]["review_status"], "APPROVED")

        # 4. Publish question
        pub_res = self.client.post(
            f"/api/hr/questions/{q_id}/transition?organization_id={org_id}",
            json={"action": "PUBLISH"},
            headers=headers
        )
        self.assertEqual(pub_res.status_code, 200)
        self.assertEqual(pub_res.json()["question"]["review_status"], "PUBLISHED")

        # 5. Edit published question -> creates new version snapshot (v2) and resets review_status
        edit_res = self.client.put(
            f"/api/hr/questions/{q_id}?organization_id={org_id}",
            json={
                "question_text": "Version 2 Edit: What do the letters in ACID stand for in DBMS?"
            },
            headers=headers
        )
        self.assertEqual(edit_res.status_code, 200)
        self.assertEqual(edit_res.json()["question"]["version"], 2)
        self.assertEqual(edit_res.json()["question"]["review_status"], "NEEDS_REVIEW")

        # 6. Verify version history preserves version 1
        history_res = self.client.get(
            f"/api/hr/questions/{q_id}/versions?organization_id={org_id}",
            headers=headers
        )
        self.assertEqual(history_res.status_code, 200)
        versions = history_res.json()["versions"]
        self.assertEqual(len(versions), 2)
        v1 = [v for v in versions if v["version"] == 1][0]
        v2 = [v for v in versions if v["version"] == 2][0]
        self.assertIn("Original Version 1", v1["question_text"])
        self.assertIn("Version 2 Edit", v2["question_text"])

    # =============================================================
    # TEST GROUP 3D: Repository Library Management
    # =============================================================

    def test_p3_10_repository_library_registration_and_state_transitions(self):
        hr = self._setup_org_and_hr("Repo Org", "hr_repo")
        org_id = hr["org_id"]
        headers = hr["headers"]

        # 1. Register valid GitHub repository
        reg_res = self.client.post(
            f"/api/hr/repositories?organization_id={org_id}",
            json={
                "repo_url": "https://github.com/psf/requests",
                "display_name": "Requests HTTP Library",
                "description": "Standard Python HTTP client for assessment benchmarks."
            },
            headers=headers
        )
        self.assertEqual(reg_res.status_code, 201)
        repo_data = reg_res.json()["repository"]
        repo_id = repo_data["id"]
        self.assertEqual(repo_data["approval_status"], "REGISTERED")

        # 2. State transition: REGISTERED -> APPROVED
        appr_res = self.client.post(
            f"/api/hr/repositories/{repo_id}/transition?organization_id={org_id}",
            json={"action": "APPROVE"},
            headers=headers
        )
        self.assertEqual(appr_res.status_code, 200)
        self.assertEqual(appr_res.json()["repository"]["approval_status"], "APPROVED")

        # 3. State transition: APPROVED -> ARCHIVE
        use_res = self.client.post(
            f"/api/hr/repositories/{repo_id}/transition?organization_id={org_id}",
            json={"action": "ARCHIVE"},
            headers=headers
        )
        self.assertEqual(use_res.status_code, 200)
        self.assertEqual(use_res.json()["repository"]["approval_status"], "ARCHIVED")

        # 4. Duplicate registration handles idempotently
        dup_res = self.client.post(
            f"/api/hr/repositories?organization_id={org_id}",
            json={
                "repo_url": "https://github.com/psf/requests",
                "display_name": "Updated Requests Name"
            },
            headers=headers
        )
        self.assertEqual(dup_res.status_code, 201)
        self.assertEqual(dup_res.json()["repository"]["id"], repo_id)

        # 5. Cross-organization isolation: Org B cannot see Org A's repository library
        hr_b = self._setup_org_and_hr("Other Org", "hr_other")
        list_b = self.client.get(
            f"/api/hr/repositories?organization_id={hr_b['org_id']}",
            headers=hr_b["headers"]
        )
        self.assertEqual(list_b.status_code, 200)
        ids_b = [r["id"] for r in list_b.json()["repositories"]]
        self.assertNotIn(repo_id, ids_b)

    # =============================================================
    # TEST GROUP 3E: Repository Question Coverage Matrix
    # =============================================================

    def test_p3_11_repository_question_coverage_matrix(self):
        hr = self._setup_org_and_hr("Coverage Org", "hr_cov")
        org_id = hr["org_id"]
        headers = hr["headers"]

        # Register repository
        reg_res = self.client.post(
            f"/api/hr/repositories?organization_id={org_id}",
            json={"repo_url": "https://github.com/encode/uvicorn"},
            headers=headers
        )
        repo_id = reg_res.json()["repository"]["id"]

        # Insert question linked to this repo
        self.question_service.create_question(
            organization_id=org_id,
            author_id=hr["user_id"],
            data={
                "question_text": "How does the ASGI lifespan protocol handle shutdown signals?",
                "response_format": "SINGLE_SELECT",
                "competency": "ARCHITECTURE_REASONING",
                "difficulty": "ADVANCED",
                "skill_tags": ["ASGI", "Python"],
                "source_type": "REPOSITORY_BASED",
                "repository_id": repo_id,
                "options": [{"id": "A", "text": "Via lifespan.shutdown event"}, {"id": "B", "text": "Via SIGKILL"}],
                "answer_key": ["A"],
                "explanation": "ASGI lifespan events coordinate startup and graceful shutdown."
            }
        )

        matrix_res = self.client.get(
            f"/api/hr/repositories/{repo_id}/coverage?organization_id={org_id}",
            headers=headers
        )
        self.assertEqual(matrix_res.status_code, 200)
        data = matrix_res.json()["coverage"]
        self.assertIn("by_competency", data)
        self.assertEqual(data["totals"]["total_questions"], 1)
        self.assertEqual(data["by_competency"]["ARCHITECTURE_REASONING"]["total"], 1)


if __name__ == "__main__":
    unittest.main()
