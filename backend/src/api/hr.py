from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks, Query
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import logging

from ..security.dependencies import require_hr
from ..services.hr_question_service import HRQuestionBankService
from ..services.hr_question_generation_service import HRQuestionGenerationService
from ..services.hr_repo_service import HRRepositoryLibraryService
from ..services.candidate_repo_service import CandidateRepositoryService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/hr", tags=["HR Question Bank & Repository Library"])

# Shared service instances
hr_question_service = HRQuestionBankService()
hr_repo_service = HRRepositoryLibraryService()
hr_gen_service = HRQuestionGenerationService()

def get_authorized_org_id(current_user: Dict[str, Any], requested_org_id: Optional[str] = None) -> str:
    """
    Resolve active organization ID for HR user.
    Strictly verifies user's organization membership unless user is system ADMIN.
    """
    user_role = current_user.get("role")
    user_orgs = current_user.get("organizations", [])

    if user_role == "ADMIN":
        if requested_org_id:
            return requested_org_id
        if user_orgs:
            return user_orgs[0]["organization_id"]
        return "admin_global_org"

    if not user_orgs:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: account has no active organization memberships."
        )

    valid_org_ids = {org["organization_id"] for org in user_orgs}

    if requested_org_id:
        if requested_org_id not in valid_org_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: you are not an authorized HR member of organization '{requested_org_id}'."
            )
        return requested_org_id

    # Default to first organization
    return user_orgs[0]["organization_id"]

# ---------------------------------------------------------
# Request Models
# ---------------------------------------------------------

class QuestionCreateRequest(BaseModel):
    question_text: str = Field(..., min_length=15)
    response_format: str = Field(...)  # 'SINGLE_SELECT', 'MULTI_SELECT', 'TRUE_FALSE'
    competency: str = Field(...)  # 'CODE_COMPREHENSION', 'DEPENDENCY_TRACING', etc.
    difficulty: str = Field(...)  # 'BEGINNER', 'INTERMEDIATE', 'ADVANCED'
    skill_tags: List[str] = Field(default_factory=lambda: ["General"])
    options: List[Dict[str, Any]] = Field(...)
    answer_key: List[str] = Field(...)
    explanation: str = Field(..., min_length=10)
    source_type: str = Field("SKILL_BASED")
    repository_id: Optional[str] = None
    evidence_references: Optional[List[Dict[str, Any]]] = None

class QuestionUpdateRequest(BaseModel):
    question_text: Optional[str] = Field(None, min_length=15)
    response_format: Optional[str] = None
    competency: Optional[str] = None
    difficulty: Optional[str] = None
    skill_tags: Optional[List[str]] = None
    options: Optional[List[Dict[str, Any]]] = None
    answer_key: Optional[List[str]] = None
    explanation: Optional[str] = Field(None, min_length=10)
    evidence_references: Optional[List[Dict[str, Any]]] = None

class QuestionTransitionRequest(BaseModel):
    action: str = Field(...)  # 'APPROVE', 'REJECT', 'PUBLISH', 'ARCHIVE', 'RESTORE'
    reviewer_notes: Optional[str] = None

class QuestionGenerateRequest(BaseModel):
    mode: str = Field("SKILL_BASED")  # 'SKILL_BASED' or 'REPOSITORY_BASED'
    skill_name: Optional[str] = None
    repo_id: Optional[str] = None
    difficulty: str = Field("INTERMEDIATE")
    competencies: Optional[List[str]] = None
    requested_count: int = Field(5, ge=1, le=15)
    notes: Optional[str] = None

class RepositoryRegisterRequest(BaseModel):
    repo_url: str = Field(..., min_length=10, max_length=500)
    display_name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    intended_evaluations: Optional[str] = Field(None, max_length=500)

class RepositoryTransitionRequest(BaseModel):
    action: str = Field(...)  # 'APPROVE', 'ARCHIVE', 'RESTORE'

# ---------------------------------------------------------
# 1. Organization Context & Discovery
# ---------------------------------------------------------

@router.get("/organizations")
async def get_authorized_organizations(current_user: Dict[str, Any] = Depends(require_hr)):
    """List organizations the authenticated HR user is authorized to manage."""
    return {"organizations": current_user.get("organizations", [])}

# ---------------------------------------------------------
# 2. HR Question Bank
# ---------------------------------------------------------

@router.get("/questions")
async def list_questions(
    organization_id: Optional[str] = None,
    search: Optional[str] = None,
    skill: Optional[str] = None,
    competency: Optional[str] = None,
    difficulty: Optional[str] = None,
    response_format: Optional[str] = None,
    source_type: Optional[str] = None,
    repository_id: Optional[str] = None,
    validation_status: Optional[str] = None,
    review_status: Optional[str] = None,
    is_archived: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = "created_at",
    sort_order: str = "desc",
    current_user: Dict[str, Any] = Depends(require_hr)
):
    """
    Search, filter, and paginate organization questions.
    Access strictly scoped to authorized organization.
    """
    org_id = get_authorized_org_id(current_user, organization_id)
    return hr_question_service.get_organization_questions(
        organization_id=org_id,
        search=search,
        skill=skill,
        competency=competency,
        difficulty=difficulty,
        response_format=response_format,
        source_type=source_type,
        repository_id=repository_id,
        validation_status=validation_status,
        review_status=review_status,
        is_archived=is_archived,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order
    )

@router.post("/questions", status_code=status.HTTP_201_CREATED)
async def create_question(
    payload: QuestionCreateRequest,
    organization_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(require_hr)
):
    """Manually author a question for the organization Question Bank."""
    org_id = get_authorized_org_id(current_user, organization_id)
    user_id = current_user["id"]
    try:
        question = hr_question_service.create_question(
            organization_id=org_id,
            author_id=user_id,
            data=payload.model_dump()
        )
        return {"question": question}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

@router.get("/questions/{question_id}")
async def get_question(
    question_id: str,
    organization_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(require_hr)
):
    """Retrieve full question details including answer key for authorized HR."""
    org_id = get_authorized_org_id(current_user, organization_id)
    try:
        question = hr_question_service.get_question_by_id(org_id, question_id)
        return {"question": question}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))

@router.put("/questions/{question_id}")
async def update_question(
    question_id: str,
    payload: QuestionUpdateRequest,
    organization_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(require_hr)
):
    """
    Update a question. If published or approved, creates a new version
    and resets review_status to NEEDS_REVIEW to preserve historical provenance.
    """
    org_id = get_authorized_org_id(current_user, organization_id)
    user_id = current_user["id"]
    try:
        updated = hr_question_service.update_question(
            organization_id=org_id,
            user_id=user_id,
            question_id=question_id,
            data=payload.model_dump()
        )
        return {"question": updated}
    except ValueError as ve:
        if "not found" in str(ve).lower() or "denied" in str(ve).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

@router.post("/questions/{question_id}/transition")
@router.post("/questions/{question_id}/approval")
async def transition_question_lifecycle(
    question_id: str,
    payload: QuestionTransitionRequest,
    organization_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(require_hr)
):
    """Execute review and publication lifecycle transition (APPROVE, REJECT, PUBLISH, ARCHIVE, RESTORE)."""
    org_id = get_authorized_org_id(current_user, organization_id)
    user_id = current_user["id"]
    try:
        updated = hr_question_service.transition_question_status(
            organization_id=org_id,
            reviewer_id=user_id,
            question_id=question_id,
            action=payload.action,
            reviewer_notes=payload.reviewer_notes
        )
        return {"question": updated}
    except ValueError as ve:
        if "not found" in str(ve).lower() or "denied" in str(ve).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

@router.get("/questions/{question_id}/versions")
async def get_question_versions(
    question_id: str,
    organization_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(require_hr)
):
    """Retrieve immutable version history for a question."""
    org_id = get_authorized_org_id(current_user, organization_id)
    try:
        versions = hr_question_service.get_question_versions(org_id, question_id)
        return {"versions": versions, "total_versions": len(versions)}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))

@router.get("/questions/{question_id}/preview")
async def preview_question(
    question_id: str,
    organization_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(require_hr)
):
    """Candidate-style preview redacting answer keys and explanations."""
    org_id = get_authorized_org_id(current_user, organization_id)
    try:
        preview = hr_question_service.preview_question_candidate_mode(org_id, question_id)
        return {"preview": preview}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))

@router.post("/questions/generate", status_code=status.HTTP_201_CREATED)
async def generate_questions(
    payload: QuestionGenerateRequest,
    organization_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(require_hr)
):
    """
    Generate questions via AI engine.
    Generated questions are scoped to organization and default to NEEDS_REVIEW.
    """
    org_id = get_authorized_org_id(current_user, organization_id)
    user_id = current_user["id"]
    try:
        result = hr_gen_service.generate_questions_for_organization(
            organization_id=org_id,
            user_id=user_id,
            mode=payload.mode,
            skill_name=payload.skill_name,
            repo_id=payload.repo_id,
            difficulty=payload.difficulty,
            competencies=payload.competencies,
            requested_count=payload.requested_count,
            notes=payload.notes
        )
        return result
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

# ---------------------------------------------------------
# 3. Approved Repository Library
# ---------------------------------------------------------

@router.get("/repositories")
async def list_repositories(
    organization_id: Optional[str] = None,
    approval_status: Optional[str] = None,
    include_archived: bool = False,
    current_user: Dict[str, Any] = Depends(require_hr)
):
    """List approved repository library for the organization."""
    org_id = get_authorized_org_id(current_user, organization_id)
    repos = hr_repo_service.get_org_repositories(
        organization_id=org_id,
        approval_filter=approval_status,
        include_archived=include_archived
    )
    return {"repositories": repos}

@router.post("/repositories", status_code=status.HTTP_201_CREATED)
async def register_repository(
    payload: RepositoryRegisterRequest,
    background_tasks: BackgroundTasks,
    organization_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(require_hr)
):
    """Register and queue analysis for repository in organization library."""
    org_id = get_authorized_org_id(current_user, organization_id)
    user_id = current_user["id"]
    try:
        repo = hr_repo_service.register_repository_for_org(
            organization_id=org_id,
            user_id=user_id,
            repo_url=payload.repo_url,
            display_name=payload.display_name,
            description=payload.description,
            intended_evaluations=payload.intended_evaluations
        )

        # Trigger analysis if pending
        if repo.get("analysis_status") == "PENDING":
            cand_service = CandidateRepositoryService(engine=hr_repo_service.engine)
            background_tasks.add_task(cand_service.run_repository_analysis_task, repo["id"])

        return {"repository": repo}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

@router.get("/repositories/{repo_id}")
async def get_repository(
    repo_id: str,
    organization_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(require_hr)
):
    """Get repository details and approval state."""
    org_id = get_authorized_org_id(current_user, organization_id)
    try:
        repo = hr_repo_service.get_org_repository_details(org_id, repo_id)
        return {"repository": repo}
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to repository.")
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))

@router.post("/repositories/{repo_id}/transition")
@router.post("/repositories/{repo_id}/approval")
async def transition_repository_approval(
    repo_id: str,
    payload: RepositoryTransitionRequest,
    organization_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(require_hr)
):
    """Approve, archive, or restore repository in organization library."""
    org_id = get_authorized_org_id(current_user, organization_id)
    user_id = current_user["id"]
    try:
        updated = hr_repo_service.transition_repo_approval(
            organization_id=org_id,
            user_id=user_id,
            repo_id=repo_id,
            action=payload.action
        )
        return {"repository": updated}
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to repository.")
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

@router.post("/repositories/{repo_id}/reanalyze")
async def reanalyze_repository(
    repo_id: str,
    background_tasks: BackgroundTasks,
    organization_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(require_hr)
):
    """Request re-analysis of repository in library."""
    org_id = get_authorized_org_id(current_user, organization_id)
    try:
        repo = hr_repo_service.get_org_repository_details(org_id, repo_id)
        cand_service = CandidateRepositoryService(engine=hr_repo_service.engine)
        background_tasks.add_task(cand_service.run_repository_analysis_task, repo_id)
        return {"status": "Re-analysis queued in background", "repo_id": repo_id}
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to repository.")
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))

@router.get("/repositories/{repo_id}/coverage")
async def get_repository_coverage(
    repo_id: str,
    organization_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(require_hr)
):
    """Retrieve actual question coverage analytics for this repository in the organization."""
    org_id = get_authorized_org_id(current_user, organization_id)
    try:
        coverage = hr_repo_service.get_repository_question_coverage(org_id, repo_id)
        return {"coverage": coverage}
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to repository.")
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
