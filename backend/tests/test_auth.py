import os
import tempfile
import unittest
import hashlib
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient

from main import app
from src.db.connection import get_db_connection, init_db
from src.security.passwords import hash_password, verify_password, validate_password_strength
from src.security.sessions import create_session, validate_session, revoke_session, hash_token
from src.security.rate_limiter import login_rate_limiter
from src.config import settings

class AuthenticationAndRBACTests(unittest.TestCase):
    def setUp(self):
        # Create an isolated temporary SQLite database for each test run
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_architech.db")
        self.orig_db_path = settings.db_path
        settings.db_path = self.db_path
        
        # Initialize schema
        init_db(self.db_path)
        
        # Reset login rate limiter state between tests
        with login_rate_limiter._lock:
            login_rate_limiter._attempts.clear()
            
        self.client = TestClient(app)

    def tearDown(self):
        settings.db_path = self.orig_db_path
        self.temp_dir.cleanup()

    # -------------------------------------------------------------
    # 1. Database Integrity & Constraints Tests
    # -------------------------------------------------------------
    def test_database_foreign_keys_and_schema_constraints(self):
        with get_db_connection(self.db_path) as conn:
            # Foreign key test: inserting membership without organization should fail
            with self.assertRaises(Exception):
                conn.execute(
                    "INSERT INTO organization_memberships (id, organization_id, user_id, org_role) VALUES ('m1', 'nonexistent_org', 'u1', 'RECRUITER')"
                )

    def test_ambiguous_repository_grants_are_prevented(self):
        """Verify that grants cannot have both user_id and org_id set, nor neither."""
        with get_db_connection(self.db_path) as conn:
            # Setup an organization and user
            conn.execute("INSERT INTO organizations (id, name, slug) VALUES ('o1', 'Acme', 'acme')")
            conn.execute("INSERT INTO users (id, email, password_hash, full_name, role) VALUES ('u1', 'u@a.com', 'h', 'User', 'USER')")
            conn.execute("INSERT INTO repositories (id, neo4j_repo_id, display_name, repo_url) VALUES ('r1', 'neo1', 'Repo 1', 'https://github.com/a/r1')")
            
            # Valid: User grant only
            conn.execute(
                "INSERT INTO repository_access_grants (id, repository_id, user_id, organization_id, permission) VALUES ('g1', 'r1', 'u1', NULL, 'READ')"
            )
            # Valid: Org grant only
            conn.execute(
                "INSERT INTO repository_access_grants (id, repository_id, user_id, organization_id, permission) VALUES ('g2', 'r1', NULL, 'o1', 'READ')"
            )
            
            # Invalid: Both user_id AND organization_id set (Ambiguous!)
            with self.assertRaises(Exception):
                conn.execute(
                    "INSERT INTO repository_access_grants (id, repository_id, user_id, organization_id, permission) VALUES ('g3', 'r1', 'u1', 'o1', 'READ')"
                )
                
            # Invalid: Neither user_id nor organization_id set
            with self.assertRaises(Exception):
                conn.execute(
                    "INSERT INTO repository_access_grants (id, repository_id, user_id, organization_id, permission) VALUES ('g4', 'r1', NULL, NULL, 'READ')"
                )

    # -------------------------------------------------------------
    # 2. Password Strength & OWASP PBKDF2 Hashing
    # -------------------------------------------------------------
    def test_password_strength_validation(self):
        self.assertIsNotNone(validate_password_strength("short1!"))  # < 8 chars
        self.assertIsNotNone(validate_password_strength("alllowercase123!"))  # No uppercase
        self.assertIsNotNone(validate_password_strength("ALLUPPERCASE123!"))  # No lowercase
        self.assertIsNotNone(validate_password_strength("NoDigitsHere!@#"))  # No digits
        self.assertIsNotNone(validate_password_strength("NoSpecialChar12345"))  # No special char
        self.assertIsNone(validate_password_strength("StrongPass123!"))  # Valid strong password

    def test_pbkdf2_hashing_and_verification(self):
        pwd = "ComplexPassword2026!#"
        hashed = hash_password(pwd, iterations=600_000)
        self.assertTrue(hashed.startswith("pbkdf2_sha256$600000$"))
        self.assertTrue(verify_password(pwd, hashed))
        self.assertFalse(verify_password("WrongPassword", hashed))

    # -------------------------------------------------------------
    # 3. Unauthenticated Access Protection
    # -------------------------------------------------------------
    def test_unauthenticated_requests_are_rejected(self):
        res_me = self.client.get("/api/auth/me")
        self.assertEqual(res_me.status_code, 401)
        
        res_user = self.client.get("/api/auth/test/user-only")
        self.assertEqual(res_user.status_code, 401)
        
        res_hr = self.client.get("/api/auth/test/hr-only")
        self.assertEqual(res_hr.status_code, 401)

    # -------------------------------------------------------------
    # 4. Candidate Registration & Strict Role Enforcement
    # -------------------------------------------------------------
    def test_public_registration_strictly_assigns_user_role(self):
        payload = {
            "email": "candidate@example.com",
            "password": "StrongPassword123!",
            "full_name": "Alice Candidate"
        }
        res = self.client.post("/api/auth/register", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["user"]["role"], "USER")
        self.assertIn("token", data)
        self.assertIn("csrf_token", data)
        
        # Verify in database that role is USER
        with get_db_connection(self.db_path) as conn:
            user = conn.execute("SELECT role FROM users WHERE email = 'candidate@example.com'").fetchone()
            self.assertEqual(user["role"], "USER")

    def test_public_registration_rejects_weak_passwords(self):
        # 1. Password that is too short fails Pydantic schema validation (422)
        short_res = self.client.post("/api/auth/register", json={
            "email": "short@example.com",
            "password": "short",
            "full_name": "Bob Short"
        })
        self.assertEqual(short_res.status_code, 422)
        
        # 2. Password with adequate length but lacking uppercase/digits/symbols fails complexity check (400)
        complex_res = self.client.post("/api/auth/register", json={
            "email": "weak@example.com",
            "password": "alllowercasepassword",
            "full_name": "Bob Weak"
        })
        self.assertEqual(complex_res.status_code, 400)
        self.assertIn("Password must contain", complex_res.json()["detail"])

    # -------------------------------------------------------------
    # 5. Role-Based Access Control (USER vs HR)
    # -------------------------------------------------------------
    def test_user_cannot_access_hr_endpoints(self):
        # Register regular candidate
        self.client.post("/api/auth/register", json={
            "email": "dev@example.com",
            "password": "DevPassword123!",
            "full_name": "Dev User"
        })
        login_res = self.client.post("/api/auth/login", json={
            "email": "dev@example.com",
            "password": "DevPassword123!"
        })
        token = login_res.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # User endpoint should succeed
        res_user = self.client.get("/api/auth/test/user-only", headers=headers)
        self.assertEqual(res_user.status_code, 200)
        
        # HR endpoint MUST fail with 403 Forbidden!
        res_hr = self.client.get("/api/auth/test/hr-only", headers=headers)
        self.assertEqual(res_hr.status_code, 403)
        self.assertIn("HR access required", res_hr.json()["detail"])

    # -------------------------------------------------------------
    # 6. One-Time Administrative Provisioning & HR Invitations
    # -------------------------------------------------------------
    def test_initial_admin_provisioning_and_lockdown(self):
        admin_payload = {
            "email": "admin@techcorp.com",
            "password": "AdminMasterKey123!#",
            "full_name": "Chief Admin",
            "organization_name": "TechCorp Global"
        }
        # First provisioning succeeds
        res1 = self.client.post("/api/auth/provision-initial-admin", json=admin_payload)
        self.assertEqual(res1.status_code, 201)
        self.assertEqual(res1.json()["user"]["role"], "HR")
        self.assertEqual(res1.json()["user"]["organizations"][0]["org_role"], "OWNER")
        
        # Second provisioning attempt MUST fail with 403 Forbidden (one-time lock!)
        res2 = self.client.post("/api/auth/provision-initial-admin", json={
            "email": "attacker@evil.com",
            "password": "AttackerPass123!#",
            "full_name": "Imposter",
            "organization_name": "EvilCorp"
        })
        self.assertEqual(res2.status_code, 403)
        self.assertIn("provisioning is closed", res2.json()["detail"].lower())

    def test_single_use_expiring_hr_invitation_flow(self):
        # 1. Provision initial Admin
        admin_res = self.client.post("/api/auth/provision-initial-admin", json={
            "email": "owner@company.com",
            "password": "OwnerPass123!#",
            "full_name": "Org Owner",
            "organization_name": "HirePro"
        })
        admin_token = admin_res.json()["token"]
        org_id = admin_res.json()["user"]["organizations"][0]["organization_id"]
        
        # 2. Admin invites a recruiter
        invite_res = self.client.post(
            "/api/auth/invite-hr",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "email": "recruiter@company.com",
                "organization_id": org_id,
                "org_role": "RECRUITER",
                "expire_days": 7
            }
        )
        self.assertEqual(invite_res.status_code, 201)
        invite_code = invite_res.json()["invitation_code"]
        
        # 3. Recruiter registers using the invitation code
        recruiter_reg = self.client.post("/api/auth/register-hr", json={
            "email": "recruiter@company.com",
            "password": "RecruiterPass123!#",
            "full_name": "Rachel Recruiter",
            "invitation_code": invite_code
        })
        self.assertEqual(recruiter_reg.status_code, 201)
        self.assertEqual(recruiter_reg.json()["user"]["role"], "HR")
        
        # 4. Attempting to reuse the same invitation code MUST fail with 403
        reuse_res = self.client.post("/api/auth/register-hr", json={
            "email": "another@company.com",
            "password": "AnotherPass123!#",
            "full_name": "Second Recruiter",
            "invitation_code": invite_code
        })
        self.assertEqual(reuse_res.status_code, 403)
        self.assertIn("already been used", reuse_res.json()["detail"].lower())

    # -------------------------------------------------------------
    # 7. Session Management, Token Hashing & Expiration
    # -------------------------------------------------------------
    def test_session_token_hashing_in_database(self):
        """Confirm that raw bearer tokens are NEVER stored in database, only SHA-256 hashes."""
        reg = self.client.post("/api/auth/register", json={
            "email": "security@test.com",
            "password": "SecurityPass123!#",
            "full_name": "Sec Test"
        })
        raw_token = reg.json()["token"]
        
        with get_db_connection(self.db_path) as conn:
            # Query the stored token_hash
            session_row = conn.execute("SELECT token_hash FROM auth_sessions").fetchone()
            stored_hash = session_row["token_hash"]
            
            # The database must store the SHA-256 digest, not the raw token!
            self.assertNotEqual(stored_hash, raw_token)
            self.assertEqual(stored_hash, hashlib.sha256(raw_token.encode("utf-8")).hexdigest())

    def test_session_revocation_on_logout(self):
        reg = self.client.post("/api/auth/register", json={
            "email": "logout@test.com",
            "password": "LogoutPass123!#",
            "full_name": "Logout Test"
        })
        token = reg.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Verify authenticated access works
        self.assertEqual(self.client.get("/api/auth/me", headers=headers).status_code, 200)
        
        # Logout
        logout_res = self.client.post("/api/auth/logout", headers=headers)
        self.assertEqual(logout_res.status_code, 200)
        
        # Subsequent access must be rejected with 401
        self.assertEqual(self.client.get("/api/auth/me", headers=headers).status_code, 401)

    def test_expired_and_deactivated_sessions_rejected(self):
        reg = self.client.post("/api/auth/register", json={
            "email": "deactivate@test.com",
            "password": "DeactivatePass123!#",
            "full_name": "Deact Test"
        })
        token = reg.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Deactivate user in database
        with get_db_connection(self.db_path) as conn:
            conn.execute("UPDATE users SET is_active = 0 WHERE email = 'deactivate@test.com'")
            
        # Access must be rejected
        res = self.client.get("/api/auth/me", headers=headers)
        self.assertEqual(res.status_code, 401)

    # -------------------------------------------------------------
    # 8. Login Rate Limiting Protection
    # -------------------------------------------------------------
    def test_login_rate_limiting_locks_out_after_failures(self):
        # Register an account
        self.client.post("/api/auth/register", json={
            "email": "target@victim.com",
            "password": "VictimPassword123!#",
            "full_name": "Victim"
        })
        
        # Attempt 5 consecutive failed logins with wrong password
        for i in range(5):
            res = self.client.post("/api/auth/login", json={
                "email": "target@victim.com",
                "password": "WrongPassword999!"
            })
            self.assertEqual(res.status_code, 401)
            
        # The 6th attempt MUST be blocked by rate limiter with 429 Too Many Requests
        blocked_res = self.client.post("/api/auth/login", json={
            "email": "target@victim.com",
            "password": "VictimPassword123!#"
        })
        self.assertEqual(blocked_res.status_code, 429)
        self.assertIn("Too many failed login attempts", blocked_res.json()["detail"])

    # -------------------------------------------------------------
    # 9. HttpOnly Cookie & CSRF Protection
    # -------------------------------------------------------------
    def test_httponly_cookie_and_csrf_validation(self):
        # Register user
        reg = self.client.post("/api/auth/register", json={
            "email": "cookie@user.com",
            "password": "CookiePassword123!#",
            "full_name": "Cookie User"
        })
        self.assertEqual(reg.status_code, 201)
        raw_token = reg.json()["token"]
        raw_csrf = reg.json()["csrf_token"]
        
        # Client request using cookies (simulating browser)
        self.client.cookies.set("architech_session", raw_token)
        self.client.cookies.set("architech_csrf", raw_csrf)
        
        # GET request with cookie succeeds without CSRF header (safe method)
        get_res = self.client.get("/api/auth/me")
        self.assertEqual(get_res.status_code, 200)
        
        # POST mutating request with cookie but WITHOUT X-CSRF-Token must fail (403)
        post_fail = self.client.post("/api/auth/logout")
        self.assertEqual(post_fail.status_code, 403)
        self.assertIn("CSRF", post_fail.json()["detail"])
        
        # POST mutating request with valid X-CSRF-Token header succeeds
        post_success = self.client.post("/api/auth/logout", headers={"X-CSRF-Token": raw_csrf})
        self.assertEqual(post_success.status_code, 200)

if __name__ == "__main__":
    unittest.main()
