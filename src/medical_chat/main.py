from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from medical_chat.api import AppState, create_router
from medical_chat.config import Settings, get_settings
from medical_chat.llm.factory import create_llm_client
from medical_chat.rate_limit import RateLimiter
from medical_chat.statistics import StatisticsCollector
from medical_chat.storage import MessageQueue, MessageStore, SharedLog
from medical_chat.worker_pool import WorkerPool


def resolve_static_dir(settings: Settings) -> Path | None:
    if settings.static_dir:
        path = Path(settings.static_dir)
        return path if path.is_dir() else None

    candidates = [
        Path(__file__).resolve().parent.parent.parent / "static",
    ]
    for path in candidates:
        if path.is_dir():
            return path
    return None


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    static_dir = resolve_static_dir(settings)

    store = MessageStore()
    queue = MessageQueue()
    shared_log = SharedLog(settings.log_file)
    stats = StatisticsCollector()
    llm_client = create_llm_client(settings)
    worker_pool = WorkerPool(
        settings=settings,
        store=store,
        queue=queue,
        shared_log=shared_log,
        llm_client=llm_client,
        stats=stats,
    )
    rate_limiter = RateLimiter(
        max_requests=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window_seconds,
    )
    state = AppState(
        settings=settings,
        store=store,
        queue=queue,
        worker_pool=worker_pool,
        stats=stats,
        rate_limiter=rate_limiter,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await worker_pool.start()
        yield
        await worker_pool.stop()

    app = FastAPI(
        title="Medical Expert AI Chat",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(create_router(state))

    if static_dir is not None:
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

        @app.get("/")
        async def index():
            return FileResponse(static_dir / "index.html")

    return app


def run() -> None:
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "medical_chat.main:create_app",
        factory=True,
        host="0.0.0.0",
        port=settings.server_port,
        reload=False,
    )


app = create_app()
