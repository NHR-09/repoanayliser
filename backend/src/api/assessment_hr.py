from fastapi import APIRouter, HTTPException, status, Depends, Query, Response
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import logging

from ..security.dependencies import require_hr
from .hr import get_authorized_org_id
from ..services.assessment_service import AssessmentService
from ..services.assessment_assignment_service import AssessmentAssignmentService
from ..services.assessment_analytics_service import AssessmentAnalyticsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/hr/assessments", tags=["HR Assessment Studio"])

assessment_service = AssessmentService()
assignment_service = AssessmentAssignmentService()
analytics_service = AssessmentAnalyticsService()

# ---------------------------------------------------------
# Request Models
# ---------------------------------------------------------

class AssessmentCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = ""
    instructions: Optional[str] = ""
    job_role: Optional[str] = ""
    mode: str = Field("CURATED", pattern="^(CURATED|RANDOMIZED)$")
    repository_id: Optional[str] = None
    question_ids: Optional[List[str]] = []
    blueprint_config: Optional[Dict[str, Any]] = None
    skills_evaluated: Optional[List[str]] = []
    competencies_evaluated: Optional[List[str]] = []
    difficulty_profile: Optional[str] = "BALANCED"
    duration_minutes: int = Field(60, ge=5, le=360)
    passing_score_pct: float = Field(70.0, ge=0.0, le=100.0)
    availability_start: Optional[str] = None
    availability_end: Optional[str] = None
    result_release_policy: str = Field("WITHHOLD_PENDING_REVIEW", pattern="^(IMMEDIATE|WITHHOLD_PENDING_REVIEW|RELEASE_SCORE_ONLY)$")
    max_attempts_per_candidate: int = Field(1, ge=1, le=5)

class AssessmentUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    instructions: Optional[str] = None
    job_role: Optional[str] = None
    mode: Optional[str] = None
    repository_id: Optional[str] = None
    question_ids: Optional[List[str]] = None
    blueprint_config: Optional[Dict[str, Any]] = None
    skills_evaluated: Optional[List[str]] = None
    competencies_evaluated: Optional[List[str]] = None
    duration_minutes: Optional[int] = None
    passing_score_pct: Optional[float] = None
    result_release_policy: Optional[str] = None

class AssignAssessmentRequest(BaseModel):
    candidate_emails: List[str] = Field(..., min_items=1)
    expires_days: int = Field(7, ge=1, le=60)
    max_attempts: int = Field(1, ge=1, le=5)

class RevokeAssignmentRequest(BaseModel):
    reason: Optional[str] = "Revoked by recruiter"

class ScoreOverrideRequest(BaseModel):
    new_score: float = Field(..., ge=0.0)
    reason: str = Field(..., min_length=5)

# ---------------------------------------------------------
# Endpoints
# ---------------------------------------------------------

@router.get("")
async def list_assessments(
    organization_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    search: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(require_hr),
):
    """List assessments belonging to the authenticated HR organization."""
    org_id = get_authorized_org_id(current_user, organization_id)
    return assessment_service.list_assessments(
        organization_id=org_id,
        page=page,
        page_size=pageSize,
        status=status,
        search=search,
    )

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_assessment(
    payload: AssessmentCreateRequest,
    organization_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(require_hr),
):
    """Create a new draft assessment."""
    org_id = get_authorized_org_id(current_user, organization_id)
    user_id = current_user["id"]
    try:
        assessment = assessment_service.create_assessment(
            organization_id=org_id,
            user_id=user_id,
            data=payload.model_dump(),
        )
        return {"assessment": assessment}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

@router.get("/{assessment_id}")
async def get_assessment(
    assessment_id: str,
    organization_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(require_hr),
):
    """Get full details of an assessment including curated questions or blueprint."""
    org_id = get_authorized_org_id(current_user, organization_id)
    try:
        assessment = assessment_service.get_assessment(org_id, assessment_id)
        return {"assessment": assessment}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))

@router.put("/{assessment_id}")
async def update_assessment(
    assessment_id: str,
    payload: AssessmentUpdateRequest,
    organization_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(require_hr),
):
    """Update assessment draft. If published, creates a new draft version."""
    org_id = get_authorized_org_id(current_user, organization_id)
    user_id = current_user["id"]
    try:
        updated = assessment_service.update_assessment(
            organization_id=org_id,
            user_id=user_id,
            assessment_id=assessment_id,
            data=payload.model_dump(exclude_unset=True),
        )
        return {"assessment": updated}
    except ValueError as ve:
        if "not found" in str(ve).lower() or "denied" in str(ve).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

@router.post("/{assessment_id}/publish")
async def publish_assessment(
    assessment_id: str,
    organization_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(require_hr),
):
    """Publish an assessment version with immutable questions snapshot."""
    org_id = get_authorized_org_id(current_user, organization_id)
    user_id = current_user["id"]
    try:
        published = assessment_service.publish_assessment(
            organization_id=org_id,
            user_id=user_id,
            assessment_id=assessment_id,
        )
        return {"assessment": published, "message": "Assessment published successfully."}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

@router.post("/{assessment_id}/archive")
async def archive_assessment(
    assessment_id: str,
    organization_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(require_hr),
):
    """Archive an assessment without deleting historical results."""
    org_id = get_authorized_org_id(current_user, organization_id)
    try:
        return assessment_service.archive_assessment(org_id, assessment_id)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))

# ---------------------------------------------------------
# Assignments & Invitations
# ---------------------------------------------------------

@router.get("/{assessment_id}/assignments")
async def list_assignments(
    assessment_id: str,
    organization_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(require_hr),
):
    """List candidate assignments for an assessment."""
    org_id = get_authorized_org_id(current_user, organization_id)
    return {"assignments": assignment_service.list_assignments_for_assessment(org_id, assessment_id)}

@router.post("/{assessment_id}/assign", status_code=status.HTTP_201_CREATED)
async def assign_assessment(
    assessment_id: str,
    payload: AssignAssessmentRequest,
    organization_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(require_hr),
):
    """Assign a published assessment to candidate email addresses."""
    org_id = get_authorized_org_id(current_user, organization_id)
    try:
        invitations = assignment_service.create_assignments(
            organization_id=org_id,
            assessment_id=assessment_id,
            candidate_emails=payload.candidate_emails,
            expires_days=payload.expires_days,
            max_attempts=payload.max_attempts,
        )
        return {"invitations": invitations, "message": f"Successfully created {len(invitations)} candidate invitations."}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

@router.post("/assignments/{assignment_id}/revoke")
async def revoke_assignment(
    assignment_id: str,
    payload: RevokeAssignmentRequest,
    organization_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(require_hr),
):
    """Revoke an active assessment invitation."""
    org_id = get_authorized_org_id(current_user, organization_id)
    user_id = current_user["id"]
    try:
        return assignment_service.revoke_assignment(org_id, user_id, assignment_id, payload.reason)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

# ---------------------------------------------------------
# Results, Scorecards & Exports
# ---------------------------------------------------------

@router.get("/{assessment_id}/attempts")
async def list_attempts(
    assessment_id: str,
    organization_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(require_hr),
):
    """List candidate attempts for an assessment."""
    org_id = get_authorized_org_id(current_user, organization_id)
    try:
        attempts = analytics_service.list_assessment_attempts(org_id, assessment_id)
        return {"attempts": attempts}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))

@router.get("/attempts/{attempt_id}/scorecard")
async def get_candidate_scorecard(
    attempt_id: str,
    organization_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(require_hr),
):
    """Get candidate scorecard with question-by-question review, answer keys, and evidence."""
    org_id = get_authorized_org_id(current_user, organization_id)
    try:
        scorecard = analytics_service.get_candidate_scorecard(org_id, attempt_id)
        return {"scorecard": scorecard}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))

@router.post("/attempts/{attempt_id}/override")
async def manual_score_override(
    attempt_id: str,
    payload: ScoreOverrideRequest,
    organization_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(require_hr),
):
    """Authorized manual score override with audit trail."""
    org_id = get_authorized_org_id(current_user, organization_id)
    user_id = current_user["id"]
    try:
        scorecard = analytics_service.manual_score_override(
            organization_id=org_id,
            user_id=user_id,
            attempt_id=attempt_id,
            new_score=payload.new_score,
            reason=payload.reason,
        )
        return {"scorecard": scorecard, "message": "Manual score override applied successfully."}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

@router.post("/attempts/{attempt_id}/release")
async def release_attempt_result(
    attempt_id: str,
    organization_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(require_hr),
):
    """Release assessment results to candidate."""
    org_id = get_authorized_org_id(current_user, organization_id)
    user_id = current_user["id"]
    try:
        return analytics_service.release_attempt_result(org_id, user_id, attempt_id)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

@router.get("/{assessment_id}/export")
async def export_results_csv(
    assessment_id: str,
    organization_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(require_hr),
):
    """Export assessment results as sanitized CSV."""
    org_id = get_authorized_org_id(current_user, organization_id)
    try:
        csv_data = analytics_service.export_results_csv(org_id, assessment_id)
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=assessment_{assessment_id}_results.csv"},
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
