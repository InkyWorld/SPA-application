FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Deps first (cached layer): uv.lock is the single source of truth, no pip.
COPY pyproject.toml uv.lock ./
RUN /uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"

COPY backend/ ./backend/
WORKDIR /app/backend
RUN python manage.py collectstatic --noinput || true

CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
