import re

GUJARATI_RE = re.compile(r"[\u0A80-\u0AFF]")
LATIN_RE = re.compile(r"[A-Za-z]")
SUSPICIOUS_RE = re.compile(r"[Œ‹›˘√ÎÏËÁÒ]")
LEGACY_ASCII_SYMBOL_RE = re.compile(r"[\\#;[\]^]")


def extraction_quality(text: str) -> tuple[float, list[str]]:
    """Score whether native PDF text is useful enough to avoid OCR."""
    stripped = text.strip()
    warnings: list[str] = []
    if len(stripped) < 40:
        return 0.0, ["too_little_text"]

    visible = [char for char in stripped if not char.isspace()]
    suspicious_ratio = len(SUSPICIOUS_RE.findall(stripped)) / max(len(visible), 1)
    legacy_symbol_ratio = len(LEGACY_ASCII_SYMBOL_RE.findall(stripped)) / max(len(visible), 1)
    script_chars = len(GUJARATI_RE.findall(stripped)) + len(LATIN_RE.findall(stripped))
    script_ratio = script_chars / max(len(visible), 1)

    score = 1.0
    if suspicious_ratio > 0.02:
        warnings.append("possible_legacy_font_encoding")
        score -= min(0.8, suspicious_ratio * 5)
    if not GUJARATI_RE.search(stripped) and legacy_symbol_ratio > 0.035:
        warnings.append("possible_ascii_mapped_gujarati_font")
        score -= min(0.8, legacy_symbol_ratio * 6)
    if script_ratio < 0.25:
        warnings.append("low_recognized_script_ratio")
        score -= 0.4
    return max(0.0, min(1.0, score)), warnings


def language_hint(text: str) -> str:
    gujarati = len(GUJARATI_RE.findall(text))
    latin = len(LATIN_RE.findall(text))
    if gujarati > latin:
        return "gu"
    if latin:
        return "en"
    return "unknown"
