from dataclasses import dataclass

MEDICAL_SYSTEM_PROMPT = """You are a medical expert assistant. Provide clear, evidence-based
information about medical topics only. Always remind users that your answers are for educational
purposes only and that they should consult a qualified healthcare professional for diagnosis
or treatment decisions. Do not provide definitive diagnoses.

If a question is not related to medicine, health, symptoms, conditions, treatments, medications,
or patient care, politely refuse and ask the user to submit a medical question instead.
Do not answer coding, legal, financial, entertainment, or general knowledge requests."""


@dataclass(frozen=True)
class LLMResult:
    answer: str
    tokens_used: int


class LLMError(Exception):
    """Raised when an LLM request fails after retries."""


class BaseLLMClient:
    async def complete(self, question: str) -> LLMResult:
        raise NotImplementedError
