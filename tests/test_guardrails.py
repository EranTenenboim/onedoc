from medical_chat.guardrails import validate_medical_question


def test_allows_medical_question():
    assert validate_medical_question(
        "What are the symptoms of iron deficiency?",
        enforce=True,
    ) is None


def test_rejects_off_topic_request():
    assert validate_medical_question(
        "Write me a Python script to scrape websites",
        enforce=True,
    ) is not None


def test_rejects_non_medical_general_question():
    assert validate_medical_question(
        "Who won the World Cup in 2022?",
        enforce=True,
    ) is not None


def test_disabled_enforcement_allows_anything():
    assert validate_medical_question(
        "Tell me a joke about cats",
        enforce=False,
    ) is None
