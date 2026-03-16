# ── Stage 1: dependencies ────────────────────────────────────────────
FROM python:3.13-slim AS deps

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# ── Stage 2: runtime ─────────────────────────────────────────────────
FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY --from=deps /app/.venv /app/.venv
COPY src/ src/
COPY config/ config/
COPY webapp/ webapp/

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    # Config directory (override via MY_INFO_VW_CONFIG_DIR at runtime)
    MY_INFO_VW_CONFIG_DIR=/app/config

# CLI entrypoint
ENTRYPOINT ["python", "-m", "src.cli"]
CMD ["--help"]
