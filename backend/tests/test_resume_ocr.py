import os
import io
import time
import json
import uuid
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

from PIL import Image, ImageDraw
import pypdf
import pytesseract

from src.config import settings
from src.db.connection import get_db_connection, init_db
from src.services.ocr_service import (
    OcrService,
    OcrError,
    OcrEngineUnavailableError,
    OcrQualityError,
    OcrResourceLimitError,
    UnsupportedFormatError
)
from src.services.resume_service import ResumeService


class TestResumeOcrSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_db_dir = Path(__file__).parent / ".test_data"
        cls.test_db_dir.mkdir(parents=True, exist_ok=True)
        cls.test_db_path = str(cls.test_db_dir / f"test_ocr_{uuid.uuid4().hex[:8]}.db")
        cls.orig_db_path = settings.db_path
        settings.db_path = cls.test_db_path
        os.environ["ARCHITECH_DB_PATH"] = cls.test_db_path
        init_db(cls.test_db_path)

        cls.storage_dir = cls.test_db_dir / "resumes"
        cls.storage_dir.mkdir(parents=True, exist_ok=True)
        cls.ocr_service = OcrService()
        cls.resume_service = ResumeService(storage_dir=cls.storage_dir, ocr_service=cls.ocr_service)

    @classmethod
    def tearDownClass(cls):
        settings.db_path = cls.orig_db_path
        # Cleanup test files
        if Path(cls.test_db_path).exists():
            try:
                Path(cls.test_db_path).unlink()
            except Exception:
                pass
        shutil = __import__("shutil")
        if cls.test_db_dir.exists():
            try:
                shutil.rmtree(cls.test_db_dir, ignore_errors=True)
            except Exception:
                pass

    def setUp(self):
        settings.db_path = self.test_db_path

    def _create_user(self, user_id: str):
        with get_db_connection(self.test_db_path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO users (id, email, password_hash, full_name, role) VALUES (?, ?, 'hash', 'Test User', 'USER')",
                (user_id, f"{user_id}@test.com")
            )

    def _create_scanned_image(self, text: str, width: int = 800, height: int = 400) -> bytes:
        """Create an image containing rendered text simulating a scanned resume."""
        img = Image.new("RGB", (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.text((40, 40), text, fill=(0, 0, 0))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def _create_scanned_pdf(self, text: str) -> bytes:
        """Create a PDF document containing a single scanned raster image page."""
        img_bytes = self._create_scanned_image(text, 800, 500)
        img = Image.open(io.BytesIO(img_bytes))
        buf = io.BytesIO()
        img.save(buf, format="PDF")
        return buf.getvalue()

    # -------------------------------------------------------------
    # 1. Genuine OCR & Extraction Tests
    # -------------------------------------------------------------

    def test_01_text_based_pdf_does_not_trigger_ocr(self):
        """Native text PDF must be extracted directly without triggering OCR fallback."""
        sample_text = "Jane Doe - Senior Full Stack Engineer with extensive Python, Django, React experience."
        fake_pdf = b"%PDF-1.4\n%real-pdf-test-mock\n%%EOF"

        # Mock pypdf.PdfReader to return adequate native text
        with patch("pypdf.PdfReader") as mock_reader:
            mock_page = MagicMock()
            mock_page.extract_text.return_value = sample_text
            mock_reader.return_value.pages = [mock_page]

            with patch.object(self.ocr_service, "extract_text_from_scanned_pdf") as mock_pdf_ocr:
                text, method, meta = self.resume_service.extract_text_with_metadata("resume.pdf", fake_pdf)
                self.assertEqual(method, "NATIVE_TEXT")
                self.assertIn("Python", text)
                mock_pdf_ocr.assert_not_called()

    def test_02_scanned_image_ocr_genuine_execution(self):
        """Image resume (.png) is processed by genuine Tesseract OCR."""
        if not self.ocr_service.is_available():
            self.skipTest("Tesseract OCR not installed on host.")

        resume_text = (
            "SARAH CONNOR\n"
            "Software Architect\n"
            "Skills: Python, TypeScript, Docker, Kubernetes, PostgreSQL\n"
            "Experience: 8 years building distributed microservices."
        )
        png_bytes = self._create_scanned_image(resume_text)

        res = self.ocr_service.extract_text_from_image(png_bytes, filename="resume.png")
        self.assertEqual(res["extraction_method"], "OCR")
        self.assertEqual(res["ocr_engine"], "tesseract")
        self.assertIn("Python", res["text"])
        self.assertIn("Docker", res["text"])
        self.assertGreater(res["duration_ms"], 0)

    def test_03_scanned_pdf_ocr_genuine_execution(self):
        """Scanned PDF (containing raster image page) triggers OCR fallback successfully."""
        if not self.ocr_service.is_available():
            self.skipTest("Tesseract OCR not installed on host.")

        resume_text = (
            "MARCUS VANCE\n"
            "DevOps Engineer\n"
            "Skills: Python, AWS, Prometheus, Grafana\n"
            "Built automated deployment pipelines."
        )
        pdf_bytes = self._create_scanned_pdf(resume_text)

        text, method, meta = self.resume_service.extract_text_with_metadata("scanned_resume.pdf", pdf_bytes)
        self.assertEqual(method, "OCR")
        self.assertEqual(meta["ocr_engine"], "tesseract")
        self.assertIn("DevOps", text)
        self.assertIn("Python", text)

    def test_04_image_resume_upload_end_to_end(self):
        """End-to-end upload of image resume persists extraction method and job status."""
        if not self.ocr_service.is_available():
            self.skipTest("Tesseract OCR not installed on host.")

        user_id = f"user_ocr_{uuid.uuid4().hex[:6]}"
        self._create_user(user_id)

        resume_text = (
            "EMILY BLUNT\n"
            "Backend Lead\n"
            "Skills: Go, Python, Redis, GraphQL, Kafka\n"
            "Specialized in high-throughput messaging."
        )
        png_bytes = self._create_scanned_image(resume_text)

        result = self.resume_service.upload_resume(user_id, "emily_resume.png", png_bytes)
        self.assertEqual(result["extraction_method"], "OCR")
        self.assertIn("job_id", result)

        # Check user_resumes database record
        stored = self.resume_service.get_user_resume(user_id)
        self.assertIsNotNone(stored)
        self.assertEqual(stored["extraction_method"], "OCR")
        self.assertEqual(stored["ocr_status"], "COMPLETED")

        # Check persistent resume_jobs database record
        job = self.resume_service.get_resume_job(result["job_id"])
        self.assertIsNotNone(job)
        self.assertEqual(job["status"], "COMPLETED")
        self.assertEqual(job["extraction_method"], "OCR")

    # -------------------------------------------------------------
    # 2. Quality & Validation Checks
    # -------------------------------------------------------------

    def test_05_blank_or_illegible_image_rejected(self):
        """Blank image produces insufficient text and raises actionable error."""
        if not self.ocr_service.is_available():
            self.skipTest("Tesseract OCR not installed on host.")

        # Completely blank white image
        blank_img = Image.new("RGB", (400, 300), color=(255, 255, 255))
        buf = io.BytesIO()
        blank_img.save(buf, format="PNG")

        with self.assertRaises(ValueError) as ctx:
            self.resume_service.upload_resume("user_blank", "blank.png", buf.getvalue())
        self.assertTrue("could not extract readable text" in str(ctx.exception).lower() or "inadequate or illegible" in str(ctx.exception).lower())

    def test_06_unsupported_image_extension_rejected(self):
        """Files with unsupported extensions are safely rejected."""
        with self.assertRaises(ValueError) as ctx:
            self.resume_service.upload_resume("user_ext", "resume.exe", b"MZ\x90\x00executable")
        self.assertIn("unsupported file format", str(ctx.exception).lower())

    def test_07_disguised_file_signature_validation(self):
        """Malicious executable disguised as a PNG is rejected by signature check."""
        fake_png = b"MZ\x90\x00this is not a valid png image stream"
        with self.assertRaises(ValueError) as ctx:
            self.resume_service.upload_resume("user_fake", "exploit.png", fake_png)
        self.assertIn("does not match genuine image signature", str(ctx.exception).lower())

    def test_08_oversized_file_rejected(self):
        """Files exceeding 10MB limit are rejected safely without crashing."""
        oversized = b"0" * (11 * 1024 * 1024)
        with self.assertRaises(ValueError) as ctx:
            self.resume_service.validate_file("large.pdf", oversized)
        self.assertIn("exceeds maximum allowed limit", str(ctx.exception).lower())

    # -------------------------------------------------------------
    # 3. Error Handling, Mocks & Resilience
    # -------------------------------------------------------------

    def test_09_tesseract_unavailable_mocked(self):
        """When Tesseract executable is unavailable, clear error message is returned."""
        with patch.object(self.ocr_service, "is_available", return_value=False):
            img_bytes = self._create_scanned_image("Some text")
            with self.assertRaises(ValueError) as ctx:
                self.resume_service.extract_text_with_metadata("resume.png", img_bytes)
            self.assertIn("ocr engine (tesseract) is not available", str(ctx.exception).lower())

    def test_10_ocr_timeout_handling(self):
        """Simulated OCR timeout raises an explicit OcrError."""
        with patch("pytesseract.image_to_string", side_effect=TimeoutError("OCR operation timed out")):
            img_bytes = self._create_scanned_image("Sample text")
            with self.assertRaises(OcrError) as ctx:
                self.ocr_service.extract_text_from_image(img_bytes, filename="test.png", timeout_seconds=5)
            self.assertIn("timed out", str(ctx.exception).lower())

    def test_11_job_status_and_stuck_job_recovery(self):
        """Jobs stuck in RUNNING or PENDING are safely recovered to FAILED on maintenance."""
        user_id = f"user_stuck_{uuid.uuid4().hex[:6]}"
        self._create_user(user_id)

        job_id = self.resume_service.create_resume_job(user_id, "interrupted_resume.pdf")
        self.resume_service.update_resume_job(job_id, status="RUNNING")

        # Manually backdate the created_at timestamp to simulate crash 30 minutes ago
        past_time = "2026-01-01T00:00:00+00:00"
        with get_db_connection(self.test_db_path) as conn:
            conn.execute("UPDATE resume_jobs SET created_at = ? WHERE id = ?", (past_time, job_id))

        recovered_count = self.resume_service.recover_interrupted_jobs(timeout_minutes=15)
        self.assertGreaterEqual(recovered_count, 1)

        job_state = self.resume_service.get_resume_job(job_id)
        self.assertEqual(job_state["status"], "FAILED")
        self.assertIn("timed out or worker process was restarted", job_state["error_message"])

    def test_12_upload_retry_idempotency(self):
        """Retrying an upload for the same user updates the record without creating duplicate user resumes."""
        user_id = f"user_retry_{uuid.uuid4().hex[:6]}"
        self._create_user(user_id)

        content1 = "Jane Doe. Skills: Python, Docker, PostgreSQL."
        content2 = "Jane Doe. Skills: Python, Docker, Kubernetes, AWS, PostgreSQL."

        res1 = self.resume_service.upload_resume(user_id, "resume_v1.txt", content1.encode("utf-8"), "text/plain")
        res2 = self.resume_service.upload_resume(user_id, "resume_v2.txt", content2.encode("utf-8"), "text/plain")

        # Must reuse the same user_resumes id
        self.assertEqual(res1["id"], res2["id"])

        with get_db_connection(self.test_db_path) as conn:
            rows = conn.execute("SELECT COUNT(*) as count FROM user_resumes WHERE user_id = ?", (user_id,)).fetchone()
            self.assertEqual(rows["count"], 1)


if __name__ == "__main__":
    unittest.main()
