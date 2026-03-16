# --- Stage 1: deps ---
FROM python:3.13-slim AS deps

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# --- Stage 2: runtime ---
FROM python:3.13-slim AS runtime

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY --from=deps /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

COPY src/ src/
COPY info-check.py info-check.sh ./
COPY config/ config/

RUN chmod +x info-check.sh

# The CLI entry-point; override CMD at runtime as needed.
ENTRYPOINT ["./info-check.sh"]
