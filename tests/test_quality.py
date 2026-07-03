from enterprise_rag.quality import extraction_quality, language_hint


def test_rejects_legacy_font_gibberish() -> None:
    score, warnings = extraction_quality("Œ@÷ ¿«ıflÌ μ’›˘√ ‹ÎÀı " * 10)
    assert score < 0.55
    assert "possible_legacy_font_encoding" in warnings


def test_accepts_gujarati_unicode() -> None:
    text = "ગામતળ વિસ્તાર બાબતનો મહેસૂલ વિભાગનો ઠરાવ અને તેની શરતો. " * 8
    score, warnings = extraction_quality(text)
    assert score >= 0.55
    assert language_hint(text) == "gu"
    assert "possible_legacy_font_encoding" not in warnings


def test_rejects_ascii_mapped_gujarati_font() -> None:
    text = r"S|D G\P lJQFI 5lZ5+v9ZFJGF\ G\AZvTFZLB 5FGF G\AZ s!f s#f ;ZSFZL %,M8 " * 8
    score, warnings = extraction_quality(text)
    assert score < 0.55
    assert "possible_ascii_mapped_gujarati_font" in warnings
