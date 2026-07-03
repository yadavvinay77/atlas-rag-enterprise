import re
from collections import Counter, defaultdict

import numpy as np
from rank_bm25 import BM25Okapi

from .models import ChunkRecord, SearchHit

TOKEN_RE = re.compile(r"[\w\u0A80-\u0AFF]+", re.UNICODE)
RETRIEVAL_STOPWORDS = {
    "a",
    "about",
    "an",
    "and",
    "are",
    "can",
    "does",
    "for",
    "from",
    "give",
    "i",
    "info",
    "infor",
    "in",
    "information",
    "is",
    "it",
    "me",
    "medicine",
    "medicines",
    "medication",
    "medications",
    "of",
    "on",
    "problem",
    "problems",
    "regarding",
    "related",
    "summarize",
    "should",
    "tackle",
    "take",
    "that",
    "the",
    "this",
    "to",
    "what",
    "which",
    "with",
}
TOKEN_NORMALIZATIONS = {
    "galbladder": "gallbladder",
}
TREATMENT_INTENT_TERMS = {
    "antibiotic",
    "antibiotics",
    "drug",
    "drugs",
    "management",
    "medicine",
    "medicines",
    "medication",
    "medications",
    "therapy",
    "treat",
    "treatment",
}
THERAPEUTIC_TERMS = {
    "acyclovir",
    "azithromycin",
    "ceftriaxone",
    "clindamycin",
    "doxycycline",
    "fluconazole",
    "metronidazole",
    "miconazole",
    "nitrofurantoin",
    "tinidazole",
    "treatment",
    "therapy",
}


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def content_tokens(text: str) -> list[str]:
    normalized = [TOKEN_NORMALIZATIONS.get(token, token) for token in tokenize(text)]
    tokens = [token for token in normalized if token not in RETRIEVAL_STOPWORDS]
    return tokens or tokenize(text)


def _looks_like_back_matter_index(text: str) -> bool:
    lowered = text.lower()
    if lowered.lstrip().startswith("index"):
        return True
    comma_count = text.count(",")
    digit_count = sum(char.isdigit() for char in text)
    word_count = max(1, len(tokenize(text)))
    return comma_count >= 4 and digit_count / word_count > 0.18


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


class HybridRetriever:
    def __init__(
        self,
        chunks: list[ChunkRecord],
        *,
        enable_dense: bool = True,
        embedding_model: str = "intfloat/multilingual-e5-base",
    ) -> None:
        if not chunks:
            raise ValueError("Cannot build a retriever without chunks")
        self.chunks = chunks
        self.search_texts = [
            f"{chunk.title or ''}\n{chunk.text}".strip() for chunk in chunks
        ]
        self.chunk_token_sets = [set(content_tokens(text)) for text in self.search_texts]
        self.document_sizes = Counter(chunk.document_id for chunk in chunks)
        self.bm25 = BM25Okapi([tokenize(text) for text in self.search_texts])
        self.encoder = None
        self.embeddings = None
        if enable_dense:
            from sentence_transformers import SentenceTransformer

            self.encoder = SentenceTransformer(embedding_model)
            passages = [f"passage: {text}" for text in self.search_texts]
            self.embeddings = self.encoder.encode(
                passages, normalize_embeddings=True, show_progress_bar=True
            )

    def search(
        self,
        query: str,
        top_k: int = 8,
        candidate_k: int = 30,
        preferred_document_ids: set[str] | None = None,
        mmr_lambda: float = 0.58,
    ) -> list[SearchHit]:
        candidate_k = min(candidate_k, len(self.chunks))
        rankings: dict[str, list[int]] = {}

        raw_query_tokens = tokenize(query)
        query_tokens = content_tokens(query)
        query_token_set = set(query_tokens)
        treatment_intent = bool(set(raw_query_tokens) & TREATMENT_INTENT_TERMS)
        requested_therapies = set(raw_query_tokens) & THERAPEUTIC_TERMS
        has_lexical_match = any(
            query_token_set & chunk_tokens for chunk_tokens in self.chunk_token_sets
        )
        bm25_scores = self.bm25.get_scores(query_tokens)
        max_bm25 = float(np.max(bm25_scores)) if len(bm25_scores) else 0.0
        rankings["bm25"] = np.argsort(bm25_scores)[::-1][:candidate_k].tolist()

        if self.encoder is not None and self.embeddings is not None:
            query_vector = self.encoder.encode(
                [f"query: {query}"], normalize_embeddings=True
            )[0]
            dense_scores = self.embeddings @ query_vector
            rankings["dense"] = np.argsort(dense_scores)[::-1][:candidate_k].tolist()
        elif not has_lexical_match:
            return []

        fused: dict[int, float] = defaultdict(float)
        rank_details: dict[int, dict[str, int]] = defaultdict(dict)
        for source, indices in rankings.items():
            for rank, index in enumerate(indices, start=1):
                fused[index] += 1 / (60 + rank)
                rank_details[index][source] = rank

        for index in fused:
            chunk_tokens = self.chunk_token_sets[index]
            if query_token_set:
                fused[index] += 0.025 * (
                    len(query_token_set & chunk_tokens) / len(query_token_set)
                )
            if max_bm25 > 0:
                fused[index] += 0.015 * (float(bm25_scores[index]) / max_bm25)
            if treatment_intent:
                therapeutic_overlap = self.chunk_token_sets[index] & THERAPEUTIC_TERMS
                if therapeutic_overlap:
                    fused[index] += 0.035
                if requested_therapies:
                    fused[index] += 0.04 * (
                        len(requested_therapies & self.chunk_token_sets[index])
                        / len(requested_therapies)
                    )

        if preferred_document_ids:
            for index in fused:
                if self.chunks[index].document_id in preferred_document_ids:
                    document_size = self.document_sizes[self.chunks[index].document_id]
                    fused[index] += 0.006 if document_size <= 500 else 0.0005

        for index in fused:
            if _looks_like_back_matter_index(
                f"{self.chunks[index].title or ''}\n"
                f"{self.chunks[index].text}\n{self.chunks[index].parent_text[:500]}"
            ):
                fused[index] -= 0.08

        sorted_candidates = sorted(fused, key=fused.get, reverse=True)
        max_fused = max((fused[index] for index in sorted_candidates), default=0.0)
        min_fused = min((fused[index] for index in sorted_candidates), default=0.0)

        def normalized_score(index: int) -> float:
            if max_fused <= min_fused:
                return 1.0
            return (fused[index] - min_fused) / (max_fused - min_fused)

        ordered: list[int] = []
        page_counts: dict[tuple[str, int], int] = defaultdict(int)
        remaining = sorted_candidates[:]
        while remaining and len(ordered) < top_k:
            eligible = [
                index
                for index in remaining
                if max(
                    (
                        _jaccard(
                            self.chunk_token_sets[index],
                            self.chunk_token_sets[selected],
                        )
                        for selected in ordered
                    ),
                    default=0.0,
                )
                < 0.88
            ]
            candidate_pool = eligible or remaining
            best_index = max(
                candidate_pool,
                key=lambda index: (
                    mmr_lambda * normalized_score(index)
                    - (1 - mmr_lambda)
                    * max(
                        (
                            _jaccard(
                                self.chunk_token_sets[index],
                                self.chunk_token_sets[selected],
                            )
                            for selected in ordered
                        ),
                        default=0.0,
                    )
                ),
            )
            remaining.remove(best_index)
            page_key = (
                self.chunks[best_index].document_id,
                self.chunks[best_index].page_number,
            )
            if page_counts[page_key] >= 2:
                continue
            ordered.append(best_index)
            page_counts[page_key] += 1
        return [
            SearchHit(chunk=self.chunks[index], score=fused[index], ranks=rank_details[index])
            for index in ordered
        ]
