from enterprise_rag.models import ChunkRecord
from enterprise_rag.retrieval import HybridRetriever


def chunk(chunk_id: str, text: str, page_number: int = 1) -> ChunkRecord:
    return ChunkRecord(
        chunk_id=chunk_id,
        document_id="doc",
        source_file="book.pdf",
        page_number=page_number,
        text=text,
        parent_text=text,
        extraction_method="native",
        quality_score=1.0,
    )


def test_retrieval_ignores_generic_question_words() -> None:
    retriever = HybridRetriever(
        [
            chunk("noise", "This page gives information about memory and decision problems."),
            chunk("target", "Gallbladder inflammation includes cholecystitis and gallstones."),
        ],
        enable_dense=False,
    )

    hits = retriever.search("what is infor related galbladder problems?", top_k=1)

    assert hits[0].chunk.chunk_id == "target"


def test_exact_medical_topic_is_boosted() -> None:
    retriever = HybridRetriever(
        [
            chunk("noise", "General exam preparation information and patient communication."),
            chunk("target", "Endoderm is a primary germ layer in embryology.", page_number=631),
        ],
        enable_dense=False,
    )

    hits = retriever.search("give me information regarding Endoderm", top_k=1)

    assert hits[0].chunk.page_number == 631


def test_retrieval_returns_no_hits_when_query_has_no_match() -> None:
    retriever = HybridRetriever(
        [
            chunk("noise", "A stepped care approach for antihypertension medications."),
            chunk("other", "General patient communication and clinical ethics."),
        ],
        enable_dense=False,
    )

    assert retriever.search("gonorrhoeae", top_k=3) == []


def test_retrieval_ignores_generic_medicine_follow_up_words() -> None:
    retriever = HybridRetriever(
        [
            chunk("adherence", "Patients may fail to take their medicines as prescribed."),
            chunk(
                "overview",
                "Vaginal infection vaginitis vulvovaginitis bacterial vaginosis candidiasis and trichomoniasis can cause vaginal discharge.",
            ),
            chunk(
                "treatment",
                "Vaginitis treatment can include metronidazole for bacterial vaginosis and trichomoniasis.",
            ),
        ],
        enable_dense=False,
    )

    hits = retriever.search(
        "vaginal infection medicines take tackle this metronidazole treatment",
        top_k=1,
    )

    assert hits[0].chunk.chunk_id == "treatment"


def test_retrieval_uses_chunk_title_without_polluting_passage_text() -> None:
    treatment = chunk(
        "treatment",
        "Recommended regimens include metronidazole gel.",
    ).model_copy(update={"title": "BACTERIAL VAGINOSIS TREATMENT"})
    overview = chunk(
        "overview",
        "Bacterial vaginosis causes vaginal discharge.",
    )
    retriever = HybridRetriever([overview, treatment], enable_dense=False)

    hits = retriever.search("bacterial vaginosis treatment", top_k=1)

    assert hits[0].chunk.chunk_id == "treatment"
    assert not hits[0].chunk.text.startswith("BACTERIAL VAGINOSIS")


def test_retrieval_penalizes_back_matter_index_entries() -> None:
    index_entry = chunk(
        "index",
        "bacterial vaginosis, 147 clindamycin vs, 188 metronidazole, 250 vaginal infections, 178 vaginitis, 155",
    ).model_copy(update={"title": "INDEX"})
    source_entry = chunk(
        "source",
        "Bacterial vaginosis treatment includes metronidazole gel or clindamycin vaginal cream.",
    )
    retriever = HybridRetriever([index_entry, source_entry], enable_dense=False)

    hits = retriever.search("bacterial vaginosis metronidazole treatment", top_k=1)

    assert hits[0].chunk.chunk_id == "source"


def test_mmr_reduces_near_duplicate_final_results() -> None:
    duplicate_a = chunk(
        "duplicate-a",
        "Kidney stone treatment includes hydration analgesia and ureteroscopy.",
        page_number=1,
    )
    duplicate_b = chunk(
        "duplicate-b",
        "Kidney stone treatment includes hydration analgesia and ureteroscopy.",
        page_number=2,
    )
    diverse = chunk(
        "diverse",
        "Kidney stone prevention includes citrate, fluids, and reducing sodium.",
        page_number=3,
    )
    retriever = HybridRetriever([duplicate_a, duplicate_b, diverse], enable_dense=False)

    hits = retriever.search("kidney stone treatment prevention", top_k=2)

    assert hits[0].chunk.chunk_id in {"duplicate-a", "duplicate-b"}
    assert hits[1].chunk.chunk_id == "diverse"
