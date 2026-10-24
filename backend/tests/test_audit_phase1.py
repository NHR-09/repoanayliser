import os
import tempfile
import unittest
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient

from main import app
from src.db.connection import get_db_connection, init_db
from src.security.passwords import hash_password, verify_password
from src.security.sessions import create_session
from src.security.rate_limiter import login_rate_limiter
from src.config import settings

class TestAuditPhase1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.test_db_path = os.path.join(cls.temp_dir.name, "test_audit_phase1.db")
        cls.orig_db_path = settings.db_path
        settings.db_path = cls.test_db_path
        os.environ["DATABASE_PATH"] = cls.test_db_path

        init_db(cls.test_db_path)
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        settings.db_path = cls.orig_db_path
        cls.temp_dir.cleanup()

    def setUp(self):
        settings.db_path = self.test_db_path
        self.client.cookies.clear()
        with login_rate_limiter._lock:
            login_rate_limiter._attempts.clear()

    # -------------------------------------------------------------
    # P1-01: Register with valid user details
    # -------------------------------------------------------------
    def test_p1_01_valid_registration(self):
        email = f"p1_01_{uuid.uuid4().hex[:6]}@example.com"
        res = self.client.post("/api/auth/register", json={
            "email": email,
            "password": "ValidPassword123!#",
            "full_name": "Valid Candidate"
        })
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["user"]["role"], "USER")
        self.assertEqual(data["user"]["email"], email.lower())
        self.assertIn("token", data)

    # -------------------------------------------------------------
    # P1-02: Register with duplicate email
    # -------------------------------------------------------------
    def test_p1_02_duplicate_email_registration(self):
        email = f"p1_02_{uuid.uuid4().hex[:6]}@example.com"
        res1 = self.client.post("/api/auth/register", json={
            "email": email,
            "password": "ValidPassword123!#",
            "full_name": "Original User"
        })
        self.assertEqual(res1.status_code, 201)

        # Duplicate attempt
        res2 = self.client.post("/api/auth/register", json={
            "email": email,
            "password": "AnotherPassword123!#",
            "full_name": "Imposter User"
        })
        self.assertEqual(res2.status_code, 409)
        self.assertIn("already exists", res2.json()["detail"].lower())

    # -------------------------------------------------------------
    # P1-03: Register using different email casing
    # -------------------------------------------------------------
    def test_p1_03_duplicate_email_differing_casing(self):
        base = f"p1_03_{uuid.uuid4().hex[:6]}"
        email_upper = f"{base.upper()}@Example.COM"
        email_lower = f"{base.lower()}@example.com"

        res1 = self.client.post("/api/auth/register", json={
            "email": email_upper,
            "password": "ValidPassword123!#",
            "full_name": "Case User One"
        })
        self.assertEqual(res1.status_code, 201)

        # Same email with lower casing must be rejected as duplicate
        res2 = self.client.post("/api/auth/register", json={
            "email": email_lower,
            "password": "ValidPassword123!#",
            "full_name": "Case User Two"
        })
        self.assertEqual(res2.status_code, 409)

    # -------------------------------------------------------------
    # P1-04: Register with malformed input
    # -------------------------------------------------------------
    def test_p1_04_malformed_registration_input(self):
        # Missing @ in email
        res1 = self.client.post("/api/auth/register", json={
            "email": "notanemail.com",
            "password": "ValidPassword123!#",
            "full_name": "Bad Email"
        })
        self.assertEqual(res1.status_code, 400)

        # Missing full_name
        res2 = self.client.post("/api/auth/register", json={
            "email": "missingname@example.com",
            "password": "ValidPassword123!#"
        })
        self.assertEqual(res2.status_code, 422)

    # -------------------------------------------------------------
    # P1-05: Register with missing or invalid password
    # -------------------------------------------------------------
    def test_p1_05_missing_or_weak_password(self):
        # Too short (< 8 chars)
        res1 = self.client.post("/api/auth/register", json={
            "email": "short@example.com",
            "password": "short",
            "full_name": "Short Pass"
        })
        self.assertEqual(res1.status_code, 422)

        # Lacks uppercase, digits, or symbols
        res2 = self.client.post("/api/auth/register", json={
            "email": "nocapital@example.com",
            "password": "alllowercasepassword",
            "full_name": "No Capital"
        })
        self.assertEqual(res2.status_code, 400)
        self.assertIn("Password must contain", res2.json()["detail"])

    # -------------------------------------------------------------
    # P1-06: Log in with valid credentials
    # -------------------------------------------------------------
    def test_p1_06_login_with_valid_credentials(self):
        email = f"p1_06_{uuid.uuid4().hex[:6]}@example.com"
        pwd = "ValidLoginPass123!#"
        self.client.post("/api/auth/register", json={
            "email": email,
            "password": pwd,
            "full_name": "Login User"
        })

        login_res = self.client.post("/api/auth/login", json={
            "email": email,
            "password": pwd
        })
        self.assertEqual(login_res.status_code, 200)
        data = login_res.json()
        self.assertIn("token", data)
        self.assertEqual(data["user"]["email"], email)
        # Check cookie was set
        self.assertIn("architech_session", login_res.cookies)

    # -------------------------------------------------------------
    # P1-07: Log in with incorrect password
    # -------------------------------------------------------------
    def test_p1_07_login_with_incorrect_password(self):
        email = f"p1_07_{uuid.uuid4().hex[:6]}@example.com"
        pwd = "CorrectPass123!#"
        self.client.post("/api/auth/register", json={
            "email": email,
            "password": pwd,
            "full_name": "Login User"
        })

        login_res = self.client.post("/api/auth/login", json={
            "email": email,
            "password": "WrongPassword999!#"
        })
        self.assertEqual(login_res.status_code, 401)
        self.assertIn("Invalid email or password", login_res.json()["detail"])

    # -------------------------------------------------------------
    # P1-08: Log in with nonexistent email
    # -------------------------------------------------------------
    def test_p1_08_login_with_nonexistent_email(self):
        login_res = self.client.post("/api/auth/login", json={
            "email": "doesnotexist@nowhere.com",
            "password": "SomePassword123!#"
        })
        self.assertEqual(login_res.status_code, 401)
        self.assertIn("Invalid email or password", login_res.json()["detail"])

    # -------------------------------------------------------------
    # P1-09: Log out
    # -------------------------------------------------------------
    def test_p1_09_logout_revokes_session(self):
        email = f"p1_09_{uuid.uuid4().hex[:6]}@example.com"
        pwd = "LogoutPass123!#"
        reg = self.client.post("/api/auth/register", json={
            "email": email,
            "password": pwd,
            "full_name": "Logout User"
        })
        token = reg.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Auth endpoint works
        me_res = self.client.get("/api/auth/me", headers=headers)
        self.assertEqual(me_res.status_code, 200)

        # Logout
        logout_res = self.client.post("/api/auth/logout", headers=headers)
        self.assertEqual(logout_res.status_code, 200)

        # Subsequent request with same token must fail
        me_after = self.client.get("/api/auth/me", headers=headers)
        self.assertEqual(me_after.status_code, 401)

    # -------------------------------------------------------------
    # P1-10: Reuse a revoked token
    # -------------------------------------------------------------
    def test_p1_10_reuse_revoked_token_is_denied(self):
        email = f"p1_10_{uuid.uuid4().hex[:6]}@example.com"
        reg = self.client.post("/api/auth/register", json={
            "email": email,
            "password": "RevokePass123!#",
            "full_name": "Revoke User"
        })
        token = reg.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        self.client.post("/api/auth/logout", headers=headers)

        # Reusing revoked token
        res = self.client.get("/api/auth/me", headers=headers)
        self.assertEqual(res.status_code, 401)
        self.assertIn("revoked", res.json()["detail"].lower())

    # -------------------------------------------------------------
    # P1-11: Use an expired token
    # -------------------------------------------------------------
    def test_p1_11_expired_token_is_denied(self):
        email = f"p1_11_{uuid.uuid4().hex[:6]}@example.com"
        reg = self.client.post("/api/auth/register", json={
            "email": email,
            "password": "ExpirePass123!#",
            "full_name": "Expire User"
        })
        token = reg.json()["token"]
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

        # Update database to set expiration in the past
        past_time = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        with get_db_connection(self.test_db_path) as conn:
            conn.execute("UPDATE auth_sessions SET expires_at = ? WHERE token_hash = ?", (past_time, token_hash))

        headers = {"Authorization": f"Bearer {token}"}
        res = self.client.get("/api/auth/me", headers=headers)
        self.assertEqual(res.status_code, 401)

    # -------------------------------------------------------------
    # P1-12: Access endpoint after account deactivation
    # -------------------------------------------------------------
    def test_p1_12_deactivated_account_is_denied(self):
        email = f"p1_12_{uuid.uuid4().hex[:6]}@example.com"
        reg = self.client.post("/api/auth/register", json={
            "email": email,
            "password": "DeactPass123!#",
            "full_name": "Deact User"
        })
        token = reg.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        with get_db_connection(self.test_db_path) as conn:
            conn.execute("UPDATE users SET is_active = 0 WHERE email = ?", (email,))

        res = self.client.get("/api/auth/me", headers=headers)
        self.assertEqual(res.status_code, 401)

    # -------------------------------------------------------------
    # P1-13: Submit malformed or tampered token
    # -------------------------------------------------------------
    def test_p1_13_tampered_token_is_rejected_safely(self):
        for bad_token in ["not-a-token", "Bearer null", "Bearer undefined", "Bearer " + "A" * 200, "Bearer !!!@#$"]:
            headers = {"Authorization": bad_token}
            res = self.client.get("/api/auth/me", headers=headers)
            self.assertEqual(res.status_code, 401)

    # -------------------------------------------------------------
    # P1-14: USER requests HR-only endpoint
    # -------------------------------------------------------------
    def test_p1_14_user_cannot_access_hr_endpoints(self):
        email = f"p1_14_{uuid.uuid4().hex[:6]}@example.com"
        reg = self.client.post("/api/auth/register", json={
            "email": email,
            "password": "UserPass123!#",
            "full_name": "User Dev"
        })
        token = reg.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        res = self.client.get("/api/auth/test/hr-only", headers=headers)
        self.assertEqual(res.status_code, 403)
        self.assertIn("HR access required", res.json()["detail"])

    # -------------------------------------------------------------
    # P1-15: USER submits request to change own role to HR
    # -------------------------------------------------------------
    def test_p1_15_user_cannot_elevate_role_via_input(self):
        email = f"p1_15_{uuid.uuid4().hex[:6]}@example.com"
        reg = self.client.post("/api/auth/register", json={
            "email": email,
            "password": "UserPass123!#",
            "full_name": "User Dev",
            "role": "HR"  # Attacker tries to register directly as HR
        })
        self.assertEqual(reg.status_code, 201)
        self.assertEqual(reg.json()["user"]["role"], "USER")

        with get_db_connection(self.test_db_path) as conn:
            user = conn.execute("SELECT role FROM users WHERE email = ?", (email,)).fetchone()
            self.assertEqual(user["role"], "USER")

    # -------------------------------------------------------------
    # P1-16: Public registration requesting HR role
    # -------------------------------------------------------------
    def test_p1_16_public_registration_cannot_grant_hr(self):
        res = self.client.post("/api/auth/register", json={
            "email": f"p1_16_{uuid.uuid4().hex[:6]}@example.com",
            "password": "UserPass123!#",
            "full_name": "User Attacker",
            "role": "ADMIN"
        })
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()["user"]["role"], "USER")

    # -------------------------------------------------------------
    # P1-17: Valid authorized HR invitation is accepted
    # -------------------------------------------------------------
    def test_p1_17_valid_hr_invitation_flow(self):
        # Setup org & admin
        admin_uid = str(uuid.uuid4())
        org_id = f"org_{uuid.uuid4().hex[:6]}"
        with get_db_connection(self.test_db_path) as conn:
            conn.execute("INSERT INTO organizations (id, name, slug) VALUES (?, ?, ?)", (org_id, "TestOrg", org_id))
            conn.execute("INSERT INTO users (id, email, password_hash, full_name, role) VALUES (?, 'admin@org.com', 'h', 'Admin', 'HR')", (admin_uid,))
            conn.execute("INSERT INTO organization_memberships (id, organization_id, user_id, org_role) VALUES (?, ?, ?, 'OWNER')", (str(uuid.uuid4()), org_id, admin_uid))

        sess = create_session(admin_uid, db_path=self.test_db_path)
        admin_headers = {"Authorization": f"Bearer {sess['token']}"}

        # Admin invites recruiter
        recruiter_email = f"recruiter_{uuid.uuid4().hex[:6]}@org.com"
        inv_res = self.client.post("/api/auth/invite-hr", headers=admin_headers, json={
            "email": recruiter_email,
            "organization_id": org_id,
            "org_role": "RECRUITER",
            "expire_days": 7
        })
        self.assertEqual(inv_res.status_code, 201)
        inv_code = inv_res.json()["invitation_code"]

        # Recruiter registers
        reg_res = self.client.post("/api/auth/register-hr", json={
            "email": recruiter_email,
            "password": "RecruiterPass123!#",
            "full_name": "Recruiter Jane",
            "invitation_code": inv_code
        })
        self.assertEqual(reg_res.status_code, 201)
        self.assertEqual(reg_res.json()["user"]["role"], "HR")

    # -------------------------------------------------------------
    # P1-18: Expired HR invitation is used
    # -------------------------------------------------------------
    def test_p1_18_expired_hr_invitation_is_denied(self):
        inv_id = str(uuid.uuid4())
        raw_code = "expired_code_xyz_12345"
        code_hash = hashlib.sha256(raw_code.encode("utf-8")).hexdigest()
        org_id = f"org_{uuid.uuid4().hex[:6]}"
        past_time = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        recruiter_email = "exp_recruiter@org.com"

        with get_db_connection(self.test_db_path) as conn:
            conn.execute("INSERT INTO organizations (id, name, slug) VALUES (?, ?, ?)", (org_id, "OrgExpired", org_id))
            conn.execute(
                """
                INSERT INTO hr_invitations (id, organization_id, email, invitation_code_hash, org_role, created_by, expires_at)
                VALUES (?, ?, ?, ?, 'RECRUITER', NULL, ?)
                """,
                (inv_id, org_id, recruiter_email, code_hash, past_time)
            )

        res = self.client.post("/api/auth/register-hr", json={
            "email": recruiter_email,
            "password": "RecruiterPass123!#",
            "full_name": "Expired Recruiter",
            "invitation_code": raw_code
        })
        self.assertEqual(res.status_code, 403)
        self.assertIn("expired", res.json()["detail"].lower())

    # -------------------------------------------------------------
    # P1-19: Reuse an already consumed invitation
    # -------------------------------------------------------------
    def test_p1_19_reuse_consumed_hr_invitation_is_denied(self):
        admin_uid = str(uuid.uuid4())
        org_id = f"org_{uuid.uuid4().hex[:6]}"
        with get_db_connection(self.test_db_path) as conn:
            conn.execute("INSERT INTO organizations (id, name, slug) VALUES (?, ?, ?)", (org_id, "ReuseOrg", org_id))
            conn.execute("INSERT INTO users (id, email, password_hash, full_name, role) VALUES (?, 'admin_reuse@org.com', 'h', 'Admin', 'HR')", (admin_uid,))
            conn.execute("INSERT INTO organization_memberships (id, organization_id, user_id, org_role) VALUES (?, ?, ?, 'OWNER')", (str(uuid.uuid4()), org_id, admin_uid))

        sess = create_session(admin_uid, db_path=self.test_db_path)
        admin_headers = {"Authorization": f"Bearer {sess['token']}"}

        email1 = f"rec1_{uuid.uuid4().hex[:6]}@org.com"
        inv_res = self.client.post("/api/auth/invite-hr", headers=admin_headers, json={
            "email": email1,
            "organization_id": org_id,
            "org_role": "RECRUITER",
            "expire_days": 7
        })
        inv_code = inv_res.json()["invitation_code"]

        # First claim succeeds
        reg1 = self.client.post("/api/auth/register-hr", json={
            "email": email1,
            "password": "Password123!#",
            "full_name": "Recruiter One",
            "invitation_code": inv_code
        })
        self.assertEqual(reg1.status_code, 201)

        # Second claim with same code fails
        email2 = f"rec2_{uuid.uuid4().hex[:6]}@org.com"
        reg2 = self.client.post("/api/auth/register-hr", json={
            "email": email2,
            "password": "Password123!#",
            "full_name": "Recruiter Two",
            "invitation_code": inv_code
        })
        self.assertEqual(reg2.status_code, 403)
        self.assertIn("already been used", reg2.json()["detail"].lower())

    # -------------------------------------------------------------
    # P1-20: HR A accesses Organization B data
    # -------------------------------------------------------------
    def test_p1_20_hr_cross_organization_access_denied(self):
        # Create HR A in Org A
        hr_a_uid = str(uuid.uuid4())
        org_a = f"org_a_{uuid.uuid4().hex[:6]}"
        with get_db_connection(self.test_db_path) as conn:
            conn.execute("INSERT INTO organizations (id, name, slug) VALUES (?, 'Org A', ?)", (org_a, org_a))
            conn.execute("INSERT INTO users (id, email, password_hash, full_name, role) VALUES (?, 'hra@a.com', 'h', 'HR A', 'HR')", (hr_a_uid,))
            conn.execute("INSERT INTO organization_memberships (id, organization_id, user_id, org_role) VALUES (?, ?, ?, 'RECRUITER')", (str(uuid.uuid4()), org_a, hr_a_uid))

            # Create Org B
            org_b = f"org_b_{uuid.uuid4().hex[:6]}"
            conn.execute("INSERT INTO organizations (id, name, slug) VALUES (?, 'Org B', ?)", (org_b, org_b))

        sess = create_session(hr_a_uid, db_path=self.test_db_path)
        headers = {"Authorization": f"Bearer {sess['token']}"}

        # HR A attempts to query questions for Org B
        res = self.client.get(f"/api/hr/questions?organization_id={org_b}", headers=headers)
        self.assertEqual(res.status_code, 403)

    # -------------------------------------------------------------
    # P1-21: HR A changes a resource ID to access Organization B
    # -------------------------------------------------------------
    def test_p1_21_hr_resource_id_tampering_denied(self):
        hr_a_uid = str(uuid.uuid4())
        org_a = f"org_a_{uuid.uuid4().hex[:6]}"
        org_b = f"org_b_{uuid.uuid4().hex[:6]}"
        q_b_id = str(uuid.uuid4())

        with get_db_connection(self.test_db_path) as conn:
            conn.execute("INSERT INTO organizations (id, name, slug) VALUES (?, 'Org A', ?)", (org_a, org_a))
            conn.execute("INSERT INTO organizations (id, name, slug) VALUES (?, 'Org B', ?)", (org_b, org_b))
            conn.execute("INSERT INTO users (id, email, password_hash, full_name, role) VALUES (?, 'hra_tamp@a.com', 'h', 'HR A', 'HR')", (hr_a_uid,))
            conn.execute("INSERT INTO organization_memberships (id, organization_id, user_id, org_role) VALUES (?, ?, ?, 'RECRUITER')", (str(uuid.uuid4()), org_a, hr_a_uid))

            # Question owned by Org B
            conn.execute("""
                INSERT INTO questions (
                    id, organization_id, created_by, source_type, skill_tags, competency,
                    response_format, difficulty, question_text, options, answer_key, explanation, review_status, version
                )
                VALUES (
                    ?, ?, NULL, 'SKILL_BASED', '["Python"]', 'CODE_COMPREHENSION',
                    'SINGLE_SELECT', 'BEGINNER', 'Secret Question?', '["A"]', '["A"]', 'Exp', 'PUBLISHED', 1
                )
            """, (q_b_id, org_b))

        sess = create_session(hr_a_uid, db_path=self.test_db_path)
        headers = {"Authorization": f"Bearer {sess['token']}"}

        # Attempt to access Org B question with Org A parameter
        res1 = self.client.get(f"/api/hr/questions/{q_b_id}?organization_id={org_a}", headers=headers)
        self.assertIn(res1.status_code, (403, 404))

        # Attempt to access Org B question with Org B parameter (rejected as non-member)
        res2 = self.client.get(f"/api/hr/questions/{q_b_id}?organization_id={org_b}", headers=headers)
        self.assertEqual(res2.status_code, 403)

    # -------------------------------------------------------------
    # P1-22: Unauthenticated client calls protected endpoint
    # -------------------------------------------------------------
    def test_p1_22_unauthenticated_request_rejected(self):
        res1 = self.client.get("/api/auth/me")
        self.assertEqual(res1.status_code, 401)
        res2 = self.client.get("/api/hr/questions")
        self.assertEqual(res2.status_code, 401)
        res3 = self.client.get("/api/candidate/assessments/assigned")
        self.assertEqual(res3.status_code, 401)

    # -------------------------------------------------------------
    # P1-23: Database integrity & cascading safety
    # -------------------------------------------------------------
    def test_p1_23_database_foreign_key_and_rollback(self):
        with get_db_connection(self.test_db_path) as conn:
            # Transaction rollback verification
            try:
                conn.execute("INSERT INTO users (id, email, password_hash, full_name, role) VALUES ('u_rollback', 'rb@test.com', 'h', 'Rollback', 'USER')")
                # Invalid second insert to force rollback
                conn.execute("INSERT INTO organization_memberships (id, organization_id, user_id) VALUES ('m_fail', 'nonexistent_org', 'u_rollback')")
            except Exception:
                pass

            # Foreign key must prevent orphaned membership
            orphaned = conn.execute("SELECT * FROM organization_memberships WHERE id = 'm_fail'").fetchone()
            self.assertIsNone(orphaned)


if __name__ == "__main__":
    unittest.main()
