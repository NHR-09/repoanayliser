from fastapi import APIRouter, HTTPException, status, Depends, Request, Response
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import uuid
import re
import secrets
import hashlib
from datetime import datetime, timedelta, timezone

from ..db.connection import get_db_connection
from ..security.passwords import hash_password, verify_password, validate_password_strength
from ..security.sessions import create_session, revoke_session
from ..security.rate_limiter import login_rate_limiter
from ..security.dependencies import (
    extract_token_and_source,
    get_current_user,
    require_user,
    require_hr,
    set_session_cookies,
    clear_session_cookies
)
from ..security.provision_admin import provision_initial_admin

router = APIRouter(prefix="/api/auth", tags=["Authentication & RBAC"])

# ---------------------------------------------------------
# Request & Response Models
# ---------------------------------------------------------

class UserRegisterRequest(BaseModel):
    """
    Public candidate registration.
    Server strictly enforces role = 'USER'.
    """
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=255)

class HrRegisterRequest(BaseModel):
    """
    HR / Recruiter registration requiring an expiring, single-use invitation code.
    """
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=255)
    invitation_code: str = Field(..., min_length=4)

class InitialAdminProvisionRequest(BaseModel):
    """
    One-time administrative provisioning request.
    Only permissible when zero HR/Admin accounts exist.
    """
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=255)
    organization_name: str = Field(..., min_length=2, max_length=255)

class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1)

class HrInviteRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    organization_id: str
    org_role: str = Field("RECRUITER", pattern="^(OWNER|ADMIN|RECRUITER)$")
    expire_days: int = Field(7, ge=1, le=30)

# ---------------------------------------------------------
# Authentication Endpoints
# ---------------------------------------------------------

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(req: UserRegisterRequest, request: Request, response: Response):
    """
    Register a candidate developer account.
    Server strictly assigns role = 'USER'.
    Enforces OWASP password complexity and sets HttpOnly session cookies.
    """
    email_clean = req.email.strip().lower()
    if "@" not in email_clean or "." not in email_clean:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email address format"
        )
        
    pw_error = validate_password_strength(req.password)
    if pw_error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=pw_error
        )
        
    user_id = str(uuid.uuid4())
    pw_hash = hash_password(req.password)
    
    with get_db_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM users WHERE email = ?",
            (email_clean,)
        ).fetchone()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email address already exists"
            )
            
        conn.execute(
            """
            INSERT INTO users (id, email, password_hash, full_name, role, is_active)
            VALUES (?, ?, ?, ?, 'USER', 1)
            """,
            (user_id, email_clean, pw_hash, req.full_name.strip())
        )
        
    client_ip = request.client.host if request.client else "127.0.0.1"
    user_agent = request.headers.get("user-agent")
    session = create_session(user_id, user_agent=user_agent, ip_address=client_ip)
    
    # Set HttpOnly session cookie + readable CSRF cookie
    set_session_cookies(response, session["token"], session["csrf_token"])
    
    return {
        "status": "success",
        "message": "User registered successfully",
        "token": session["token"],
        "csrf_token": session["csrf_token"],
        "expires_at": session["expires_at"],
        "user": {
            "id": user_id,
            "email": email_clean,
            "full_name": req.full_name.strip(),
            "role": "USER",
            "organizations": []
        }
    }

@router.post("/provision-initial-admin", status_code=status.HTTP_201_CREATED)
async def provision_initial_admin_endpoint(
    req: InitialAdminProvisionRequest,
    request: Request,
    response: Response
):
    """
    One-time administrative provisioning endpoint.
    Permanently disables itself once any HR or ADMIN account exists.
    """
    try:
        result = provision_initial_admin(
            email=req.email,
            password=req.password,
            full_name=req.full_name,
            organization_name=req.organization_name
        )
    except PermissionError as pe:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(pe)
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
        
    client_ip = request.client.host if request.client else "127.0.0.1"
    user_agent = request.headers.get("user-agent")
    session = create_session(result["user_id"], user_agent=user_agent, ip_address=client_ip)
    
    set_session_cookies(response, session["token"], session["csrf_token"])
    
    return {
        "status": "success",
        "message": "Initial administrator provisioned successfully",
        "token": session["token"],
        "csrf_token": session["csrf_token"],
        "expires_at": session["expires_at"],
        "user": {
            "id": result["user_id"],
            "email": result["email"],
            "full_name": req.full_name.strip(),
            "role": "HR",
            "organizations": [
                {
                    "organization_id": result["organization_id"],
                    "org_name": result["organization_name"],
                    "org_slug": result["organization_slug"],
                    "org_role": "OWNER"
                }
            ]
        }
    }

@router.post("/register-hr", status_code=status.HTTP_201_CREATED)
async def register_hr(req: HrRegisterRequest, request: Request, response: Response):
    """
    Register an HR Recruiter account using a single-use expiring invitation code.
    """
    email_clean = req.email.strip().lower()
    if "@" not in email_clean or "." not in email_clean:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email address format"
        )
        
    pw_error = validate_password_strength(req.password)
    if pw_error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=pw_error
        )
        
    code_raw = req.invitation_code.strip()
    code_hash = hashlib.sha256(code_raw.encode("utf-8")).hexdigest()
    
    user_id = str(uuid.uuid4())
    pw_hash = hash_password(req.password)
    
    with get_db_connection() as conn:
        existing = conn.execute("SELECT id FROM users WHERE email = ?", (email_clean,)).fetchone()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email address already exists"
            )
            
        # Verify invitation
        invite = conn.execute(
            """
            SELECT id, organization_id, email, org_role, expires_at, used_at
            FROM hr_invitations
            WHERE invitation_code_hash = ?
            """,
            (code_hash,)
        ).fetchone()
        
        if not invite:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid HR invitation code"
            )
        if invite["used_at"] is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="HR invitation code has already been used"
            )
            
        if invite["email"] and invite["email"].strip().lower() != email_clean:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="HR invitation code was issued to a different email address"
            )

        expires_at = datetime.fromisoformat(invite["expires_at"])
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="HR invitation code has expired"
            )
            
        org_id = invite["organization_id"]
        org_role = invite["org_role"]
        
        org_row = conn.execute("SELECT name, slug FROM organizations WHERE id = ?", (org_id,)).fetchone()
        if not org_row:
            raise HTTPException(status_code=404, detail="Target organization not found")
        org_name = org_row["name"]
        org_slug = org_row["slug"]
        
        # Atomically mark invitation as used
        conn.execute(
            "UPDATE hr_invitations SET used_at = CURRENT_TIMESTAMP WHERE id = ?",
            (invite["id"],)
        )
        
        # Create HR user
        conn.execute(
            """
            INSERT INTO users (id, email, password_hash, full_name, role, is_active)
            VALUES (?, ?, ?, ?, 'HR', 1)
            """,
            (user_id, email_clean, pw_hash, req.full_name.strip())
        )
        
        # Assign membership
        conn.execute(
            """
            INSERT INTO organization_memberships (id, organization_id, user_id, org_role)
            VALUES (?, ?, ?, ?)
            """,
            (str(uuid.uuid4()), org_id, user_id, org_role)
        )
        
    client_ip = request.client.host if request.client else "127.0.0.1"
    user_agent = request.headers.get("user-agent")
    session = create_session(user_id, user_agent=user_agent, ip_address=client_ip)
    
    set_session_cookies(response, session["token"], session["csrf_token"])
    
    return {
        "status": "success",
        "message": "HR account created successfully",
        "token": session["token"],
        "csrf_token": session["csrf_token"],
        "expires_at": session["expires_at"],
        "user": {
            "id": user_id,
            "email": email_clean,
            "full_name": req.full_name.strip(),
            "role": "HR",
            "organizations": [
                {
                    "organization_id": org_id,
                    "org_name": org_name,
                    "org_slug": org_slug,
                    "org_role": org_role
                }
            ]
        }
    }

@router.post("/login")
async def login(req: LoginRequest, request: Request, response: Response):
    """
    Authenticate user with rate-limiting protection.
    Returns session token and sets HttpOnly session + CSRF cookies.
    """
    email_clean = req.email.strip().lower()
    client_ip = request.client.host if request.client else "127.0.0.1"
    
    ip_key = f"ip:{client_ip}"
    email_key = f"email:{email_clean}"
    
    # Check rate limiting
    login_rate_limiter.check_rate_limit(ip_key)
    login_rate_limiter.check_rate_limit(email_key)
    
    with get_db_connection() as conn:
        user = conn.execute(
            """
            SELECT id, email, password_hash, full_name, role, is_active
            FROM users
            WHERE email = ?
            """,
            (email_clean,)
        ).fetchone()
        
        if not user or not verify_password(req.password, user["password_hash"]):
            login_rate_limiter.record_failed_attempt(ip_key)
            login_rate_limiter.record_failed_attempt(email_key)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
            
        if not user["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated. Please contact an administrator."
            )
            
        # Clear failed attempts on successful authentication
        login_rate_limiter.clear_failed_attempts(ip_key)
        login_rate_limiter.clear_failed_attempts(email_key)
        
        memberships = conn.execute(
            """
            SELECT om.organization_id, om.org_role, o.name as org_name, o.slug as org_slug
            FROM organization_memberships om
            JOIN organizations o ON om.organization_id = o.id
            WHERE om.user_id = ?
            """,
            (user["id"],)
        ).fetchall()
        
        orgs = [
            {
                "organization_id": m["organization_id"],
                "org_role": m["org_role"],
                "org_name": m["org_name"],
                "org_slug": m["org_slug"]
            }
            for m in memberships
        ]
        
    user_agent = request.headers.get("user-agent")
    session = create_session(user["id"], user_agent=user_agent, ip_address=client_ip)
    
    set_session_cookies(response, session["token"], session["csrf_token"])
    
    return {
        "status": "success",
        "message": "Login successful",
        "token": session["token"],
        "csrf_token": session["csrf_token"],
        "expires_at": session["expires_at"],
        "user": {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "role": user["role"],
            "organizations": orgs
        }
    }

@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Revoke active session and clear session cookies."""
    token, _ = await extract_token_and_source(request)
    revoke_session(token)
    clear_session_cookies(response)
    return {
        "status": "success",
        "message": "Session successfully logged out and revoked"
    }

@router.get("/me")
async def get_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Retrieve details of the currently authenticated user."""
    return {
        "status": "success",
        "user": current_user
    }

@router.post("/invite-hr", status_code=status.HTTP_201_CREATED)
async def invite_hr_member(
    req: HrInviteRequest,
    current_user: Dict[str, Any] = Depends(require_hr)
):
    """
    Allow an authorized HR Admin/Owner to generate a single-use expiring invitation code for a recruiter.
    """
    org_id = req.organization_id
    user_org = next(
        (o for o in current_user.get("organizations", []) if o["organization_id"] == org_id),
        None
    )
    
    if not user_org and current_user.get("role") != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to invite members to this organization"
        )
    if user_org and user_org["org_role"] not in ("OWNER", "ADMIN") and current_user.get("role") != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Organization Owners or Admins can invite new HR members"
        )
        
    raw_invite_code = secrets.token_urlsafe(24)
    code_hash = hashlib.sha256(raw_invite_code.encode("utf-8")).hexdigest()
    invite_id = str(uuid.uuid4())
    expires_at = (datetime.now(timezone.utc) + timedelta(days=req.expire_days)).isoformat()
    
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO hr_invitations (id, organization_id, email, invitation_code_hash, org_role, created_by, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                invite_id,
                org_id,
                req.email.strip().lower(),
                code_hash,
                req.org_role,
                current_user["id"],
                expires_at
            )
        )
        
    return {
        "status": "success",
        "invitation_id": invite_id,
        "invitation_code": raw_invite_code,
        "expires_at": expires_at,
        "organization_id": org_id,
        "target_email": req.email.strip().lower(),
        "assigned_role": req.org_role
    }

# ---------------------------------------------------------
# Protected Example Endpoints (Verifying RBAC Boundaries)
# ---------------------------------------------------------

@router.get("/test/user-only")
async def test_user_endpoint(current_user: Dict[str, Any] = Depends(require_user)):
    """Protected endpoint accessible by all active authenticated accounts."""
    return {
        "status": "success",
        "message": f"Hello {current_user['full_name']}! You have access to user features.",
        "user_id": current_user["id"],
        "role": current_user["role"]
    }

@router.get("/test/hr-only")
async def test_hr_endpoint(current_user: Dict[str, Any] = Depends(require_hr)):
    """Protected endpoint accessible ONLY by HR or ADMIN accounts."""
    return {
        "status": "success",
        "message": f"Hello {current_user['full_name']}! You have verified HR access.",
        "user_id": current_user["id"],
        "role": current_user["role"],
        "organizations": current_user.get("organizations", [])
    }
