from anthropic import AsyncAnthropic

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

    async def complete(self, question: str) -> LLMResult:
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            temperature=self._temperature,
            system=MEDICAL_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": question}],
        )
        text_blocks = [block.text for block in response.content if block.type == "text"]
        answer = "\n".join(text_blocks)
        tokens = response.usage.input_tokens + response.usage.output_tokens
        return LLMResult(answer=answer, tokens_used=tokens)
