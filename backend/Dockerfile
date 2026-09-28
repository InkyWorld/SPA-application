FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Deps first (cached layer): uv.lock is the single source of truth, no pip.
COPY pyproject.toml uv.lock ./
RUN /uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"

COPY backend/ ./backend/
WORKDIR /app/backend
RUN python manage.py collectstatic --noinput

FROM python:3.12-slim AS runtime

WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

RUN groupadd --system app \
	&& useradd --system --gid app --home-dir /app --shell /usr/sbin/nologin appuser

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/backend /app/backend
RUN sed -i 's/\r$//' /app/backend/entrypoint.sh \
	&& chmod +x /app/backend/entrypoint.sh \
	&& chown -R appuser:app /app

USER appuser
WORKDIR /app/backend
ENTRYPOINT ["/app/backend/entrypoint.sh"]
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
