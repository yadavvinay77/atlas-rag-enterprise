from pathlib import Path

import fitz

from enterprise_rag.ingestion import ingest_pdf


def test_image_only_page_does_not_fail_without_tesseract(tmp_path: Path, monkeypatch) -> None:
    pdf_path = tmp_path / "image-only.pdf"
    document = fitz.open()
    document.new_page()
    document.save(pdf_path)
    document.close()

    monkeypatch.setattr("enterprise_rag.ingestion.shutil.which", lambda _: None)
    pages = ingest_pdf(pdf_path)

    assert len(pages) == 1
    assert pages[0].extraction_method == "unavailable"
    assert "ocr_unavailable" in pages[0].warnings

