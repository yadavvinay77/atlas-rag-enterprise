from fastapi.testclient import TestClient
import httpx

from enterprise_rag.config import settings
from enterprise_rag.io import write_jsonl
from enterprise_rag.models import ChunkRecord, DocumentSummary, PageRecord
from enterprise_rag.service import app, generation_failure_message, get_retriever


def test_home_and_status_are_available() -> None:
    client = TestClient(app)
    home = client.get("/")
    status = client.get("/api/status")
    providers = client.get("/api/generation/providers")

    assert home.status_code == 200
    assert "Atlas RAG" in home.text
    assert status.status_code == 200
    assert "chunk_count" in status.json()
    assert providers.status_code == 200
    assert {item["provider"] for item in providers.json()} >= {
        "extractive",
        "ollama",
        "openai",
        "compatible",
    }


def test_agent_plan_endpoint_returns_trace() -> None:
    client = TestClient(app)

    response = client.post("/api/agent/plan", json={"question": "Summarize this policy"})

    assert response.status_code == 200
    assert response.json()["intent"] == "summarize"
    assert response.json()["route"] == "multi-document"


def test_generation_timeout_message_is_actionable() -> None:
    message = generation_failure_message(httpx.ReadTimeout("slow model"))

    assert "did not finish" in message


def test_remove_document_endpoint_deletes_only_that_indexed_document(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    pages = [
        PageRecord(
            document_id="doc-a",
            source_file="a.pdf",
            page_number=1,
            text="alpha",
            extraction_method="native",
            quality_score=1.0,
        ),
        PageRecord(
            document_id="doc-b",
            source_file="b.pdf",
            page_number=1,
            text="beta",
            extraction_method="native",
            quality_score=1.0,
        ),
    ]
    chunks = [
        ChunkRecord(
            chunk_id="a1",
            document_id="doc-a",
            source_file="a.pdf",
            page_number=1,
            text="alpha",
            parent_text="alpha",
            extraction_method="native",
            quality_score=1.0,
        ),
        ChunkRecord(
            chunk_id="b1",
            document_id="doc-b",
            source_file="b.pdf",
            page_number=1,
            text="beta",
            parent_text="beta",
            extraction_method="native",
            quality_score=1.0,
        ),
    ]
    summaries = [
        DocumentSummary(
            document_id="doc-a",
            source_file="a.pdf",
            page_count=1,
            chunk_count=1,
            ocr_page_count=0,
            low_quality_page_count=0,
        ),
        DocumentSummary(
            document_id="doc-b",
            source_file="b.pdf",
            page_count=1,
            chunk_count=1,
            ocr_page_count=0,
            low_quality_page_count=0,
        ),
    ]
    write_jsonl(tmp_path / "pages.jsonl", pages)
    write_jsonl(tmp_path / "chunks.jsonl", chunks)
    write_jsonl(tmp_path / "documents.jsonl", summaries)

    client = TestClient(app)
    response = client.delete("/api/documents/doc-a")
    remaining = client.get("/api/documents")

    assert response.status_code == 200
    assert response.json()["source_file"] == "a.pdf"
    assert [item["document_id"] for item in remaining.json()] == ["doc-b"]


def test_ask_response_includes_agent_trace(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    get_retriever.cache_clear()
    chunks = [
        ChunkRecord(
            chunk_id="policy-1",
            document_id="policy",
            source_file="policy.pdf",
            page_number=1,
            text="Employee bonus policy requires manager approval and HR review.",
            parent_text="Employee bonus policy requires manager approval and HR review.",
            extraction_method="native",
            quality_score=1.0,
        )
    ]
    write_jsonl(tmp_path / "chunks.jsonl", chunks)

    client = TestClient(app)
    response = client.post(
        "/api/ask",
        json={
            "question": "What is the employee bonus policy?",
            "generate": False,
            "run_native_evaluators": False,
        },
    )

    get_retriever.cache_clear()

    assert response.status_code == 200
    trace = response.json()["agent_trace"]
    assert trace["steps"][0]["agent"] == "Planner Agent"
    assert trace["steps"][-1]["agent"] == "Human Approval Node"
