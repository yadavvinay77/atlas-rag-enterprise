from pathlib import Path
from threading import Lock
from uuid import uuid4

import fitz

from .chunking import chunk_pages
from .config import settings
from .ingestion import ingest_pdf
from .io import read_jsonl, write_jsonl
from .models import ChunkRecord, DocumentSummary, IndexJob, PageRecord

JOBS: dict[str, IndexJob] = {}
JOBS_LOCK = Lock()
INDEX_LOCK = Lock()


def create_job(source_file: str) -> IndexJob:
    job = IndexJob(job_id=uuid4().hex[:12], status="queued", source_file=source_file)
    with JOBS_LOCK:
        JOBS[job.job_id] = job
    return job


def get_job(job_id: str) -> IndexJob | None:
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        return job.model_copy(deep=True) if job else None


def _update_job(job_id: str, **changes: object) -> None:
    with JOBS_LOCK:
        current = JOBS[job_id]
        JOBS[job_id] = current.model_copy(update=changes)


def index_pdf_job(
    job_id: str,
    pdf_path: Path,
    *,
    replace_index: bool,
    max_pages: int | None = None,
) -> None:
    index_paths_job(
        job_id,
        [pdf_path],
        replace_index=replace_index,
        max_pages=max_pages,
    )


def index_paths_job(
    job_id: str,
    pdf_paths: list[Path],
    *,
    replace_index: bool,
    max_pages: int | None = None,
) -> None:
    try:
        _update_job(job_id, status="running", message="Opening PDF collection")
        totals: list[int] = []
        for path in pdf_paths:
            with fitz.open(path) as document:
                totals.append(min(len(document), max_pages or len(document)))
        total_pages = sum(totals)
        completed_before = 0
        all_pages: list[PageRecord] = []

        def progress(current: int, total: int, message: str) -> None:
            _update_job(
                job_id,
                current_page=completed_before + current,
                total_pages=total_pages,
                message=message,
            )

        for pdf_path, page_total in zip(pdf_paths, totals, strict=True):
            _update_job(job_id, message=f"Extracting {pdf_path.name}")
            pages = ingest_pdf(
                pdf_path,
                ocr_languages=settings.ocr_languages,
                ocr_dpi=settings.ocr_dpi,
                max_pages=max_pages,
                progress=progress,
            )
            all_pages.extend(pages)
            completed_before += page_total

        _update_job(job_id, message="Creating searchable chunks")
        chunks = chunk_pages(all_pages)

        with INDEX_LOCK:
            existing_pages = [] if replace_index else read_jsonl(
                settings.data_dir / "pages.jsonl", PageRecord
            )
            existing_chunks = [] if replace_index else read_jsonl(
                settings.data_dir / "chunks.jsonl", ChunkRecord
            )
            document_ids = {page.document_id for page in all_pages}
            existing_pages = [
                page for page in existing_pages if page.document_id not in document_ids
            ]
            existing_chunks = [
                chunk for chunk in existing_chunks if chunk.document_id not in document_ids
            ]
            write_jsonl(settings.data_dir / "pages.jsonl", [*existing_pages, *all_pages])
            write_jsonl(settings.data_dir / "chunks.jsonl", [*existing_chunks, *chunks])
            write_jsonl(
                settings.data_dir / "documents.jsonl",
                summarize_records([*existing_pages, *all_pages], [*existing_chunks, *chunks]),
            )

        _update_job(
            job_id,
            status="completed",
            current_page=len(all_pages),
            total_pages=len(all_pages),
            message="Index ready for questions",
            pages_indexed=len(all_pages),
            chunks_created=len(chunks),
        )
    except Exception as exc:
        _update_job(job_id, status="failed", message=str(exc))


def summarize_records(
    pages: list[PageRecord], chunks: list[ChunkRecord]
) -> list[DocumentSummary]:
    by_document: dict[str, list[PageRecord]] = {}
    chunks_by_document: dict[str, int] = {}
    for page in pages:
        by_document.setdefault(page.document_id, []).append(page)
    for chunk in chunks:
        chunks_by_document[chunk.document_id] = chunks_by_document.get(chunk.document_id, 0) + 1

    return [
        DocumentSummary(
            document_id=document_id,
            source_file=document_pages[0].source_file,
            page_count=len(document_pages),
            chunk_count=chunks_by_document.get(document_id, 0),
            ocr_page_count=sum(page.extraction_method == "ocr" for page in document_pages),
            low_quality_page_count=sum(page.quality_score < 0.55 for page in document_pages),
        )
        for document_id, document_pages in by_document.items()
    ]


def document_summaries() -> list[DocumentSummary]:
    manifest = read_jsonl(settings.data_dir / "documents.jsonl", DocumentSummary)
    if manifest:
        return manifest
    pages = read_jsonl(settings.data_dir / "pages.jsonl", PageRecord)
    chunks = read_jsonl(settings.data_dir / "chunks.jsonl", ChunkRecord)
    summaries = summarize_records(pages, chunks)
    if summaries:
        write_jsonl(settings.data_dir / "documents.jsonl", summaries)
    return summaries


def remove_document_from_index(document_id: str) -> DocumentSummary:
    with INDEX_LOCK:
        pages = read_jsonl(settings.data_dir / "pages.jsonl", PageRecord)
        chunks = read_jsonl(settings.data_dir / "chunks.jsonl", ChunkRecord)
        matching_pages = [page for page in pages if page.document_id == document_id]
        matching_chunks = [chunk for chunk in chunks if chunk.document_id == document_id]
        if not matching_pages and not matching_chunks:
            raise KeyError(document_id)

        removed_summary = DocumentSummary(
            document_id=document_id,
            source_file=(
                matching_pages[0].source_file
                if matching_pages
                else matching_chunks[0].source_file
            ),
            page_count=len(matching_pages),
            chunk_count=len(matching_chunks),
            ocr_page_count=sum(page.extraction_method == "ocr" for page in matching_pages),
            low_quality_page_count=sum(
                page.quality_score < 0.55 for page in matching_pages
            ),
        )
        remaining_pages = [page for page in pages if page.document_id != document_id]
        remaining_chunks = [
            chunk for chunk in chunks if chunk.document_id != document_id
        ]
        write_jsonl(settings.data_dir / "pages.jsonl", remaining_pages)
        write_jsonl(settings.data_dir / "chunks.jsonl", remaining_chunks)
        write_jsonl(
            settings.data_dir / "documents.jsonl",
            summarize_records(remaining_pages, remaining_chunks),
        )
        return removed_summary
