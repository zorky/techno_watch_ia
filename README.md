# Outil de veille techno

## Environnement

### uv

- init uv & création

$ uv venv
$ source .venv/Scripts/activate
$ uv sync --dev
$ uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

- environnement déjà existant & cloné

$ source .venv/Scripts/activate
$ uv sync --dev
$ uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

### Prérequis

Ollama doit être lancé, par défaut, il prend le modèle LLM_MODEL du .env

`docker compose -f ollama.yml up -d'

### torch GPU

https://docs.astral.sh/uv/guides/integration/pytorch/#using-uv-with-pytorch : avec le pyproject.toml et cu118 : ne fonctionne pas

Obligé d'utiliser pip install pour la version CUDA de Torch :

$ uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118