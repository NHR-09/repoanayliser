import os
import io
import time
import shutil
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from PIL import Image
import pytesseract
import pypdf

logger = logging.getLogger(__name__)

# Resource limits & safety guards
MAX_IMAGE_PIXELS = 25_000_000
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
MAX_OCR_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_PDF_PAGES_OCR = 5
OCR_TIMEOUT_SECONDS = 30

SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp"}

class OcrError(Exception):
    """Base exception for OCR operations."""
    pass

class OcrEngineUnavailableError(OcrError):
    """Raised when Tesseract OCR engine or language data is not available."""
    pass

class OcrQualityError(OcrError):
    """Raised when OCR produces insufficient legible text."""
    pass

class OcrResourceLimitError(OcrError):
    """Raised when uploaded file exceeds bounded processing limits."""
    pass

class UnsupportedFormatError(OcrError):
    """Raised when file signature or extension is unsupported."""
    pass


class OcrService:
    """
    Production-hardened OCR extraction service using Tesseract with bounded resource limits,
    decompression bomb defense, image validation, and quality assessment.
    """
    def __init__(self, tesseract_cmd: Optional[str] = None):
        self._cmd = tesseract_cmd or self._discover_tesseract_cmd()
        if self._cmd:
            pytesseract.pytesseract.tesseract_cmd = self._cmd

    def _discover_tesseract_cmd(self) -> Optional[str]:
        """Locate Tesseract executable on PATH, env var, or standard installation paths."""
        env_cmd = os.getenv("TESSERACT_CMD")
        if env_cmd and Path(env_cmd).is_file():
            return env_cmd

        # Check standard Windows paths
        win_candidates = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
        ]
        for candidate in win_candidates:
            if Path(candidate).is_file():
                return candidate

        # Check standard Unix/Linux paths
        which_path = shutil.which("tesseract")
        if which_path:
            return which_path

        unix_candidates = [
            "/usr/bin/tesseract",
            "/usr/local/bin/tesseract",
            "/opt/homebrew/bin/tesseract"
        ]
        for candidate in unix_candidates:
            if Path(candidate).is_file():
                return candidate

        return None

    def is_available(self) -> bool:
        """Check if Tesseract OCR is installed, configured, and responsive."""
        if not self._cmd or not Path(self._cmd).is_file():
            self._cmd = self._discover_tesseract_cmd()
            if self._cmd:
                pytesseract.pytesseract.tesseract_cmd = self._cmd
            else:
                return False
        try:
            version = pytesseract.get_tesseract_version()
            return version is not None
        except Exception as e:
            logger.warning(f"Tesseract OCR availability check failed: {e}")
            return False

    def get_available_languages(self) -> List[str]:
        """Retrieve list of installed OCR languages."""
        if not self.is_available():
            return []
        try:
            return pytesseract.get_languages()
        except Exception as e:
            logger.warning(f"Failed to fetch available OCR languages: {e}")
            return []

    def validate_image_signature(self, file_bytes: bytes, filename: str) -> str:
        """Validate true image file signature (magic bytes) to prevent executable injection."""
        _, ext = os.path.splitext(filename.lower())
        if ext not in SUPPORTED_IMAGE_EXTENSIONS:
            raise UnsupportedFormatError(f"File extension '{ext}' is not a supported image format.")

        if file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        elif file_bytes.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        elif file_bytes.startswith(b"II*\x00") or file_bytes.startswith(b"MM\x00*"):
            return "image/tiff"
        elif file_bytes.startswith(b"BM"):
            return "image/bmp"
        elif len(file_bytes) > 12 and file_bytes[:4] == b"RIFF" and file_bytes[8:12] == b"WEBP":
            return "image/webp"

        raise UnsupportedFormatError(f"File content does not match genuine image signature for '{filename}'.")

    def extract_text_from_image(
        self,
        file_bytes: bytes,
        filename: str = "",
        lang: str = "eng",
        timeout_seconds: int = OCR_TIMEOUT_SECONDS
    ) -> Dict[str, Any]:
        """
        Run OCR on an uploaded image file with bounded limits and validation.
        """
        if not self.is_available():
            raise OcrEngineUnavailableError(
                "OCR engine (Tesseract) is not installed or available on this host. "
                "Please configure Tesseract OCR or upload a text-based PDF/DOCX file."
            )

        if len(file_bytes) > MAX_OCR_FILE_SIZE:
            raise OcrResourceLimitError(
                f"File size ({len(file_bytes) / 1024 / 1024:.2f} MB) exceeds maximum limit of 10 MB."
            )

        mime_type = self.validate_image_signature(file_bytes, filename or "image.png")

        try:
            with Image.open(io.BytesIO(file_bytes)) as img:
                # Decompression bomb and dimension checks
                w, h = img.size
                if w * h > MAX_IMAGE_PIXELS:
                    raise OcrResourceLimitError(f"Image resolution ({w}x{h}) exceeds safe processing limit.")

                # Convert to RGB/Grayscale for best OCR recognition
                if img.mode not in ("L", "RGB"):
                    img = img.convert("RGB")

                start_time = time.time()
                raw_text = pytesseract.image_to_string(
                    img,
                    lang=lang,
                    timeout=timeout_seconds
                )
                duration_ms = int((time.time() - start_time) * 1000)

        except (TimeoutError, Exception) as e:
            if isinstance(e, TimeoutError) or "timed out" in str(e).lower() or "timeout" in str(e).lower():
                raise OcrError(f"OCR processing timed out after {timeout_seconds} seconds.")
            if isinstance(e, OcrError):
                raise
            logger.error(f"Error during image OCR processing: {e}")
            raise OcrError(f"OCR image extraction failed: {str(e)}")

        normalized = self._normalize_ocr_text(raw_text)
        is_legible, reason = self.validate_text_quality(normalized)
        if not is_legible:
            raise OcrQualityError(
                f"Scanned image OCR produced inadequate or illegible text: {reason}. "
                "Please ensure the resume image is clear, high-contrast, and legible."
            )

        return {
            "text": normalized,
            "extraction_method": "OCR",
            "ocr_engine": "tesseract",
            "ocr_language": lang,
            "duration_ms": duration_ms,
            "character_count": len(normalized),
            "mime_type": mime_type
        }

    def extract_text_from_scanned_pdf(
        self,
        file_bytes: bytes,
        filename: str = "",
        max_pages: int = MAX_PDF_PAGES_OCR,
        lang: str = "eng",
        timeout_seconds: int = OCR_TIMEOUT_SECONDS
    ) -> Dict[str, Any]:
        """
        Run OCR fallback on pages of a scanned PDF that yielded insufficient native text.
        Extracts embedded raster page images and runs OCR on them.
        """
        if not self.is_available():
            raise OcrEngineUnavailableError(
                "OCR engine (Tesseract) is not installed or available on this host. "
                "Please configure Tesseract OCR or upload a text-based PDF/DOCX file."
            )

        if len(file_bytes) > MAX_OCR_FILE_SIZE:
            raise OcrResourceLimitError(f"PDF size exceeds maximum limit of 10 MB.")

        try:
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        except Exception as e:
            raise ValueError(f"Invalid or corrupted PDF file: {str(e)}")

        total_pages = len(reader.pages)
        if total_pages == 0:
            raise ValueError("PDF document contains zero pages.")

        pages_to_process = min(total_pages, max_pages)
        extracted_pages = []
        start_time = time.time()

        for page_idx in range(pages_to_process):
            # Check timeout
            if (time.time() - start_time) > timeout_seconds:
                raise OcrError(f"OCR processing timed out after {timeout_seconds} seconds.")

            page = reader.pages[page_idx]
            page_text_parts = []

            # Check embedded images on page
            images = getattr(page, "images", [])
            for img_file in images:
                try:
                    img_data = img_file.data
                    with Image.open(io.BytesIO(img_data)) as pil_img:
                        w, h = pil_img.size
                        if w * h > MAX_IMAGE_PIXELS:
                            continue
                        if pil_img.mode not in ("L", "RGB"):
                            pil_img = pil_img.convert("RGB")

                        img_text = pytesseract.image_to_string(pil_img, lang=lang, timeout=15)
                        if img_text.strip():
                            page_text_parts.append(img_text.strip())
                except Exception as img_err:
                    logger.warning(f"Could not OCR image on page {page_idx + 1}: {img_err}")

            if page_text_parts:
                extracted_pages.append("\n".join(page_text_parts))

        duration_ms = int((time.time() - start_time) * 1000)
        full_text = "\n\n".join(extracted_pages)
        normalized = self._normalize_ocr_text(full_text)

        is_legible, reason = self.validate_text_quality(normalized)
        if not is_legible:
            raise OcrQualityError(
                f"Scanned PDF OCR produced inadequate or illegible text: {reason}. "
                "Please upload a clear, legible resume document."
            )

        return {
            "text": normalized,
            "extraction_method": "OCR",
            "ocr_engine": "tesseract",
            "ocr_language": lang,
            "duration_ms": duration_ms,
            "character_count": len(normalized),
            "pages_processed": pages_to_process,
            "total_pages": total_pages,
            "mime_type": "application/pdf"
        }

    def validate_text_quality(self, text: str) -> Tuple[bool, str]:
        """
        Evaluate whether OCR output contains genuine readable resume content
        rather than noise, corrupted glyphs, or empty scans.
        """
        cleaned = text.strip()
        if len(cleaned) < 25:
            return False, "Extracted text is too short (< 25 characters)"

        words = [w for w in cleaned.split() if len(w) >= 2]
        if len(words) < 5:
            return False, f"Extracted text contains too few words ({len(words)} found, minimum 5 required)"

        # Check alphanumeric ratio to reject binary junk or noise artifacts
        alnum_chars = sum(1 for c in cleaned if c.isalnum())
        ratio = alnum_chars / len(cleaned) if len(cleaned) > 0 else 0
        if ratio < 0.35:
            return False, f"Extracted text has high noise or non-alphanumeric ratio ({ratio:.1%})"

        return True, "Legible content verified"

    def _normalize_ocr_text(self, text: str) -> str:
        """Clean OCR artifact characters while preserving formatting, technology names, and structure."""
        if not text:
            return ""
        import re
        # Remove null bytes and non-printable control characters except newlines/tabs
        cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)
        cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
        # Collapse multiple blank lines
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()
