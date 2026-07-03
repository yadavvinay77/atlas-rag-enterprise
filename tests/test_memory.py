from enterprise_rag.memory import ConversationStore, contextualize_question
from enterprise_rag.models import ConversationTurn


def kidney_stone_turn() -> ConversationTurn:
    return ConversationTurn(
        question="Explain urinary stone disease",
        answer="Urinary stone disease includes calcium, uric acid, and other stones.",
        retrieval_query="Explain urinary stone disease",
        cited_document_ids=["kidney-doc"],
        cited_source_files=["Kidney-stones.pdf"],
    )


def test_short_follow_up_inherits_topic() -> None:
    query = contextualize_question(
        "What food plan should we follow for this?", [kidney_stone_turn()]
    )

    assert "urinary" in query
    assert "stone" in query
    assert "food plan" in query


def test_explicit_new_topic_is_not_rewritten() -> None:
    question = "Explain the diagnostic criteria for diabetes mellitus in adults"
    query = contextualize_question(question, [kidney_stone_turn()])

    assert query == question


def test_short_explicit_medical_topic_does_not_inherit_previous_topic() -> None:
    query = contextualize_question("gonorrhoeae", [kidney_stone_turn()])

    assert query.startswith("gonorrhoeae")
    assert "Neisseria gonorrhoeae" in query
    assert "urinary" not in query
    assert "stone" not in query


def test_conversation_store_is_bounded() -> None:
    store = ConversationStore(max_turns=2)
    conversation_id = store.create_or_get(None)
    for index in range(3):
        turn = kidney_stone_turn().model_copy(update={"question": f"Question {index}"})
        store.add(conversation_id, turn)

    assert [turn.question for turn in store.turns(conversation_id)] == [
        "Question 1",
        "Question 2",
    ]


def test_standalone_organ_question_does_not_assume_kidneys() -> None:
    query = contextualize_question("Which organs are involved?", [])

    assert query == "Which organs are involved?"


def test_hypertension_treatment_question_expands_to_guideline_terms() -> None:
    query = contextualize_question("Summarize the treatment of hypertension.", [])

    assert "antihypertensive agents" in query
    assert "ACE inhibitor" in query
    assert "thiazide diuretic" in query


def test_cervix_cancer_question_expands_to_medical_synonyms() -> None:
    query = contextualize_question("explain me cervix cancer", [])

    assert "cervical cancer" in query
    assert "carcinoma cervix" in query
    assert "HPV" in query


def test_gonorrhoeae_question_expands_to_medical_synonyms() -> None:
    query = contextualize_question("gonorrhoeae", [])

    assert "Neisseria gonorrhoeae" in query
    assert "ceftriaxone" in query


def test_vaginal_infection_medicine_follow_up_keeps_topic_and_treatment_terms() -> None:
    turn = ConversationTurn(
        question="explain me the vaginal infection",
        answer="Vaginal infection may present with discharge.",
        retrieval_query="explain me the vaginal infection",
        cited_document_ids=["cmdt"],
        cited_source_files=["CURRENT Medical Diagnosis _ Treatment 2026.pdf"],
    )

    query = contextualize_question(
        "what are the medicines we can take to tackle this?", [turn]
    )

    assert "vaginal infection" in query
    assert "metronidazole" in query
    assert "fluconazole" in query
    assert "ceftriaxone" in query
