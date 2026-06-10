FROM python:3.11-slim AS base
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml ./
RUN pip install --upgrade pip hatchling \
    && pip install ".[dev]" 2>/dev/null || pip install .
COPY src ./src
COPY config ./config
RUN pip install --no-deps .
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -fsS http://localhost:8000/healthz || exit 1
CMD ["uvicorn", "tv_list_aggregator.main:app", "--host", "0.0.0.0", "--port", "8000"]
