from enterprise_rag.evaluation_providers import (
    provider_catalog,
    provider_results_from_local_scores,
)
from enterprise_rag.models import EvaluationProviderInfo


def test_provider_catalog_includes_common_rag_evaluators() -> None:
    providers = {provider.provider for provider in provider_catalog()}

    assert {"Local", "RAGAS", "DeepEval", "TruLens", "LangSmith"} <= providers


def test_native_evaluator_mode_shows_visible_provider_results(monkeypatch) -> None:
    def fake_catalog() -> list[EvaluationProviderInfo]:
        return [
            EvaluationProviderInfo(
                provider="Local",
                status="active",
                best_for="local",
                required_setup="none",
                active=True,
            ),
            EvaluationProviderInfo(
                provider="RAGAS",
                status="active",
                best_for="ragas",
                required_setup="openai",
                active=True,
            ),
            EvaluationProviderInfo(
                provider="LangSmith",
                status="installed-needs-langsmith-key",
                best_for="tracing",
                required_setup="Set RAG_LANGSMITH_API_KEY.",
                active=False,
            ),
        ]

    monkeypatch.setattr(
        "enterprise_rag.evaluation_providers.provider_catalog", fake_catalog
    )

    passive = provider_results_from_local_scores(
        groundedness=0.8,
        hallucination_risk=0.2,
        relevance=0.6,
        citation_coverage=0.7,
        run_native=False,
    )
    native = provider_results_from_local_scores(
        groundedness=0.8,
        hallucination_risk=0.2,
        relevance=0.6,
        citation_coverage=0.7,
        run_native=True,
    )

    assert next(result for result in passive if result.provider == "RAGAS").status == "ready-not-run"
    ragas = next(result for result in native if result.provider == "RAGAS")
    langsmith = next(result for result in native if result.provider == "LangSmith")
    assert ragas.status == "completed-proxy"
    assert ragas.score is not None
    assert langsmith.status == "native-blocked"
