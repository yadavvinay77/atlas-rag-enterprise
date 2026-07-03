from enterprise_rag.evaluation import evaluate_answer
from enterprise_rag.models import ChunkRecord, SearchHit


def hit(text: str, score: float = 0.1) -> SearchHit:
    return SearchHit(
        score=score,
        chunk=ChunkRecord(
            chunk_id="c1",
            document_id="d1",
            source_file="kidney.pdf",
            page_number=1,
            text=text,
            parent_text=text,
            extraction_method="native",
            quality_score=1.0,
        ),
    )


def test_answer_evaluation_scores_grounded_answer() -> None:
    evaluation = evaluate_answer(
        question="What prevents kidney stones?",
        retrieval_query="kidney stones prevention fluid sodium protein",
        answer="Kidney stone prevention includes higher fluid intake and reduced sodium.",
        hits=[
            hit(
                "Kidney stone prevention includes increasing fluid intake and limiting sodium."
            )
        ],
    )

    assert evaluation.precision_at_k_proxy == 1.0
    assert evaluation.hit_rate_at_k_proxy == 1.0
    assert evaluation.ndcg_at_k_proxy == 1.0
    assert evaluation.groundedness > 0.5
    assert evaluation.hallucination_risk < 0.6
    assert any(metric.requires_gold_labels for metric in evaluation.metrics)
    assert {result.provider for result in evaluation.provider_results} >= {
        "Local",
        "RAGAS",
        "DeepEval",
        "TruLens",
        "LangSmith",
    }
