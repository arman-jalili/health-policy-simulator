# syntax=docker/dockerfile:1.7
# Backend image: FastAPI + Alembic, PostgreSQL, PyMuPDF and a Tesseract stack for scanned corpora.
# Build context is ``backend/`` (see ../compose.yaml).

FROM python:3.12-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Dependency layer first: pyproject + lock change rarely, source changes often.
COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY src ./src
COPY migrations ./migrations
COPY alembic.ini ./
COPY config ./config
COPY samples ./samples
COPY scripts ./scripts
COPY docker ./docker
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev


FROM python:3.12-slim-bookworm AS runtime

# tesseract-ocr + German language data: the OCR adapter shells out to the binary
# (issues #427/#434). Without it, /readyz reports ocr: absent and OCR-routed files fail
# with OCR_UNAVAILABLE — the demo corpus must not depend on the host having it.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      tesseract-ocr tesseract-ocr-deu curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /app /app

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    API_HOST=0.0.0.0 \
    API_PORT=8000

RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin hps \
 && chown -R hps:hps /app
USER hps

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=25s --retries=6 \
    CMD curl -fsS "http://127.0.0.1:${API_PORT}/healthz" >/dev/null || exit 1

ENTRYPOINT ["/app/docker/entrypoint.sh"]
