from .config import settings
from .models import ArchitectureLayer, ArchitectureMethod, ArchitectureReport


def method(name: str, status: str, notes: str) -> ArchitectureMethod:
    return ArchitectureMethod(name=name, status=status, notes=notes)


def architecture_report() -> ArchitectureReport:
    dense_status = "active" if settings.enable_dense else "available"
    hybrid_status = "active" if settings.enable_dense else "partial"
    return ArchitectureReport(
        active_summary={
            "chunking": "Section-aware parent-child + semantic chunks",
            "retrieval": "BM25 with conversation-aware query expansion"
            + (" + dense fusion" if settings.enable_dense else "")
            + " + MMR diversity",
            "reranking": "Heuristic reranking + MMR; cross-encoder reranking is planned",
            "context": "Top-K cited passages with source/page metadata",
            "reasoning": "Conversation memory + selectable grounded synthesis provider",
            "llm": f"{settings.generation_provider}: {settings.ollama_model}",
            "evaluation": "Per-answer proxy metrics + gold-set hooks",
        },
        layers=[
            ArchitectureLayer(
                layer="3. Chunking",
                methods=[
                    ArchitectureMethod(
                        name="Fixed",
                        status="available",
                        notes="Can split every N characters/tokens; not active because it ignores page and paragraph structure.",
                    ),
                    ArchitectureMethod(
                        name="Recursive",
                        status="active",
                        notes="Current splitter uses paragraph/sentence boundaries, target character windows, and overlap.",
                    ),
                    ArchitectureMethod(
                        name="Semantic",
                        status="active-lite",
                        notes="Splits on medical headings, table/figure markers, bullets, paragraphs, and sentence boundaries.",
                    ),
                    ArchitectureMethod(
                        name="Parent-Child",
                        status="active",
                        notes="Child chunks retrieve precisely; parent_text preserves the detected section as parent context.",
                    ),
                    ArchitectureMethod(
                        name="Agentic",
                        status="active-lite",
                        notes="Rule-based document intelligence detects treatment, diagnosis, disease, and table sections during ingestion.",
                    ),
                ],
            ),
            ArchitectureLayer(
                layer="6. Retrieval",
                methods=[
                    method("BM25", "active", "Keyword retrieval over all chunks."),
                    method("Dense", dense_status, "Uses sentence-transformers when RAG_ENABLE_DENSE=true."),
                    method("Hybrid", hybrid_status, "RRF fusion is active when dense retrieval is enabled."),
                    method("MMR", "active", "Maximal Marginal Relevance reduces repeated/near-duplicate chunks in final Top-K."),
                    method("Multi-Query", "active-lite", "Follow-up questions are rewritten with topic memory and medical synonym expansion."),
                    method("Agentic", "planned", "Future router can choose search, summarize, compare, or evaluate tools."),
                ],
            ),
            ArchitectureLayer(
                layer="7. Reranking",
                methods=[
                    method("Cross Encoder", "planned", "Best accuracy option; requires a reranker model."),
                    method("BGE Reranker", "planned", "Good open-source reranker candidate."),
                    method("LLM Rerank", "available", "Can be added through Ollama/GPT style judge; slower but explainable."),
                    method("Heuristic Rerank", "active", "Penalizes index pages, boosts recent small topical docs, deduplicates pages."),
                ],
            ),
            ArchitectureLayer(
                layer="8. Context Building",
                methods=[
                    method("Prompt Template", "active", "System prompt requires evidence-only answers and page citations."),
                    method("Compression", "available-lite", "Context is capped by character budget; semantic compression is planned."),
                    method("Filtering", "active-lite", "Top-K selection, index-page filtering, source continuity, and page dedupe."),
                ],
            ),
            ArchitectureLayer(
                layer="9. Reasoning",
                methods=[
                    method("ReAct", "planned", "Tool-using reasoning loop is not active yet."),
                    method("Reflection", "available-lite", "Evaluation metrics expose answer risk; LLM self-check can be added."),
                    method("Multi-Agent", "planned", "Future roles: retriever, verifier, medical safety reviewer."),
                ],
            ),
            ArchitectureLayer(
                layer="10. LLM",
                methods=[
                    method("GPT", "active-ready", f"OpenAI route uses {settings.openai_model} when RAG_OPENAI_API_KEY is set."),
                    method("Claude", "compatible", "Can be wired through an Anthropic provider adapter."),
                    method("Gemini", "compatible", "Can be wired through a Gemini provider adapter."),
                    method("Llama", "active-ready", f"Ollama route can use {settings.ollama_model} or any installed local model."),
                    method("Qwen", "active-ready", "Works through Ollama or an OpenAI-compatible local server if installed."),
                    method("OpenAI-Compatible Local", "active-ready", "Supports LM Studio, vLLM, llama.cpp server, and similar /v1/chat/completions endpoints."),
                ],
            ),
            ArchitectureLayer(
                layer="11. Evaluation",
                methods=[
                    method("Precision@K", "active-proxy", "Measured from query/chunk overlap until a gold set is available."),
                    method("Hit Rate@K", "active-proxy", "Shows whether at least one retrieved passage appears relevant."),
                    method("nDCG@K", "active-proxy", "Rewards relevant chunks appearing near the top of the evidence list."),
                    method("Recall@K", "gold-required", "Needs labeled relevant chunks per question."),
                    method("Faithfulness", "active-proxy", "Measures answer-token support in retrieved evidence."),
                    method("Groundedness", "active-proxy", "Measures sentence support from cited passages."),
                    method("Hallucination Rate", "active-proxy", "Estimated as unsupported answer content risk."),
                    method("RAGAS", "provider-ready", "Best for offline dataset evaluation: faithfulness, answer relevancy, context precision/recall."),
                    method("DeepEval", "provider-ready", "Best for CI tests and threshold assertions for RAG quality."),
                    method("TruLens", "provider-ready", "Best for app instrumentation, feedback functions, and trace-level quality review."),
                    method("LangSmith", "provider-ready", "Best for tracing, datasets, human review, experiments, and production monitoring."),
                ],
            ),
        ],
    )
