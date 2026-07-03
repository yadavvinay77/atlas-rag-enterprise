from pathlib import Path
import sys

import typer

from .chunking import chunk_pages
from .config import settings
from .evaluation import retrieval_metrics
from .ingestion import ingest_pdf
from .indexing import summarize_records
from .io import read_jsonl, write_jsonl
from .models import ChunkRecord, PageRecord
from .retrieval import HybridRetriever

app = typer.Typer(no_args_is_help=True)


def _configure_utf8_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


_configure_utf8_console()

DEMO_PAGES = [
    PageRecord(
        document_id="demo-policy",
        source_file="demo_policy.txt",
        page_number=1,
        text=(
            "ગામતળ વિસ્તાર માટે જમીન ફાળવણી સંબંધિત ઠરાવ. "
            "જમીન ફાળવણી પહેલાં સ્થાનિક જરૂરિયાત, ઉપલબ્ધ સરકારી જમીન અને "
            "સક્ષમ અધિકારીની મંજૂરી તપાસવી જરૂરી છે."
        ),
        extraction_method="native",
        quality_score=1.0,
        language_hint="gu",
    ),
    PageRecord(
        document_id="demo-policy",
        source_file="demo_policy.txt",
        page_number=2,
        text=(
            "Village-site expansion applications must be examined against local need, "
            "availability of government land, and approval by the competent authority."
        ),
        extraction_method="native",
        quality_score=1.0,
        language_hint="en",
    ),
]


@app.command()
def ingest(pdf: Path, max_pages: int | None = None) -> None:
    """Extract, OCR-route, and chunk a PDF."""
    pages = ingest_pdf(
        pdf,
        ocr_languages=settings.ocr_languages,
        ocr_dpi=settings.ocr_dpi,
        max_pages=max_pages,
    )
    chunks = chunk_pages(pages)
    write_jsonl(settings.data_dir / "pages.jsonl", pages)
    write_jsonl(settings.data_dir / "chunks.jsonl", chunks)
    typer.echo(f"Wrote {len(pages)} pages and {len(chunks)} chunks to {settings.data_dir}")


@app.command()
def create_demo_index() -> None:
    """Create a tiny bilingual index so search and Q&A can be tested immediately."""
    chunks = chunk_pages(DEMO_PAGES)
    write_jsonl(settings.data_dir / "pages.jsonl", DEMO_PAGES)
    write_jsonl(settings.data_dir / "chunks.jsonl", chunks)
    typer.echo(f"Wrote {len(chunks)} demo chunks to {settings.data_dir}")


@app.command()
def rechunk() -> None:
    """Rebuild chunks from the already extracted pages."""
    pages = read_jsonl(settings.data_dir / "pages.jsonl", PageRecord)
    if not pages:
        raise typer.BadParameter("No pages.jsonl found. Ingest documents first.")
    chunks = chunk_pages(pages)
    write_jsonl(settings.data_dir / "chunks.jsonl", chunks)
    write_jsonl(settings.data_dir / "documents.jsonl", summarize_records(pages, chunks))
    typer.echo(f"Rebuilt {len(chunks)} chunks from {len(pages)} pages.")


@app.command()
def search(query: str, top_k: int = 8) -> None:
    """Search the local hybrid index."""
    chunks = read_jsonl(settings.data_dir / "chunks.jsonl", ChunkRecord)
    retriever = HybridRetriever(
        chunks,
        enable_dense=settings.enable_dense,
        embedding_model=settings.embedding_model,
    )
    for hit in retriever.search(query, top_k=top_k):
        typer.echo(
            f"{hit.score:.4f} | page {hit.chunk.page_number} | "
            f"{hit.chunk.text[:240].replace(chr(10), ' ')}"
        )


@app.command()
def evaluate() -> None:
    """Print an example metric calculation; replace with the labeled JSONL set."""
    result = retrieval_metrics([["a", "b"], ["c"]], [{"b"}, {"x"}])
    typer.echo(f"Recall@K={result.recall_at_k:.3f} MRR={result.mean_reciprocal_rank:.3f}")


@app.command()
def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Start the FastAPI service."""
    import uvicorn

    uvicorn.run("enterprise_rag.service:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    app()
