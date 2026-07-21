from medical_chat.config import Settings
from medical_chat.llm.anthropic_client import AnthropicLLMClient
from medical_chat.llm.base import BaseLLMClient
from medical_chat.llm.mock import MockLLMClient
from medical_chat.llm.openai_client import OpenAILLMClient
from medical_chat.models import LLMProvider


def create_llm_client(settings: Settings) -> BaseLLMClient:
    if settings.llm_provider == LLMProvider.MOCK:
        return MockLLMClient(
            fail_rate=settings.mock_fail_rate,
            fail_times=settings.mock_fail_times,
        )
    if settings.llm_provider == LLMProvider.OPENAI:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
        return OpenAILLMClient(
            api_key=settings.openai_api_key,
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )
    if settings.llm_provider == LLMProvider.ANTHROPIC:
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required when LLM_PROVIDER=anthropic")
        return AnthropicLLMClient(
            api_key=settings.anthropic_api_key,
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )
    raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")
