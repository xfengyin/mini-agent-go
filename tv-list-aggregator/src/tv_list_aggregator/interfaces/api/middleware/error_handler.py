"""全局错误处理中间件：领域异常 -> 4xx，未知 -> 500。

修复 issue #11：返回 RFC 7807 (problem+json) 格式 + request_id。
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from ....core.exceptions import PermanentError, TransientError, TVListBaseError
from ....core.logging import get_logger

log = get_logger(__name__)


def _problem(
    *,
    request: Request,
    status_code: int,
    title: str,
    detail: str,
    type_uri: str = "about:blank",
    extra: dict[str, Any] | None = None,
) -> JSONResponse:
    """构造 RFC 7807 problem+json 响应（含 request_id）。"""
    rid = getattr(request.state, "request_id", None) or "unknown"
    body: dict[str, Any] = {
        "type": type_uri,
        "title": title,
        "status": status_code,
        "detail": detail,
        "instance": str(request.url.path),
        "request_id": rid,
    }
    if extra:
        body.update(extra)
    return JSONResponse(
        body, status_code=status_code, headers={"x-request-id": rid}
    )


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        try:
            return await call_next(request)
        except TransientError as e:
            log.warning("api.transient_error", error=str(e), path=request.url.path)
            return _problem(
                request=request,
                status_code=503,
                title="Service Unavailable",
                detail=str(e),
                type_uri="/problems/transient-error",
                extra={"retryable": True, "error": type(e).__name__},
            )
        except PermanentError as e:
            log.warning("api.permanent_error", error=str(e), path=request.url.path)
            return _problem(
                request=request,
                status_code=400,
                title="Bad Request",
                detail=str(e),
                type_uri="/problems/permanent-error",
                extra={"retryable": False, "error": type(e).__name__},
            )
        except TVListBaseError as e:
            log.warning("api.domain_error", error=str(e), path=request.url.path)
            return _problem(
                request=request,
                status_code=400,
                title="Domain Error",
                detail=str(e),
                type_uri="/problems/domain-error",
                extra={"error": type(e).__name__},
            )
        # 内置异常 -> 标准 HTTP 状态码：避免 500 暴露实现细节，
        # 同时让客户端能用语义化状态码做统一处理。
        # 必须放在 TVListBaseError 之后，否则子类会被基类分支抢走。
        except ValueError as e:
            log.warning("api.value_error", error=str(e), path=request.url.path)
            return _problem(
                request=request,
                status_code=400,
                title="Bad Request",
                detail=str(e) or "invalid value",
                type_uri="/problems/value-error",
                extra={"error": type(e).__name__},
            )
        except PermissionError as e:
            log.warning("api.permission_error", error=str(e), path=request.url.path)
            return _problem(
                request=request,
                status_code=403,
                title="Forbidden",
                detail=str(e) or "permission denied",
                type_uri="/problems/permission-error",
                extra={"error": type(e).__name__},
            )
        except KeyError as e:
            # KeyError 默认 repr 带引号（"'foo'"），仅取 key 字符串
            key_name = e.args[0] if e.args else ""
            detail = f"key not found: {key_name}" if key_name else "key not found"
            log.warning("api.key_error", error=detail, path=request.url.path)
            return _problem(
                request=request,
                status_code=404,
                title="Not Found",
                detail=detail,
                type_uri="/problems/key-error",
                extra={"error": type(e).__name__},
            )
        except Exception as e:  # noqa: BLE001
            log.error(
                "api.unhandled_error",
                path=request.url.path,
                error=str(e),
                exc_info=True,
            )
            # 在非生产环境返回真实错误以便排查
            from ....core.settings import get_settings as _gs

            if _gs().app_env != "production":
                return _problem(
                    request=request,
                    status_code=500,
                    title="Internal Server Error",
                    detail=f"{type(e).__name__}: {e}",
                    type_uri="/problems/internal-error",
                )
            return _problem(
                request=request,
                status_code=500,
                title="Internal Server Error",
                detail="internal error",
                type_uri="/problems/internal-error",
            )
