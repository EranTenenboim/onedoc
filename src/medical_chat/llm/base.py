from collections.abc import AsyncIterator
from dataclasses import dataclass

from medical_chat.domain import ChatTurn

MEDICAL_SYSTEM_PROMPT = """You are a medical expert assistant. Provide clear, evidence-based
information about medical topics only. Always remind users that your answers are for educational
purposes only and that they should consult a qualified healthcare professional for diagnosis
or treatment decisions. Do not provide definitive diagnoses.

If a question is not related to medicine, health, symptoms, conditions, treatments, medications,
or patient care, politely refuse and ask the user to submit a medical question instead.
Do not answer coding, legal, financial, entertainment, or general knowledge requests.

When prior conversation turns are provided, use them for continuity and refer to earlier answers
when relevant."""


@dataclass(frozen=True)
class LLMResult:
    answer: str
    tokens_used: int


class LLMError(Exception):
    """Raised when an LLM request fails after retries."""


class BaseLLMClient:
    async def stream(
        self,
        question: str,
        history: list[ChatTurn] | None = None,
    ) -> AsyncIterator[str]:
        raise NotImplementedError
        yield  # pragma: no cover - makes this an async generator type

    async def complete(
        self,
        question: str,
        history: list[ChatTurn] | None = None,
    ) -> LLMResult:
        chunks: list[str] = []
        async for chunk in self.stream(question, history):
            chunks.append(chunk)
        answer = "".join(chunks)
        tokens = sum(len(part.split()) for part in [question, answer])
        if history:
            tokens += sum(len(turn.content.split()) for turn in history)
        return LLMResult(answer=answer, tokens_used=tokens)
