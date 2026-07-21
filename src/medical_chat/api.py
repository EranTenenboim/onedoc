from dataclasses import dataclass

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from medical_chat.config import Settings
from medical_chat.guardrails import validate_medical_question
from medical_chat.models import MessageStatus
from medical_chat.rate_limit import RateLimiter
from medical_chat.statistics import StatisticsCollector
from medical_chat.storage import MessageQueue, MessageStore
from medical_chat.worker_pool import WorkerPool


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)


class ChatSubmitResponse(BaseModel):
    messageId: str


class ChatProcessingResponse(BaseModel):
    status: str = "processing"


class ChatCompletedResponse(BaseModel):
    status: str = "completed"
    answer: str


class ChatFailedResponse(BaseModel):
    status: str = "failed"
    error: str


@dataclass
class AppState:
    settings: Settings
    store: MessageStore
    queue: MessageQueue
    worker_pool: WorkerPool
    stats: StatisticsCollector
    rate_limiter: RateLimiter


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

        message = state.store.create(question=request.question)
        await state.queue.enqueue(message.message_id)
        return ChatSubmitResponse(messageId=message.message_id)

    @router.get("/chat/{message_id}")
    async def get_chat(message_id: str):
        message = state.store.get(message_id)
        if message is None:
            raise HTTPException(status_code=404, detail="Message not found")

        if message.status in (MessageStatus.PENDING, MessageStatus.PROCESSING):
            return ChatProcessingResponse()
        if message.status == MessageStatus.COMPLETED:
            return ChatCompletedResponse(answer=message.answer or "")
        return ChatFailedResponse(error=message.error or "Unknown error")

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
