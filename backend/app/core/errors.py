from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    def __init__(
        self,
        code: int,
        message: str,
        data: Any = None,
        http_status: int = 400,
    ) -> None:
        self.code = code
        self.message = message
        self.data = data
        self.http_status = http_status
        super().__init__(message)


class ErrorCode:
    OK = 0
    PARAM = 40001
    UNAUTHORIZED = 40101
    FORBIDDEN = 40301
    NOT_FOUND = 40401
    CONFLICT = 40901
    INTERNAL = 50001
    AI_FAILED = 50002


def ok(data: Any = None, message: str = "ok") -> dict[str, Any]:
    return {"code": ErrorCode.OK, "message": message, "data": data}


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.http_status,
        content={"code": exc.code, "message": exc.message, "data": exc.data},
    )


async def http_exception_handler(
    _: Request, exc: StarletteHTTPException
) -> JSONResponse:
    code = ErrorCode.UNAUTHORIZED if exc.status_code == 401 else ErrorCode.INTERNAL
    if exc.status_code == 403:
        code = ErrorCode.FORBIDDEN
    elif exc.status_code == 404:
        code = ErrorCode.NOT_FOUND
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": code, "message": str(exc.detail), "data": None},
    )


async def validation_exception_handler(
    _: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "code": ErrorCode.PARAM,
            "message": "参数错误",
            "data": exc.errors(),
        },
    )
