from fastapi import Request, Response, HTTPException, status, Depends
from typing import Optional, Dict, Any, Tuple
import hashlib
import hmac

from .sessions import validate_session

SESSION_COOKIE_NAME = "architech_session"
CSRF_COOKIE_NAME = "architech_csrf"
CSRF_HEADER_NAME = "X-CSRF-Token"

def set_session_cookies(
    response: Response,
    token: str,
    csrf_token: str,
    max_age_seconds: int = 86400,
    secure: bool = False
):
    """
    Set secure HttpOnly session cookie and accessible CSRF cookie.
    Lax SameSite prevents cross-site leakage while allowing normal navigation.
    """
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=secure,
        max_age=max_age_seconds,
        path="/"
    )
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf_token,
        httponly=False,  # Readable by frontend JavaScript to populate X-CSRF-Token header
        samesite="lax",
        secure=secure,
        max_age=max_age_seconds,
        path="/"
    )

def clear_session_cookies(response: Response):
    """Clear session and CSRF cookies on logout."""
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    response.delete_cookie(key=CSRF_COOKIE_NAME, path="/")

async def extract_token_and_source(request: Request) -> Tuple[str, str]:
    """
    Extract session token from Authorization header, X-Session-Token header,
    or HttpOnly cookie.
    Returns (raw_token, source) where source is 'bearer' or 'cookie'.
    """
    auth_header = request.headers.get("Authorization")
    if auth_header:
        parts = auth_header.strip().split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1], "bearer"
        elif len(parts) == 1:
            return parts[0], "bearer"
            
    x_token = request.headers.get("X-Session-Token")
    if x_token:
        return x_token.strip(), "bearer"
        
    cookie_token = request.cookies.get(SESSION_COOKIE_NAME)
    if cookie_token:
        return cookie_token.strip(), "cookie"
        
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing authentication credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )

async def get_current_user(request: Request) -> Dict[str, Any]:
    """
    Validate active session from header or cookie.
    Enforces CSRF protection on state-changing requests when authenticated via cookie.
    """
    token, source = await extract_token_and_source(request)
    user = validate_session(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or revoked session",
            headers={"WWW-Authenticate": "Bearer"}
        )
        
    # Enforce CSRF protection for cookie-authenticated mutating requests
    if source == "cookie" and request.method in ("POST", "PUT", "DELETE", "PATCH"):
        csrf_header = request.headers.get(CSRF_HEADER_NAME)
        csrf_cookie = request.cookies.get(CSRF_COOKIE_NAME)
        
        if not csrf_header or not csrf_cookie or csrf_header != csrf_cookie:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF validation failed: missing or mismatched CSRF token"
            )
            
        stored_csrf_hash = user.get("csrf_token_hash")
        if stored_csrf_hash:
            header_hash = hashlib.sha256(csrf_header.encode("utf-8")).hexdigest()
            if not hmac.compare_digest(header_hash, stored_csrf_hash):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="CSRF validation failed: invalid CSRF token"
                )
                
    return user

async def require_user(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Ensure user is an active authenticated user."""
    if current_user.get("role") not in ("USER", "HR", "ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: invalid account role"
        )
    return current_user

async def require_hr(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Ensure user has the HR or ADMIN role."""
    if current_user.get("role") not in ("HR", "ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="HR access required: candidates cannot access this resource"
        )
    return current_user

def require_org_hr(organization_id: str):
    """
    Factory dependency ensuring the authenticated user has HR access
    specifically within the targeted organization.
    """
    async def _dependency(current_user: Dict[str, Any] = Depends(require_hr)) -> Dict[str, Any]:
        if current_user.get("role") == "ADMIN":
            return current_user
            
        user_org_ids = [
            org["organization_id"] for org in current_user.get("organizations", [])
        ]
        if organization_id not in user_org_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: you are not an authorized HR member of organization '{organization_id}'"
            )
        return current_user
        
    return _dependency
