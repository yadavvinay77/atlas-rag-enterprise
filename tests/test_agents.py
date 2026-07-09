from enterprise_rag.agents import (
    plan_agent,
    record_approval_agent,
    record_retrieval_agent,
    record_validation_agent,
)
from enterprise_rag.generation import answer_extractively
from enterprise_rag.models import ChunkRecord, SearchHit


def hit(text: str) -> SearchHit:
    chunk = ChunkRecord(
        chunk_id="c1",
        document_id="doc",
        source_file="policy.pdf",
        page_number=1,
        text=text,
        parent_text=text,
        extraction_method="native",
        quality_score=1.0,
    )
    return SearchHit(chunk=chunk, score=1.0)


def test_agent_plan_classifies_and_routes_summary() -> None:
    trace = plan_agent("Summarize the employee policy", [])

    assert trace.intent == "summarize"
    assert trace.route == "multi-document"
    assert [step.agent for step in trace.steps] == [
        "Planner Agent",
        "Router Agent",
        "Memory Agent",
    ]


def test_agent_trace_records_retrieval_validation_and_approval() -> None:
    hits = [hit("Employee bonus policy requires manager approval and HR review.")]
    answer = answer_extractively("What is the employee bonus policy?", hits)
    trace = plan_agent("What is the employee bonus policy?", [])

    trace = record_retrieval_agent(trace, hits)
    trace = record_validation_agent(
        trace,
        question="What is the employee bonus policy?",
        answer=answer,
        hits=hits,
        run_native_evaluators=False,
    )
    trace = record_approval_agent(trace, "What is the employee bonus policy?", answer)

    assert trace.validation_status in {"pass", "review"}
    assert trace.steps[-1].agent == "Human Approval Node"
    assert trace.approval_required is False


def test_approval_agent_flags_medical_treatment_questions() -> None:
    hits = [hit("The document mentions metronidazole as a treatment option.")]
    answer = answer_extractively("What medicine can treat this?", hits)
    trace = plan_agent("What medicine can treat this?", [])
    trace = record_validation_agent(
        trace,
        question="What medicine can treat this?",
        answer=answer,
        hits=hits,
        run_native_evaluators=False,
    )
    trace = record_approval_agent(trace, "What medicine can treat this?", answer)

    assert trace.approval_required is True
    assert "medical" in trace.approval_reason
