import asyncio

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from medical_chat.config import Settings
from medical_chat.main import create_app
from medical_chat.models import LLMProvider


@pytest.fixture
def settings() -> Settings:
    return Settings(
        SERVER_PORT=8000,
        LLM_PROVIDER=LLMProvider.MOCK,
        LLM_MODEL="mock",
        LLM_TEMPERATURE=0.3,
        LLM_MAX_TOKENS=512,
        RETRY_DELAY=0.01,
        MAX_RETRIES=2,
        WORKER_IDLE_TIMEOUT=5,
        LOG_FILE="logs/test-interactions.log",
    )


@pytest.fixture
async def client(settings: Settings):
    app = create_app(settings)
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


@pytest.mark.asyncio
async def test_submit_and_retrieve_chat(client: AsyncClient):
    submit = await client.post("/chat", json={"question": "What is anemia?"})
    assert submit.status_code == 200
    message_id = submit.json()["messageId"]

    for _ in range(50):
        response = await client.get(f"/chat/{message_id}")
        data = response.json()
        if data["status"] == "completed":
            assert "answer" in data
            assert data["answer"]
            return
        if data["status"] == "failed":
            pytest.fail(data.get("error", "unexpected failure"))
        await asyncio.sleep(0.1)

    pytest.fail("Timed out waiting for chat completion")


@pytest.mark.asyncio
async def test_statistics(client: AsyncClient):
    await client.post("/chat", json={"question": "What is hypertension?"})

    for _ in range(50):
        stats = await client.get("/statistics")
        assert stats.status_code == 200
        body = stats.json()
        if body["messagesProcessed"] >= 1:
            assert "currentQueueLength" in body
            assert "activeWorkers" in body
            return
        await asyncio.sleep(0.1)

    pytest.fail("Timed out waiting for statistics update")


@pytest.mark.asyncio
async def test_unknown_message_returns_404(client: AsyncClient):
    response = await client.get("/chat/does-not-exist")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_rejects_off_topic_question(client: AsyncClient):
    response = await client.post(
        "/chat",
        json={"question": "Write me Python code for a game"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_rate_limit_blocks_excessive_requests(settings: Settings):
    limited_settings = Settings(
        SERVER_PORT=8000,
        LLM_PROVIDER=LLMProvider.MOCK,
        LLM_MODEL="mock",
        RETRY_DELAY=0.01,
        MAX_RETRIES=2,
        WORKER_IDLE_TIMEOUT=5,
        LOG_FILE="logs/test-interactions.log",
        RATE_LIMIT_REQUESTS=2,
        RATE_LIMIT_WINDOW_SECONDS=60,
        ENFORCE_MEDICAL_ONLY=True,
    )
    app = create_app(limited_settings)
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            for _ in range(2):
                ok = await client.post(
                    "/chat",
                    json={"question": "What are anemia symptoms?"},
                )
                assert ok.status_code == 200
            blocked = await client.post(
                "/chat",
                json={"question": "What are fever symptoms?"},
            )
            assert blocked.status_code == 429
