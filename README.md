# Outil de veille techno

Objectif : développer un agent avec LangGraph qui effectue une veille technologique à l'aide de flux RSS

Process déroulé :

- Lit un OPML contenant les flux RSS / Atom
- Lit les flux RSS / Atom pour obtenir leur contenu
- Indexe le contenu obtenu à l'aide d'une base vectorielle
- Recherche dans le contenu de mots clés (vectorisés) prédéfinis 
- Les articles trouvés sur un seuil prédéfini remontent (scoring avec similartié cosinus)
- Résume les articles filtrés
- Envoi l'ensemble par mail

# Techno Watch Tool

Objective: Develop an agent using LangGraph to perform tech watch using RSS feeds.
Process

- Reads an OPML file containing RSS/Atom feeds
- Fetches and parses the RSS/Atom feed content
- Indexes the content using a vector database
- Searches for predefined (vectorized) keywords in the content
- Retrieves articles that meet a predefined similarity threshold (cosine similarity scoring)
- Summarizes the filtered articles
- Sends the results by email

## Environnement

### uv

- init uv & création

```bash
$ uv venv
$ source .venv/Scripts/activate
$ uv sync --dev
```

- environnement déjà existant & cloné

```
$ source .venv/Scripts/activate # ou source .venv/scripts/activate
$ uv sync --dev
```

/!\ torch avec CUDA 118 est installé pour une utilisation du GPU pour les embeddings, voir selon la config. de la station de travail (Windows / Linux ou Mac) /!\

### Prérequis

- Ollama doit être lancé avant le cli, par défaut, il prend le modèle LLM_MODEL défini dans le `.env`


```bash
$ docker compose -f ollama.yml up -d
```

Le modèle est chargé au moment du lancement du _container_.

- Fichier OPML de flux RSS

Le fichier `my.opml` est conseillé, par défaut il prendra une liste en dur de 3 flux RSS

- Copier le .env.example sur .env puis le configurer 

```
# Configuration LLM et limite inférence
LLM_MODEL=mistral
MAX_TOKENS_GENERATE=200

# Configuration indexation et recherche
FILTER_KEYWORDS=ai agent,genai,artificial intelligence,python,django,cybersecurité,cve
THRESHOLD_SEMANTIC_SEARCH=0.3
LIMIT_ARTICLES_TO_RESUME=10

# Configuration fetch RSS
OPML_FILE=my.opml
MAX_DAYS=20

# Configuration SMTP pour l'envoi du mail de la veille techno
SMTP_SERVER=smtp.domain.ntld
SMTP_PORT=587
SMTP_LOGIN=login
SMTP_PASSWORD=your_password
SENDER=email_from@domain.ntld
SEND_EMAIL_TO=email_to@domain.ntld
```


## Cli

Se résume à un seul script à lancer

```bash
$ python main_agent_rss.py
```

ou pour obtenir plus d'informations 

```bash
$ python main_agent_rss.py --debug
```

## Interface UI pour les articles résumés

```bash
$ uvicorn web:app --reload
```bash

Sur http://127.0.0.1:8000/

## L'automate exécuté 

![Schéma généré](schema-graphe.png)

## Gmail SMTP

Si Google gmail est utilisé pour envoyé le mail des résumé, un mot de passe application doit être créé 

Sinon le login / mot de passe de user@gmail.com provoquera une erreur du type

`smtplib.SMTPAuthenticationError: (534, b'5.7.9 Application-specific password required. For more information, go to\n5.7.9  https://support.google.com/mail/?p=InvalidSecondFactor ffacd0b85a97d-3e8c7375fb7sm2117460f8f.14 - gsmtp')`

> Page d'aide : https://support.google.com/accounts/answer/185833?visit_id=638933697167636567-786859144&p=InvalidSecondFactor&rd=1 

> Configurer un mot de passe application : https://myaccount.google.com/apppasswords 

Ce mot de passe application sera mis dans la variable `SMTP_PASSWORD` du .env

