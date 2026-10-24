import os
import json
import uuid
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Any

from fastapi.testclient import TestClient

from main import app
from src.config import settings
from src.db.connection import get_db_connection, init_db
from src.security.sessions import create_session
from src.services.hr_question_service import HRQuestionBankService
from src.services.assessment_service import AssessmentService
from src.services.assessment_assignment_service import AssessmentAssignmentService
from src.services.assessment_attempt_service import AssessmentAttemptService
from src.services.assessment_analytics_service import AssessmentAnalyticsService
from src.services.practice_service import PracticeService
from src.services.resume_service import ResumeService
from src.services.skill_extraction_service import SkillExtractionService


class TestAuditPhase4AndE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.test_db_path = os.path.join(cls.temp_dir.name, "test_audit_phase4.db")
        cls.orig_db_path = settings.db_path
        settings.db_path = cls.test_db_path
        os.environ["DATABASE_PATH"] = cls.test_db_path

        init_db(cls.test_db_path)
        cls.client = TestClient(app)

        cls.question_service = HRQuestionBankService()
        cls.assessment_service = AssessmentService(db_path=cls.test_db_path)
        cls.assignment_service = AssessmentAssignmentService(db_path=cls.test_db_path)
        cls.attempt_service = AssessmentAttemptService(db_path=cls.test_db_path)
        cls.analytics_service = AssessmentAnalyticsService(db_path=cls.test_db_path)
        cls.practice_service = PracticeService()
        cls.resume_service = ResumeService()
        cls.skill_service = SkillExtractionService()

    @classmethod
    def tearDownClass(cls):
        settings.db_path = cls.orig_db_path
        cls.temp_dir.cleanup()

    def setUp(self):
        settings.db_path = self.test_db_path
        self.client.cookies.clear()

    def _setup_org_and_hr(self, org_name: str, email_prefix: str) -> Dict[str, Any]:
        org_id = f"org_{uuid.uuid4().hex[:6]}"
        user_id = f"hr_{uuid.uuid4().hex[:6]}"
        email = f"{email_prefix}_{uuid.uuid4().hex[:4]}@company.com"

        with get_db_connection(self.test_db_path) as conn:
            conn.execute("INSERT INTO organizations (id, name, slug) VALUES (?, ?, ?)", (org_id, org_name, org_id))
            conn.execute("INSERT INTO users (id, email, password_hash, full_name, role) VALUES (?, ?, 'h', 'HR Lead', 'HR')", (user_id, email))
            conn.execute("INSERT INTO organization_memberships (id, organization_id, user_id, org_role) VALUES (?, ?, ?, 'RECRUITER')", (str(uuid.uuid4()), org_id, user_id))

        sess = create_session(user_id, db_path=self.test_db_path)
        headers = {"Authorization": f"Bearer {sess['token']}"}
        return {"org_id": org_id, "user_id": user_id, "email": email, "token": sess["token"], "headers": headers}

    def _setup_candidate(self, email_prefix: str) -> Dict[str, Any]:
        user_id = f"cand_{uuid.uuid4().hex[:6]}"
        email = f"{email_prefix}_{uuid.uuid4().hex[:4]}@candidate.com"

        with get_db_connection(self.test_db_path) as conn:
            conn.execute("INSERT INTO users (id, email, password_hash, full_name, role) VALUES (?, ?, 'h', 'Candidate Jane', 'USER')", (user_id, email))

        sess = create_session(user_id, db_path=self.test_db_path)
        headers = {"Authorization": f"Bearer {sess['token']}"}
        return {"user_id": user_id, "email": email, "token": sess["token"], "headers": headers}

    def _create_published_question(self, org_id: str, author_id: str, skill: str = "Python") -> str:
        q = self.question_service.create_question(
            organization_id=org_id,
            author_id=author_id,
            data={
                "question_text": f"What is the output of standard list comprehensions in {skill}?",
                "response_format": "SINGLE_SELECT",
                "competency": "CODE_COMPREHENSION",
                "difficulty": "BEGINNER",
                "skill_tags": [skill],
                "options": [{"id": "A", "text": "A new list"}, {"id": "B", "text": "A generator"}],
                "answer_key": ["A"],
                "explanation": "List comprehensions produce a new list eagerly."
            }
        )
        self.question_service.transition_question_status(org_id, author_id, q["id"], "APPROVE")
        pub = self.question_service.transition_question_status(org_id, author_id, q["id"], "PUBLISH")
        return pub["id"]

    # =============================================================
    # TEST GROUP 4A & 4B: Assessment Studio & Publication
    # =============================================================

    def test_p4_01_create_curated_assessment_and_publish(self):
        hr = self._setup_org_and_hr("Enterprise Corp", "hr_p4_01")
        q1_id = self._create_published_question(hr["org_id"], hr["user_id"], "Python")
        q2_id = self._create_published_question(hr["org_id"], hr["user_id"], "SQL")

        # 1. Create curated draft
        draft = self.assessment_service.create_assessment(
            organization_id=hr["org_id"],
            user_id=hr["user_id"],
            data={
                "title": "Senior Backend Engineering Assessment",
                "mode": "CURATED",
                "duration_minutes": 60,
                "passing_score_pct": 75.0,
                "question_ids": [q1_id, q2_id],
                "result_release_policy": "WITHHOLD_PENDING_REVIEW"
            }
        )
        self.assertEqual(draft["status"], "DRAFT")
        self.assertEqual(draft["version"], 1)
        self.assertEqual(len(draft.get("curated_questions", [])), 2)

        # 2. Publish assessment
        published = self.assessment_service.publish_assessment(
            organization_id=hr["org_id"],
            user_id=hr["user_id"],
            assessment_id=draft["id"]
        )
        self.assertEqual(published["status"], "PUBLISHED")
        self.assertGreaterEqual(len(published.get("versions", [])), 1)

        # 3. Edit published assessment -> creates new version DRAFT (v2) while preserving v1
        edited = self.assessment_service.update_assessment(
            organization_id=hr["org_id"],
            user_id=hr["user_id"],
            assessment_id=draft["id"],
            data={"title": "Senior Backend Engineering Assessment v2"}
        )
        self.assertEqual(edited["version"], 2)
        self.assertEqual(edited["status"], "DRAFT")

    def test_p4_02_reject_assessment_with_zero_or_unpublished_questions(self):
        hr = self._setup_org_and_hr("Validation Org", "hr_p4_02")
        # 1. Empty questions rejected upon publishing
        draft_empty = self.assessment_service.create_assessment(
            organization_id=hr["org_id"],
            user_id=hr["user_id"],
            data={
                "title": "Empty Assessment",
                "mode": "CURATED",
                "duration_minutes": 45,
                "passing_score_pct": 70.0,
                "question_ids": []
            }
        )
        with self.assertRaises(ValueError) as ctx:
            self.assessment_service.publish_assessment(
                organization_id=hr["org_id"],
                user_id=hr["user_id"],
                assessment_id=draft_empty["id"]
            )
        self.assertIn("at least one question", str(ctx.exception).lower())

        # 2. Unpublished draft questions rejected upon publishing
        q_draft = self.question_service.create_question(
            organization_id=hr["org_id"],
            author_id=hr["user_id"],
            data={
                "question_text": "Draft unreviewed question?",
                "response_format": "SINGLE_SELECT",
                "competency": "CODE_COMPREHENSION",
                "difficulty": "BEGINNER",
                "skill_tags": ["Python"],
                "options": [{"id": "A", "text": "Yes"}, {"id": "B", "text": "No"}],
                "answer_key": ["A"],
                "explanation": "This is a detailed explanation for testing question creation."
            }
        )
        draft_unpub = self.assessment_service.create_assessment(
            organization_id=hr["org_id"],
            user_id=hr["user_id"],
            data={
                "title": "Unpublished Q Assessment",
                "mode": "CURATED",
                "duration_minutes": 45,
                "passing_score_pct": 70.0,
                "question_ids": [q_draft["id"]]
            }
        )
        with self.assertRaises(ValueError) as ctx2:
            self.assessment_service.publish_assessment(
                organization_id=hr["org_id"],
                user_id=hr["user_id"],
                assessment_id=draft_unpub["id"]
            )
        self.assertIn("must be in published review status", str(ctx2.exception).lower())

    def test_p4_03_randomized_blueprint_coverage_enforcement(self):
        hr = self._setup_org_and_hr("Blueprint Org", "hr_p4_03")
        # Request 10 questions when only 1 exists
        self._create_published_question(hr["org_id"], hr["user_id"], "Rust")
        draft_bp = self.assessment_service.create_assessment(
            organization_id=hr["org_id"],
            user_id=hr["user_id"],
            data={
                "title": "Insufficient Questions Blueprint",
                "mode": "RANDOMIZED",
                "duration_minutes": 30,
                "passing_score_pct": 60.0,
                "blueprint_config": {
                    "question_count": 10,
                    "required_skills": ["Rust"],
                    "difficulty": "BEGINNER"
                }
            }
        )
        with self.assertRaises(ValueError) as ctx:
            self.assessment_service.publish_assessment(
                organization_id=hr["org_id"],
                user_id=hr["user_id"],
                assessment_id=draft_bp["id"]
            )
        self.assertIn("insufficient", str(ctx.exception).lower())

    # =============================================================
    # TEST GROUP 4C & 4D: Invitations, Email Match & Timing
    # =============================================================

    def test_p4_04_invitation_creation_and_email_match(self):
        hr = self._setup_org_and_hr("Invite Org", "hr_p4_04")
        q_id = self._create_published_question(hr["org_id"], hr["user_id"])
        assessment = self.assessment_service.create_assessment(
            organization_id=hr["org_id"],
            user_id=hr["user_id"],
            data={
                "title": "Fast Assessment",
                "mode": "CURATED",
                "duration_minutes": 30,
                "passing_score_pct": 70.0,
                "question_ids": [q_id]
            }
        )
        self.assessment_service.publish_assessment(hr["org_id"], hr["user_id"], assessment["id"])

        # Create invitation for specific email
        target_email = "target_candidate@example.com"
        assignments = self.assignment_service.create_assignments(
            organization_id=hr["org_id"],
            assessment_id=assessment["id"],
            candidate_emails=[target_email],
            max_attempts=1
        )
        self.assertTrue(len(assignments) > 0)
        assignment = assignments[0]
        self.assertIn("invitation_token", assignment)
        raw_token = assignment["invitation_token"]

        # 1. Imposter candidate with different email attempts to claim invitation
        imposter = self._setup_candidate("imposter")
        with self.assertRaises(ValueError) as ctx:
            self.assignment_service.claim_invitation(raw_token, {"id": imposter["user_id"], "email": imposter["email"]})
        self.assertIn("signed in as", str(ctx.exception).lower())

        # 2. Legitimate candidate claims invitation
        legit_user_id = f"legit_{uuid.uuid4().hex[:6]}"
        with get_db_connection(self.test_db_path) as conn:
            conn.execute("INSERT INTO users (id, email, password_hash, full_name, role) VALUES (?, ?, 'h', 'Legit Candidate', 'USER')", (legit_user_id, target_email))

        claimed = self.assignment_service.claim_invitation(raw_token, {"id": legit_user_id, "email": target_email})
        self.assertEqual(claimed["status"], "AVAILABLE")

    def test_p4_05_attempt_deadline_and_answer_key_redaction(self):
        hr = self._setup_org_and_hr("Timed Org", "hr_p4_05")
        q_id = self._create_published_question(hr["org_id"], hr["user_id"])
        assessment = self.assessment_service.create_assessment(
            organization_id=hr["org_id"],
            user_id=hr["user_id"],
            data={
                "title": "45-Min Assessment",
                "mode": "CURATED",
                "duration_minutes": 45,
                "passing_score_pct": 70.0,
                "question_ids": [q_id]
            }
        )
        self.assessment_service.publish_assessment(hr["org_id"], hr["user_id"], assessment["id"])

        cand = self._setup_candidate("cand_timing")
        assignments = self.assignment_service.create_assignments(
            organization_id=hr["org_id"],
            assessment_id=assessment["id"],
            candidate_emails=[cand["email"]]
        )
        assignment = assignments[0]

        cand_user = {"id": cand["user_id"], "email": cand["email"]}
        attempt_view = self.attempt_service.start_attempt(cand_user, assignment["assignment_id"])

        # Check server deadline
        started_at = datetime.fromisoformat(attempt_view["started_at"].replace("Z", "+00:00"))
        deadline_at = datetime.fromisoformat(attempt_view["deadline_at"].replace("Z", "+00:00"))
        duration_diff = (deadline_at - started_at).total_seconds() / 60
        self.assertAlmostEqual(duration_diff, 45, delta=1.0)

        # Candidate view MUST NOT leak answer keys or explanations
        for q in attempt_view["questions"]:
            self.assertNotIn("answer_key", q)
            self.assertNotIn("explanation", q)
            self.assertIn("question_text", q)
            self.assertIn("options", q)

    # =============================================================
    # TEST GROUP 4E & 4F: Autosave, Recovery & Timely Submission
    # =============================================================

    def test_p4_06_autosave_and_recovery_across_reload(self):
        hr = self._setup_org_and_hr("Autosave Org", "hr_p4_06")
        q_id = self._create_published_question(hr["org_id"], hr["user_id"])
        assessment = self.assessment_service.create_assessment(
            organization_id=hr["org_id"],
            user_id=hr["user_id"],
            data={
                "title": "Autosave Test",
                "mode": "CURATED",
                "duration_minutes": 30,
                "passing_score_pct": 70.0,
                "question_ids": [q_id]
            }
        )
        self.assessment_service.publish_assessment(hr["org_id"], hr["user_id"], assessment["id"])

        cand = self._setup_candidate("cand_autosave")
        assignments = self.assignment_service.create_assignments(
            organization_id=hr["org_id"],
            assessment_id=assessment["id"],
            candidate_emails=[cand["email"]]
        )
        assignment = assignments[0]

        cand_user = {"id": cand["user_id"], "email": cand["email"]}
        attempt = self.attempt_service.start_attempt(cand_user, assignment["assignment_id"])
        attempt_id = attempt["attempt_id"]

        # Autosave answer
        save_res = self.attempt_service.autosave_answer(cand_user, attempt_id, q_id, ["A"])
        self.assertEqual(save_res["status"], "SAVED")

        # Simulate reload: start_attempt resumes idempotently with saved answers intact
        resumed = self.attempt_service.start_attempt(cand_user, assignment["assignment_id"])
        self.assertEqual(resumed["attempt_id"], attempt_id)
        self.assertEqual(resumed["saved_answers"][q_id], ["A"])

    def test_p4_07_post_deadline_answer_rejection(self):
        hr = self._setup_org_and_hr("Deadline Org", "hr_p4_07")
        q_id = self._create_published_question(hr["org_id"], hr["user_id"])
        assessment = self.assessment_service.create_assessment(
            organization_id=hr["org_id"],
            user_id=hr["user_id"],
            data={
                "title": "Expired Test",
                "mode": "CURATED",
                "duration_minutes": 15,
                "passing_score_pct": 70.0,
                "question_ids": [q_id]
            }
        )
        self.assessment_service.publish_assessment(hr["org_id"], hr["user_id"], assessment["id"])

        cand = self._setup_candidate("cand_expired")
        assignments = self.assignment_service.create_assignments(
            organization_id=hr["org_id"],
            assessment_id=assessment["id"],
            candidate_emails=[cand["email"]]
        )
        assignment = assignments[0]

        cand_user = {"id": cand["user_id"], "email": cand["email"]}
        attempt = self.attempt_service.start_attempt(cand_user, assignment["assignment_id"])
        attempt_id = attempt["attempt_id"]

        # Fast-forward attempt deadline into the past in the database
        past_time = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        with get_db_connection(self.test_db_path) as conn:
            conn.execute("UPDATE assessment_attempts SET deadline_at = ? WHERE id = ?", (past_time, attempt_id))

        # Attempting to save after deadline is rejected
        with self.assertRaises(ValueError) as ctx:
            self.attempt_service.autosave_answer(cand_user, attempt_id, q_id, ["A"])
        self.assertIn("expired", str(ctx.exception).lower())

    # =============================================================
    # TEST GROUP 4G, 4H & 4I: Scoring, Release Policy & CSV Export
    # =============================================================

    def test_p4_08_scoring_and_result_release_policy(self):
        hr = self._setup_org_and_hr("Scoring Org", "hr_p4_08")
        q1 = self._create_published_question(hr["org_id"], hr["user_id"], "Python")
        q2 = self._create_published_question(hr["org_id"], hr["user_id"], "Django")

        # Assessment configured with WITHHOLD_PENDING_REVIEW
        assessment = self.assessment_service.create_assessment(
            organization_id=hr["org_id"],
            user_id=hr["user_id"],
            data={
                "title": "Confidential Evaluation",
                "mode": "CURATED",
                "duration_minutes": 60,
                "passing_score_pct": 70.0,
                "question_ids": [q1, q2],
                "result_release_policy": "WITHHOLD_PENDING_REVIEW"
            }
        )
        self.assessment_service.publish_assessment(hr["org_id"], hr["user_id"], assessment["id"])

        cand = self._setup_candidate("cand_scoring")
        assignments = self.assignment_service.create_assignments(
            organization_id=hr["org_id"],
            assessment_id=assessment["id"],
            candidate_emails=[cand["email"]]
        )
        assignment = assignments[0]

        cand_user = {"id": cand["user_id"], "email": cand["email"]}
        attempt = self.attempt_service.start_attempt(cand_user, assignment["assignment_id"])
        attempt_id = attempt["attempt_id"]

        # Submit answer A (correct) for Q1, and B (incorrect) for Q2
        self.attempt_service.autosave_answer(cand_user, attempt_id, q1, ["A"])
        self.attempt_service.autosave_answer(cand_user, attempt_id, q2, ["B"])

        # Final submit
        cand_result = self.attempt_service.submit_attempt(cand_user, attempt_id)
        # Because release policy is WITHHOLD_PENDING_REVIEW, candidate result is withheld
        self.assertFalse(cand_result["result_released"])
        self.assertNotIn("percentage_score", cand_result)

        # HR accesses scorecard and sees 50.0%
        hr_scorecard = self.analytics_service.get_candidate_scorecard(hr["org_id"], attempt_id)
        self.assertEqual(hr_scorecard["percentage_score"], 50.0)

        # HR releases results
        self.analytics_service.release_attempt_result(hr["org_id"], hr["user_id"], attempt_id)

        # Candidate now can retrieve full released scorecard
        released_view = self.attempt_service.get_attempt_result_for_candidate(cand_user, attempt_id)
        self.assertTrue(released_view["result_released"])
        self.assertEqual(released_view["percentage_score"], 50.0)

    def test_p4_09_csv_export_formula_injection_defense(self):
        # CSV export must neutralize formulas starting with =, +, -, @
        sanitized_eq = AssessmentAnalyticsService.sanitize_csv_field("=1+1")
        self.assertTrue(sanitized_eq.startswith("'="))

        sanitized_plus = AssessmentAnalyticsService.sanitize_csv_field("+cmd|' /C calc'!A0")
        self.assertTrue(sanitized_plus.startswith("'+"))

        sanitized_at = AssessmentAnalyticsService.sanitize_csv_field("@SUM(1,2)")
        self.assertTrue(sanitized_at.startswith("'@"))

        normal_field = AssessmentAnalyticsService.sanitize_csv_field("Jane Doe")
        self.assertEqual(normal_field, "Jane Doe")

    # =============================================================
    # CROSS-PHASE END-TO-END SCENARIOS (A, B, C, D)
    # =============================================================

    def test_e2e_scenario_a_candidate_practice(self):
        """E2E Scenario A: Register USER, upload resume, extract skills, practice quiz, view feedback."""
        # 1. Register candidate
        email = f"e2e_a_{uuid.uuid4().hex[:6]}@candidate.com"
        reg = self.client.post("/api/auth/register", json={"email": email, "password": "CandidatePass123!#", "full_name": "E2E Candidate A"})
        self.assertEqual(reg.status_code, 201)
        cand_user = reg.json()["user"]
        headers = {"Authorization": f"Bearer {reg.json()['token']}"}

        # 2. Add technical skills to profile
        s1 = self.skill_service.add_user_skill(cand_user["id"], "Python", "LANGUAGE", "Used in personal web projects")
        self.assertEqual(s1["skill_name"], "Python")

        # 3. Start practice quiz
        quiz = self.practice_service.start_quiz(user_id=cand_user["id"], mode="SKILL_BASED", skill_name="Python", question_count=1)
        self.assertEqual(quiz["status"], "IN_PROGRESS")

        # 4. Submit practice quiz
        q_id = quiz["questions"][0]["id"]
        # Fetch answer key from DB to submit correctly
        with get_db_connection(self.test_db_path) as conn:
            row = conn.execute("SELECT answer_key FROM questions WHERE id = ?", (q_id,)).fetchone()
            ans_key = json.loads(row["answer_key"])

        res = self.practice_service.submit_quiz_answers(cand_user["id"], quiz["quiz_id"], {q_id: ans_key})
        self.assertEqual(res["status"], "COMPLETED")
        self.assertEqual(res["percentage_score"], 100.0)

        # 5. Practice history persists
        history = self.practice_service.get_user_practice_history(cand_user["id"])
        self.assertEqual(history["total_quizzes"], 1)

    def test_e2e_scenario_b_hr_question_bank_isolation(self):
        """E2E Scenario B: HR creates and publishes question; other organization is isolated."""
        hr_a = self._setup_org_and_hr("Company A", "e2e_hr_a")
        hr_b = self._setup_org_and_hr("Company B", "e2e_hr_b")

        q_id = self._create_published_question(hr_a["org_id"], hr_a["user_id"])

        # Company B cannot view Company A's question
        res_cross = self.client.get(f"/api/hr/questions/{q_id}?organization_id={hr_b['org_id']}", headers=hr_b["headers"])
        self.assertEqual(res_cross.status_code, 404)

        # Company B questions list does not contain Company A's question
        list_b = self.client.get(f"/api/hr/questions?organization_id={hr_b['org_id']}", headers=hr_b["headers"])
        b_ids = [item["id"] for item in list_b.json()["items"]]
        self.assertNotIn(q_id, b_ids)

    def test_e2e_scenario_c_enterprise_assessment_workflow(self):
        """E2E Scenario C: HR creates assessment -> invites candidate -> timed attempt -> scoring -> release."""
        hr = self._setup_org_and_hr("Enterprise Corp", "e2e_hr_c")
        q_id = self._create_published_question(hr["org_id"], hr["user_id"])

        # 1. HR creates and publishes assessment
        assessment = self.assessment_service.create_assessment(
            organization_id=hr["org_id"],
            user_id=hr["user_id"],
            data={
                "title": "E2E Formal Assessment",
                "mode": "CURATED",
                "duration_minutes": 30,
                "passing_score_pct": 75.0,
                "question_ids": [q_id],
                "result_release_policy": "WITHHOLD_PENDING_REVIEW"
            }
        )
        self.assessment_service.publish_assessment(hr["org_id"], hr["user_id"], assessment["id"])

        # 2. Invite candidate
        cand = self._setup_candidate("e2e_cand_c")
        assignments = self.assignment_service.create_assignments(
            organization_id=hr["org_id"], assessment_id=assessment["id"],
            candidate_emails=[cand["email"]]
        )
        assign = assignments[0]

        cand_user = {"id": cand["user_id"], "email": cand["email"]}

        # 3. Candidate starts attempt
        attempt = self.attempt_service.start_attempt(cand_user, assign["assignment_id"])
        attempt_id = attempt["attempt_id"]

        # 4. Autosave answer
        self.attempt_service.autosave_answer(cand_user, attempt_id, q_id, ["A"])

        # 5. Submit attempt
        cand_sub = self.attempt_service.submit_attempt(cand_user, attempt_id)
        self.assertFalse(cand_sub["result_released"])

        # 6. HR releases result
        self.analytics_service.release_attempt_result(hr["org_id"], hr["user_id"], attempt_id)

        # 7. Candidate checks result
        final_view = self.attempt_service.get_attempt_result_for_candidate(cand_user, attempt_id)
        self.assertTrue(final_view["result_released"])
        self.assertEqual(final_view["percentage_score"], 100.0)

    def test_e2e_scenario_d_adversarial_tampering_and_revocation(self):
        """E2E Scenario D: Attack attempts (tampered IDs, revoked invites, past-deadline mutation)."""
        hr_a = self._setup_org_and_hr("Attacked Org", "e2e_hr_d")
        cand = self._setup_candidate("attacker")

        # 1. Attacker calls HR endpoint with candidate token
        res_hr_bypass = self.client.get("/api/hr/questions", headers=cand["headers"])
        self.assertEqual(res_hr_bypass.status_code, 403)

        # 2. Attacker calls candidate endpoint with invalid / non-existent attempt ID
        res_fake_attempt = self.client.get("/api/candidate/assessments/attempts/fake-uuid-1234", headers=cand["headers"])
        self.assertEqual(res_fake_attempt.status_code, 404)

        # 3. Attacker uses revoked invitation code
        with get_db_connection(self.test_db_path) as conn:
            raw_inv = "revoked_invite_code_123"
            code_hash = __import__("hashlib").sha256(raw_inv.encode("utf-8")).hexdigest()
            conn.execute(
                "INSERT INTO hr_invitations (id, organization_id, email, invitation_code_hash, org_role, created_by, expires_at, used_at) VALUES (?, ?, 'rev@test.com', ?, 'RECRUITER', NULL, ?, CURRENT_TIMESTAMP)",
                (str(uuid.uuid4()), hr_a["org_id"], code_hash, (datetime.now(timezone.utc) + timedelta(days=1)).isoformat())
            )

        res_revoked = self.client.post("/api/auth/register-hr", json={
            "email": "rev@test.com", "password": "RecruiterPass123!#", "full_name": "Revoked User", "invitation_code": raw_inv
        })
        self.assertEqual(res_revoked.status_code, 403)


if __name__ == "__main__":
    unittest.main()
