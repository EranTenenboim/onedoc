from collections.abc import AsyncIterator

from anthropic import AsyncAnthropic

from medical_chat.domain import ChatTurn
from medical_chat.llm.base import BaseLLMClient, LLMResult, MEDICAL_SYSTEM_PROMPT


class AnthropicLLMClient(BaseLLMClient):
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> None:
        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens

    def _messages(self, question: str, history: list[ChatTurn] | None) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        if history:
            messages.extend({"role": turn.role, "content": turn.content} for turn in history)
        messages.append({"role": "user", "content": question})
        return messages

    async def stream(
        self,
        question: str,
        history: list[ChatTurn] | None = None,
    ) -> AsyncIterator[str]:
        async with self._client.messages.stream(
            model=self._model,
            max_tokens=self._max_tokens,
            temperature=self._temperature,
            system=MEDICAL_SYSTEM_PROMPT,
            messages=self._messages(question, history),
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def complete(
        self,
        question: str,
        history: list[ChatTurn] | None = None,
    ) -> LLMResult:
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            temperature=self._temperature,
            system=MEDICAL_SYSTEM_PROMPT,
            messages=self._messages(question, history),
        )
        text_blocks = [block.text for block in response.content if block.type == "text"]
        answer = "\n".join(text_blocks)
        tokens = response.usage.input_tokens + response.usage.output_tokens
        return LLMResult(answer=answer, tokens_used=tokens)
