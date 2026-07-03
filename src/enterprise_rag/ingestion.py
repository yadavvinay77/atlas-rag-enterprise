import hashlib
from pathlib import Path
import shutil
from collections.abc import Callable

import fitz
import pytesseract
from pytesseract import TesseractNotFoundError
from PIL import Image

from .models import PageRecord
from .quality import extraction_quality, language_hint


def _ocr_page(page: fitz.Page, languages: str, dpi: int) -> str:
    scale = dpi / 72
    pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
    image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
    return pytesseract.image_to_string(image, lang=languages).strip()


def _document_id(pdf_path: Path) -> str:
    digest = hashlib.sha256()
    with pdf_path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()[:16]


def ingest_pdf(
    pdf_path: Path,
    *,
    ocr_languages: str = "guj+eng",
    ocr_dpi: int = 300,
    native_quality_threshold: float = 0.55,
    max_pages: int | None = None,
    progress: Callable[[int, int, str], None] | None = None,
) -> list[PageRecord]:
    document_id = _document_id(pdf_path)
    records: list[PageRecord] = []
    tesseract_available = shutil.which("tesseract") is not None

    with fitz.open(pdf_path) as document:
        page_count = min(len(document), max_pages or len(document))
        for index in range(page_count):
            if progress:
                progress(index + 1, page_count, "Extracting document text")
            page = document[index]
            native_text = page.get_text("text").strip()
            quality, warnings = extraction_quality(native_text)
            method = "native"
            text = native_text

            if quality < native_quality_threshold and tesseract_available:
                try:
                    method = "ocr"
                    text = _ocr_page(page, ocr_languages, ocr_dpi)
                    quality, ocr_warnings = extraction_quality(text)
                    warnings.extend(["native_text_rejected", *ocr_warnings])
                except (TesseractNotFoundError, pytesseract.TesseractError):
                    warnings.append("ocr_failed")
            elif quality < native_quality_threshold:
                warnings.append("ocr_unavailable")
                if not native_text:
                    method = "unavailable"

            records.append(
                PageRecord(
                    document_id=document_id,
                    source_file=pdf_path.name,
                    page_number=index + 1,
                    text=text,
                    extraction_method=method,
                    quality_score=quality,
                    language_hint=language_hint(text),
                    warnings=sorted(set(warnings)),
                )
            )
    return records
