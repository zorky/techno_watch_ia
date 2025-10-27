# Dockerfile pour l'application CLI techno_watch_ia
# docker build -f docker/Dockerfile.app -t techno-watch-ia:latest .
# docker run --env-file .env techno-watch-ia:latest
FROM python:3.11-slim

# Variables d'environnement pour Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # Configuration uv
    UV_SYSTEM_PYTHON=1

# Installation de uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Répertoire de travail
WORKDIR /app

# Copie des fichiers de dépendances
COPY pyproject.toml ./
COPY uv.lock* ./

# Installation des dépendances avec uv
RUN uv sync --frozen --no-dev

# Copie du code source
COPY app/ ./app/
# COPY tests/ ./tests/

# Point d'entrée pour lancer l'application
ENTRYPOINT ["python", "-m", "app"]

# Arguments par défaut (peuvent être surchargés)
CMD []