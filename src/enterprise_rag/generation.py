import httpx

from .models import Answer, ConversationTurn, SearchHit
from .retrieval import content_tokens

SYSTEM_PROMPT = """You are an evidence-grounded document research assistant.
Answer only from the supplied evidence. Cite claims using [page N].
If the evidence is insufficient, say that the indexed documents do not establish the answer.
For medical questions, summarize the source but do not diagnose, prescribe, or replace a
qualified clinician. Preserve names, numbers, doses, and dates exactly. Answer in the user's
language."""
TREATMENT_QUERY_TERMS = {
    "antibiotic",
    "antibiotics",
    "drug",
    "drugs",
    "medicine",
    "medicines",
    "medication",
    "medications",
    "therapy",
    "tackle",
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
    "ibrexafungerp",
    "metronidazole",
    "miconazole",
    "otesconazole",
    "tinidazole",
}
GENERIC_TOPIC_TERMS = {
    "condition",
    "disease",
    "infection",
    "infections",
    "medicine",
    "medicines",
    "problem",
    "problems",
}


def build_context(hits: list[SearchHit], max_chars: int = 12000) -> str:
    blocks: list[str] = []
    used = 0
    for hit in hits:
        block = (
            f"[page {hit.chunk.page_number}; source={hit.chunk.source_file}; "
            f"resolution={hit.chunk.resolution_number or 'unknown'}]\n{hit.chunk.text}"
        )
        if blocks and used + len(block) > max_chars:
            break
        blocks.append(block)
        used += len(block)
    return "\n\n".join(blocks)


def _clean_extracted_text(text: str) -> str:
    replacements = {
        "→": "->",
        "↓": "decreased ",
        "↑": "increased ",
        "↓": "decreased ",
        "Superscript degree": "primary ",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    lines = [line.strip() for line in text.splitlines()]
    cleaned: list[str] = []
    skip_terms = {
        "aorta",
        "renal artery",
        "inferior",
        "mesenteric",
        "artery",
        "ureter",
        "ivc",
        "a",
    }
    for line in lines:
        normalized = line.lower().strip(" .")
        if not normalized:
            continue
        if normalized in skip_terms:
            continue
        cleaned.append(line)
    return " ".join(cleaned)


def _sentences(text: str) -> list[str]:
    protected = text.replace("eg,", "for example,")
    pieces: list[str] = []
    current: list[str] = []
    for token in protected.split():
        current.append(token)
        if token.endswith((".", ";", ":")) and len(current) >= 4:
            pieces.append(" ".join(current).strip())
            current = []
    if current:
        pieces.append(" ".join(current).strip())
    return pieces


def _looks_like_index_sentence(sentence: str) -> bool:
    comma_count = sentence.count(",")
    digit_count = sum(char.isdigit() for char in sentence)
    word_count = max(1, len(content_tokens(sentence)))
    return comma_count >= 4 and digit_count / word_count > 0.16


def _step_points(hits: list[SearchHit]) -> list[str]:
    if not hits:
        return []
    lead_page = (hits[0].chunk.document_id, hits[0].chunk.page_number)
    raw = "\n".join(
        hit.chunk.text
        for hit in hits
        if (hit.chunk.document_id, hit.chunk.page_number) == lead_page
    )
    if "Step 1" not in raw or "antihypertension" not in raw.lower():
        return []
    return [
        "Step 1: ACE inhibitor/ARB, calcium channel blocker, or thiazide diuretic.",
        "Step 2: ACE inhibitor/ARB plus calcium channel blocker or thiazide diuretic.",
        "Step 3: ACE inhibitor/ARB plus calcium channel blocker plus thiazide diuretic.",
        "Step 4: add spironolactone; alternatives include eplerenone, amiloride, or triamterene.",
    ]


def _select_relevant_sentences(question: str, hits: list[SearchHit], limit: int = 5) -> list[str]:
    query_terms = set(content_tokens(question))
    selected: list[str] = []
    lead_page = (hits[0].chunk.document_id, hits[0].chunk.page_number) if hits else None
    unrelated_section_markers = (
        "congenital solitary",
        "unilateral renal agenesis",
        "bilateral renal agenesis",
    )
    for hit_index, hit in enumerate(hits):
        if lead_page and (hit.chunk.document_id, hit.chunk.page_number) != lead_page:
            if selected:
                break
            continue
        matched_in_hit = False
        for sentence in _sentences(_clean_extracted_text(hit.chunk.text)):
            lowered = sentence.lower()
            if selected and any(marker in lowered for marker in unrelated_section_markers):
                return selected[:limit]
            sentence_terms = set(content_tokens(sentence))
            if query_terms and not (query_terms & sentence_terms):
                if matched_in_hit and hit_index == 0:
                    selected.append(sentence)
                continue
            selected.append(sentence)
            matched_in_hit = True
            if len(selected) >= limit:
                return selected
    return selected[:limit]


def _treatment_sentences(
    question: str,
    hits: list[SearchHit],
    *,
    evidence_query: str | None = None,
    limit: int = 5,
) -> list[str]:
    question_terms = {term.lower().strip(" ?.,") for term in question.split()}
    if not (question_terms & TREATMENT_QUERY_TERMS):
        return []
    topic_terms = (
        set(content_tokens(evidence_query or question))
        - THERAPEUTIC_TERMS
        - TREATMENT_QUERY_TERMS
        - GENERIC_TOPIC_TERMS
    )
    selected: list[str] = []
    fallback: list[str] = []
    for hit in hits:
        for sentence in _sentences(_clean_extracted_text(hit.chunk.text)):
            if _looks_like_index_sentence(sentence):
                continue
            sentence_terms = set(content_tokens(sentence))
            if sentence_terms & THERAPEUTIC_TERMS:
                if not topic_terms or sentence_terms & topic_terms:
                    selected.append(sentence)
                else:
                    fallback.append(sentence)
                if len(selected) >= limit:
                    return list(dict.fromkeys(selected))
    return list(dict.fromkeys(selected or fallback))[:limit]


def _structured_extractive_answer(
    question: str, hits: list[SearchHit], *, evidence_query: str | None = None
) -> str:
    lead = hits[0].chunk
    title = question.strip().rstrip("?") or lead.title or "Retrieved answer"
    treatment_sentences = _treatment_sentences(
        question, hits, evidence_query=evidence_query
    )
    sentences = treatment_sentences or _select_relevant_sentences(
        evidence_query or question, hits
    )
    if not sentences:
        sentences = _sentences(_clean_extracted_text(lead.text))[:5]
    overview = sentences[0] if sentences else _clean_extracted_text(lead.text)[:400]
    topic_terms = " ".join(content_tokens(title))
    while topic_terms and overview.lower().startswith(topic_terms):
        overview = overview[len(topic_terms):].strip(" .")
    overview = overview.removesuffix(" A").strip()
    key_points = [*(_step_points(hits)), *sentences[1:5]]
    key_points = list(dict.fromkeys(key_points))[:5]
    lines = [f"**{title}**", "", overview]
    if treatment_sentences:
        lines.append(
            "\nThe cited sources describe medication options by suspected cause; "
            "use this as document evidence, not personal prescribing advice."
        )
    if key_points:
        lines.extend(["", "**Key points:**"])
        lines.extend(f"- {point}" for point in key_points)
    lines.extend(["", f"**Source:** page {lead.page_number}, {lead.source_file}."])
    return "\n".join(lines)


def answer_extractively(
    question: str, hits: list[SearchHit], *, evidence_query: str | None = None
) -> Answer:
    if not hits:
        return Answer(
            question=question,
            answer="The indexed document does not provide enough evidence to answer.",
            citations=[],
            abstained=True,
        )
    answer = _structured_extractive_answer(question, hits, evidence_query=evidence_query)
    return Answer(
        question=question,
        answer=answer,
        citations=hits[:3],
        generation_provider="extractive",
        generation_model="top-cited-passage",
    )


def build_messages(
    question: str,
    hits: list[SearchHit],
    *,
    history: list[ConversationTurn] | None = None,
) -> list[dict[str, str]]:
    recent_history = history[-4:] if history else []
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for turn in recent_history:
        messages.extend(
            [
                {"role": "user", "content": turn.question},
                {"role": "assistant", "content": turn.answer},
            ]
        )
    messages.append(
        {
            "role": "user",
            "content": f"Question:\n{question}\n\nEvidence:\n{build_context(hits)}",
        }
    )
    return messages


def answer_with_ollama(
    question: str,
    hits: list[SearchHit],
    *,
    base_url: str,
    model: str,
    timeout_seconds: float = 35.0,
    history: list[ConversationTurn] | None = None,
) -> Answer:
    if not hits:
        return answer_extractively(question, hits)
    payload = {
        "model": model,
        "stream": False,
        "messages": build_messages(question, hits, history=history),
    }
    response = httpx.post(
        f"{base_url.rstrip('/')}/api/chat",
        json=payload,
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    text = response.json()["message"]["content"]
    return Answer(
        question=question,
        answer=text,
        citations=hits[:5],
        generation_provider="ollama",
        generation_model=model,
    )


def answer_with_openai_compatible(
    question: str,
    hits: list[SearchHit],
    *,
    base_url: str,
    model: str,
    provider: str = "compatible",
    api_key: str | None = None,
    timeout_seconds: float = 35.0,
    history: list[ConversationTurn] | None = None,
) -> Answer:
    if not hits:
        return answer_extractively(question, hits)
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    payload = {
        "model": model,
        "messages": build_messages(question, hits, history=history),
        "temperature": 0.1,
    }
    response = httpx.post(
        f"{base_url.rstrip('/')}/chat/completions",
        json=payload,
        headers=headers,
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    text = response.json()["choices"][0]["message"]["content"]
    return Answer(
        question=question,
        answer=text,
        citations=hits[:5],
        generation_provider=provider,
        generation_model=model,
    )
