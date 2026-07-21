import asyncio
import random
from collections.abc import AsyncIterator

from medical_chat.domain import ChatTurn
from medical_chat.llm.base import BaseLLMClient, LLMResult


class MockLLMClient(BaseLLMClient):
    """Deterministic mock LLM for local development and tests."""

    def __init__(self, *, fail_rate: float = 0.0) -> None:
        self._fail_rate = fail_rate

    async def stream(
        self,
        question: str,
        history: list[ChatTurn] | None = None,
    ) -> AsyncIterator[str]:
        await asyncio.sleep(random.uniform(0.05, 0.15))
        if random.random() < self._fail_rate:
            raise RuntimeError("Simulated LLM failure")

        prior = ""
        if history:
            prior = f" Using {len(history) // 2} earlier turn(s) in this conversation."

        answer = (
            f"[Mock medical expert response] Regarding your question about "
            f"'{question}':{prior} common symptoms may include fatigue, weakness, and "
            "other non-specific signs. Please consult a healthcare professional "
            "for personalized advice."
        )
        words = answer.split(" ")
        for index, word in enumerate(words):
            chunk = word if index == 0 else f" {word}"
            yield chunk
            await asyncio.sleep(0.01)

    async def complete(
        self,
        question: str,
        history: list[ChatTurn] | None = None,
    ) -> LLMResult:
        chunks: list[str] = []
        async for chunk in self.stream(question, history):
            chunks.append(chunk)
        answer = "".join(chunks)
        tokens = len(question.split()) + len(answer.split())
        if history:
            tokens += sum(len(turn.content.split()) for turn in history)
        return LLMResult(answer=answer, tokens_used=tokens)
