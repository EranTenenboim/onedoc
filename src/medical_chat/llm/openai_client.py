from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from medical_chat.domain import ChatTurn
from medical_chat.llm.base import BaseLLMClient, LLMResult, MEDICAL_SYSTEM_PROMPT


class OpenAILLMClient(BaseLLMClient):
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens

    def _messages(self, question: str, history: list[ChatTurn] | None) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = [{"role": "system", "content": MEDICAL_SYSTEM_PROMPT}]
        if history:
            messages.extend({"role": turn.role, "content": turn.content} for turn in history)
        messages.append({"role": "user", "content": question})
        return messages

    async def stream(
        self,
        question: str,
        history: list[ChatTurn] | None = None,
    ) -> AsyncIterator[str]:
        stream = await self._client.chat.completions.create(
            model=self._model,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
            stream=True,
            messages=self._messages(question, history),
        )
        async for event in stream:
            delta = event.choices[0].delta.content if event.choices else None
            if delta:
                yield delta

    async def complete(
        self,
        question: str,
        history: list[ChatTurn] | None = None,
    ) -> LLMResult:
        response = await self._client.chat.completions.create(
            model=self._model,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
            messages=self._messages(question, history),
        )
        choice = response.choices[0].message.content or ""
        tokens = response.usage.total_tokens if response.usage else len(choice.split())
        return LLMResult(answer=choice, tokens_used=tokens)
