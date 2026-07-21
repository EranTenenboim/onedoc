import asyncio
from pathlib import Path

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from medical_chat.config import Settings
from medical_chat.main import create_app
from medical_chat.models import LLMProvider


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        SERVER_PORT=8000,
        LLM_PROVIDER=LLMProvider.MOCK,
        LLM_MODEL="mock",
        LLM_TEMPERATURE=0.3,
        LLM_MAX_TOKENS=512,
        RETRY_DELAY=0.01,
        MAX_RETRIES=2,
        WORKER_IDLE_TIMEOUT=5,
        LOG_FILE=str(tmp_path / "interactions.log"),
        SQLITE_PATH=str(tmp_path / "test.db"),
        PERSISTENCE_ENABLED=True,
        RATE_LIMIT_REQUESTS=100,
        RATE_LIMIT_WINDOW_SECONDS=60,
    )


@pytest.fixture
async def client(settings: Settings):
    app = create_app(settings)
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


async def wait_for_completion(client: AsyncClient, message_id: str) -> dict:
    for _ in range(80):
        response = await client.get(f"/chat/{message_id}")
        data = response.json()
        if data["status"] in {"completed", "failed"}:
            return data
        await asyncio.sleep(0.1)
    pytest.fail("Timed out waiting for chat completion")


@pytest.mark.asyncio
async def test_submit_and_retrieve_chat(client: AsyncClient):
    submit = await client.post("/chat", json={"question": "What is anemia?"})
    assert submit.status_code == 200
    body = submit.json()
    assert "messageId" in body
    assert "conversationId" in body
    data = await wait_for_completion(client, body["messageId"])
    assert data["status"] == "completed"
    assert data["answer"]


@pytest.mark.asyncio
async def test_statistics(client: AsyncClient):
    await client.post("/chat", json={"question": "What is hypertension?"})
    for _ in range(80):
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
async def test_rate_limit_blocks_excessive_requests(tmp_path: Path):
    limited_settings = Settings(
        SERVER_PORT=8000,
        LLM_PROVIDER=LLMProvider.MOCK,
        LLM_MODEL="mock",
        RETRY_DELAY=0.01,
        MAX_RETRIES=2,
        WORKER_IDLE_TIMEOUT=5,
        LOG_FILE=str(tmp_path / "rate.log"),
        SQLITE_PATH=str(tmp_path / "rate.db"),
        PERSISTENCE_ENABLED=True,
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


@pytest.mark.asyncio
async def test_conversation_history_agent_mode(client: AsyncClient):
    first = await client.post("/chat", json={"question": "What is anemia?"})
    first_body = first.json()
    await wait_for_completion(client, first_body["messageId"])

    second = await client.post(
        "/chat",
        json={
            "question": "What are common treatments for iron deficiency anemia?",
            "conversationId": first_body["conversationId"],
        },
    )
    assert second.status_code == 200
    assert second.json()["conversationId"] == first_body["conversationId"]
    data = await wait_for_completion(client, second.json()["messageId"])
    assert data["status"] == "completed"
    assert "earlier turn" in data["answer"]


@pytest.mark.asyncio
async def test_persistence_across_restart(tmp_path: Path):
    db_path = tmp_path / "persist.db"
    settings = Settings(
        SERVER_PORT=8000,
        LLM_PROVIDER=LLMProvider.MOCK,
        RETRY_DELAY=0.01,
        MAX_RETRIES=2,
        WORKER_IDLE_TIMEOUT=5,
        LOG_FILE=str(tmp_path / "persist.log"),
        SQLITE_PATH=str(db_path),
        PERSISTENCE_ENABLED=True,
        RATE_LIMIT_REQUESTS=100,
    )

    app1 = create_app(settings)
    async with LifespanManager(app1):
        transport = ASGITransport(app=app1)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            submit = await client.post("/chat", json={"question": "What is fever?"})
            message_id = submit.json()["messageId"]
            data = await wait_for_completion(client, message_id)
            assert data["status"] == "completed"
            answer = data["answer"]

    app2 = create_app(settings)
    async with LifespanManager(app2):
        transport = ASGITransport(app=app2)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            restored = await client.get(f"/chat/{message_id}")
            assert restored.status_code == 200
            body = restored.json()
            assert body["status"] == "completed"
            assert body["answer"] == answer


@pytest.mark.asyncio
async def test_streaming_endpoint(client: AsyncClient):
    submit = await client.post("/chat", json={"question": "What is diabetes?"})
    message_id = submit.json()["messageId"]

    tokens = []
    async with client.stream("GET", f"/chat/{message_id}/stream") as response:
        assert response.status_code == 200
        async for line in response.aiter_lines():
            if line.startswith("event: token"):
                tokens.append("token")
            if line.startswith("event: done"):
                tokens.append("done")
                break
            if line.startswith("event: error"):
                pytest.fail("stream error")

    assert "done" in tokens
