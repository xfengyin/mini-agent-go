"""应用启动入口。"""
from __future__ import annotations

import uvicorn

from tv_list_aggregator.interfaces.api.app import app


def main() -> None:
    """uvicorn 入口。"""
    uvicorn.run(app, host="0.0.0.0", port=8000, log_config=None)  # noqa: S104


if __name__ == "__main__":
    main()
