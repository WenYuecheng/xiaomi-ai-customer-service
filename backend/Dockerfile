FROM ghcr.io/astral-sh/uv:0.11.2 AS uv
FROM python:3.11.9-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

COPY --from=uv /uv /usr/local/bin/uv
RUN groupadd --system app && useradd --system --gid app --home-dir /app app
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-cache
COPY backend/app ./app
COPY backend/alembic ./alembic
COPY backend/alembic.ini ./alembic.ini
RUN mkdir -p /data/uploads /data/chroma /data/models && chown -R app:app /app /data
USER app
EXPOSE 8000
CMD ["sh", "-c", "python -m app.commands init-demo && fastapi run app/main.py --host 0.0.0.0 --port 8000"]

