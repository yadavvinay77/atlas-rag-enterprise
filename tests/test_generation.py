from enterprise_rag.generation import answer_extractively
from enterprise_rag.models import ChunkRecord, SearchHit


def hit(text: str) -> SearchHit:
    return SearchHit(
        score=1.0,
        chunk=ChunkRecord(
            chunk_id="kidney",
            document_id="first-aid",
            source_file="First Aid.pdf",
            page_number=619,
            text=text,
            parent_text=text,
            extraction_method="native",
            quality_score=1.0,
        ),
    )


def test_extractive_answer_is_structured_not_raw_diagram_dump() -> None:
    answer = answer_extractively(
        "Horseshoe kidney",
        [
            hit(
                """Horseshoe kidney
Aorta
Renal artery
Inferior
mesenteric
artery
Ureter
Inferior poles of both kidneys fuse abnormally.
As they ascend from pelvis during fetal development, horseshoe kidneys get trapped under inferior mesenteric artery and remain low in the abdomen.
Kidneys can function normally, but associated with hydronephrosis, renal stones, infection, increased risk of renal cancer.
Higher incidence in chromosomal aneuploidy."""
            )
        ],
    )

    assert "**Horseshoe kidney**" in answer.answer
    assert "**Key points:**" in answer.answer
    assert "Inferior poles of both kidneys fuse" in answer.answer
    assert "\nAorta\n" not in answer.answer


def test_extractive_answer_formats_hypertension_stepped_care() -> None:
    answer = answer_extractively(
        "Summarize the treatment of hypertension.",
        [
            hit(
                """Table 13-13.
A stepped care approach to the initiation and titration of antihypertension medications.
Step 1
ACE inhibitor/ARB or
Calcium channel blocker or
Thiazide diuretic
Step 2
ACE inhibitor/ARB plus
Calcium channel blocker or thiazide diuretic
Step 3
ACE inhibitor/ARB plus calcium channel blocker plus thiazide diuretic
Step 4
ACE inhibitor/ARB plus calcium channel blocker plus thiazide diuretic plus spironolactone"""
            )
        ],
    )

    assert "Step 1: ACE inhibitor/ARB" in answer.answer
    assert "Step 4: add spironolactone" in answer.answer


def test_extractive_answer_collects_treatment_sentences_across_hits() -> None:
    answer = answer_extractively(
        "what are the medicines we can take to tackle this?",
        [
            hit("Vaginitis may be caused by bacterial vaginosis, candidiasis, or trichomoniasis."),
            hit("Metronidazole is used for bacterial vaginosis and trichomoniasis."),
            hit("Fluconazole is used for vulvovaginal candidiasis."),
        ],
    )

    assert "Metronidazole" in answer.answer
    assert "Fluconazole" in answer.answer
    assert "not personal prescribing advice" in answer.answer


def test_extractive_treatment_answer_filters_general_drug_facts_with_evidence_query() -> None:
    answer = answer_extractively(
        "what are the medicines we can take to tackle this?",
        [
            hit("Metronidazole vaginal cream is effective for vaginitis."),
            hit("In anaerobic infections, metronidazole can be given orally or intravenously."),
            hit("Intravenous metronidazole may be used for fulminant C difficile infection."),
        ],
        evidence_query="vaginal infection vaginitis treatment metronidazole",
    )

    assert "Metronidazole vaginal cream" in answer.answer
    assert "anaerobic infections" not in answer.answer
    assert "C difficile" not in answer.answer


def test_extractive_answer_filters_index_like_treatment_lines() -> None:
    answer = answer_extractively(
        "what medicines treat this?",
        [
            hit("Metronidazole vaginal cream is effective for vaginitis."),
            hit(
                "bacterial vaginosis, 147 clindamycin vs, 188 metronidazole, 250 vaginal infections, 178 vaginitis, 155"
            ),
        ],
        evidence_query="vaginitis treatment metronidazole",
    )

    assert "Metronidazole vaginal cream" in answer.answer
    assert "clindamycin vs" not in answer.answer
