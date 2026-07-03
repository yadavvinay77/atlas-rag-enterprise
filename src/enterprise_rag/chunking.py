import hashlib
import re

from .models import ChunkRecord, PageRecord

RESOLUTION_RE = re.compile(
    r"(?:resolution|tharav|paripatra|circular)\s*(?:no\.?|num\.?)?\s*[:\-]?\s*([A-Z0-9/._-]+)",
    re.IGNORECASE,
)
DATE_RE = re.compile(r"\b([0-3]?\d[-/.][01]?\d[-/.](?:19|20)\d{2})\b")
SPLIT_RE = re.compile(r"\n\s*\n|(?<=[.!?])\s+")
LINE_SPLIT_RE = re.compile(r"\r?\n")
MEDICAL_HEADING_RE = re.compile(
    r"^(?:[A-Z]\.\s*)?(?:ESSENTIALS? OF DIAGNOSIS|GENERAL CONSIDERATIONS|"
    r"CLINICAL FINDINGS|SYMPTOMS|SIGNS|DIAGNOSIS|DIFFERENTIAL DIAGNOSIS|"
    r"TREATMENT|MEDICATIONS?|DRUGS?|SCREENING|PREVENTION|WHEN TO REFER|"
    r"WHEN TO ADMIT|PROGNOSIS|COMPLICATIONS|VAGINAL DISCHARGE|"
    r"CARCINOMA OF THE CERVIX|BACTERIAL VAGINOSIS|CANDIDIASIS|TRICHOMONIASIS)\b",
    re.IGNORECASE,
)
TABLE_RE = re.compile(r"^(?:table|figure|algorithm)\s+\d", re.IGNORECASE)


def _window(parts: list[str], target_chars: int, overlap_parts: int = 1) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    size = 0
    for part in parts:
        if current and size + len(part) > target_chars:
            chunks.append("\n".join(current))
            current = current[-overlap_parts:]
            size = sum(map(len, current))
        current.append(part)
        size += len(part)
    if current:
        chunks.append("\n".join(current))
    return chunks


def _is_heading(line: str) -> bool:
    clean = line.strip(" \t:-")
    if not clean or len(clean) > 120:
        return False
    if MEDICAL_HEADING_RE.search(clean) or TABLE_RE.search(clean):
        return True
    if clean.startswith(("»", "▶")):
        return True
    letters = [char for char in clean if char.isalpha()]
    if len(letters) >= 5:
        upper_ratio = sum(char.isupper() for char in letters) / len(letters)
        if upper_ratio > 0.72 and not clean.endswith("."):
            return True
    return False


def _sections(page_text: str) -> list[str]:
    lines = [line.rstrip() for line in LINE_SPLIT_RE.split(page_text)]
    sections: list[str] = []
    current: list[str] = []
    for line in lines:
        clean = line.strip()
        if _is_heading(clean) and current:
            sections.append("\n".join(current).strip())
            current = [line]
        else:
            current.append(line)
    if current:
        sections.append("\n".join(current).strip())
    return [section for section in sections if section]


def _section_title(section_text: str, fallback: str | None) -> str | None:
    for line in LINE_SPLIT_RE.split(section_text):
        clean = line.strip(" \t:-»▶")
        if clean and len(clean) <= 180:
            return clean
    return fallback


def _semantic_parts(text: str) -> list[str]:
    parts: list[str] = []
    for block in re.split(r"\n\s*\n", text):
        block = block.strip()
        if not block:
            continue
        lines = [line.strip() for line in LINE_SPLIT_RE.split(block) if line.strip()]
        if len(lines) >= 3 and any(_is_heading(line) for line in lines[:2]):
            parts.extend(lines)
            continue
        if any(line.startswith(("•", "-", "»")) for line in lines):
            parts.extend(lines)
            continue
        parts.extend(part.strip() for part in SPLIT_RE.split(block) if part.strip())
    return parts


def chunk_pages(pages: list[PageRecord], target_chars: int = 850) -> list[ChunkRecord]:
    records: list[ChunkRecord] = []
    for page in pages:
        page_sections = _sections(page.text)
        if not page_sections:
            continue
        resolution = RESOLUTION_RE.search(page.text)
        date = DATE_RE.search(page.text)
        fallback_title = page_sections[0][:180] if len(page_sections[0]) < 240 else None

        ordinal = 0
        for section_index, section in enumerate(page_sections):
            parts = _semantic_parts(section)
            if not parts:
                continue
            title = _section_title(section, fallback_title)
            for text in _window(parts, target_chars):
                identity = (
                    f"{page.document_id}:{page.page_number}:{section_index}:"
                    f"{ordinal}:{text}"
                )
                chunk_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]
                records.append(
                    ChunkRecord(
                        chunk_id=chunk_id,
                        document_id=page.document_id,
                        source_file=page.source_file,
                        page_number=page.page_number,
                        text=text,
                        parent_text=section[:5000],
                        title=title,
                        resolution_number=resolution.group(1) if resolution else None,
                        document_date=date.group(1) if date else None,
                        extraction_method=page.extraction_method,
                        quality_score=page.quality_score,
                    )
                )
                ordinal += 1
    return records
