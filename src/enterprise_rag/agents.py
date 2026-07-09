from uuid import uuid4

from .evaluation import evaluate_answer
from .memory import contextualize_question, should_use_conversation_context
from .models import AgentStep, AgentTrace, Answer, ConversationTurn, SearchHit

MEDICAL_SAFETY_TERMS = {
    "diagnose",
    "dose",
    "drug",
    "medicine",
    "medication",
    "prescribe",
    "therapy",
    "treat",
    "treatment",
}
COMPARISON_TERMS = {"compare", "difference", "versus", "vs"}
SUMMARY_TERMS = {"summarize", "summary", "overview", "explain"}
EVALUATION_TERMS = {"confidence", "evaluate", "evidence", "faithful", "grounded", "source"}


def _tokens(text: str) -> set[str]:
    return {token.strip(".,?!:;()[]{}").lower() for token in text.split()}


def plan_agent(question: str, history: list[ConversationTurn]) -> AgentTrace:
    terms = _tokens(question)
    used_memory = should_use_conversation_context(question, history)
    retrieval_query = contextualize_question(question, history)

    if terms & COMPARISON_TERMS:
        intent = "compare"
    elif terms & SUMMARY_TERMS:
        intent = "summarize"
    elif terms & EVALUATION_TERMS:
        intent = "evaluate"
    elif used_memory:
        intent = "follow-up"
    else:
        intent = "answer"

    route = "multi-document" if intent in {"compare", "summarize"} else "focused-qa"
    steps = [
        AgentStep(
            agent="Planner Agent",
            action=f"Classified request as {intent}.",
            status="completed",
            rationale="The planner inspects user wording and conversation state before retrieval.",
        ),
        AgentStep(
            agent="Router Agent",
            action=f"Selected {route} route.",
            status="completed",
            rationale="The route controls retrieval breadth and downstream validation expectations.",
        ),
        AgentStep(
            agent="Memory Agent",
            action="Resolved follow-up context." if used_memory else "No follow-up context needed.",
            status="completed",
            rationale="Conversation memory is only used when the question is context-dependent.",
        ),
    ]
    return AgentTrace(
        run_id=str(uuid4()),
        intent=intent,
        route=route,
        retrieval_query=retrieval_query,
        steps=steps,
    )


def record_retrieval_agent(trace: AgentTrace, hits: list[SearchHit]) -> AgentTrace:
    sources = len({hit.chunk.source_file for hit in hits})
    trace.steps.append(
        AgentStep(
            agent="Retrieval Agent",
            action=f"Retrieved {len(hits)} cited passages from {sources} source(s).",
            status="completed" if hits else "abstain",
            rationale="The retriever uses the resolved query, hybrid scoring when enabled, and MMR diversity.",
        )
    )
    return trace


def record_validation_agent(
    trace: AgentTrace,
    *,
    question: str,
    answer: Answer,
    hits: list[SearchHit],
    run_native_evaluators: bool,
) -> AgentTrace:
    evaluation = answer.evaluation or evaluate_answer(
        question=question,
        retrieval_query=trace.retrieval_query,
        answer=answer.answer,
        hits=hits,
        run_native_evaluators=run_native_evaluators,
    )
    validation_score = (
        (evaluation.groundedness * 0.45)
        + (evaluation.citation_coverage * 0.35)
        + ((1 - evaluation.hallucination_risk) * 0.20)
    )
    trace.validation_score = round(validation_score, 4)
    trace.validation_status = "pass" if validation_score >= 0.45 else "review"
    trace.steps.append(
        AgentStep(
            agent="Validation Agent",
            action=f"Validated answer grounding with score {trace.validation_score}.",
            status=trace.validation_status,
            rationale="Validation combines faithfulness, citation support, and hallucination-risk proxies.",
        )
    )
    return trace


def record_approval_agent(trace: AgentTrace, question: str, answer: Answer) -> AgentTrace:
    terms = _tokens(question)
    reasons: list[str] = []
    if terms & MEDICAL_SAFETY_TERMS:
        reasons.append("medical or treatment-oriented wording")
    if answer.abstained:
        reasons.append("answer abstained due to insufficient evidence")
    if trace.validation_status == "review":
        reasons.append("validation score below portfolio safety threshold")

    trace.approval_required = bool(reasons)
    trace.approval_reason = "; ".join(reasons) if reasons else None
    trace.steps.append(
        AgentStep(
            agent="Human Approval Node",
            action="Flagged for review." if reasons else "Auto-approved grounded answer.",
            status="review-required" if reasons else "completed",
            rationale=trace.approval_reason or "Evidence and validation passed without safety flags.",
        )
    )
    return trace
