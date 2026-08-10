from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import get_settings
from app.core.errors import (
    AppError,
    app_error_handler,
    http_exception_handler,
    ok,
    validation_exception_handler,
)
from app.features.admin.router import router as admin_router
from app.features.mock.router import router as mock_router
from app.features.profile.router import router as profile_router
from app.features.reply.router import router as reply_router
from app.features.schedule.router import router as schedule_router
from app.features.tag.router import router as tag_router
from app.features.wecom.context_router import router as context_router
from app.features.wecom.router import router as auth_router
from app.features.wecom.sse_router import router as sse_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    prefix = settings.api_prefix

    @app.get("/health")
    async def health():
        return ok(
            {
                "service": settings.app_name,
                "mock_wecom": settings.mock_wecom,
                "mock_llm": settings.mock_llm,
                "llm_provider": settings.llm_provider,
            }
        )

    @app.get(f"{prefix}/hello")
    async def hello():
        return ok({"hello": "K12-UserProfile", "phase": "mvp"})

    app.include_router(auth_router, prefix=prefix)
    app.include_router(context_router, prefix=prefix)
    app.include_router(sse_router, prefix=prefix)
    app.include_router(profile_router, prefix=prefix)
    app.include_router(tag_router, prefix=prefix)
    app.include_router(reply_router, prefix=prefix)
    app.include_router(schedule_router, prefix=prefix)
    app.include_router(admin_router, prefix=prefix)
    app.include_router(mock_router, prefix=prefix)

    return app


app = create_app()
