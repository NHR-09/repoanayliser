from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import logging

from ..security.dependencies import require_user
from ..services.resume_service import ResumeService
from ..services.skill_extraction_service import SkillExtractionService
from ..services.candidate_repo_service import CandidateRepositoryService
from ..services.skill_evidence_service import SkillEvidenceService
from ..services.question_generation_service import QuestionGenerationService
from ..services.practice_service import PracticeService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/candidate", tags=["Candidate Practice & Intelligence"])

# Shared service instances
resume_service = ResumeService()
skill_service = SkillExtractionService()
repo_service = CandidateRepositoryService()
evidence_service = SkillEvidenceService(engine=repo_service.engine)
gen_service = QuestionGenerationService(engine=repo_service.engine, llm_reasoner=skill_service.reasoner)
practice_service = PracticeService(generation_service=gen_service)

# ---------------------------------------------------------
# Request Models
# ---------------------------------------------------------

class SkillCreateRequest(BaseModel):
    skill_name: str = Field(..., min_length=1, max_length=100)
    category: str = Field("OTHER", max_length=50)
    evidence_text: Optional[str] = Field(None, max_length=500)

class SkillUpdateRequest(BaseModel):
    skill_name: Optional[str] = Field(None, min_length=1, max_length=100)
    category: Optional[str] = Field(None, max_length=50)
    evidence_text: Optional[str] = Field(None, max_length=500)

class RepoRegisterRequest(BaseModel):
    repo_url: str = Field(..., min_length=10, max_length=500)
    display_name: Optional[str] = Field(None, max_length=100)

class QuizGenerateRequest(BaseModel):
    mode: str = Field("SKILL_BASED")  # 'SKILL_BASED' or 'REPOSITORY_BASED'
    skill_name: Optional[str] = None
    repo_id: Optional[str] = None
    difficulty: str = Field("INTERMEDIATE")  # 'BEGINNER', 'INTERMEDIATE', 'ADVANCED'
    competencies: Optional[List[str]] = None
    question_count: int = Field(5, ge=1, le=15)

class QuizSubmitRequest(BaseModel):
    answers: Dict[str, List[str]] = Field(...)

# ---------------------------------------------------------
# 1. Resume Upload & Skill Extraction
# ---------------------------------------------------------

@router.post("/resume/upload", status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(require_user)
):
    """
    Upload resume (PDF, DOCX, TXT), extract plain text securely,
    and automatically extract technical skills into candidate profile.
    """
    user_id = current_user["id"]
    try:
        content = await file.read()
        filename = file.filename or "resume.pdf"
        mime_type = file.content_type

        # 1. Validate & store file
        resume_record = resume_service.upload_resume(
            user_id=user_id,
            filename=filename,
            file_bytes=content,
            mime_type=mime_type
        )

        # 2. Extract technical skills and save with source='RESUME'
        raw_text = resume_service.get_resume_raw_text(user_id)
        extraction_result = skill_service.process_and_save_resume_skills(user_id, raw_text or "")

        return {
            "resume": resume_record,
            "extracted_skills": extraction_result["saved_skills"],
            "github_urls": extraction_result["extracted"].get("github_urls", []),
            "projects": extraction_result["extracted"].get("projects", []),
            "extraction_method": resume_record.get("extraction_method", "NATIVE_TEXT"),
            "ocr_metadata": resume_record.get("ocr_metadata")
        }

    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"Error handling resume upload for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to process resume upload.")

@router.get("/resume/status/{job_id}")
async def get_resume_job_status(
    job_id: str,
    current_user: Dict[str, Any] = Depends(require_user)
):
    """Query persistent processing status of a resume extraction job."""
    job = resume_service.get_resume_job(job_id)
    if not job or job["user_id"] != current_user["id"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume processing job not found.")
    return {"job": job}

@router.get("/resume/job")
async def get_latest_resume_job(
    current_user: Dict[str, Any] = Depends(require_user)
):
    """Retrieve the candidate's most recent resume extraction job status."""
    job = resume_service.get_user_latest_job(current_user["id"])
    return {"job": job}

@router.get("/resume/ocr-capabilities")
async def get_ocr_capabilities(
    current_user: Dict[str, Any] = Depends(require_user)
):
    """Report OCR engine availability and supported languages."""
    available = resume_service.ocr_service.is_available()
    languages = resume_service.ocr_service.get_available_languages() if available else []
    return {
        "ocr_available": available,
        "ocr_engine": "tesseract",
        "supported_languages": languages,
        "supported_extensions": [".pdf", ".docx", ".txt", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"]
    }

@router.get("/resume")
async def get_resume(current_user: Dict[str, Any] = Depends(require_user)):
    """Retrieve active resume metadata and preview for authenticated candidate."""
    user_id = current_user["id"]
    record = resume_service.get_user_resume(user_id)
    if not record:
        return {"resume": None}
    # Redact raw file path on disk
    record.pop("file_path", None)
    record.pop("raw_text", None)
    return {"resume": record}

@router.delete("/resume", status_code=status.HTTP_200_OK)
async def delete_resume(current_user: Dict[str, Any] = Depends(require_user)):
    """Delete candidate resume and remove stored file."""
    user_id = current_user["id"]
    deleted = resume_service.delete_user_resume(user_id)
    return {"deleted": deleted}

# ---------------------------------------------------------
# 2. Candidate Reviewed Skills CRUD
# ---------------------------------------------------------

@router.get("/skills")
async def get_skills(current_user: Dict[str, Any] = Depends(require_user)):
    """Get candidate reviewed skills list with category and source provenance."""
    user_id = current_user["id"]
    skills = skill_service.get_user_skills(user_id)
    return {"skills": skills}

@router.post("/skills", status_code=status.HTTP_201_CREATED)
async def add_skill(
    payload: SkillCreateRequest,
    current_user: Dict[str, Any] = Depends(require_user)
):
    """Manually add a skill to candidate profile (source='MANUAL')."""
    user_id = current_user["id"]
    try:
        skill = skill_service.add_user_skill(
            user_id=user_id,
            skill_name=payload.skill_name,
            category=payload.category,
            evidence_text=payload.evidence_text
        )
        return {"skill": skill}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

@router.put("/skills/{skill_id}")
async def update_skill(
    skill_id: str,
    payload: SkillUpdateRequest,
    current_user: Dict[str, Any] = Depends(require_user)
):
    """Edit skill details while keeping provenance distinguishable."""
    user_id = current_user["id"]
    try:
        updated = skill_service.update_user_skill(
            user_id=user_id,
            skill_id=skill_id,
            skill_name=payload.skill_name,
            category=payload.category,
            evidence_text=payload.evidence_text
        )
        return {"skill": updated}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))

@router.delete("/skills/{skill_id}")
async def delete_skill(
    skill_id: str,
    current_user: Dict[str, Any] = Depends(require_user)
):
    """Delete a skill claim from candidate profile."""
    user_id = current_user["id"]
    deleted = skill_service.delete_user_skill(user_id, skill_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found or access denied.")
    return {"deleted": True}

# ---------------------------------------------------------
# 3. GitHub Repository Integration & Analysis
# ---------------------------------------------------------

@router.post("/repositories", status_code=status.HTTP_201_CREATED)
async def register_repository(
    payload: RepoRegisterRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(require_user)
):
    """Register public GitHub repo, perform SSRF validation, and queue analysis."""
    user_id = current_user["id"]
    try:
        repo = repo_service.register_repository(
            user_id=user_id,
            repo_url=payload.repo_url,
            display_name=payload.display_name
        )
        # Trigger background analysis if pending
        if repo.get("analysis_status") == "PENDING":
            background_tasks.add_task(repo_service.run_repository_analysis_task, repo["id"])

        return {"repository": repo}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"Error registering repository: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to connect repository.")

@router.get("/repositories")
async def list_repositories(current_user: Dict[str, Any] = Depends(require_user)):
    """List all repositories registered by or granted to the candidate."""
    user_id = current_user["id"]
    repos = repo_service.get_user_repositories(user_id)
    return {"repositories": repos}

@router.get("/repositories/{repo_id}/status")
async def get_repository_status(
    repo_id: str,
    current_user: Dict[str, Any] = Depends(require_user)
):
    """Check repository analysis status and commit metadata."""
    user_id = current_user["id"]
    try:
        details = repo_service.get_repository_details(user_id, repo_id)
        return {
            "id": details["id"],
            "neo4j_repo_id": details["neo4j_repo_id"],
            "display_name": details["display_name"],
            "analysis_status": details.get("analysis_status", "PENDING"),
            "last_analyzed_commit": details.get("last_analyzed_commit"),
            "last_analyzed_at": details.get("last_analyzed_at"),
            "analysis_error": details.get("analysis_error")
        }
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to repository.")
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))

@router.post("/repositories/{repo_id}/analyze")
async def trigger_reanalysis(
    repo_id: str,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(require_user)
):
    """Request re-analysis of repository."""
    user_id = current_user["id"]
    try:
        details = repo_service.get_repository_details(user_id, repo_id)
        background_tasks.add_task(repo_service.run_repository_analysis_task, repo_id)
        return {"status": "Analysis queued", "repo_id": repo_id}
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to repository.")
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))

# ---------------------------------------------------------
# 4. Skill-to-Code Evidence Mapping
# ---------------------------------------------------------

@router.get("/skills/evidence")
async def get_skill_evidence(
    repo_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(require_user)
):
    """
    Retrieve skill-to-code evidence mappings.
    If repo_id is provided, automatically evaluates candidate skills against AST.
    """
    user_id = current_user["id"]
    try:
        if repo_id:
            # Check repo access
            if not repo_service.check_user_access(user_id, repo_id):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to repository.")
            evidence = evidence_service.map_skills_to_repository(user_id, repo_id)
            return {"evidence": evidence}
        else:
            evidence = evidence_service.get_user_skill_evidence(user_id)
            return {"evidence": evidence}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

# ---------------------------------------------------------
# 5. Practice Quiz Workflow & History
# ---------------------------------------------------------

@router.post("/practice/generate", status_code=status.HTTP_201_CREATED)
async def generate_quiz(
    payload: QuizGenerateRequest,
    current_user: Dict[str, Any] = Depends(require_user)
):
    """
    Generate validated practice quiz in Skill or Repository mode.
    Response strictly redacts answer_key from questions!
    """
    user_id = current_user["id"]
    try:
        quiz = practice_service.start_quiz(
            user_id=user_id,
            mode=payload.mode,
            skill_name=payload.skill_name,
            repo_id=payload.repo_id,
            difficulty=payload.difficulty,
            competencies=payload.competencies,
            question_count=payload.question_count
        )
        return quiz
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"Error generating quiz: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to generate quiz questions.")

@router.get("/practice/quiz/{quiz_id}")
async def get_quiz(
    quiz_id: str,
    current_user: Dict[str, Any] = Depends(require_user)
):
    """Retrieve quiz. Answer keys remain redacted while quiz is IN_PROGRESS."""
    user_id = current_user["id"]
    try:
        quiz = practice_service.get_quiz_for_candidate(user_id, quiz_id)
        return {"quiz": quiz}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))

@router.post("/practice/quiz/{quiz_id}/submit")
async def submit_quiz(
    quiz_id: str,
    payload: QuizSubmitRequest,
    current_user: Dict[str, Any] = Depends(require_user)
):
    """
    Submit candidate answers, execute objective scoring,
    and return complete explanations and evidence.
    """
    user_id = current_user["id"]
    try:
        results = practice_service.submit_quiz_answers(
            user_id=user_id,
            quiz_id=quiz_id,
            answers=payload.answers
        )
        return {"results": results}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

@router.get("/practice/quiz/{quiz_id}/results")
async def get_quiz_results(
    quiz_id: str,
    current_user: Dict[str, Any] = Depends(require_user)
):
    """Get detailed results, competency breakdown, and explanations for completed quiz."""
    user_id = current_user["id"]
    try:
        results = practice_service.get_quiz_results(user_id, quiz_id)
        return {"results": results}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))

@router.get("/practice/history")
async def get_practice_history(current_user: Dict[str, Any] = Depends(require_user)):
    """Get candidate practice history, cumulative accuracy, and competency breakdown."""
    user_id = current_user["id"]
    history = practice_service.get_user_practice_history(user_id)
    return history
