import json
from collections.abc import AsyncIterator
from dataclasses import dataclass

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from medical_chat.config import Settings
from medical_chat.guardrails import validate_medical_question
from medical_chat.models import MessageStatus
from medical_chat.rate_limit import RateLimiter
from medical_chat.statistics import StatisticsCollector
from medical_chat.storage import MessageQueue, MessageStore
from medical_chat.stream_hub import StreamHub
from medical_chat.worker_pool import WorkerPool


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    conversationId: str | None = None


class ChatSubmitResponse(BaseModel):
    messageId: str
    conversationId: str


class ChatProcessingResponse(BaseModel):
    status: str = "processing"
    conversationId: str | None = None


class ChatCompletedResponse(BaseModel):
    status: str = "completed"
    answer: str
    conversationId: str


class ChatFailedResponse(BaseModel):
    status: str = "failed"
    error: str
    conversationId: str | None = None


@dataclass
class AppState:
    settings: Settings
    store: MessageStore
    queue: MessageQueue
    worker_pool: WorkerPool
    stats: StatisticsCollector
    rate_limiter: RateLimiter
    stream_hub: StreamHub


def create_router(state: AppState) -> APIRouter:
    router = APIRouter()

    @router.post("/chat", response_model=ChatSubmitResponse)
    async def submit_chat(request: ChatRequest, http_request: Request) -> ChatSubmitResponse:
        client_key = http_request.client.host if http_request.client else "unknown"
        if not state.rate_limiter.allow(client_key):
            retry_after = state.rate_limiter.retry_after_seconds(client_key)
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please wait before submitting another question.",
                headers={"Retry-After": str(retry_after)},
            )

        rejection = validate_medical_question(
            request.question,
            enforce=state.settings.enforce_medical_only,
        )
        if rejection:
            raise HTTPException(status_code=422, detail=rejection)

        message = state.store.create(
            question=request.question,
            conversation_id=request.conversationId,
        )
        await state.queue.enqueue(message.message_id)
        return ChatSubmitResponse(
            messageId=message.message_id,
            conversationId=message.conversation_id,
        )

    @router.get("/chat/{message_id}")
    async def get_chat(message_id: str):
        message = state.store.get(message_id)
        if message is None:
            raise HTTPException(status_code=404, detail="Message not found")

        if message.status in (MessageStatus.PENDING, MessageStatus.PROCESSING):
            return ChatProcessingResponse(conversationId=message.conversation_id)
        if message.status == MessageStatus.COMPLETED:
            return ChatCompletedResponse(
                answer=message.answer or "",
                conversationId=message.conversation_id,
            )
        return ChatFailedResponse(
            error=message.error or "Unknown error",
            conversationId=message.conversation_id,
        )

    @router.get("/chat/{message_id}/stream")
    async def stream_chat(message_id: str):
        message = state.store.get(message_id)
        if message is None:
            raise HTTPException(status_code=404, detail="Message not found")

        async def event_generator() -> AsyncIterator[str]:
            if message.status == MessageStatus.COMPLETED:
                yield _sse("done", message.answer or "")
                return
            if message.status == MessageStatus.FAILED:
                yield _sse("error", message.error or "Unknown error")
                return

            queue = await state.stream_hub.subscribe(message_id)
            while True:
                event = await queue.get()
                if event is None:
                    break
                yield _sse(event.event, event.data)

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    @router.get("/health")
    async def health_check():
        return {"status": "ok"}

    @router.get("/statistics")
    async def get_statistics():
        idle, active = state.worker_pool.worker_counts()
        snapshot = state.stats.snapshot(
            queue_length=state.queue.qsize(),
            idle_workers=idle,
            active_workers=active,
        )
        return snapshot.to_api_dict()

    return router


def _sse(event: str, data: str) -> str:
    payload = json.dumps({"text": data}) if event == "token" else json.dumps({"value": data})
    return f"event: {event}\ndata: {payload}\n\n"
