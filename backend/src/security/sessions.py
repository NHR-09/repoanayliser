import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

from ..db.connection import get_db_connection
from ..config import settings

def hash_token(raw_token: str) -> str:
    """Compute SHA-256 hex digest of raw token."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

def create_session(
    user_id: str,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None,
    expire_hours: Optional[int] = None,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate an opaque bearer token and CSRF token, storing their SHA-256 hashes in the database.
    Returns dictionary with raw tokens (to return to user/set in cookies) and metadata.
    """
    raw_token = secrets.token_urlsafe(32)
    token_digest = hash_token(raw_token)
    
    raw_csrf = secrets.token_urlsafe(32)
    csrf_digest = hash_token(raw_csrf)
    
    session_id = str(uuid.uuid4())
    
    hours = expire_hours if expire_hours is not None else settings.session_expire_hours
    expires_at = datetime.now(timezone.utc) + timedelta(hours=hours)
    expires_at_iso = expires_at.isoformat()
    
    with get_db_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO auth_sessions (id, token_hash, user_id, csrf_token_hash, expires_at, user_agent, ip_address)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (session_id, token_digest, user_id, csrf_digest, expires_at_iso, user_agent, ip_address)
        )
        
    return {
        "session_id": session_id,
        "token": raw_token,
        "csrf_token": raw_csrf,
        "expires_at": expires_at_iso
    }

def validate_session(raw_token: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Validate a raw bearer token against stored token hashes.
    Verifies that the session exists, is not revoked, has not expired,
    and that the user account is active.
    Returns user info with organization memberships if valid, else None.
    """
    if not raw_token:
        return None
        
    token_digest = hash_token(raw_token)
    
    with get_db_connection(db_path) as conn:
        row = conn.execute(
            """
            SELECT s.id as session_id, s.csrf_token_hash, s.expires_at, s.revoked_at,
                   u.id as user_id, u.email, u.full_name, u.role, u.is_active
            FROM auth_sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.token_hash = ?
            """,
            (token_digest,)
        ).fetchone()
        
        if not row:
            return None
            
        # Check revocation
        if row["revoked_at"] is not None:
            return None
            
        # Check expiration
        try:
            expires_at_str = row["expires_at"]
            if isinstance(expires_at_str, str):
                expires_at = datetime.fromisoformat(expires_at_str)
            else:
                expires_at = expires_at_str
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at < datetime.now(timezone.utc):
                return None
        except Exception:
            return None
            
        # Check user active status
        if not row["is_active"]:
            return None
            
        # Fetch organization memberships for HR users
        memberships = conn.execute(
            """
            SELECT om.organization_id, om.org_role, o.name as org_name, o.slug as org_slug
            FROM organization_memberships om
            JOIN organizations o ON om.organization_id = o.id
            WHERE om.user_id = ?
            """,
            (row["user_id"],)
        ).fetchall()
        
        orgs: List[Dict[str, Any]] = [
            {
                "organization_id": m["organization_id"],
                "org_role": m["org_role"],
                "org_name": m["org_name"],
                "org_slug": m["org_slug"]
            }
            for m in memberships
        ]
        
        return {
            "id": row["user_id"],
            "email": row["email"],
            "full_name": row["full_name"],
            "role": row["role"],
            "is_active": bool(row["is_active"]),
            "session_id": row["session_id"],
            "csrf_token_hash": row["csrf_token_hash"],
            "organizations": orgs
        }

def revoke_session(raw_token: str, db_path: Optional[str] = None) -> bool:
    """Revoke an active session by setting revoked_at timestamp."""
    if not raw_token:
        return False
        
    token_digest = hash_token(raw_token)
    with get_db_connection(db_path) as conn:
        cursor = conn.execute(
            """
            UPDATE auth_sessions
            SET revoked_at = CURRENT_TIMESTAMP
            WHERE token_hash = ? AND revoked_at IS NULL
            """,
            (token_digest,)
        )
        return cursor.rowcount > 0
