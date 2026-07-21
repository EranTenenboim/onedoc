"""Sanitize and validate user-supplied input to block injection and data poisoning."""

from __future__ import annotations

import re
import unicodedata
from uuid import UUID

# Reject C0/C1 controls except tab/newline/carriage-return.
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
)

MAX_QUESTION_LENGTH = 4000
MAX_HISTORY_TURNS = 20  # user+assistant pairs counted as turns; cap pairs via // 2
MAX_ID_LENGTH = 36


class InputValidationError(ValueError):
    """Raised when user input is unsafe or malformed."""


def sanitize_text(value: str, *, max_length: int = MAX_QUESTION_LENGTH) -> str:
    """Normalize Unicode, strip null/control chars, and bound length."""
    if not isinstance(value, str):
        raise InputValidationError("Value must be a string")

    # NFKC collapses homoglyphs / compatibility forms used in obfuscation.
    cleaned = unicodedata.normalize("NFKC", value)
    cleaned = cleaned.replace("\x00", "")
    cleaned = _CONTROL_CHARS.sub("", cleaned)
    cleaned = " ".join(cleaned.split())
    if not cleaned:
        raise InputValidationError("Text is empty after sanitization")
    if len(cleaned) > max_length:
        raise InputValidationError(f"Text exceeds maximum length of {max_length}")
    return cleaned


def parse_uuid(value: str, *, field_name: str = "id") -> str:
    """Accept only canonical UUID strings (blocks arbitrary/poisoned IDs)."""
    if not isinstance(value, str):
        raise InputValidationError(f"{field_name} must be a string")
    candidate = value.strip()
    if len(candidate) > MAX_ID_LENGTH or not _UUID_RE.fullmatch(candidate):
        raise InputValidationError(f"Invalid {field_name}")
    try:
        return str(UUID(candidate))
    except ValueError as exc:
        raise InputValidationError(f"Invalid {field_name}") from exc


def sanitize_question(question: str) -> str:
    return sanitize_text(question, max_length=MAX_QUESTION_LENGTH)


def sanitize_optional_conversation_id(conversation_id: str | None) -> str | None:
    if conversation_id is None or conversation_id.strip() == "":
        return None
    return parse_uuid(conversation_id, field_name="conversationId")


def sanitize_stored_text(value: str | None, *, max_length: int = MAX_QUESTION_LENGTH) -> str | None:
    """Best-effort clean text loaded from storage before reuse in prompts."""
    if value is None:
        return None
    try:
        return sanitize_text(value, max_length=max_length)
    except InputValidationError:
        return None
