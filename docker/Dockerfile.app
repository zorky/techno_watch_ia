# Dockerfile pour l'application CLI techno_watch_ia
#
# par le cli docker : docker build -f docker/Dockerfile.app -t techno-watch-ia:latest .
# par le compose : docker compose -f techno-watch.yml build
#
# run par le cli :
# docker run --env-file .env techno-watch-ia:latest
# docker run --env-file .env -v $(pwd)/data:/app/data -w /app techno-watch-ia:latest
# run par le compose :
# docker compose -f techno-watch.yml run app
# 
# entrer dans le container en surchargeant l'entrypoint mis dans le Dockerfile :
# docker compose -f techno-watch.yml run --rm --entrypoint bash app
# docker run --rm -it --entrypoint bash techno-watch-ia -v ./data:/app/data

FROM python:3.11-slim AS builder

# Variables d'environnement pour Python et uv
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_SYSTEM_PYTHON=1

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock* ./

RUN uv sync --frozen --no-dev

# Stage 2: Runtime
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY app/ ./app/

ENV PATH="/app/.venv/bin:$PATH"

VOLUME ["/app/data"]

ENTRYPOINT ["python", "-m", "app"]

CMD []