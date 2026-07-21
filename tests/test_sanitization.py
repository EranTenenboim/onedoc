import pytest

from medical_chat.sanitization import (
    InputValidationError,
    parse_uuid,
    sanitize_optional_conversation_id,
    sanitize_question,
)


def test_sanitize_question_strips_controls_and_nulls():
    cleaned = sanitize_question("What is\x00 anemia?\x07")
    assert cleaned == "What is anemia?"
    assert "\x00" not in cleaned


def test_sanitize_question_rejects_empty_after_clean():
    with pytest.raises(InputValidationError):
        sanitize_question("\x00\x01   ")


def test_conversation_id_must_be_uuid():
    with pytest.raises(InputValidationError):
        sanitize_optional_conversation_id("'; DROP TABLE messages;--")
    with pytest.raises(InputValidationError):
        sanitize_optional_conversation_id("../etc/passwd")
    valid = sanitize_optional_conversation_id("550e8400-e29b-41d4-a716-446655440000")
    assert valid == "550e8400-e29b-41d4-a716-446655440000"


def test_parse_uuid_rejects_injection_payloads():
    with pytest.raises(InputValidationError):
        parse_uuid("1 OR 1=1", field_name="messageId")
    with pytest.raises(InputValidationError):
        parse_uuid("'; SELECT * FROM messages --", field_name="messageId")
