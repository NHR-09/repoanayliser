from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import logging

from ..security.dependencies import require_user
from ..services.assessment_assignment_service import AssessmentAssignmentService
from ..services.assessment_attempt_service import AssessmentAttemptService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/candidate/assessments", tags=["Candidate Assessment Workspace"])

assignment_service = AssessmentAssignmentService()
attempt_service = AssessmentAttemptService()

# ---------------------------------------------------------
# Request Models
# ---------------------------------------------------------

class ClaimInvitationRequest(BaseModel):
    token: str = Field(..., min_length=10)

class StartAttemptRequest(BaseModel):
    assignment_id: str

class AutosaveAnswerRequest(BaseModel):
    question_id: str
    candidate_response: Any

# ---------------------------------------------------------
# Candidate Endpoints
# ---------------------------------------------------------

@router.get("/assigned")
async def list_assigned_assessments(
    current_user: Dict[str, Any] = Depends(require_user),
):
    """List all assessments assigned to the authenticated candidate."""
    return {"assigned": assignment_service.list_candidate_assigned_assessments(current_user)}

@router.post("/claim")
async def claim_invitation(
    payload: ClaimInvitationRequest,
    current_user: Dict[str, Any] = Depends(require_user),
):
    """Claim an assessment invitation link."""
    try:
        claimed = assignment_service.claim_invitation(payload.token, current_user)
        return {"claimed": claimed, "message": "Invitation claimed successfully."}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

@router.post("/start")
async def start_assessment_attempt(
    payload: StartAttemptRequest,
    current_user: Dict[str, Any] = Depends(require_user),
):
    """Start or resume a timed assessment attempt."""
    try:
        attempt_view = attempt_service.start_attempt(current_user, payload.assignment_id)
        return {"attempt": attempt_view}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

@router.get("/attempts/{attempt_id}")
async def get_active_attempt(
    attempt_id: str,
    current_user: Dict[str, Any] = Depends(require_user),
):
    """Retrieve active attempt workspace view with timer and redacted questions."""
    # Attempt service resume
    try:
        # We can fetch attempt by calling start_attempt with existing assignment or direct lookup
        from src.db.connection import get_db_connection
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        with get_db_connection(attempt_service.db_path) as conn:
            att = conn.execute(
                "SELECT * FROM assessment_attempts WHERE id = ? AND user_id = ?",
                (attempt_id, current_user["id"]),
            ).fetchone()
            if not att:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found.")
            if att["status"] != "IN_PROGRESS":
                return {"attempt": {"id": attempt_id, "status": att["status"]}}
            return {"attempt": attempt_service._build_candidate_attempt_view(conn, dict(att), now)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/attempts/{attempt_id}/answers")
async def autosave_answer(
    attempt_id: str,
    payload: AutosaveAnswerRequest,
    current_user: Dict[str, Any] = Depends(require_user),
):
    """Autosave candidate answer with server-authoritative deadline check."""
    try:
        return attempt_service.autosave_answer(
            candidate_user=current_user,
            attempt_id=attempt_id,
            question_id=payload.question_id,
            candidate_response=payload.candidate_response,
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

@router.post("/attempts/{attempt_id}/submit")
async def submit_attempt(
    attempt_id: str,
    current_user: Dict[str, Any] = Depends(require_user),
):
    """Finalize assessment attempt and trigger objective scoring."""
    try:
        result = attempt_service.submit_attempt(current_user, attempt_id)
        return {"result": result, "message": "Assessment submitted successfully."}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

@router.get("/attempts/{attempt_id}/result")
async def get_attempt_result(
    attempt_id: str,
    current_user: Dict[str, Any] = Depends(require_user),
):
    """Retrieve score and feedback according to the assessment's release policy."""
    try:
        result = attempt_service.get_attempt_result_for_candidate(current_user, attempt_id)
        return {"result": result}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))


# ---------------------------------------------------------
# Read-only Codebase Exploration for Active Attempt
# ---------------------------------------------------------

def _resolve_attempt_repo_dir(attempt_id: str, user_id: str):
    import os
    from src.db.connection import get_db_connection
    with get_db_connection(attempt_service.db_path) as conn:
        row = conn.execute(
            """
            SELECT a.id, v.repository_id, r.repo_url, r.display_name
            FROM assessment_attempts a
            JOIN assessment_versions v ON a.assessment_version_id = v.id
            LEFT JOIN repositories r ON v.repository_id = r.id
            WHERE a.id = ? AND a.user_id = ?
            """,
            (attempt_id, user_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found.")
        
        repo_url = row["repo_url"]
        display_name = row["display_name"]
        if not repo_url and not display_name:
            return None, None

        workspace_base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "workspace"))
        candidates = []
        if display_name:
            candidates.append(os.path.join(workspace_base, display_name))
        if repo_url:
            cleaned = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
            candidates.append(os.path.join(workspace_base, cleaned))

        for cand in candidates:
            if os.path.isdir(cand):
                return cand, os.path.basename(cand)
        return None, None


@router.get("/attempts/{attempt_id}/codebase/files")
async def get_attempt_codebase_files(
    attempt_id: str,
    current_user: Dict[str, Any] = Depends(require_user),
):
    """Retrieve safe read-only list of repository files for assessment workspace."""
    import os
    repo_path, repo_name = _resolve_attempt_repo_dir(attempt_id, current_user["id"])
    if not repo_path:
        return {"files": [], "repo_name": None}

    file_list = []
    ignored_dirs = {".git", ".venv", "node_modules", "__pycache__", ".idea", ".vscode", "dist", "build"}
    ignored_exts = {".pyc", ".png", ".jpg", ".jpeg", ".ico", ".svg", ".zip", ".tar", ".gz", ".exe", ".bin"}

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in ignored_dirs and not d.startswith(".")]
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in ignored_exts or f.startswith("."):
                continue
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, repo_path).replace("\\", "/")
            file_list.append(rel_path)
            if len(file_list) >= 500:
                break
        if len(file_list) >= 500:
            break

    return {"files": sorted(file_list), "repo_name": repo_name}


@router.get("/attempts/{attempt_id}/codebase/file-content")
async def get_attempt_codebase_file_content(
    attempt_id: str,
    path: str,
    current_user: Dict[str, Any] = Depends(require_user),
):
    """Read file content with strict path traversal validation."""
    import os
    repo_path, repo_name = _resolve_attempt_repo_dir(attempt_id, current_user["id"])
    if not repo_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No repository attached to this assessment.")

    clean_path = os.path.normpath(path).lstrip("/\\")
    full_path = os.path.abspath(os.path.join(repo_path, clean_path))

    if not full_path.startswith(os.path.abspath(repo_path)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Path traversal forbidden.")
    if not os.path.isfile(full_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")

    try:
        with open(full_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(150000)
        return {
            "path": clean_path.replace("\\", "/"),
            "content": content,
            "lines_count": len(content.splitlines()),
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to read file: {e}")

