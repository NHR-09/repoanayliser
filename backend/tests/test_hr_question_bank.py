import unittest
import os
import uuid
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from main import app
from src.config import settings
from src.db.connection import get_db_connection, init_db
from src.security import hash_password, create_session

class TestHRQuestionBank(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create an isolated test SQLite DB
        cls.test_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        cls.test_db_path = cls.test_db_file.name
        cls.test_db_file.close()

        cls.orig_db_path = settings.db_path
        settings.db_path = cls.test_db_path
        os.environ["DATABASE_PATH"] = cls.test_db_path

        init_db(cls.test_db_path)
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        settings.db_path = cls.orig_db_path
        if os.path.exists(cls.test_db_path):
            try:
                os.remove(cls.test_db_path)
            except Exception:
                pass

    def setUp(self):
        # Seed test organizations and users
        self.org_a_id = f"org_a_{uuid.uuid4().hex[:6]}"
        self.org_b_id = f"org_b_{uuid.uuid4().hex[:6]}"

        self.hr_a_id = f"user_hr_a_{uuid.uuid4().hex[:6]}"
        self.hr_b_id = f"user_hr_b_{uuid.uuid4().hex[:6]}"
        self.candidate_id = f"user_cand_{uuid.uuid4().hex[:6]}"

        password_hash = hash_password("ValidPass123!@#")

        with get_db_connection(self.test_db_path) as conn:
            # Create Org A and Org B
            conn.execute("INSERT INTO organizations (id, name, slug) VALUES (?, 'Org Alpha', ?)", (self.org_a_id, f"slug_{self.org_a_id}"))
            conn.execute("INSERT INTO organizations (id, name, slug) VALUES (?, 'Org Beta', ?)", (self.org_b_id, f"slug_{self.org_b_id}"))

            # Create HR User A (belongs to Org A)
            conn.execute(
                "INSERT INTO users (id, email, password_hash, full_name, role) VALUES (?, ?, ?, 'HR Alice', 'HR')",
                (self.hr_a_id, f"{self.hr_a_id}@org-a.com", password_hash)
            )
            conn.execute(
                "INSERT INTO organization_memberships (id, organization_id, user_id, org_role) VALUES (?, ?, ?, 'OWNER')",
                (str(uuid.uuid4()), self.org_a_id, self.hr_a_id)
            )

            # Create HR User B (belongs to Org B)
            conn.execute(
                "INSERT INTO users (id, email, password_hash, full_name, role) VALUES (?, ?, ?, 'HR Bob', 'HR')",
                (self.hr_b_id, f"{self.hr_b_id}@org-b.com", password_hash)
            )
            conn.execute(
                "INSERT INTO organization_memberships (id, organization_id, user_id, org_role) VALUES (?, ?, ?, 'OWNER')",
                (str(uuid.uuid4()), self.org_b_id, self.hr_b_id)
            )

            # Create Candidate (USER role, no HR organization membership)
            conn.execute(
                "INSERT INTO users (id, email, password_hash, full_name, role) VALUES (?, ?, ?, 'Candidate Dan', 'USER')",
                (self.candidate_id, f"{self.candidate_id}@example.com", password_hash)
            )

        # Create active sessions
        sess_hr_a = create_session(user_id=self.hr_a_id, db_path=self.test_db_path)
        self.token_hr_a = sess_hr_a["token"]
        self.csrf_hr_a = sess_hr_a["csrf_token"]
        self.headers_hr_a = {
            "Authorization": f"Bearer {self.token_hr_a}",
            "X-CSRF-Token": self.csrf_hr_a
        }

        sess_hr_b = create_session(user_id=self.hr_b_id, db_path=self.test_db_path)
        self.token_hr_b = sess_hr_b["token"]
        self.csrf_hr_b = sess_hr_b["csrf_token"]
        self.headers_hr_b = {
            "Authorization": f"Bearer {self.token_hr_b}",
            "X-CSRF-Token": self.csrf_hr_b
        }

        sess_cand = create_session(user_id=self.candidate_id, db_path=self.test_db_path)
        self.token_cand = sess_cand["token"]
        self.csrf_cand = sess_cand["csrf_token"]
        self.headers_cand = {
            "Authorization": f"Bearer {self.token_cand}",
            "X-CSRF-Token": self.csrf_cand
        }

    # =========================================================
    # 1. RBAC & Security Checks
    # =========================================================

    def test_unauthenticated_requests_are_rejected(self):
        res = self.client.get(f"/api/hr/questions?organization_id={self.org_a_id}")
        self.assertEqual(res.status_code, 401)

    def test_candidate_cannot_access_hr_endpoints(self):
        res = self.client.get(f"/api/hr/questions?organization_id={self.org_a_id}", headers=self.headers_cand)
        self.assertEqual(res.status_code, 403)
        self.assertIn("HR access required", res.json()["detail"])

    def test_hr_user_cannot_access_other_organization(self):
        # HR A attempts to access Org B
        res = self.client.get(f"/api/hr/questions?organization_id={self.org_b_id}", headers=self.headers_hr_a)
        self.assertEqual(res.status_code, 403)
        self.assertIn("Access denied", res.json()["detail"])

    # =========================================================
    # 2. Manual Question Authoring & Validation
    # =========================================================

    def test_create_valid_single_select_question(self):
        payload = {
            "organization_id": self.org_a_id,
            "question_text": "What is the primary architectural purpose of a reverse proxy in microservices?",
            "competency": "ARCHITECTURE_REASONING",
            "difficulty": "INTERMEDIATE",
            "response_format": "SINGLE_SELECT",
            "skill_tags": ["Microservices", "Networking", "Architecture"],
            "options": [
                {"key": "A", "text": "To compile TypeScript code ahead of time."},
                {"key": "B", "text": "To provide centralized load balancing, SSL termination, and routing."},
                {"key": "C", "text": "To manage physical hard drive sectors directly."},
                {"key": "D", "text": "To serialize SQL records to XML."}
            ],
            "answer_key": ["B"],
            "explanation": "A reverse proxy fronts backend microservices to coordinate traffic, terminate SSL, and enforce routing rules."
        }
        res = self.client.post("/api/hr/questions", json=payload, headers=self.headers_hr_a)
        self.assertEqual(res.status_code, 201)
        data = res.json()["question"]
        self.assertEqual(data["review_status"], "NEEDS_REVIEW")
        self.assertEqual(data["validation_status"], "VALIDATED")
        self.assertEqual(data["version"], 1)
        self.assertEqual(data["organization_id"], self.org_a_id)

    def test_reject_single_select_with_multiple_answers(self):
        payload = {
            "organization_id": self.org_a_id,
            "question_text": "Which design pattern is used for publish-subscribe event systems in web apps?",
            "competency": "ARCHITECTURE_REASONING",
            "difficulty": "BEGINNER",
            "response_format": "SINGLE_SELECT",
            "skill_tags": ["Patterns"],
            "options": [
                {"key": "A", "text": "Observer pattern"},
                {"key": "B", "text": "PubSub broker pattern"},
                {"key": "C", "text": "Singleton pattern"}
            ],
            "answer_key": ["A", "B"],  # Invalid for SINGLE_SELECT!
            "explanation": "Multiple answers are strictly invalid for single select questions."
        }
        res = self.client.post("/api/hr/questions", json=payload, headers=self.headers_hr_a)
        self.assertEqual(res.status_code, 400)
        self.assertIn("exactly one keyed answer", res.json()["detail"])

    def test_reject_nonexistent_answer_key_reference(self):
        payload = {
            "organization_id": self.org_a_id,
            "question_text": "How do database indexes improve query execution speed for indexed columns?",
            "competency": "CODE_COMPREHENSION",
            "difficulty": "BEGINNER",
            "response_format": "SINGLE_SELECT",
            "skill_tags": ["Databases"],
            "options": [
                {"key": "A", "text": "By executing a sequential scan across all blocks."},
                {"key": "B", "text": "By storing sorted references via B-tree or Hash structures."}
            ],
            "answer_key": ["Z"],  # 'Z' does not exist in options!
            "explanation": "Invalid reference explanation."
        }
        res = self.client.post("/api/hr/questions", json=payload, headers=self.headers_hr_a)
        self.assertEqual(res.status_code, 400)
        self.assertIn("does not match any available option", res.json()["detail"])

    def test_reject_duplicate_option_keys(self):
        payload = {
            "organization_id": self.org_a_id,
            "question_text": "Which HTTP status code signifies that a resource was successfully created?",
            "competency": "CODE_COMPREHENSION",
            "difficulty": "BEGINNER",
            "response_format": "SINGLE_SELECT",
            "skill_tags": ["REST"],
            "options": [
                {"key": "A", "text": "200 OK"},
                {"key": "A", "text": "201 Created"}  # Duplicate key 'A'!
            ],
            "answer_key": ["A"],
            "explanation": "201 Created is the standard response."
        }
        res = self.client.post("/api/hr/questions", json=payload, headers=self.headers_hr_a)
        self.assertEqual(res.status_code, 400)
        self.assertIn("Duplicate option key", res.json()["detail"])

    # =========================================================
    # 3. Question Lifecycle, Versioning & Historical Immutability
    # =========================================================

    def test_question_editing_and_versioning_lifecycle(self):
        # 1. Create Question in Org A
        create_payload = {
            "organization_id": self.org_a_id,
            "question_text": "What is the primary benefit of dependency injection in modular architectures?",
            "competency": "ARCHITECTURE_REASONING",
            "difficulty": "INTERMEDIATE",
            "response_format": "SINGLE_SELECT",
            "skill_tags": ["Architecture", "Testing"],
            "options": [
                {"key": "A", "text": "Decreases testability by coupling components."},
                {"key": "B", "text": "Decouples component creation from usage, facilitating mock injection."},
                {"key": "C", "text": "Forces all methods to execute synchronously."}
            ],
            "answer_key": ["B"],
            "explanation": "DI decouples object construction from consumption, allowing mock injection during unit tests."
        }
        res = self.client.post("/api/hr/questions", json=create_payload, headers=self.headers_hr_a)
        self.assertEqual(res.status_code, 201)
        q_id = res.json()["question"]["id"]
        self.assertEqual(res.json()["question"]["version"], 1)
        self.assertEqual(res.json()["question"]["review_status"], "NEEDS_REVIEW")

        # 2. Update while in NEEDS_REVIEW (draft update in-place)
        update_payload = {
            "question_text": "What is the primary benefit of dependency injection in modular software architectures?",
            "explanation": "Updated explanation."
        }
        res_update = self.client.put(f"/api/hr/questions/{q_id}?organization_id={self.org_a_id}", json=update_payload, headers=self.headers_hr_a)
        self.assertEqual(res_update.status_code, 200)
        self.assertEqual(res_update.json()["question"]["version"], 1)

        # 3. Approve Question
        res_appr = self.client.post(f"/api/hr/questions/{q_id}/approval", json={
            "organization_id": self.org_a_id,
            "action": "APPROVE",
            "reviewer_notes": "Meets architectural testing standards."
        }, headers=self.headers_hr_a)
        self.assertEqual(res_appr.status_code, 200)
        self.assertEqual(res_appr.json()["question"]["review_status"], "APPROVED")

        # 4. Publish Question
        res_pub = self.client.post(f"/api/hr/questions/{q_id}/approval", json={
            "organization_id": self.org_a_id,
            "action": "PUBLISH"
        }, headers=self.headers_hr_a)
        self.assertEqual(res_pub.status_code, 200)
        self.assertEqual(res_pub.json()["question"]["review_status"], "PUBLISHED")

        # 5. Editing a PUBLISHED question MUST increment version to 2 and reset review_status to NEEDS_REVIEW
        res_edit_pub = self.client.put(f"/api/hr/questions/{q_id}?organization_id={self.org_a_id}", json={
            "question_text": "In clean architecture, what is the core benefit of dependency inversion/injection?",
            "difficulty": "ADVANCED"
        }, headers=self.headers_hr_a)
        self.assertEqual(res_edit_pub.status_code, 200)
        updated_q = res_edit_pub.json()["question"]
        self.assertEqual(updated_q["version"], 2)
        self.assertEqual(updated_q["review_status"], "NEEDS_REVIEW")

        # 6. Check Version History: must have immutable records for both v1 and v2
        res_hist = self.client.get(f"/api/hr/questions/{q_id}/versions?organization_id={self.org_a_id}", headers=self.headers_hr_a)
        self.assertEqual(res_hist.status_code, 200)
        hist = res_hist.json()
        self.assertEqual(hist["total_versions"], 2)
        versions = [v["version"] for v in hist["versions"]]
        self.assertIn(1, versions)
        self.assertIn(2, versions)

        # 7. Candidate-style preview redacts answer key & explanation
        res_prev = self.client.get(f"/api/hr/questions/{q_id}/preview?organization_id={self.org_a_id}", headers=self.headers_hr_a)
        self.assertEqual(res_prev.status_code, 200)
        prev = res_prev.json()["preview"]
        self.assertIn("question_text", prev)
        self.assertNotIn("answer_key", prev)
        self.assertNotIn("explanation", prev)
        # Check that options do not have is_correct or answer indicators
        for opt in prev["options"]:
            self.assertNotIn("is_correct", opt)

    def test_cross_organization_question_access_prevented(self):
        # Create Question in Org A
        create_payload = {
            "organization_id": self.org_a_id,
            "question_text": "Confidential question belonging to Organization Alpha exclusively.",
            "competency": "DEBUGGING",
            "difficulty": "INTERMEDIATE",
            "response_format": "TRUE_FALSE",
            "skill_tags": ["Security"],
            "options": [
                {"key": "true", "text": "True"},
                {"key": "false", "text": "False"}
            ],
            "answer_key": ["true"],
            "explanation": "Exclusively for Org A."
        }
        res = self.client.post("/api/hr/questions", json=create_payload, headers=self.headers_hr_a)
        self.assertEqual(res.status_code, 201)
        q_id = res.json()["question"]["id"]

        # HR B tries to retrieve Org A's question
        res_leak = self.client.get(f"/api/hr/questions/{q_id}?organization_id={self.org_b_id}", headers=self.headers_hr_b)
        self.assertEqual(res_leak.status_code, 404)

        # HR B tries to approve Org A's question
        res_appr_leak = self.client.post(f"/api/hr/questions/{q_id}/approval", json={
            "organization_id": self.org_b_id,
            "action": "APPROVE"
        }, headers=self.headers_hr_b)
        self.assertEqual(res_appr_leak.status_code, 404)

    # =========================================================
    # 4. Repository Library Registration, Approval & Coverage
    # =========================================================

    @patch("src.services.candidate_repo_service.CandidateRepositoryService.run_repository_analysis_task")
    def test_repository_library_registration_and_ssrf_protection(self, mock_analysis):
        # 1. SSRF Protection: Reject private/local IPs
        res_ssrf = self.client.post("/api/hr/repositories", json={
            "organization_id": self.org_a_id,
            "repo_url": "https://127.0.0.1/internal",
            "display_name": "Localhost exploit"
        }, headers=self.headers_hr_a)
        self.assertEqual(res_ssrf.status_code, 400)
        self.assertIn("Only official 'github.com' repositories", res_ssrf.json()["detail"])

        # 2. Valid GitHub repository registration
        valid_repo_url = "https://github.com/facebook/react"
        res_reg = self.client.post("/api/hr/repositories", json={
            "organization_id": self.org_a_id,
            "repo_url": valid_repo_url,
            "display_name": "React Frontend Core",
            "description": "Approved UI library for technical assessment",
            "intended_evaluations": "Frontend component comprehension"
        }, headers=self.headers_hr_a)
        self.assertEqual(res_reg.status_code, 201)
        repo_data = res_reg.json()["repository"]
        repo_id = repo_data["id"]
        self.assertEqual(repo_data["approval_status"], "REGISTERED")
        self.assertEqual(repo_data["display_name"], "React Frontend Core")

        # 3. Attempt to approve unanalyzed repository must be rejected
        res_early_appr = self.client.post(f"/api/hr/repositories/{repo_id}/approval", json={
            "organization_id": self.org_a_id,
            "action": "APPROVE"
        }, headers=self.headers_hr_a)
        self.assertEqual(res_early_appr.status_code, 400)
        self.assertIn("Cannot approve repository", res_early_appr.json()["detail"])

        # 4. Simulate analysis completion in DB
        with get_db_connection(self.test_db_path) as conn:
            conn.execute(
                "UPDATE repositories SET analysis_status = 'COMPLETED', last_analyzed_commit = 'abc1234' WHERE id = ?",
                (repo_id,)
            )

        # 5. Now approve repository
        res_appr = self.client.post(f"/api/hr/repositories/{repo_id}/approval", json={
            "organization_id": self.org_a_id,
            "action": "APPROVE",
            "intended_evaluations": "Verified codebase for assessment"
        }, headers=self.headers_hr_a)
        self.assertEqual(res_appr.status_code, 200)
        self.assertEqual(res_appr.json()["repository"]["approval_status"], "APPROVED")

        # 6. Add questions linked to this repository and verify question coverage calculation
        with get_db_connection(self.test_db_path) as conn:
            q_id1 = str(uuid.uuid4())
            conn.execute("""
                INSERT INTO questions (
                    id, organization_id, created_by, source_type, repository_id,
                    skill_tags, competency, response_format, difficulty,
                    question_text, options, answer_key, explanation,
                    validation_status, review_status
                ) VALUES (?, ?, ?, 'REPOSITORY_BASED', ?, '["React"]', 'CODE_COMPREHENSION', 'SINGLE_SELECT', 'INTERMEDIATE', 'React Q1', '[]', '[]', '', 'VALIDATED', 'APPROVED')
            """, (q_id1, self.org_a_id, self.hr_a_id, repo_id))

        res_cov = self.client.get(f"/api/hr/repositories/{repo_id}/coverage?organization_id={self.org_a_id}", headers=self.headers_hr_a)
        self.assertEqual(res_cov.status_code, 200)
        cov = res_cov.json()["coverage"]
        self.assertEqual(cov["totals"]["total_questions"], 1)
        self.assertEqual(cov["totals"]["approved"], 1)
        self.assertEqual(cov["by_competency"]["CODE_COMPREHENSION"]["total"], 1)
        self.assertIn("DEPENDENCY_TRACING", cov["coverage_gaps"])

    # =========================================================
    # 5. AI Question Generation Integration
    # =========================================================

    @patch("src.services.question_generation_service.QuestionGenerationService.generate_quiz_questions")
    def test_hr_question_generation_defaults_to_needs_review(self, mock_gen):
        mock_gen.return_value = ([
            {
                "question_text": "What is the time complexity of searching a binary search tree in the worst case?",
                "response_format": "SINGLE_SELECT",
                "competency": "CODE_COMPREHENSION",
                "difficulty": "INTERMEDIATE",
                "skill_tags": ["Data Structures", "Algorithms"],
                "options": [
                    {"key": "A", "text": "O(1)"},
                    {"key": "B", "text": "O(log n)"},
                    {"key": "C", "text": "O(n)"},
                    {"key": "D", "text": "O(n^2)"}
                ],
                "answer_key": ["C"],
                "explanation": "In an unbalanced BST (skewed tree), lookup degrades to O(n).",
                "evidence_references": []
            }
        ], "Generated 1 validated question from algorithm templates.")

        gen_payload = {
            "organization_id": self.org_a_id,
            "mode": "SKILL_BASED",
            "skill_name": "Data Structures",
            "difficulty": "INTERMEDIATE",
            "requested_count": 1
        }
        res = self.client.post("/api/hr/questions/generate", json=gen_payload, headers=self.headers_hr_a)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["generated_count"], 1)
        created_q = data["questions"][0]
        # Generated questions MUST be in NEEDS_REVIEW
        self.assertEqual(created_q["review_status"], "NEEDS_REVIEW")
        self.assertEqual(created_q["validation_status"], "VALIDATED")
        self.assertEqual(created_q["version"], 1)

if __name__ == "__main__":
    unittest.main()
