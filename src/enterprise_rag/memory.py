import re
from collections import deque
from threading import Lock
from uuid import uuid4

from .models import ConversationTurn

FOLLOW_UP_RE = re.compile(
    r"\b(this|that|it|these|those|the problem|the condition|for this|related to this|"
    r"what about|how about|which organs?|food plan|diet|treatment|prevention)\b",
    re.IGNORECASE,
)
WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9'-]+")
STOPWORDS = {
    "about", "after", "again", "also", "and", "are", "based", "before", "can",
    "could", "does", "explain", "for", "from", "have", "how", "into", "its",
    "more", "most", "should", "than", "that", "the", "their", "them", "then",
    "there", "these", "they", "this", "those", "what", "when", "where", "which",
    "with", "would", "your",
}
QUERY_EXPANSIONS = (
    (
        re.compile(r"\b(cervix cancer|cervical cancer|cancer of the cervix)\b", re.IGNORECASE),
        "cervical cancer carcinoma cervix squamous cell carcinoma adenocarcinoma HPV screening Pap smear",
    ),
    (
        re.compile(r"\b(gonorrhoeae|gonorrhea|gonorrhoea)\b", re.IGNORECASE),
        "Neisseria gonorrhoeae gonorrhea urethritis cervicitis neonatal conjunctivitis ceftriaxone",
    ),
    (
        re.compile(
            r"\b(vaginal infection|vaginitis|vulvovaginitis|vaginal discharge)\b",
            re.IGNORECASE,
        ),
        "vaginitis vulvovaginitis bacterial vaginosis candidiasis trichomoniasis cervicitis vaginal discharge",
    ),
    (re.compile(r"\b(food plan|diet|nutrition)\b", re.IGNORECASE),
     "diet nutrition sodium protein fluid intake prevention"),
    (re.compile(r"\b(urinary stone disease|kidney stones?)\b", re.IGNORECASE),
     "kidney stone nephrolithiasis urolithiasis"),
    (
        re.compile(
            r"\b(hypertension|high blood pressure)\b.*\b(treat|treatment|therapy|manage|management)\b"
            r"|\b(treat|treatment|therapy|manage|management)\b.*\b(hypertension|high blood pressure)\b",
            re.IGNORECASE,
        ),
        "systemic hypertension antihypertensive agents stepped care ACE inhibitor ARB calcium channel blocker thiazide diuretic lifestyle combination therapy blood pressure",
    ),
)


class ConversationStore:
    def __init__(self, max_sessions: int = 200, max_turns: int = 12) -> None:
        self.max_sessions = max_sessions
        self.max_turns = max_turns
        self._sessions: dict[str, deque[ConversationTurn]] = {}
        self._lock = Lock()

    def create_or_get(self, conversation_id: str | None) -> str:
        with self._lock:
            identifier = conversation_id or uuid4().hex
            if identifier not in self._sessions:
                if len(self._sessions) >= self.max_sessions:
                    oldest = next(iter(self._sessions))
                    self._sessions.pop(oldest, None)
                self._sessions[identifier] = deque(maxlen=self.max_turns)
            return identifier

    def turns(self, conversation_id: str) -> list[ConversationTurn]:
        with self._lock:
            return list(self._sessions.get(conversation_id, ()))

    def add(self, conversation_id: str, turn: ConversationTurn) -> None:
        with self._lock:
            self._sessions.setdefault(
                conversation_id, deque(maxlen=self.max_turns)
            ).append(turn)

    def clear(self, conversation_id: str) -> None:
        with self._lock:
            self._sessions.pop(conversation_id, None)


def _topic_terms(turns: list[ConversationTurn], limit: int = 8) -> list[str]:
    if not turns:
        return []
    candidates: list[str] = []
    # Prefer the latest explicit user topic, then reinforce it with prior retrieval queries.
    for text in reversed([turn.question for turn in turns] + [turn.retrieval_query for turn in turns]):
        for word in WORD_RE.findall(text):
            normalized = word.lower()
            if len(normalized) < 4 or normalized in STOPWORDS or normalized in candidates:
                continue
            candidates.append(normalized)
            if len(candidates) >= limit:
                return candidates
    return candidates


def should_use_conversation_context(question: str, turns: list[ConversationTurn]) -> bool:
    clean = question.strip().rstrip("#").strip()
    return bool(turns) and bool(FOLLOW_UP_RE.search(clean))


def _has_treatment_intent(text: str) -> bool:
    return bool(
        re.search(
            r"\b(medicines?|medications?|drugs?|antibiotics?|treat|treatment|therapy|"
            r"manage|management|tackle|cure)\b",
            text,
            re.IGNORECASE,
        )
    )


def contextualize_question(question: str, turns: list[ConversationTurn]) -> str:
    clean = question.strip().rstrip("#").strip()
    contextualized = clean
    if should_use_conversation_context(clean, turns):
        topic = " ".join(_topic_terms(turns))
        contextualized = f"{topic} {clean}".strip() if topic else clean
    expansions = [
        expansion
        for pattern, expansion in QUERY_EXPANSIONS
        if pattern.search(contextualized)
    ]
    if (
        re.search(r"\b(organs?|anatomy|body parts?)\b", contextualized, re.IGNORECASE)
        and re.search(
            r"\b(urinary|kidney|stone|nephrolithiasis|urolithiasis)\b",
            contextualized,
            re.IGNORECASE,
        )
    ):
        expansions.append("kidney kidneys ureter ureters bladder urinary tract")
    if (
        _has_treatment_intent(contextualized)
        and re.search(
            r"\b(vaginal infection|vaginitis|vulvovaginitis|vaginal discharge|"
            r"bacterial vaginosis|candidiasis|trichomoniasis)\b",
            contextualized,
            re.IGNORECASE,
        )
    ):
        expansions.append(
            "treatment therapy metronidazole fluconazole ceftriaxone doxycycline "
            "clindamycin tinidazole miconazole candidiasis trichomoniasis bacterial vaginosis"
        )
    return f"{contextualized} {' '.join(expansions)}".strip()


conversations = ConversationStore()
