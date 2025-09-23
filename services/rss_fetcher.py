import feedparser
from datetime import datetime, timedelta
import logging

from services.base_fetcher import BaseFetcher
from services.models import Source

logging.basicConfig(level=logging.INFO)
from core.logger import logger, Fore

class RSSFetcher(BaseFetcher):
    def get_summary(self, entry: dict):
        """
        Affiche le résumé ou le contenu d'une entrée de flux RSS ou Atom
        RSS 2.0: 'summary'
        Atom: 'content'

        Args:
            entry: Une entrée de flux RSS/Atom.
        """
        if "content" in entry.keys():
            content: list[feedparser.FeedParserDict] = entry.get("content", [dict])
            return content[0].get("value", "Pas de résumé")
        
        return entry.get("summary", "Pas de résumé")

    def strip_html(self, text: str) -> str:
        """Supprime les balises HTML d'un texte pour n'avoir que du texte brut."""
        from bs4 import BeautifulSoup
        return BeautifulSoup(text, "html.parser").get_text()
    
    def add_article_with_entry_syndication(self, entry, articles, cutoff_date, recent_in_feed):
        """
        A partir du contenu d'une entrée entry, ajoute un article récent à la liste des articles à traiter.

        Args:
            entry: Un article du flux RSS/Atom.
            articles: La liste des articles à traiter.
            cutoff_date: La date limite pour qu'un article soit considéré comme récent.
            recent_in_feed: Le compteur d'articles récents dans le flux actuel.
        """
        # Récupération de la date de publication (priorité à published, sinon updated)
        published_time = None
        if hasattr(entry, "published_parsed"):
            published_time = datetime(*entry.published_parsed[:6])
        elif hasattr(entry, "updated_parsed"):
            published_time = datetime(*entry.updated_parsed[:6])

        # Vérification de la date
        is_recent = published_time and (published_time >= cutoff_date)
        logger.debug(
            f"Article: {getattr(entry, 'title', 'Sans titre')} "
            f"(publié le {published_time}) : {'récent' if is_recent else 'trop ancien' if published_time else 'date inconnue'}"
        )

        if is_recent:
            # Normalisation des champs (RSS/Atom)
            title = getattr(entry, "title", "Sans titre")
            summary = self.get_summary(entry)
            summary = self.strip_html(summary)  # Nettoyage du HTML
            logger.debug(f"Résumé brut (après nettoyage) : {summary}")
            link = getattr(entry, "link", "#")
            if isinstance(link, list):  # Cas Atom où link est un objet
                link = link[0].href if link else "#"
            logger.info(Fore.GREEN + f"🆕 Article récent : {title} ({link})")
            articles.append(
                {
                    "title": title,
                    "summary": summary,
                    "link": link,
                    "published": published_time.isoformat() if published_time else None,
                    "score": "0 %"
                }
            )
            recent_in_feed += 1
        return recent_in_feed


    async def fetch_articles(self, source: Source, max_age_days: int) -> list[dict]:
        """Votre logique RSS existante"""
        AGENT = "ReaderRSS/1.0"
        RESOLVE_RELATIVE_URIS = False
        SANITIZE_HTML = True
        articles = []
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        logger.info(f"seuil date : {cutoff_date}")

        # for url in rss_urls:
        logger.info(Fore.BLUE + f"Lecture du flux RSS : {url}")
        feed = feedparser.parse(
            source.url,
            resolve_relative_uris=RESOLVE_RELATIVE_URIS,
            sanitize_html=SANITIZE_HTML,
            agent=AGENT,
        )  # voir Etag et modified pour ne pas tout recharger
        recent_in_feed = 0

        for entry in feed.entries:
            recent_in_feed = self.add_article_with_entry_syndication(
                entry, articles, cutoff_date, recent_in_feed
            )

        logger.info(
            f"{len(feed.entries)} articles trouvés dans ce flux, {recent_in_feed} récents !"
        )

        logger.debug(f"{len(articles)} articles récents récupérés")
        return articles
    
        feed = feedparser.parse(source.url)
        articles = []
        
        cutoff_date = datetime.now() - timedelta(days=max_days)
        
        for entry in feed.entries:
            # Logique existante adaptée
            pub_date = datetime.fromtimestamp(entry.published_parsed)
            if pub_date > cutoff_date:
                articles.append({
                    'title': entry.title,
                    'content': entry.summary,
                    'link': entry.link,
                    'published': pub_date.isoformat(),
                    'source_type': 'rss',
                    'source_name': source.name or feed.feed.title
                })
        
        return articles