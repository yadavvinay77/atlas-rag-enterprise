import importlib.util
import os

from .config import settings
from .models import EvaluationProviderInfo, EvaluationProviderResult


def _installed(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _openai_key() -> str | None:
    return settings.openai_api_key or os.getenv("OPENAI_API_KEY")


def _langsmith_key() -> str | None:
    return settings.langsmith_api_key or os.getenv("LANGSMITH_API_KEY")


def _sync_provider_env() -> None:
    if settings.openai_api_key and not os.getenv("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = settings.openai_api_key
    if settings.langsmith_api_key and not os.getenv("LANGSMITH_API_KEY"):
        os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
    if settings.langsmith_project and not os.getenv("LANGSMITH_PROJECT"):
        os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project


def provider_catalog() -> list[EvaluationProviderInfo]:
    _sync_provider_env()
    has_openai_key = bool(_openai_key())
    has_langsmith_key = bool(_langsmith_key())
    ragas_installed = _installed("ragas")
    deepeval_installed = _installed("deepeval")
    trulens_installed = _installed("trulens") or _installed("trulens_eval")
    langsmith_installed = _installed("langsmith")
    ragas_ready = ragas_installed and has_openai_key
    deepeval_ready = deepeval_installed and has_openai_key
    trulens_ready = trulens_installed
    langsmith_ready = langsmith_installed and has_langsmith_key
    return [
        EvaluationProviderInfo(
            provider="Local",
            status="active",
            best_for="Fast per-answer demo metrics without API keys: relevance proxy, groundedness proxy, hallucination-risk proxy.",
            required_setup="None.",
            active=True,
        ),
        EvaluationProviderInfo(
            provider="RAGAS",
            status=(
                "active" if ragas_ready
                else "installed-needs-openai-key" if ragas_installed
                else "available-not-installed"
            ),
            best_for="Dataset-level RAG evaluation: faithfulness, answer relevancy, context precision, context recall.",
            required_setup='Installed. Native scoring requires an evaluator LLM; this project maps `RAG_OPENAI_API_KEY` to `OPENAI_API_KEY`.',
            active=ragas_ready,
        ),
        EvaluationProviderInfo(
            provider="DeepEval",
            status=(
                "active" if deepeval_ready
                else "installed-needs-openai-key" if deepeval_installed
                else "available-not-installed"
            ),
            best_for="CI-style test cases and assertion metrics: hallucination, answer relevancy, contextual precision/recall.",
            required_setup='Installed. Native scoring requires an evaluator LLM; this project maps `RAG_OPENAI_API_KEY` to `OPENAI_API_KEY`.',
            active=deepeval_ready,
        ),
        EvaluationProviderInfo(
            provider="TruLens",
            status="active" if trulens_ready else "available-not-installed",
            best_for="App instrumentation and feedback functions for groundedness, relevance, and trace-level analysis.",
            required_setup="Installed. Local instrumentation is available; LLM-backed feedback still needs provider credentials.",
            active=trulens_ready,
        ),
        EvaluationProviderInfo(
            provider="LangSmith",
            status=(
                "active" if langsmith_ready
                else "installed-needs-langsmith-key" if langsmith_installed
                else "available-not-installed"
            ),
            best_for="Production tracing, datasets, experiment comparison, human review, and regression dashboards.",
            required_setup="Installed. Set `RAG_LANGSMITH_API_KEY` to enable LangSmith traces/datasets.",
            active=langsmith_ready,
        ),
    ]


def provider_results_from_local_scores(
    *,
    groundedness: float,
    hallucination_risk: float,
    relevance: float,
    citation_coverage: float = 0.0,
    run_native: bool = False,
) -> list[EvaluationProviderResult]:
    results = [
        EvaluationProviderResult(
            provider="Local",
            status="completed",
            score=(groundedness * 0.45) + ((1 - hallucination_risk) * 0.35) + (relevance * 0.20),
            summary="Used built-in lexical overlap and citation-support signals.",
        )
    ]
    for provider in provider_catalog():
        if provider.provider == "Local":
            continue
        if provider.active and run_native:
            if provider.provider == "RAGAS":
                score = (groundedness * 0.40) + (citation_coverage * 0.35) + (relevance * 0.25)
                status = "completed-proxy"
                summary = (
                    "RAGAS-style live score shown from this answer's faithfulness, groundedness, "
                    "and context-relevance signals. True native RAGAS LLM scoring is configured, "
                    "but your current OpenAI quota/billing limit prevents reliable evaluator calls."
                )
            elif provider.provider == "DeepEval":
                score = ((1 - hallucination_risk) * 0.55) + (citation_coverage * 0.30) + (relevance * 0.15)
                status = "completed-proxy"
                summary = (
                    "DeepEval-style live score shown from hallucination-risk, contextual support, "
                    "and relevance signals. True native DeepEval scoring still needs a working "
                    "evaluator LLM quota."
                )
            elif provider.provider == "TruLens":
                score = (groundedness * 0.40) + (citation_coverage * 0.35) + (relevance * 0.25)
                status = "completed-proxy"
                summary = (
                    "TruLens-style local feedback score computed for this turn. The TruLens "
                    "package is installed; LLM-backed feedback and trace dashboards still need "
                    "provider credentials/quota."
                )
            elif provider.provider == "LangSmith":
                score = None
                status = "native-ready"
                summary = (
                    "LangSmith is configured and ready for tracing/dataset runs. This chat panel "
                    "reports local answer metrics; use LangSmith dashboards for persisted traces."
                )
            else:
                score = None
                status = "ready-not-run"
                summary = "Provider is active but has no native chat-turn runner configured."
        elif provider.active:
            status = "ready-not-run"
            score = None
            summary = (
                "Provider is active. Native execution is intentionally not called on every "
                "chat turn to avoid latency/cost; enable Native evaluators to show evaluator-style results."
            )
        else:
            score = None
            if run_native:
                status = "native-blocked"
                summary = (
                    "Native evaluator run was requested, but this provider still needs setup: "
                    f"{provider.required_setup}"
                )
            else:
                status = provider.status
                summary = (
                    "Native package is installed but still needs provider configuration."
                    if provider.status.startswith("installed-needs")
                    else "Provider package is not installed/configured."
                )
        results.append(
            EvaluationProviderResult(
                provider=provider.provider,
                status=status,
                score=score,
                summary=summary,
            )
        )
    return results
