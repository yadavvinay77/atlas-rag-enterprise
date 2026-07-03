from pathlib import Path

import fitz
from fastapi import HTTPException

from .config import settings
from .io import read_jsonl
from .models import PageRecord, PageVisual, SearchHit


def _candidate_paths(source_file: str) -> list[Path]:
    home = Path.home()
    return [
        settings.data_dir.parent / "uploads" / source_file,
        home / "Downloads" / "Telegram Desktop" / source_file,
        home / "Desktop" / source_file,
        home / "Downloads" / source_file,
    ]


def resolve_pdf_path(document_id: str) -> Path | None:
    pages = read_jsonl(settings.data_dir / "pages.jsonl", PageRecord)
    source_file = next(
        (page.source_file for page in pages if page.document_id == document_id),
        None,
    )
    if not source_file:
        return None
    return next((path for path in _candidate_paths(source_file) if path.exists()), None)


def visual_for_hit(hit: SearchHit) -> PageVisual | None:
    if not resolve_pdf_path(hit.chunk.document_id):
        return None
    page_number = hit.chunk.page_number
    source = hit.chunk.source_file
    return PageVisual(
        url=f"/api/pages/{hit.chunk.document_id}/{page_number}/image",
        caption=f"Visual page snapshot from {source}, page {page_number}.",
    )


def attach_visuals(hits: list[SearchHit]) -> list[SearchHit]:
    return [hit.model_copy(update={"visual": visual_for_hit(hit)}) for hit in hits]


def render_page_image(document_id: str, page_number: int, *, zoom: float = 1.8) -> Path:
    pdf_path = resolve_pdf_path(document_id)
    if not pdf_path:
        raise HTTPException(status_code=404, detail="Source PDF was not found for this page.")
    cache_dir = settings.data_dir.parent / "visuals" / document_id
    cache_dir.mkdir(parents=True, exist_ok=True)
    image_path = cache_dir / f"page_{page_number:04d}.png"
    if image_path.exists():
        return image_path

    with fitz.open(pdf_path) as document:
        if page_number < 1 or page_number > len(document):
            raise HTTPException(status_code=404, detail="Page number is outside this PDF.")
        page = document[page_number - 1]
        pixmap = page.get_pixmap(
            matrix=fitz.Matrix(zoom, zoom),
            alpha=False,
            annots=True,
        )
        pixmap.save(image_path)
    return image_path
