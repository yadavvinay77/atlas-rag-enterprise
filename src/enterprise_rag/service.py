from functools import lru_cache
from pathlib import Path
from threading import Thread

import httpx

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

from .architecture import architecture_report
from .agents import (
    plan_agent,
    record_approval_agent,
    record_retrieval_agent,
    record_validation_agent,
)
from .config import settings
from .evaluation import evaluate_answer
from .evaluation_providers import provider_catalog
from .generation import answer_extractively, answer_with_ollama, answer_with_openai_compatible
from .generation_providers import GenerationProviderInfo, generation_provider_catalog, provider_info
from .indexing import (
    create_job,
    document_summaries,
    get_job,
    index_paths_job,
    remove_document_from_index,
)
from .io import read_jsonl
from .memory import conversations, should_use_conversation_context
from .models import (
    Answer,
    ArchitectureReport,
    ChunkRecord,
    ConversationTurn,
    DocumentSummary,
    IndexJob,
    SearchHit,
    EvaluationProviderInfo,
)
from .retrieval import HybridRetriever
from .ui import HTML
from .visuals import attach_visuals, render_page_image

app = FastAPI(title="Enterprise Document RAG", version="0.2.0")


class AskRequest(BaseModel):
    question: str = Field(min_length=2)
    top_k: int = Field(default=5, ge=1, le=20)
    generate: bool = True
    run_native_evaluators: bool = True
    generation_provider: str | None = None
    generation_model: str | None = None
    conversation_id: str | None = None


class PathIngestRequest(BaseModel):
    path: str = Field(min_length=3)
    replace_index: bool = True
    max_pages: int | None = Field(default=None, ge=1)


def generation_failure_message(exc: Exception) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
        if status_code == 403:
            return "HTTP 403: the selected model is not available to this API project."
        if status_code == 429:
            return "HTTP 429: quota or billing limit exceeded for this API project."
        return f"HTTP {status_code}: provider rejected the request."
    if isinstance(exc, httpx.ReadTimeout):
        return "ReadTimeout: provider did not finish before the configured timeout."
    if isinstance(exc, httpx.RequestError):
        return f"{type(exc).__name__}: provider endpoint was unreachable."
    return f"{type(exc).__name__}: {exc}"


def _provider_answer(
    *,
    provider: str,
    model: str | None,
    question: str,
    hits: list[SearchHit],
    history: list[ConversationTurn],
) -> Answer:
    if provider == "openai":
        return answer_with_openai_compatible(
            question,
            hits,
            base_url=settings.openai_base_url,
            model=model or settings.openai_model,
            provider="openai",
            api_key=settings.openai_api_key,
            timeout_seconds=settings.ollama_timeout_seconds,
            history=history,
        )
    if provider == "compatible":
        return answer_with_openai_compatible(
            question,
            hits,
            base_url=settings.compatible_base_url,
            model=model or settings.compatible_model,
            provider="compatible",
            api_key=settings.compatible_api_key,
            timeout_seconds=settings.ollama_timeout_seconds,
            history=history,
        )
    return answer_with_ollama(
        question,
        hits,
        base_url=settings.ollama_url,
        model=model or settings.ollama_model,
        timeout_seconds=settings.ollama_timeout_seconds,
        history=history,
    )


def _fallback_provider(selected_provider: str) -> str | None:
    active = {
        provider.provider
        for provider in generation_provider_catalog()
        if provider.status == "active"
    }
    for candidate in ("ollama", "openai"):
        if candidate != selected_provider and candidate in active:
            return candidate
    return None


def _build_pipeline_trace(
    *,
    request: AskRequest,
    retrieval_query: str,
    used_conversation_context: bool,
    hits: list[SearchHit],
    answer: Answer,
) -> dict[str, object]:
    sources = list(dict.fromkeys(hit.chunk.source_file for hit in hits))
    pages = list(
        dict.fromkeys(f"{hit.chunk.source_file} page {hit.chunk.page_number}" for hit in hits)
    )
    retrieval_mode = "hybrid BM25 + dense + MMR" if settings.enable_dense else "BM25 + MMR"
    evaluation = answer.evaluation
    provider_results = evaluation.provider_results if evaluation else []
    return {
        "query": {
            "original": request.question,
            "resolved": retrieval_query,
            "used_memory": used_conversation_context,
            "expansion_detected": retrieval_query.strip() != request.question.strip().rstrip("#").strip(),
        },
        "retrieval": {
            "mode": retrieval_mode,
            "top_k": request.top_k,
            "candidate_count": 30,
            "mmr_enabled": True,
            "dense_enabled": settings.enable_dense,
            "citation_count": len(hits),
        },
        "context": {
            "sources": sources,
            "pages": pages,
            "source_diversity": evaluation.source_diversity if evaluation else 0.0,
            "context_relevance": evaluation.mean_context_relevance if evaluation else 0.0,
        },
        "generation": {
            "provider": answer.generation_provider,
            "model": answer.generation_model,
            "status": answer.generation_status,
            "note": answer.generation_note,
        },
        "evaluation": {
            "precision_at_k": evaluation.precision_at_k_proxy if evaluation else 0.0,
            "hit_rate_at_k": evaluation.hit_rate_at_k_proxy if evaluation else 0.0,
            "ndcg_at_k": evaluation.ndcg_at_k_proxy if evaluation else 0.0,
            "groundedness": evaluation.citation_coverage if evaluation else 0.0,
            "faithfulness": evaluation.groundedness if evaluation else 0.0,
            "hallucination_risk": evaluation.hallucination_risk if evaluation else 1.0,
            "providers": [
                {
                    "provider": result.provider,
                    "status": result.status,
                    "score": result.score,
                    "summary": result.summary,
                }
                for result in provider_results
            ],
        },
    }


@lru_cache
def get_retriever() -> HybridRetriever:
    chunks = read_jsonl(settings.data_dir / "chunks.jsonl", ChunkRecord)
    if not chunks:
        raise RuntimeError("No index found. Run `enterprise-rag ingest <pdf>` first.")
    return HybridRetriever(
        chunks,
        enable_dense=settings.enable_dense,
        embedding_model=settings.embedding_model,
    )


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return HTML


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/status")
def status() -> dict[str, str | int | bool]:
    summaries = document_summaries()
    return {
        "chunk_count": sum(item.chunk_count for item in summaries),
        "retrieval_mode": (
            "hybrid BM25 + dense + MMR"
            if settings.enable_dense
            else "BM25 + MMR"
        ),
        "generation_model": settings.ollama_model,
        "generation_provider": settings.generation_provider,
        "demo_index": bool(
            summaries and summaries[0].document_id == "demo-policy"
        ),
        "document_count": len(summaries),
    }


@app.get("/api/documents", response_model=list[DocumentSummary])
def documents() -> list[DocumentSummary]:
    return document_summaries()


@app.delete("/api/documents/{document_id}", response_model=DocumentSummary)
def remove_document(document_id: str) -> DocumentSummary:
    try:
        removed = remove_document_from_index(document_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Indexed document not found.") from exc
    get_retriever.cache_clear()
    return removed


@app.get("/api/architecture", response_model=ArchitectureReport)
def architecture() -> ArchitectureReport:
    return architecture_report()


@app.post("/api/agent/plan")
def agent_plan(request: AskRequest):
    conversation_id = conversations.create_or_get(request.conversation_id)
    return plan_agent(request.question, conversations.turns(conversation_id))


@app.get("/api/evaluators", response_model=list[EvaluationProviderInfo])
def evaluators() -> list[EvaluationProviderInfo]:
    return provider_catalog()


@app.get("/api/generation/providers", response_model=list[GenerationProviderInfo])
def generation_providers() -> list[GenerationProviderInfo]:
    return generation_provider_catalog()


def _start_index_job(
    source_path: Path, *, replace_index: bool, max_pages: int | None = None
) -> IndexJob:
    if source_path.is_dir():
        pdf_paths = sorted(source_path.glob("*.pdf"))
        source_name = f"{source_path.name} ({len(pdf_paths)} PDFs)"
    elif source_path.is_file() and source_path.suffix.lower() == ".pdf":
        pdf_paths = [source_path]
        source_name = source_path.name
    else:
        pdf_paths = []
        source_name = source_path.name
    if not pdf_paths:
        raise HTTPException(
            status_code=400,
            detail="Select an existing PDF file or a folder containing PDF files.",
        )
    job = create_job(source_name)
    Thread(
        target=index_paths_job,
        args=(job.job_id, pdf_paths),
        kwargs={"replace_index": replace_index, "max_pages": max_pages},
        daemon=True,
    ).start()
    return job


@app.post("/api/index/path", response_model=IndexJob)
def index_from_path(request: PathIngestRequest) -> IndexJob:
    return _start_index_job(
        Path(request.path).expanduser(),
        replace_index=request.replace_index,
        max_pages=request.max_pages,
    )


@app.post("/api/index/upload", response_model=IndexJob)
async def index_upload(
    file: UploadFile = File(...),
    replace_index: bool = Form(True),
    max_pages: int | None = Form(None),
) -> IndexJob:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported.")
    upload_dir = settings.data_dir.parent / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    destination = upload_dir / Path(file.filename).name
    with destination.open("wb") as handle:
        while block := await file.read(1024 * 1024):
            handle.write(block)
    return _start_index_job(
        destination, replace_index=replace_index, max_pages=max_pages
    )


@app.get("/api/jobs/{job_id}", response_model=IndexJob)
def job_status(job_id: str) -> IndexJob:
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Indexing job not found.")
    if job.status == "completed":
        get_retriever.cache_clear()
    return job


@app.get("/search", response_model=list[SearchHit])
def search(q: str = Query(min_length=2), top_k: int = Query(8, ge=1, le=30)) -> list[SearchHit]:
    try:
        return attach_visuals(get_retriever().search(q, top_k=top_k))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/ask", response_model=Answer)
def ask(q: str = Query(min_length=2), top_k: int = Query(8, ge=1, le=20)) -> Answer:
    hits = search(q, top_k)
    return answer_extractively(q, hits)


@app.post("/api/ask", response_model=Answer)
def ask_verified(request: AskRequest) -> Answer:
    conversation_id = conversations.create_or_get(request.conversation_id)
    history = conversations.turns(conversation_id)
    agent_trace = plan_agent(request.question, history)
    used_conversation_context = should_use_conversation_context(request.question, history)
    retrieval_query = agent_trace.retrieval_query
    preferred_document_ids = (
        {
            document_id
            for turn in history[-3:]
            for document_id in turn.cited_document_ids
        }
        if used_conversation_context
        else set()
    )
    hits = get_retriever().search(
        retrieval_query,
        top_k=request.top_k,
        preferred_document_ids=preferred_document_ids,
    )
    hits = attach_visuals(hits)
    agent_trace = record_retrieval_agent(agent_trace, hits)
    generation_provider = (request.generation_provider or settings.generation_provider).lower()
    generation_model = request.generation_model
    if not request.generate or generation_provider == "extractive":
        answer = answer_extractively(
            request.question, hits, evidence_query=retrieval_query
        )
    else:
        selected_provider = provider_info(generation_provider)
        try:
            if selected_provider and selected_provider.status != "active":
                answer = answer_extractively(
                    request.question, hits, evidence_query=retrieval_query
                )
                answer.generation_status = "fallback"
                answer.generation_note = (
                    f"{selected_provider.label} is {selected_provider.status}. "
                    f"Setup needed: {selected_provider.setup}"
                )
            else:
                answer = _provider_answer(
                    provider=generation_provider,
                    model=generation_model,
                    question=request.question,
                    hits=hits,
                    history=history,
                )
        except Exception as exc:
            failure_reason = generation_failure_message(exc)
            fallback_provider = _fallback_provider(generation_provider)
            if fallback_provider:
                try:
                    answer = _provider_answer(
                        provider=fallback_provider,
                        model=None,
                        question=request.question,
                        hits=hits,
                        history=history,
                    )
                    answer.generation_status = "fallback"
                    answer.generation_note = (
                        f"{generation_provider} failed ({failure_reason}); "
                        f"used {fallback_provider} instead."
                    )
                except Exception as fallback_exc:
                    answer = answer_extractively(
                        request.question, hits, evidence_query=retrieval_query
                    )
                    answer.generation_status = "fallback"
                    answer.generation_note = (
                        f"{generation_provider} failed ({failure_reason}); "
                        f"{fallback_provider} also failed "
                        f"({generation_failure_message(fallback_exc)})."
                    )
            else:
                answer = answer_extractively(
                    request.question, hits, evidence_query=retrieval_query
                )
                answer.generation_status = "fallback"
                answer.generation_note = f"{generation_provider} failed: {failure_reason}"
    answer.conversation_id = conversation_id
    answer.retrieval_query = retrieval_query
    answer.used_conversation_context = used_conversation_context
    answer.evaluation = evaluate_answer(
        question=request.question,
        retrieval_query=retrieval_query,
        answer=answer.answer,
        hits=hits,
        run_native_evaluators=request.run_native_evaluators,
    )
    agent_trace = record_validation_agent(
        agent_trace,
        question=request.question,
        answer=answer,
        hits=hits,
        run_native_evaluators=request.run_native_evaluators,
    )
    answer.agent_trace = record_approval_agent(agent_trace, request.question, answer)
    answer.pipeline_trace = _build_pipeline_trace(
        request=request,
        retrieval_query=retrieval_query,
        used_conversation_context=used_conversation_context,
        hits=hits,
        answer=answer,
    )
    conversations.add(
        conversation_id,
        ConversationTurn(
            question=request.question,
            answer=answer.answer,
            retrieval_query=retrieval_query,
            cited_document_ids=list(
                dict.fromkeys(hit.chunk.document_id for hit in hits)
            ),
            cited_source_files=list(
                dict.fromkeys(hit.chunk.source_file for hit in hits)
            ),
        ),
    )
    return answer


@app.delete("/api/conversations/{conversation_id}")
def clear_conversation(conversation_id: str) -> dict[str, str]:
    conversations.clear(conversation_id)
    return {"status": "cleared"}


@app.get("/api/pages/{document_id}/{page_number}/image")
def page_image(document_id: str, page_number: int) -> FileResponse:
    image_path = render_page_image(document_id, page_number)
    return FileResponse(image_path, media_type="image/png")
