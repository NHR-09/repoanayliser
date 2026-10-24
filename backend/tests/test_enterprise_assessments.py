import unittest
import os
import json
import sqlite3
import tempfile
import uuid
from unittest.mock import patch
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from main import app
from src.db.connection import get_db_connection
from src.db.migrations import run_migrations
from src.security import hash_password, create_session
from src.services.assessment_assignment_service import AssessmentAssignmentService

class TestEnterpriseAssessments(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_db_fd, cls.test_db_path = tempfile.mkstemp(suffix=".db")
        from src.config import settings
        cls.orig_db_path = settings.db_path
        settings.db_path = cls.test_db_path
        os.environ["DATABASE_PATH"] = cls.test_db_path
        os.environ["DATABASE_URL"] = f"sqlite:///{cls.test_db_path}"
        run_migrations(cls.test_db_path)
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        from src.config import settings
        settings.db_path = cls.orig_db_path
        os.close(cls.test_db_fd)
        if os.path.exists(cls.test_db_path):
            os.remove(cls.test_db_path)

    def setUp(self):
        # Override db path for all service instances
        from src.api.assessment_hr import assessment_service, assignment_service, analytics_service
        from src.api.assessment_candidate import assignment_service as cand_assign_svc, attempt_service
        from src.api.hr import hr_question_service, hr_repo_service

        assessment_service.db_path = self.test_db_path
        assignment_service.db_path = self.test_db_path
        analytics_service.db_path = self.test_db_path
        cand_assign_svc.db_path = self.test_db_path
        attempt_service.db_path = self.test_db_path
        hr_question_service.db_path = self.test_db_path
        hr_repo_service.db_path = self.test_db_path

    def _create_user_and_session(self, email: str, role: str, org_role: str = "RECRUITER"):
        uid = str(uuid.uuid4())
        org_id = f"org_{uuid.uuid4().hex[:6]}"
        with get_db_connection(self.test_db_path) as conn:
            conn.execute(
                "INSERT INTO organizations (id, name, slug) VALUES (?, ?, ?)",
                (org_id, f"Corp {org_id}", org_id),
            )
            conn.execute(
                "INSERT INTO users (id, email, password_hash, full_name, role) VALUES (?, ?, ?, ?, ?)",
                (uid, email, hash_password("SecurePass123!"), f"User {uid[:6]}", role),
            )
            conn.execute(
                "INSERT INTO organization_memberships (id, organization_id, user_id, org_role) VALUES (?, ?, ?, ?)",
                (str(uuid.uuid4()), org_id, uid, org_role),
            )

        sess = create_session(uid, self.test_db_path)
        token = sess["token"]
        return uid, org_id, token

    def _create_published_question(self, org_id: str, author_id: str, competency="CODE_COMPREHENSION", fmt="SINGLE_SELECT"):
        qid = str(uuid.uuid4())
        options = [
            {"id": "A", "key": "A", "text": "Option Alpha"},
            {"id": "B", "key": "B", "text": "Option Beta"},
            {"id": "C", "key": "C", "text": "Option Gamma"},
        ]
        answer_key = {"correct_option": "A"} if fmt == "SINGLE_SELECT" else {"correct_options": ["A", "B"]}

        with get_db_connection(self.test_db_path) as conn:
            conn.execute(
                """
                INSERT INTO questions (
                    id, organization_id, created_by, source_type, skill_tags, competency,
                    response_format, difficulty, question_text, options, answer_key,
                    explanation, review_status, validation_status, version
                ) VALUES (?, ?, ?, 'SKILL_BASED', ?, ?, ?, 'INTERMEDIATE', ?, ?, ?, ?, 'PUBLISHED', 'VALIDATED', 1)
                """,
                (
                    qid,
                    org_id,
                    author_id,
                    json.dumps(["python", "architecture"]),
                    competency,
                    fmt,
                    f"Sample question for {competency} verification?",
                    json.dumps(options),
                    json.dumps(answer_key),
                    "Defensible explanation of architectural trade-offs.",
                ),
            )
        return qid

    def test_hr_can_create_valid_assessment_draft(self):
        """HR recruiter can create a valid draft assessment."""
        hr_id, org_id, token = self._create_user_and_session("hr_draft@corp.com", "HR")
        headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "title": "Backend Engineering Evaluation",
            "description": "Assessment of Python, async, and distributed design.",
            "instructions": "Answer all questions independently without external assistance.",
            "job_role": "Senior Backend Engineer",
            "mode": "CURATED",
            "duration_minutes": 60,
            "passing_score_pct": 75.0,
            "result_release_policy": "WITHHOLD_PENDING_REVIEW",
        }

        res = self.client.post(f"/api/hr/assessments?organization_id={org_id}", json=payload, headers=headers)
        self.assertEqual(res.status_code, 201)
        data = res.json()["assessment"]
        self.assertEqual(data["title"], "Backend Engineering Evaluation")
        self.assertEqual(data["status"], "DRAFT")
        self.assertEqual(data["version"], 1)

    def test_candidate_cannot_create_or_publish_assessment(self):
        """Candidate accounts cannot access HR assessment studio."""
        cand_id, org_id, token = self._create_user_and_session("cand_no_hr@corp.com", "USER")
        headers = {"Authorization": f"Bearer {token}"}

        res = self.client.post(
            f"/api/hr/assessments?organization_id={org_id}",
            json={"title": "Hacked Assessment"},
            headers=headers,
        )
        self.assertEqual(res.status_code, 403)

    def test_curated_assessment_publication_and_versioning(self):
        """Curated assessment requires published questions; publishing creates immutable snapshot."""
        hr_id, org_id, token = self._create_user_and_session("hr_curated@corp.com", "HR")
        headers = {"Authorization": f"Bearer {token}"}

        q1 = self._create_published_question(org_id, hr_id, "CODE_COMPREHENSION")
        q2 = self._create_published_question(org_id, hr_id, "DEPENDENCY_TRACING")

        # Create draft with 2 questions
        create_res = self.client.post(
            f"/api/hr/assessments?organization_id={org_id}",
            json={
                "title": "Core Architectural Evaluation",
                "mode": "CURATED",
                "question_ids": [q1, q2],
                "duration_minutes": 45,
                "passing_score_pct": 70.0,
            },
            headers=headers,
        )
        self.assertEqual(create_res.status_code, 201)
        assessment_id = create_res.json()["assessment"]["id"]

        # Publish assessment
        pub_res = self.client.post(
            f"/api/hr/assessments/{assessment_id}/publish?organization_id={org_id}",
            headers=headers,
        )
        self.assertEqual(pub_res.status_code, 200)
        pub_data = pub_res.json()["assessment"]
        self.assertEqual(pub_data["status"], "PUBLISHED")
        self.assertIsNotNone(pub_data["published_version_id"])

        # Edit published assessment: must increment version and reset status to DRAFT
        update_res = self.client.put(
            f"/api/hr/assessments/{assessment_id}?organization_id={org_id}",
            json={"title": "Core Architectural Evaluation - Revision 2"},
            headers=headers,
        )
        self.assertEqual(update_res.status_code, 200)
        updated = update_res.json()["assessment"]
        self.assertEqual(updated["version"], 2)
        self.assertEqual(updated["status"], "DRAFT")

    def test_randomized_blueprint_fails_when_coverage_insufficient(self):
        """Randomized blueprint mode fails safely if question pool does not meet quota."""
        hr_id, org_id, token = self._create_user_and_session("hr_random@corp.com", "HR")
        headers = {"Authorization": f"Bearer {token}"}

        # Request 10 questions when only 1 exists
        q1 = self._create_published_question(org_id, hr_id, "DEBUGGING")

        create_res = self.client.post(
            f"/api/hr/assessments?organization_id={org_id}",
            json={
                "title": "Randomized Debugging Exam",
                "mode": "RANDOMIZED",
                "blueprint_config": {
                    "question_count": 10,
                    "required_competencies": ["DEBUGGING"],
                    "difficulty": "INTERMEDIATE",
                },
                "duration_minutes": 60,
            },
            headers=headers,
        )
        self.assertEqual(create_res.status_code, 201)
        assessment_id = create_res.json()["assessment"]["id"]

        # Publishing must fail because 10 questions were requested but only 1 exists
        pub_res = self.client.post(
            f"/api/hr/assessments/{assessment_id}/publish?organization_id={org_id}",
            headers=headers,
        )
        self.assertEqual(pub_res.status_code, 400)
        self.assertIn("Insufficient published question coverage", pub_res.json()["detail"])

    def test_candidate_invitations_and_secure_claim(self):
        """HR assigns assessment to candidate emails; raw token hashes are verified and claimed."""
        hr_id, org_id, hr_token = self._create_user_and_session("hr_assign@corp.com", "HR")
        cand_id, _, cand_token = self._create_user_and_session("candidate_alice@test.com", "USER")

        q1 = self._create_published_question(org_id, hr_id)
        # Create and publish assessment
        create_res = self.client.post(
            f"/api/hr/assessments?organization_id={org_id}",
            json={"title": "Frontend Lead Assessment", "mode": "CURATED", "question_ids": [q1]},
            headers={"Authorization": f"Bearer {hr_token}"},
        )
        assessment_id = create_res.json()["assessment"]["id"]
        self.client.post(f"/api/hr/assessments/{assessment_id}/publish?organization_id={org_id}", headers={"Authorization": f"Bearer {hr_token}"})

        # Assign to Alice
        assign_res = self.client.post(
            f"/api/hr/assessments/{assessment_id}/assign?organization_id={org_id}",
            json={"candidate_emails": ["candidate_alice@test.com"], "expires_days": 7},
            headers={"Authorization": f"Bearer {hr_token}"},
        )
        self.assertEqual(assign_res.status_code, 201)
        invitation = assign_res.json()["invitations"][0]
        raw_token = invitation["invitation_token"]

        # Verify DB does NOT store raw token in plaintext
        with get_db_connection(self.test_db_path) as conn:
            row = conn.execute(
                "SELECT invitation_token_hash FROM assessment_assignments WHERE id = ?",
                (invitation["assignment_id"],),
            ).fetchone()
            self.assertNotEqual(row["invitation_token_hash"], raw_token)
            self.assertEqual(row["invitation_token_hash"], AssessmentAssignmentService.hash_token(raw_token))

        # Alice claims invitation
        claim_res = self.client.post(
            "/api/candidate/assessments/claim",
            json={"token": raw_token},
            headers={"Authorization": f"Bearer {cand_token}"},
        )
        self.assertEqual(claim_res.status_code, 200)
        self.assertEqual(claim_res.json()["claimed"]["status"], "AVAILABLE")

    def test_candidate_cannot_claim_another_candidates_invitation(self):
        """Candidate B cannot claim an invitation created for Candidate A."""
        hr_id, org_id, hr_token = self._create_user_and_session("hr_inv_guard@corp.com", "HR")
        _, _, cand_b_token = self._create_user_and_session("cand_bob@test.com", "USER")

        q1 = self._create_published_question(org_id, hr_id)
        create_res = self.client.post(
            f"/api/hr/assessments?organization_id={org_id}",
            json={"title": "Security Specialist Assessment", "mode": "CURATED", "question_ids": [q1]},
            headers={"Authorization": f"Bearer {hr_token}"},
        )
        aid = create_res.json()["assessment"]["id"]
        self.client.post(f"/api/hr/assessments/{aid}/publish?organization_id={org_id}", headers={"Authorization": f"Bearer {hr_token}"})

        # Assign strictly to alice
        assign_res = self.client.post(
            f"/api/hr/assessments/{aid}/assign?organization_id={org_id}",
            json={"candidate_emails": ["alice_intended@test.com"]},
            headers={"Authorization": f"Bearer {hr_token}"},
        )
        raw_token = assign_res.json()["invitations"][0]["invitation_token"]

        # Bob attempts to claim
        bob_claim = self.client.post(
            "/api/candidate/assessments/claim",
            json={"token": raw_token},
            headers={"Authorization": f"Bearer {cand_b_token}"},
        )
        self.assertEqual(bob_claim.status_code, 400)
        self.assertIn("Invitation is addressed to", bob_claim.json()["detail"])

    def test_timed_attempt_lifecycle_autosave_and_objective_scoring(self):
        """
        Complete end-to-end assessment lifecycle:
        Start attempt ➔ Verify answer keys redacted ➔ Autosave answers ➔ Submit ➔ Objective score.
        """
        hr_id, org_id, hr_token = self._create_user_and_session("hr_lifecycle@corp.com", "HR")
        cand_id, _, cand_token = self._create_user_and_session("cand_eval@test.com", "USER")

        # 1. Create two published questions (Q1: single select A, Q2: multi select A, B)
        q1 = self._create_published_question(org_id, hr_id, "CODE_COMPREHENSION", "SINGLE_SELECT")
        q2 = self._create_published_question(org_id, hr_id, "DEPENDENCY_TRACING", "MULTI_SELECT")

        # 2. Create and publish assessment with WITHHOLD_PENDING_REVIEW policy
        create_res = self.client.post(
            f"/api/hr/assessments?organization_id={org_id}",
            json={
                "title": "Full Stack Engineer Evaluation",
                "mode": "CURATED",
                "question_ids": [q1, q2],
                "duration_minutes": 30,
                "passing_score_pct": 50.0,
                "result_release_policy": "WITHHOLD_PENDING_REVIEW",
            },
            headers={"Authorization": f"Bearer {hr_token}"},
        )
        aid = create_res.json()["assessment"]["id"]
        self.client.post(f"/api/hr/assessments/{aid}/publish?organization_id={org_id}", headers={"Authorization": f"Bearer {hr_token}"})

        # 3. Assign and claim
        assign_res = self.client.post(
            f"/api/hr/assessments/{aid}/assign?organization_id={org_id}",
            json={"candidate_emails": ["cand_eval@test.com"]},
            headers={"Authorization": f"Bearer {hr_token}"},
        )
        invitation = assign_res.json()["invitations"][0]
        self.client.post(
            "/api/candidate/assessments/claim",
            json={"token": invitation["invitation_token"]},
            headers={"Authorization": f"Bearer {cand_token}"},
        )

        # 4. Start attempt
        start_res = self.client.post(
            "/api/candidate/assessments/start",
            json={"assignment_id": invitation["assignment_id"]},
            headers={"Authorization": f"Bearer {cand_token}"},
        )
        self.assertEqual(start_res.status_code, 200)
        attempt_data = start_res.json()["attempt"]
        attempt_id = attempt_data["attempt_id"]
        self.assertEqual(attempt_data["status"], "IN_PROGRESS")
        self.assertGreater(attempt_data["remaining_seconds"], 0)

        # CRITICAL VERIFICATION: Candidate question view has answer keys and explanations REDACTED
        for q in attempt_data["questions"]:
            self.assertNotIn("answer_key", q)
            self.assertNotIn("explanation", q)

        # 5. Autosave answers
        # Q1: Correct "A"
        save_q1 = self.client.post(
            f"/api/candidate/assessments/attempts/{attempt_id}/answers",
            json={"question_id": q1, "candidate_response": "A"},
            headers={"Authorization": f"Bearer {cand_token}"},
        )
        self.assertEqual(save_q1.status_code, 200)
        self.assertEqual(save_q1.json()["status"], "SAVED")

        # Q2: Correct ["A", "B"]
        save_q2 = self.client.post(
            f"/api/candidate/assessments/attempts/{attempt_id}/answers",
            json={"question_id": q2, "candidate_response": ["A", "B"]},
            headers={"Authorization": f"Bearer {cand_token}"},
        )
        self.assertEqual(save_q2.status_code, 200)

        # 6. Submit attempt
        submit_res = self.client.post(
            f"/api/candidate/assessments/attempts/{attempt_id}/submit",
            headers={"Authorization": f"Bearer {cand_token}"},
        )
        self.assertEqual(submit_res.status_code, 200)

        # Verify candidate gets withheld status (result_release_policy == WITHHOLD_PENDING_REVIEW)
        cand_result = submit_res.json()["result"]
        self.assertFalse(cand_result["result_released"])
        self.assertIn("pending recruiter review", cand_result["message"])

        # 7. HR inspects candidate scorecard (HR sees full details, points, answer keys)
        scorecard_res = self.client.get(
            f"/api/hr/assessments/attempts/{attempt_id}/scorecard?organization_id={org_id}",
            headers={"Authorization": f"Bearer {hr_token}"},
        )
        self.assertEqual(scorecard_res.status_code, 200)
        card = scorecard_res.json()["scorecard"]
        self.assertEqual(card["total_score"], 2.0)
        self.assertEqual(card["percentage_score"], 100.0)
        self.assertEqual(card["passed"], 1)

        # 8. HR releases results
        release_res = self.client.post(
            f"/api/hr/assessments/attempts/{attempt_id}/release?organization_id={org_id}",
            headers={"Authorization": f"Bearer {hr_token}"},
        )
        self.assertEqual(release_res.status_code, 200)

        # 9. Candidate can now view released score
        post_release_res = self.client.get(
            f"/api/candidate/assessments/attempts/{attempt_id}/result",
            headers={"Authorization": f"Bearer {cand_token}"},
        )
        self.assertEqual(post_release_res.status_code, 200)
        released_card = post_release_res.json()["result"]
        self.assertTrue(released_card["result_released"])
        self.assertEqual(released_card["percentage_score"], 100.0)

    def test_csv_export_with_formula_injection_protection(self):
        """CSV export sanitizes formulas starting with '=', '+', '-', '@'."""
        hr_id, org_id, hr_token = self._create_user_and_session("hr_csv@corp.com", "HR")
        headers = {"Authorization": f"Bearer {hr_token}"}

        q1 = self._create_published_question(org_id, hr_id)
        create_res = self.client.post(
            f"/api/hr/assessments?organization_id={org_id}",
            json={"title": "Data Engineering Test", "mode": "CURATED", "question_ids": [q1]},
            headers=headers,
        )
        aid = create_res.json()["assessment"]["id"]
        self.client.post(f"/api/hr/assessments/{aid}/publish?organization_id={org_id}", headers=headers)

        # Assign to email with leading formula character
        self.client.post(
            f"/api/hr/assessments/{aid}/assign?organization_id={org_id}",
            json={"candidate_emails": ["=cmd|' /C calc'!A0@test.com"]},
            headers=headers,
        )

        export_res = self.client.get(
            f"/api/hr/assessments/{aid}/export?organization_id={org_id}",
            headers=headers,
        )
        self.assertEqual(export_res.status_code, 200)
        self.assertEqual(export_res.headers["content-type"], "text/csv; charset=utf-8")
        csv_text = export_res.text
        # Check formula character was quoted
        self.assertNotIn("\n=cmd", csv_text)

    def test_cross_organization_assessment_isolation(self):
        """HR from Org B cannot read, assign, or access Org A's assessments or attempts."""
        hr_a_id, org_a, hr_a_token = self._create_user_and_session("hr_org_a@corp.com", "HR")
        _, org_b, hr_b_token = self._create_user_and_session("hr_org_b@corp.com", "HR")

        q1 = self._create_published_question(org_a, hr_a_id)
        create_res = self.client.post(
            f"/api/hr/assessments?organization_id={org_a}",
            json={"title": "Org A Private Assessment", "mode": "CURATED", "question_ids": [q1]},
            headers={"Authorization": f"Bearer {hr_a_token}"},
        )
        aid = create_res.json()["assessment"]["id"]

        # Org B attempts to retrieve Org A's assessment
        leak_res = self.client.get(
            f"/api/hr/assessments/{aid}?organization_id={org_b}",
            headers={"Authorization": f"Bearer {hr_b_token}"},
        )
        self.assertEqual(leak_res.status_code, 404)

if __name__ == "__main__":
    unittest.main()
