"""全局错误处理中间件：领域异常 -> 4xx，未知 -> 500。"""
from __future__ import annotations

import traceback

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from ....core.exceptions import PermanentError, TransientError, TVListBaseError
from ....core.logging import get_logger

log = get_logger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except TransientError as e:
            log.warning("api.transient_error", error=str(e), path=request.url.path)
            return JSONResponse(
                {"error": type(e).__name__, "message": str(e), "retryable": True},
                status_code=503,
            )
        except PermanentError as e:
            log.warning("api.permanent_error", error=str(e), path=request.url.path)
            return JSONResponse(
                {"error": type(e).__name__, "message": str(e), "retryable": False},
                status_code=400,
            )
        except TVListBaseError as e:
            log.warning("api.domain_error", error=str(e), path=request.url.path)
            return JSONResponse(
                {"error": type(e).__name__, "message": str(e)}, status_code=400
            )
        except Exception:
            log.error("api.unhandled_error", path=request.url.path, trace=traceback.format_exc())
            return JSONResponse(
                {"error": "InternalServerError", "message": "internal error"},
                status_code=500,
            )
