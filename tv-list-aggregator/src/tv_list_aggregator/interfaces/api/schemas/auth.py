"""Auth DTO：token 刷新、登录等响应模型。"""
from __future__ import annotations

from pydantic import BaseModel


class RefreshOut(BaseModel):
    """POST /auth/refresh 响应：返回新签发的 access_token。

    设计原则：不返回密码、hash 等敏感信息；
    与 /auth/token 保持一致：仅暴露 access_token + token_type。
    """

    access_token: str
    token_type: str = "bearer"  # noqa: S105
