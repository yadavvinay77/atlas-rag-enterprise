from enterprise_rag.chunking import chunk_pages
from enterprise_rag.models import PageRecord


def test_chunks_keep_citation_metadata() -> None:
    page = PageRecord(
        document_id="doc-1",
        source_file="policy.pdf",
        page_number=12,
        text="ઠરાવ નં. LND-3962\nતારીખ 17-04-1964.\n" + ("જમીન ફાળવણી અંગેની શરતો. " * 80),
        extraction_method="ocr",
        quality_score=0.9,
        language_hint="gu",
    )
    chunks = chunk_pages([page], target_chars=300)
    assert len(chunks) > 1
    assert all(chunk.page_number == 12 for chunk in chunks)
    assert all(chunk.source_file == "policy.pdf" for chunk in chunks)
    assert len({chunk.chunk_id for chunk in chunks}) == len(chunks)


def test_chunking_uses_section_parent_child_boundaries() -> None:
    page = PageRecord(
        document_id="doc-2",
        source_file="medical.pdf",
        page_number=8,
        text=(
            "VAGINAL DISCHARGE\n"
            "Common causes of vaginitis are bacterial vaginosis, candidiasis, and trichomoniasis.\n\n"
            "TREATMENT\n"
            "Bacterial vaginosis treatment includes metronidazole or clindamycin.\n"
            "Trichomoniasis can be treated with metronidazole or tinidazole."
        ),
        extraction_method="native",
        quality_score=1.0,
    )

    chunks = chunk_pages([page], target_chars=120)

    assert len(chunks) >= 2
    assert any(chunk.title == "VAGINAL DISCHARGE" for chunk in chunks)
    treatment_chunks = [chunk for chunk in chunks if chunk.title == "TREATMENT"]
    assert treatment_chunks
    assert all("VAGINAL DISCHARGE" not in chunk.parent_text for chunk in treatment_chunks)
