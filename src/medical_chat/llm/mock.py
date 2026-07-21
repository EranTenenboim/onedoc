import asyncio
import random

from medical_chat.llm.base import BaseLLMClient, LLMResult


class MockLLMClient(BaseLLMClient):
    """Deterministic mock LLM for local development and tests."""

    def __init__(self, *, fail_rate: float = 0.0) -> None:
        self._fail_rate = fail_rate

    async def complete(self, question: str) -> LLMResult:
        await asyncio.sleep(random.uniform(0.3, 0.8))
        if random.random() < self._fail_rate:
            raise RuntimeError("Simulated LLM failure")
        answer = (
            f"[Mock medical expert response] Regarding your question about "
            f"'{question}': common symptoms may include fatigue, weakness, and "
            "other non-specific signs. Please consult a healthcare professional "
            "for personalized advice."
        )
        tokens = len(question.split()) + len(answer.split())
        return LLMResult(answer=answer, tokens_used=tokens)
