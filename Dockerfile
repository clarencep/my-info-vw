# Stage 1: dependencies
FROM python:3.13-slim AS deps

RUN pip install --no-cache-dir uv

WORKDIR /app

# Copy dependency manifests first for better layer caching
COPY pyproject.toml uv.lock ./

# Install production dependencies only
RUN uv sync --frozen --no-dev --no-install-project

# Stage 2: runtime
FROM python:3.13-slim AS runtime

WORKDIR /app

# Copy virtual environment from deps stage
COPY --from=deps /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy application source
COPY src/ ./src/
COPY config/ ./config/
COPY info-check.py info-check.sh ./

# Ensure entry point is executable
RUN chmod +x info-check.sh

# Runtime environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Default config directory (override with MY_INFO_VW_CONFIG_DIR)
ENV MY_INFO_VW_CONFIG_DIR=/app/config

ENTRYPOINT ["./info-check.sh"]
