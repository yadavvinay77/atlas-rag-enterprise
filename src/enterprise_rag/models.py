from typing import Literal

from pydantic import BaseModel, Field


class PageRecord(BaseModel):
    document_id: str
    source_file: str
    page_number: int = Field(ge=1)
    text: str
    extraction_method: Literal["native", "ocr", "unavailable"]
    quality_score: float = Field(ge=0, le=1)
    language_hint: str = "unknown"
    warnings: list[str] = Field(default_factory=list)


class ChunkRecord(BaseModel):
    chunk_id: str
    document_id: str
    source_file: str
    page_number: int
    text: str
    parent_text: str
    title: str | None = None
    resolution_number: str | None = None
    document_date: str | None = None
    department: str | None = None
    extraction_method: str
    quality_score: float


class SearchHit(BaseModel):
    chunk: ChunkRecord
    score: float
    ranks: dict[str, int] = Field(default_factory=dict)
    visual: "PageVisual | None" = None


class PageVisual(BaseModel):
    kind: str = "page-snapshot"
    url: str
    caption: str


class Answer(BaseModel):
    question: str
    answer: str
    citations: list[SearchHit]
    abstained: bool = False
    conversation_id: str | None = None
    retrieval_query: str | None = None
    used_conversation_context: bool = False
    generation_provider: str = "extractive"
    generation_model: str = "top-cited-passage"
    generation_status: str = "completed"
    generation_note: str | None = None
    evaluation: "AnswerEvaluation | None" = None
    pipeline_trace: dict[str, object] = Field(default_factory=dict)


class ConversationTurn(BaseModel):
    question: str
    answer: str
    retrieval_query: str
    cited_document_ids: list[str] = Field(default_factory=list)
    cited_source_files: list[str] = Field(default_factory=list)


class DocumentSummary(BaseModel):
    document_id: str
    source_file: str
    page_count: int
    chunk_count: int
    ocr_page_count: int
    low_quality_page_count: int


class IndexJob(BaseModel):
    job_id: str
    status: Literal["queued", "running", "completed", "failed"]
    source_file: str
    current_page: int = 0
    total_pages: int = 0
    message: str = ""
    pages_indexed: int = 0
    chunks_created: int = 0


class MetricValue(BaseModel):
    name: str
    value: float | None
    interpretation: str
    requires_gold_labels: bool = False


class AnswerEvaluation(BaseModel):
    precision_at_k_proxy: float
    hit_rate_at_k_proxy: float = 0.0
    ndcg_at_k_proxy: float = 0.0
    mean_context_relevance: float
    groundedness: float
    citation_coverage: float
    hallucination_risk: float
    source_diversity: float
    metrics: list[MetricValue]
    evaluator: str = "local"
    provider_results: list["EvaluationProviderResult"] = Field(default_factory=list)


class EvaluationProviderResult(BaseModel):
    provider: str
    status: str
    score: float | None = None
    summary: str


class EvaluationProviderInfo(BaseModel):
    provider: str
    status: str
    best_for: str
    required_setup: str
    active: bool = False


class ArchitectureMethod(BaseModel):
    name: str
    status: str
    notes: str


class ArchitectureLayer(BaseModel):
    layer: str
    methods: list[ArchitectureMethod]


class ArchitectureReport(BaseModel):
    active_summary: dict[str, str]
    layers: list[ArchitectureLayer]
