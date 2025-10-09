# Images docker

## Interface Web

Cette interface affiche les résumés ayant étaient réalisés.
Une recherche plein texte est disponible.

A **partir de la racine du projet**, pour utiliser `web.yml`

```bash
$ docker compose -f web.yml build
```

Lancement du container FastAPI

```bash
$ docker compose -f web.yml up
```

L'application Web est accessible par http://127.0.0.1:8000/
