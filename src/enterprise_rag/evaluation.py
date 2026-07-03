from dataclasses import dataclass
from math import log2
import re

from .models import AnswerEvaluation, MetricValue, SearchHit
from .evaluation_providers import provider_results_from_local_scores

TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9'-]+")
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
STOPWORDS = {
    "about", "also", "and", "are", "because", "been", "being", "but", "can",
    "does", "for", "from", "have", "into", "its", "may", "more", "must",
    "not", "that", "the", "their", "them", "then", "there", "these", "this",
    "those", "with", "within", "would", "your",
}


@dataclass(frozen=True)
class RetrievalMetrics:
    recall_at_k: float
    mean_reciprocal_rank: float


def retrieval_metrics(
    ranked_chunk_ids: list[list[str]], relevant_chunk_ids: list[set[str]]
) -> RetrievalMetrics:
    if len(ranked_chunk_ids) != len(relevant_chunk_ids):
        raise ValueError("Predictions and labels must contain the same number of queries")
    if not ranked_chunk_ids:
        return RetrievalMetrics(0.0, 0.0)

    recalls: list[float] = []
    reciprocal_ranks: list[float] = []
    for predicted, relevant in zip(ranked_chunk_ids, relevant_chunk_ids, strict=True):
        recalls.append(float(bool(set(predicted) & relevant)))
        first_rank = next((i for i, item in enumerate(predicted, 1) if item in relevant), 0)
        reciprocal_ranks.append(1 / first_rank if first_rank else 0.0)
    return RetrievalMetrics(
        recall_at_k=sum(recalls) / len(recalls),
        mean_reciprocal_rank=sum(reciprocal_ranks) / len(reciprocal_ranks),
    )


def content_tokens(text: str) -> set[str]:
    return {
        token.lower()
        for token in TOKEN_RE.findall(text)
        if len(token) > 2 and token.lower() not in STOPWORDS
    }


def overlap_score(left: str, right: str) -> float:
    left_tokens = content_tokens(left)
    if not left_tokens:
        return 0.0
    right_tokens = content_tokens(right)
    return len(left_tokens & right_tokens) / len(left_tokens)


def ndcg_at_k(relevance_scores: list[float]) -> float:
    if not relevance_scores:
        return 0.0

    def dcg(scores: list[float]) -> float:
        return sum(score / log2(rank + 1) for rank, score in enumerate(scores, start=1))

    ideal = sorted(relevance_scores, reverse=True)
    ideal_dcg = dcg(ideal)
    return dcg(relevance_scores) / ideal_dcg if ideal_dcg else 0.0


def evaluate_answer(
    *,
    question: str,
    retrieval_query: str,
    answer: str,
    hits: list[SearchHit],
    run_native_evaluators: bool = False,
) -> AnswerEvaluation:
    if not hits:
        return AnswerEvaluation(
            precision_at_k_proxy=0.0,
            hit_rate_at_k_proxy=0.0,
            ndcg_at_k_proxy=0.0,
            mean_context_relevance=0.0,
            groundedness=0.0,
            citation_coverage=0.0,
            hallucination_risk=1.0,
            source_diversity=0.0,
            metrics=[],
        )

    relevance_scores = [overlap_score(question, hit.chunk.text) for hit in hits]
    precision_proxy = sum(score >= 0.08 for score in relevance_scores) / len(hits)
    hit_rate_proxy = float(any(score >= 0.08 for score in relevance_scores))
    ndcg_proxy = ndcg_at_k(relevance_scores)
    mean_relevance = sum(relevance_scores) / len(relevance_scores)

    context = "\n".join(hit.chunk.text for hit in hits)
    groundedness = overlap_score(answer, context)
    answer_sentences = [sentence for sentence in SENTENCE_RE.split(answer) if sentence.strip()]
    if answer_sentences:
        supported_sentences = sum(
            overlap_score(sentence, context) >= 0.35 for sentence in answer_sentences
        )
        citation_coverage = supported_sentences / len(answer_sentences)
    else:
        citation_coverage = 0.0

    source_diversity = len({hit.chunk.source_file for hit in hits}) / len(hits)
    hallucination_risk = max(0.0, 1.0 - ((groundedness * 0.7) + (citation_coverage * 0.3)))

    metrics = [
        MetricValue(
            name="Precision@K proxy",
            value=precision_proxy,
            interpretation="Share of retrieved chunks with meaningful lexical overlap to the resolved query.",
        ),
        MetricValue(
            name="Hit Rate@K proxy",
            value=hit_rate_proxy,
            interpretation="Whether at least one retrieved chunk has meaningful overlap with the question.",
        ),
        MetricValue(
            name="nDCG@K proxy",
            value=ndcg_proxy,
            interpretation="Ranks higher when more relevant chunks appear earlier in the retrieved evidence list.",
        ),
        MetricValue(
            name="Recall@K",
            value=None,
            interpretation="Requires a labeled set of relevant chunks for each question.",
            requires_gold_labels=True,
        ),
        MetricValue(
            name="MRR",
            value=None,
            interpretation="Requires labels identifying the first truly relevant retrieved chunk.",
            requires_gold_labels=True,
        ),
        MetricValue(
            name="Faithfulness proxy",
            value=groundedness,
            interpretation="Share of answer content tokens supported by retrieved evidence.",
        ),
        MetricValue(
            name="Groundedness",
            value=citation_coverage,
            interpretation="Share of answer sentences substantially supported by cited evidence.",
        ),
        MetricValue(
            name="Hallucination risk",
            value=hallucination_risk,
            interpretation="Higher means more answer content is not visible in retrieved context.",
        ),
    ]
    return AnswerEvaluation(
        precision_at_k_proxy=precision_proxy,
        hit_rate_at_k_proxy=hit_rate_proxy,
        ndcg_at_k_proxy=ndcg_proxy,
        mean_context_relevance=mean_relevance,
        groundedness=groundedness,
        citation_coverage=citation_coverage,
        hallucination_risk=hallucination_risk,
        source_diversity=source_diversity,
        metrics=metrics,
        evaluator="local-auto",
        provider_results=provider_results_from_local_scores(
            groundedness=groundedness,
            hallucination_risk=hallucination_risk,
            relevance=mean_relevance,
            citation_coverage=citation_coverage,
            run_native=run_native_evaluators,
        ),
    )
