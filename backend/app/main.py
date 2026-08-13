"""FastAPI 应用入口：中间件、统一异常、路由挂载。"""

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
from app.features.asr.router import router as asr_router
from app.features.mock.router import router as mock_router
from app.features.profile.router import router as profile_router
from app.features.reply.router import router as reply_router
from app.features.schedule.router import router as schedule_router
from app.features.tag.router import router as tag_router
from app.features.wecom.context_router import router as context_router
from app.features.wecom.messages_router import router as messages_router
from app.features.wecom.router import router as auth_router
from app.features.wecom.sse_router import router as sse_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    """应用生命周期钩子（当前无启动/关闭副作用）。"""
    yield


def create_app() -> FastAPI:
    """组装并返回 FastAPI 实例。"""
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # type: ignore — pyright 与 Starlette ExceptionHandler 签名逆变不兼容（运行时正常）
    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]

    prefix = settings.api_prefix

    @app.get("/health")
    async def health():
        """健康检查，附带 mock/LLM/ASR/日历能力态便于侧栏能力条对齐。"""
        settings = get_settings()
        calendar_ready = bool(
            not settings.mock_wecom
            and settings.wecom_corp_id
            and settings.wecom_secret
        )
        asr = (settings.asr_provider or "fake").strip().lower()
        return ok(
            {
                "service": settings.app_name,
                "mock_wecom": settings.mock_wecom,
                "mock_llm": settings.mock_llm,
                "llm_provider": settings.llm_provider,
                "asr_provider": asr,
                "calendar_mode": "ready" if calendar_ready else "degraded",
                "calendar_hint": (
                    "可尝试同步企微日历"
                    if calendar_ready
                    else "企微日历未接入（Mock 或缺 corp/secret），同步将降级"
                ),
            }
        )

    @app.get(f"{prefix}/hello")
    async def hello():
        """探活示例接口。"""
        return ok({"hello": "K12-UserProfile", "phase": "mvp"})

    # 侧边栏 / 企微 / 管理后台 / Mock 联调
    app.include_router(auth_router, prefix=prefix)
    app.include_router(context_router, prefix=prefix)
    app.include_router(messages_router, prefix=prefix)
    app.include_router(sse_router, prefix=prefix)
    app.include_router(profile_router, prefix=prefix)
    app.include_router(tag_router, prefix=prefix)
    app.include_router(reply_router, prefix=prefix)
    app.include_router(asr_router, prefix=prefix)
    app.include_router(schedule_router, prefix=prefix)
    app.include_router(admin_router, prefix=prefix)
    app.include_router(mock_router, prefix=prefix)

    return app


app = create_app()
