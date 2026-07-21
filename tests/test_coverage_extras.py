import asyncio
from pathlib import Path

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from medical_chat.config import Settings
from medical_chat.main import create_app
from medical_chat.models import LLMProvider


async def wait_for_completion(client: AsyncClient, message_id: str) -> dict:
    for _ in range(80):
        response = await client.get(f"/chat/{message_id}")
        data = response.json()
        if data["status"] in {"completed", "failed"}:
            return data
        await asyncio.sleep(0.1)
    pytest.fail("Timed out waiting for chat completion")


def _settings(tmp_path: Path, **overrides: object) -> Settings:
    base = {
        "SERVER_PORT": 8000,
        "LLM_PROVIDER": LLMProvider.MOCK,
        "LLM_MODEL": "mock",
        "RETRY_DELAY": 0.01,
        "MAX_RETRIES": 2,
        "WORKER_IDLE_TIMEOUT": 5,
        "LOG_FILE": str(tmp_path / "extra.log"),
        "SQLITE_PATH": str(tmp_path / "extra.db"),
        "PERSISTENCE_ENABLED": True,
        "RATE_LIMIT_REQUESTS": 100,
        "ENFORCE_MEDICAL_ONLY": True,
    }
    base.update(overrides)
    return Settings(**base)


@pytest.mark.asyncio
async def test_health_endpoint(tmp_path: Path):
    app = create_app(_settings(tmp_path))
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_llm_retries_then_succeeds(tmp_path: Path):
    app = create_app(_settings(tmp_path, MOCK_FAIL_TIMES=1, MAX_RETRIES=2))
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            submit = await client.post("/chat", json={"question": "What is anemia?"})
            assert submit.status_code == 200
            data = await wait_for_completion(client, submit.json()["messageId"])
            assert data["status"] == "completed"
            assert data["answer"]

            stats = await client.get("/statistics")
            body = stats.json()
            assert body["messagesSucceeded"] >= 1
            assert body["totalRetries"] >= 1


@pytest.mark.asyncio
async def test_llm_fails_after_retries(tmp_path: Path):
    app = create_app(
        _settings(tmp_path, MOCK_FAIL_TIMES=5, MAX_RETRIES=1, RETRY_DELAY=0.01)
    )
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            submit = await client.post("/chat", json={"question": "What is fever?"})
            assert submit.status_code == 200
            data = await wait_for_completion(client, submit.json()["messageId"])
            assert data["status"] == "failed"
            assert "error" in data

            stats = await client.get("/statistics")
            body = stats.json()
            assert body["messagesFailed"] >= 1


@pytest.mark.asyncio
async def test_worker_idle_timeout_exits(tmp_path: Path):
    app = create_app(_settings(tmp_path, WORKER_IDLE_TIMEOUT=0.2))
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            submit = await client.post(
                "/chat",
                json={"question": "What are diabetes symptoms?"},
            )
            data = await wait_for_completion(client, submit.json()["messageId"])
            assert data["status"] == "completed"

            mid = await client.get("/statistics")
            mid_body = mid.json()
            assert mid_body["idleWorkers"] + mid_body["activeWorkers"] >= 1

            await asyncio.sleep(0.5)
            end = await client.get("/statistics")
            end_body = end.json()
            assert end_body["idleWorkers"] == 0
            assert end_body["activeWorkers"] == 0
