import os
import io
import uuid
import re
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta

import pypdf
import docx

from src.db.connection import get_db_connection
from .ocr_service import (
    OcrService,
    OcrError,
    OcrEngineUnavailableError,
    OcrQualityError,
    OcrResourceLimitError,
    UnsupportedFormatError,
    SUPPORTED_IMAGE_EXTENSIONS
)

logger = logging.getLogger(__name__)

# Base storage directory for resumes (outside static web root)
RESUME_STORAGE_DIR = Path(os.getenv("RESUME_STORAGE_DIR", Path(__file__).resolve().parent.parent.parent / ".data" / "resumes"))
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB default

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}.union(SUPPORTED_IMAGE_EXTENSIONS)
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/x-pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "text/plain",
    "image/png",
    "image/jpeg",
    "image/tiff",
    "image/bmp",
    "image/webp"
}

class ResumeService:
    def __init__(self, storage_dir: Optional[Path] = None, ocr_service: Optional[OcrService] = None):
        self.storage_dir = storage_dir or RESUME_STORAGE_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.ocr_service = ocr_service or OcrService()

    def validate_file(self, filename: str, file_bytes: bytes, mime_type: Optional[str] = None):
        """Validate file size, extension, and binary signature."""
        if not file_bytes:
            raise ValueError("Uploaded file is empty.")

        if len(file_bytes) > MAX_FILE_SIZE:
            raise ValueError(f"File size ({len(file_bytes) / 1024 / 1024:.2f} MB) exceeds maximum allowed limit of 10 MB.")

        # Validate extension
        _, ext = os.path.splitext(filename.lower())
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"Unsupported file format '{ext}'. Supported formats: PDF, DOCX, TXT, PNG, JPG, TIFF, BMP, WEBP.")

        # Signature/magic byte checks
        if ext == ".pdf":
            if not file_bytes.startswith(b"%PDF-"):
                raise ValueError("Invalid PDF format: missing valid PDF file header.")
        elif ext == ".docx":
            if not file_bytes.startswith(b"PK\x03\x04"):
                raise ValueError("Invalid DOCX format: missing valid document archive signature.")
        elif ext in SUPPORTED_IMAGE_EXTENSIONS:
            try:
                self.ocr_service.validate_image_signature(file_bytes, filename)
            except UnsupportedFormatError as e:
                raise ValueError(str(e))

    def extract_text_with_metadata(self, filename: str, file_bytes: bytes) -> Tuple[str, str, Dict[str, Any]]:
        """
        Extract text from document preserving existing native extraction paths (PDF, DOCX, TXT)
        and falling back to Tesseract OCR when native text is insufficient or when uploading image formats.
        Returns (text, extraction_method, metadata) where extraction_method is 'NATIVE_TEXT' or 'OCR'.
        """
        _, ext = os.path.splitext(filename.lower())
        raw_text = ""
        extraction_method = "NATIVE_TEXT"
        metadata: Dict[str, Any] = {"filename": filename, "extension": ext}

        try:
            if ext == ".pdf":
                reader = pypdf.PdfReader(io.BytesIO(file_bytes))
                pages_text = []
                for i, page in enumerate(reader.pages):
                    page_content = page.extract_text() or ""
                    if page_content.strip():
                        pages_text.append(page_content)
                raw_text = "\n\n".join(pages_text)
                normalized = self._normalize_text(raw_text)

                # If native text extraction yields sufficient text (>= 30 characters), use native text
                if len(normalized.strip()) >= 30:
                    metadata["method"] = "NATIVE_TEXT"
                    metadata["pages"] = len(reader.pages)
                    return normalized, "NATIVE_TEXT", metadata

                # Insufficient native text in PDF: Scanned PDF fallback to OCR
                logger.info(f"PDF {filename} yielded insufficient native text ({len(normalized.strip())} chars). Attempting OCR fallback...")
                try:
                    ocr_res = self.ocr_service.extract_text_from_scanned_pdf(file_bytes, filename=filename)
                    return ocr_res["text"], "OCR", ocr_res
                except OcrQualityError as oqe:
                    raise ValueError(f"Could not extract readable text from resume. {str(oqe)}")
                except OcrEngineUnavailableError as oee:
                    raise ValueError(
                        "Could not extract readable text from resume. "
                        "If this is a scanned or image-based PDF, please provide a text-based PDF or DOCX file."
                    )
                except Exception as oe:
                    raise ValueError(
                        "Could not extract readable text from resume. "
                        "If this is a scanned or image-based PDF, please provide a text-based PDF or DOCX file."
                    )

            elif ext in SUPPORTED_IMAGE_EXTENSIONS:
                # Direct image OCR
                try:
                    ocr_res = self.ocr_service.extract_text_from_image(file_bytes, filename=filename)
                    return ocr_res["text"], "OCR", ocr_res
                except OcrQualityError as oqe:
                    raise ValueError(f"Could not extract readable text from resume image: {str(oqe)}")
                except OcrEngineUnavailableError as oee:
                    raise ValueError(
                        "OCR engine (Tesseract) is not available to process image resumes. "
                        "Please upload a text-based PDF, DOCX, or plain text file."
                    )
                except Exception as oe:
                    raise ValueError(f"Could not extract readable text from resume image: {str(oe)}")

            elif ext == ".docx":
                doc = docx.Document(io.BytesIO(file_bytes))
                parts = []
                for p in doc.paragraphs:
                    if p.text.strip():
                        parts.append(p.text)
                for table in doc.tables:
                    for row in table.rows:
                        row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                        if row_text:
                            parts.append(row_text)
                raw_text = "\n".join(parts)
                normalized = self._normalize_text(raw_text)
                if len(normalized.strip()) < 20:
                    raise ValueError("Could not extract readable text from resume.")
                metadata["method"] = "NATIVE_TEXT"
                return normalized, "NATIVE_TEXT", metadata

            elif ext == ".txt":
                try:
                    raw_text = file_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    raw_text = file_bytes.decode("latin-1", errors="replace")
                normalized = self._normalize_text(raw_text)
                if len(normalized.strip()) < 20:
                    raise ValueError("Could not extract readable text from resume.")
                metadata["method"] = "NATIVE_TEXT"
                return normalized, "NATIVE_TEXT", metadata

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error parsing resume document {filename}: {e}")
            raise ValueError(f"Unable to parse document: {str(e)}")

        normalized = self._normalize_text(raw_text)
        if len(normalized.strip()) < 20:
            raise ValueError(
                "Could not extract readable text from resume. "
                "If this is a scanned or image-based PDF, please provide a text-based PDF or DOCX file."
            )
        return normalized, extraction_method, metadata

    def extract_text(self, filename: str, file_bytes: bytes) -> str:
        """Extract and normalize plain text from PDF, DOCX, TXT, or scanned image."""
        text, _, _ = self.extract_text_with_metadata(filename, file_bytes)
        return text

    def _normalize_text(self, text: str) -> str:
        """Clean control chars while keeping newlines, indentation, and code symbols."""
        if not text:
            return ""
        # Remove null bytes and non-printable control characters (except \n, \r, \t)
        text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)
        # Standardize carriage returns
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        # Collapse excessive newlines (>3) to double newlines
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def upload_resume(
        self,
        user_id: str,
        filename: str,
        file_bytes: bytes,
        mime_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Validate, extract (with OCR fallback), save file to disk, and persist resume & job metadata."""
        self.validate_file(filename, file_bytes, mime_type)
        extracted_text, method, metadata = self.extract_text_with_metadata(filename, file_bytes)

        # Generate internal storage identifier and safe storage path
        storage_id = str(uuid.uuid4())
        clean_filename = Path(filename.replace('\\', '/')).name
        _, ext = os.path.splitext(clean_filename.lower())
        safe_ext = ext if ext in ALLOWED_EXTENSIONS else ".bin"
        if not clean_filename:
            clean_filename = f"resume{safe_ext}"

        user_storage_dir = self.storage_dir / user_id
        user_storage_dir.mkdir(parents=True, exist_ok=True)
        file_path = user_storage_dir / f"{storage_id}{safe_ext}"

        # Delete any existing resume file for this user before saving new one
        existing = self.get_user_resume(user_id)
        if existing and existing.get("file_path"):
            old_path = Path(existing["file_path"])
            if old_path.exists():
                try:
                    old_path.unlink()
                except Exception as e:
                    logger.warning(f"Failed to remove previous resume file {old_path}: {e}")

        # Write file securely
        with open(file_path, "wb") as f:
            f.write(file_bytes)

        # Database record
        resume_record_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        metadata_json = json.dumps(metadata)

        with get_db_connection() as conn:
            # Check if user already has a resume record
            if existing:
                conn.execute("""
                    UPDATE user_resumes
                    SET filename = ?, file_path = ?, file_size = ?, mime_type = ?, raw_text = ?,
                        extraction_method = ?, ocr_status = 'COMPLETED', ocr_metadata = ?, updated_at = ?
                    WHERE user_id = ?
                """, (
                    clean_filename,
                    str(file_path),
                    len(file_bytes),
                    mime_type or f"application/{safe_ext.lstrip('.')}",
                    extracted_text,
                    method,
                    metadata_json,
                    now,
                    user_id
                ))
                resume_record_id = existing["id"]
            else:
                conn.execute("""
                    INSERT INTO user_resumes (
                        id, user_id, filename, file_path, file_size, mime_type, raw_text,
                        extraction_method, ocr_status, ocr_metadata, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'COMPLETED', ?, ?, ?)
                """, (
                    resume_record_id,
                    user_id,
                    clean_filename,
                    str(file_path),
                    len(file_bytes),
                    mime_type or f"application/{safe_ext.lstrip('.')}",
                    extracted_text,
                    method,
                    metadata_json,
                    now,
                    now
                ))

            # Record persistent job completion
            job_id = str(uuid.uuid4())
            conn.execute("""
                INSERT INTO resume_jobs (id, user_id, filename, status, extraction_method, ocr_metadata, created_at, updated_at)
                VALUES (?, ?, ?, 'COMPLETED', ?, ?, ?, ?)
            """, (
                job_id,
                user_id,
                clean_filename,
                method,
                metadata_json,
                now,
                now
            ))

        preview = extracted_text[:300] + ("..." if len(extracted_text) > 300 else "")
        return {
            "id": resume_record_id,
            "job_id": job_id,
            "filename": clean_filename,
            "file_size": len(file_bytes),
            "mime_type": mime_type or f"application/{safe_ext.lstrip('.')}",
            "created_at": now,
            "text_preview": preview,
            "character_count": len(extracted_text),
            "extraction_method": method,
            "ocr_metadata": metadata
        }

    def create_resume_job(self, user_id: str, filename: str) -> str:
        """Create a new pending resume processing job for persistent state tracking."""
        job_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        clean_filename = Path(filename.replace('\\', '/')).name
        with get_db_connection() as conn:
            conn.execute("""
                INSERT INTO resume_jobs (id, user_id, filename, status, extraction_method, created_at, updated_at)
                VALUES (?, ?, ?, 'PENDING', 'NATIVE_TEXT', ?, ?)
            """, (job_id, user_id, clean_filename, now, now))
        return job_id

    def update_resume_job(
        self,
        job_id: str,
        status: str,
        extraction_method: str = "NATIVE_TEXT",
        ocr_metadata: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ):
        """Update persistent processing status of a resume job."""
        now = datetime.now(timezone.utc).isoformat()
        meta_json = json.dumps(ocr_metadata) if ocr_metadata else None
        with get_db_connection() as conn:
            conn.execute("""
                UPDATE resume_jobs
                SET status = ?, extraction_method = ?, ocr_metadata = ?, error_message = ?, updated_at = ?
                WHERE id = ?
            """, (status, extraction_method, meta_json, error_message, now, job_id))

    def get_resume_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve resume job status and metadata by ID."""
        with get_db_connection() as conn:
            row = conn.execute("""
                SELECT id, user_id, filename, status, extraction_method, ocr_metadata, error_message, created_at, updated_at
                FROM resume_jobs
                WHERE id = ?
            """, (job_id,)).fetchone()
            if not row:
                return None
            data = dict(row)
            if data.get("ocr_metadata"):
                try:
                    data["ocr_metadata"] = json.loads(data["ocr_metadata"])
                except Exception:
                    pass
            return data

    def get_user_latest_job(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve the most recent resume job for a user."""
        with get_db_connection() as conn:
            row = conn.execute("""
                SELECT id, user_id, filename, status, extraction_method, ocr_metadata, error_message, created_at, updated_at
                FROM resume_jobs
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (user_id,)).fetchone()
            if not row:
                return None
            data = dict(row)
            if data.get("ocr_metadata"):
                try:
                    data["ocr_metadata"] = json.loads(data["ocr_metadata"])
                except Exception:
                    pass
            return data

    def recover_interrupted_jobs(self, timeout_minutes: int = 15) -> int:
        """
        Recover abandoned or interrupted jobs stuck in PENDING or RUNNING on startup.
        Respects idempotency and marks timed-out jobs as FAILED.
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes)).isoformat()
        now = datetime.now(timezone.utc).isoformat()
        with get_db_connection() as conn:
            cursor = conn.execute("""
                UPDATE resume_jobs
                SET status = 'FAILED', error_message = 'Job timed out or worker process was restarted.', updated_at = ?
                WHERE status IN ('PENDING', 'RUNNING') AND created_at < ?
            """, (now, cutoff))
            recovered = cursor.rowcount
            if recovered > 0:
                logger.info(f"Recovered {recovered} abandoned resume processing jobs.")
            return recovered

    def get_user_resume(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve user's active resume metadata and preview."""
        with get_db_connection() as conn:
            row = conn.execute("""
                SELECT id, user_id, filename, file_path, file_size, mime_type, raw_text,
                       extraction_method, ocr_status, ocr_metadata, created_at, updated_at
                FROM user_resumes
                WHERE user_id = ?
            """, (user_id,)).fetchone()
            if not row:
                return None
            data = dict(row)
            data["text_preview"] = data["raw_text"][:300] + ("..." if len(data["raw_text"]) > 300 else "")
            if data.get("ocr_metadata"):
                try:
                    data["ocr_metadata"] = json.loads(data["ocr_metadata"])
                except Exception:
                    pass
            return data

    def get_resume_raw_text(self, user_id: str) -> Optional[str]:
        """Get full extracted text for skill analysis."""
        with get_db_connection() as conn:
            row = conn.execute("SELECT raw_text FROM user_resumes WHERE user_id = ?", (user_id,)).fetchone()
            return row["raw_text"] if row else None

    def delete_user_resume(self, user_id: str) -> bool:
        """Delete resume record and remove file from disk."""
        existing = self.get_user_resume(user_id)
        if not existing:
            return False

        if existing.get("file_path"):
            path = Path(existing["file_path"])
            if path.exists():
                try:
                    path.unlink()
                except Exception as e:
                    logger.warning(f"Failed to delete resume file {path}: {e}")

        with get_db_connection() as conn:
            conn.execute("DELETE FROM user_resumes WHERE user_id = ?", (user_id,))
            return True
