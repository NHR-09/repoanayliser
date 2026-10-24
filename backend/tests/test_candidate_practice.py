import unittest
import os
import io
import json
import uuid
import tempfile
from pathlib import Path
import docx
import pypdf
from fastapi.testclient import TestClient

from main import app
from src.config import settings
from src.db.connection import get_db_connection, init_db
from src.services.resume_service import ResumeService
from src.services.skill_extraction_service import SkillExtractionService
from src.services.candidate_repo_service import CandidateRepositoryService
from src.services.question_generation_service import QuestionGenerationService
from src.services.practice_service import PracticeService

class TestCandidatePractice(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Use an isolated test database
        cls.test_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        cls.test_db_path = cls.test_db_file.name
        cls.test_db_file.close()

        cls.storage_temp_dir = tempfile.TemporaryDirectory()
        cls.storage_dir = Path(cls.storage_temp_dir.name)

        cls.orig_db_path = settings.db_path
        settings.db_path = cls.test_db_path
        os.environ["DATABASE_PATH"] = cls.test_db_path
        os.environ["RESUME_STORAGE_DIR"] = str(cls.storage_dir)

        init_db(cls.test_db_path)
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        settings.db_path = cls.orig_db_path
        cls.storage_temp_dir.cleanup()
        if os.path.exists(cls.test_db_path):
            try:
                os.remove(cls.test_db_path)
            except Exception:
                pass

    def setUp(self):
        # Create candidate User A
        self.user_a_email = f"candidate_a_{uuid.uuid4().hex[:6]}@example.com"
        self.user_a_password = "Password123!@#"
        reg_a = self.client.post("/api/auth/register", json={
            "email": self.user_a_email,
            "password": self.user_a_password,
            "full_name": "Candidate Alice"
        })
        self.assertEqual(reg_a.status_code, 201)
        self.user_a_token = reg_a.json()["token"]
        self.user_a_csrf = reg_a.json()["csrf_token"]
        self.user_a_id = reg_a.json()["user"]["id"]
        self.user_a_headers = {
            "Authorization": f"Bearer {self.user_a_token}",
            "X-CSRF-Token": self.user_a_csrf
        }

        # Create candidate User B for isolation testing
        self.user_b_email = f"candidate_b_{uuid.uuid4().hex[:6]}@example.com"
        self.user_b_password = "Password123!@#"
        reg_b = self.client.post("/api/auth/register", json={
            "email": self.user_b_email,
            "password": self.user_b_password,
            "full_name": "Candidate Bob"
        })
        self.assertEqual(reg_b.status_code, 201)
        self.user_b_token = reg_b.json()["token"]
        self.user_b_csrf = reg_b.json()["csrf_token"]
        self.user_b_id = reg_b.json()["user"]["id"]
        self.user_b_headers = {
            "Authorization": f"Bearer {self.user_b_token}",
            "X-CSRF-Token": self.user_b_csrf
        }

    # =========================================================
    # 1. Resume Upload & Extraction Tests
    # =========================================================

    def _create_dummy_pdf(self, text: str) -> bytes:
        writer = pypdf.PdfWriter()
        writer.add_blank_page(width=72, height=72)
        # We can write an empty page and add text metadata or create a minimal stream
        # Or write simple text with pypdf annotations
        buf = io.BytesIO()
        writer.write(buf)
        raw = buf.getvalue()
        # Ensure starts with %PDF-
        return raw

    def _create_dummy_docx(self, text: str) -> bytes:
        doc = docx.Document()
        doc.add_heading("Technical Resume", 0)
        doc.add_paragraph(text)
        buf = io.BytesIO()
        doc.save(buf)
        return buf.getvalue()

    def test_resume_txt_upload_and_extraction(self):
        """Test uploading valid plain-text resume and skill extraction."""
        resume_content = (
            "Senior Backend Engineer with 5 years of experience in Python, FastAPI, and PostgreSQL. "
            "Designed microservices deployed on Docker and AWS. GitHub: https://github.com/alice/backend-api."
        ).encode("utf-8")

        response = self.client.post(
            "/api/candidate/resume/upload",
            files={"file": ("resume.txt", io.BytesIO(resume_content), "text/plain")},
            headers=self.user_a_headers
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIn("resume", data)
        self.assertEqual(data["resume"]["filename"], "resume.txt")
        self.assertIn("extracted_skills", data)
        self.assertTrue(len(data["extracted_skills"]) > 0)

        # Check skills in DB
        skills_resp = self.client.get("/api/candidate/skills", headers=self.user_a_headers)
        self.assertEqual(skills_resp.status_code, 200)
        skill_names = [s["skill_name"] for s in skills_resp.json()["skills"]]
        self.assertTrue(any("Python" in s or "FastAPI" in s for s in skill_names))

    def test_resume_docx_upload(self):
        """Test uploading valid DOCX document."""
        docx_bytes = self._create_dummy_docx(
            "Experienced React and TypeScript frontend developer with deep knowledge of Redux and Tailwind CSS."
        )
        response = self.client.post(
            "/api/candidate/resume/upload",
            files={"file": ("resume.docx", io.BytesIO(docx_bytes), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            headers=self.user_a_headers
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["resume"]["filename"], "resume.docx")

    def test_resume_rejects_unsupported_extensions(self):
        """Test that non-whitelisted formats (e.g. .exe, .sh, .py) are rejected."""
        fake_binary = b"MZ\x90\x00\x03\x00\x00\x00"
        response = self.client.post(
            "/api/candidate/resume/upload",
            files={"file": ("malware.exe", io.BytesIO(fake_binary), "application/octet-stream")},
            headers=self.user_a_headers
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Unsupported file format", response.json()["detail"])

    def test_resume_rejects_oversized_files(self):
        """Test rejection of resumes exceeding 10MB."""
        service = ResumeService()
        huge_bytes = b"X" * (11 * 1024 * 1024)
        with self.assertRaises(ValueError) as ctx:
            service.validate_file("huge.txt", huge_bytes)
        self.assertIn("exceeds maximum allowed limit", str(ctx.exception))

    def test_resume_and_skills_user_isolation(self):
        """Test that User B cannot view or delete User A's resume or skills."""
        # User A uploads resume
        resume_content = "Specialist in Go, Kubernetes, and gRPC distributed systems.".encode("utf-8")
        upload_a = self.client.post(
            "/api/candidate/resume/upload",
            files={"file": ("alice_cv.txt", io.BytesIO(resume_content), "text/plain")},
            headers=self.user_a_headers
        )
        self.assertEqual(upload_a.status_code, 201)

        # User B queries their resume -> should be empty
        resp_b = self.client.get("/api/candidate/resume", headers=self.user_b_headers)
        self.assertEqual(resp_b.status_code, 200)
        self.assertIsNone(resp_b.json()["resume"])

        # User B queries skills -> should have 0 skills
        skills_b = self.client.get("/api/candidate/skills", headers=self.user_b_headers)
        self.assertEqual(skills_b.status_code, 200)
        self.assertEqual(len(skills_b.json()["skills"]), 0)

        # User A deletes their resume
        del_a = self.client.delete("/api/candidate/resume", headers=self.user_a_headers)
        self.assertEqual(del_a.status_code, 200)
        self.assertTrue(del_a.json()["deleted"])

    # =========================================================
    # 2. Editable Review CRUD & Provenance
    # =========================================================

    def test_manual_skill_crud_and_provenance(self):
        """Test adding, editing, and deleting manual skills while distinguishing RESUME vs MANUAL."""
        # 1. Add manual skill
        add_resp = self.client.post("/api/candidate/skills", json={
            "skill_name": "Apache Kafka",
            "category": "TOOL",
            "evidence_text": "Built high-throughput event streaming pipelines"
        }, headers=self.user_a_headers)
        self.assertEqual(add_resp.status_code, 201)
        skill = add_resp.json()["skill"]
        self.assertEqual(skill["skill_name"], "Apache Kafka")
        self.assertEqual(skill["source"], "MANUAL")
        skill_id = skill["id"]

        # 2. Edit skill
        edit_resp = self.client.put(f"/api/candidate/skills/{skill_id}", json={
            "category": "ARCHITECTURE",
            "evidence_text": "Updated architectural event-driven stream processing"
        }, headers=self.user_a_headers)
        self.assertEqual(edit_resp.status_code, 200)
        self.assertEqual(edit_resp.json()["skill"]["category"], "ARCHITECTURE")

        # 3. User B cannot edit User A's skill
        b_edit = self.client.put(f"/api/candidate/skills/{skill_id}", json={
            "skill_name": "Hacked Skill"
        }, headers=self.user_b_headers)
        self.assertEqual(b_edit.status_code, 404)

        # 4. Delete skill
        del_resp = self.client.delete(f"/api/candidate/skills/{skill_id}", headers=self.user_a_headers)
        self.assertEqual(del_resp.status_code, 200)

    # =========================================================
    # 3. GitHub Repository Validation & Security
    # =========================================================

    def test_github_url_validation_and_ssrf_prevention(self):
        """Test URL validation rejects SSRF targets, localhost, credentials, and non-github hosts."""
        service = CandidateRepositoryService()

        # Valid public GitHub URL
        valid = service.validate_github_url("https://github.com/torvalds/linux")
        self.assertEqual(valid["owner"], "torvalds")
        self.assertEqual(valid["repo_name"], "linux")

        # Insecure scheme (http)
        with self.assertRaises(ValueError):
            service.validate_github_url("http://github.com/user/repo")

        # Embedded credentials
        with self.assertRaises(ValueError):
            service.validate_github_url("https://user:pass@github.com/user/repo")

        # Non-standard port
        with self.assertRaises(ValueError):
            service.validate_github_url("https://github.com:8080/user/repo")

        # Non-github host / SSRF
        with self.assertRaises(ValueError):
            service.validate_github_url("https://169.254.169.254/user/repo")
        with self.assertRaises(ValueError):
            service.validate_github_url("https://localhost/user/repo")
        with self.assertRaises(ValueError):
            service.validate_github_url("https://gitlab.com/user/repo")

    from unittest.mock import patch

    @patch("src.api.practice.repo_service.run_repository_analysis_task")
    def test_repository_registration_and_access(self, mock_run_analysis):
        """Test registering repository creates entry and restricts access across users."""
        reg_resp = self.client.post("/api/candidate/repositories", json={
            "repo_url": "https://github.com/architech/demo-repo",
            "display_name": "Demo Repo"
        }, headers=self.user_a_headers)
        self.assertEqual(reg_resp.status_code, 201)
        repo_id = reg_resp.json()["repository"]["id"]

        # Check status
        status_resp = self.client.get(f"/api/candidate/repositories/{repo_id}/status", headers=self.user_a_headers)
        self.assertEqual(status_resp.status_code, 200)
        self.assertEqual(status_resp.json()["display_name"], "Demo Repo")

        # User B cannot access status
        b_status = self.client.get(f"/api/candidate/repositories/{repo_id}/status", headers=self.user_b_headers)
        self.assertEqual(b_status.status_code, 403)

    # =========================================================
    # 4. Question Quality Validation & Redaction
    # =========================================================

    def test_question_quality_validation(self):
        """Verify strict question schema, option counts, and answer key consistency."""
        gen_service = QuestionGenerationService()

        # 1. Valid Single-Select
        valid_ss = {
            "question_text": "What does a database index primarily optimize in relational systems?",
            "response_format": "SINGLE_SELECT",
            "options": [
                {"id": "A", "text": "Storage capacity on spinning hard disks"},
                {"id": "B", "text": "Read query lookup speed at the cost of additional write overhead"},
                {"id": "C", "text": "Network bandwidth between client and server"},
                {"id": "D", "text": "Cryptographic key exchange latency"}
            ],
            "answer_key": ["B"],
            "explanation": "Indexes create auxiliary search structures (e.g. B-Trees) accelerating reads while requiring writes to keep updated."
        }
        ok, reason = gen_service._validate_question_quality(valid_ss, "SKILL_BASED", None)
        self.assertTrue(ok, f"Validation failed: {reason}")

        # 2. Reject SINGLE_SELECT with multiple answers
        invalid_ss = dict(valid_ss)
        invalid_ss["answer_key"] = ["A", "B"]
        ok, reason = gen_service._validate_question_quality(invalid_ss, "SKILL_BASED", None)
        self.assertFalse(ok)
        self.assertIn("exactly 1 correct answer", reason)

        # 3. Reject with duplicate options
        invalid_dup = dict(valid_ss)
        invalid_dup["options"] = [
            {"id": "A", "text": "Same text"},
            {"id": "B", "text": "Same text"},
            {"id": "C", "text": "Different"},
            {"id": "D", "text": "Another"}
        ]
        ok, reason = gen_service._validate_question_quality(invalid_dup, "SKILL_BASED", None)
        self.assertFalse(ok)
        self.assertIn("Duplicate option content", reason)

        # 4. Reject answer key not in options
        invalid_key = dict(valid_ss)
        invalid_key["answer_key"] = ["Z"]
        ok, reason = gen_service._validate_question_quality(invalid_key, "SKILL_BASED", None)
        self.assertFalse(ok)
        self.assertIn("does not exist in options", reason)

    def test_candidate_question_serialization_redacts_answer_key(self):
        """CRITICAL SECURITY: Verify answer_key and explanation are completely redacted from candidate."""
        q = {
            "id": "q-123",
            "question_text": "What is Neo4j?",
            "response_format": "SINGLE_SELECT",
            "competency": "ARCHITECTURE_REASONING",
            "difficulty": "BEGINNER",
            "source_type": "SKILL_BASED",
            "skill_tags": ["Neo4j"],
            "options": [
                {"id": "A", "text": "Graph database"},
                {"id": "B", "text": "Relational DB"},
                {"id": "C", "text": "Key-value store"},
                {"id": "D", "text": "CSS compiler"}
            ],
            "answer_key": ["A"],
            "explanation": "Neo4j is an ACID-compliant graph database storing nodes and relationships natively.",
            "evidence_references": [{"file_path": "graph_db.py", "entity_name": "GraphDB"}]
        }
        serialized = QuestionGenerationService.serialize_for_candidate(q)
        self.assertNotIn("answer_key", serialized)
        self.assertNotIn("explanation", serialized)
        self.assertEqual(serialized["id"], "q-123")
        self.assertEqual(len(serialized["options"]), 4)

    # =========================================================
    # 5. Practice Quiz Execution & Objective Scoring
    # =========================================================

    def test_practice_quiz_full_flow_and_scoring(self):
        """
        Test end-to-end quiz flow:
        1. Generate skill quiz
        2. Verify candidate questions lack answer keys
        3. Submit answers (Single-select, multi-select, true-false)
        4. Validate objective scoring & partial credit
        5. Verify results and history persistence
        """
        # 1. Generate quiz
        gen_resp = self.client.post("/api/candidate/practice/generate", json={
            "mode": "SKILL_BASED",
            "skill_name": "Python",
            "difficulty": "INTERMEDIATE",
            "competencies": ["CODE_COMPREHENSION", "DEPENDENCY_TRACING"],
            "question_count": 3
        }, headers=self.user_a_headers)
        self.assertEqual(gen_resp.status_code, 201)
        quiz_data = gen_resp.json()
        quiz_id = quiz_data["quiz_id"]
        questions = quiz_data["questions"]
        self.assertTrue(len(questions) >= 1)

        # 2. Check candidate active quiz - answer_key must NOT be exposed
        get_active = self.client.get(f"/api/candidate/practice/quiz/{quiz_id}", headers=self.user_a_headers)
        self.assertEqual(get_active.status_code, 200)
        active_q = get_active.json()["quiz"]["questions"][0]
        self.assertNotIn("answer_key", active_q)
        self.assertNotIn("explanation", active_q)

        # 3. Look up actual answer keys from database to test scoring
        answers_payload = {}
        with get_db_connection(self.test_db_path) as conn:
            for q in questions:
                row = conn.execute("SELECT answer_key, response_format FROM questions WHERE id = ?", (q["id"],)).fetchone()
                keys = json.loads(row["answer_key"])
                # Submit correct answer for first question
                answers_payload[q["id"]] = keys

        # 4. Submit answers
        sub_resp = self.client.post(
            f"/api/candidate/practice/quiz/{quiz_id}/submit",
            json={"answers": answers_payload},
            headers=self.user_a_headers
        )
        self.assertEqual(sub_resp.status_code, 200)
        results = sub_resp.json()["results"]
        self.assertEqual(results["status"], "COMPLETED")
        self.assertEqual(results["total_score"], results["max_score"])
        self.assertEqual(results["percentage_score"], 100.0)

        # Now explanations and answer_key ARE revealed after submission
        self.assertIn("explanation", results["questions"][0])
        self.assertIn("answer_key", results["questions"][0])

        # 5. Check practice history
        hist_resp = self.client.get("/api/candidate/practice/history", headers=self.user_a_headers)
        self.assertEqual(hist_resp.status_code, 200)
        hist = hist_resp.json()
        self.assertEqual(hist["completed_quizzes_count"], 1)
        self.assertEqual(hist["average_score_pct"], 100.0)

        # 6. User B cannot view User A's quiz results
        b_get_quiz = self.client.get(f"/api/candidate/practice/quiz/{quiz_id}", headers=self.user_b_headers)
        self.assertEqual(b_get_quiz.status_code, 404)

if __name__ == "__main__":
    unittest.main()
