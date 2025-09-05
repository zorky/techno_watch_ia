# Outil de veille techno

## Environnement

### uv

- création

$ uv venv
$ source .venv/Scripts/activate
$ uv init

**Paquets installés :**

$ uv add langchain-openai langchain-ollama langgraph langchain_community pydantic colorama dotenv feedparser opml
$ uv add ruff --dev

- environnement déjà existant, déjà cloné

$ source .venv/Scripts/activate
$ uv sync --dev

### Prérequis

Ollama doit être lancé, par défaut, il prend le modèle LLM_MODEL du .env

`docker compose -f ollama.yml up -d'

