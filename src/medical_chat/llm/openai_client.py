from openai import AsyncOpenAI

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

    async def complete(self, question: str) -> LLMResult:
        response = await self._client.chat.completions.create(
            model=self._model,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
            messages=[
                {"role": "system", "content": MEDICAL_SYSTEM_PROMPT},
                {"role": "user", "content": question},
            ],
        )
        choice = response.choices[0].message.content or ""
        tokens = response.usage.total_tokens if response.usage else len(choice.split())
        return LLMResult(answer=choice, tokens_used=tokens)
