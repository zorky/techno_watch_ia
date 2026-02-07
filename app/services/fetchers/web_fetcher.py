import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)

from app.core.logger import logger, Fore
from app.core import measure_time

from app.services.decorators import fetcher_class
from app.services.fetchers.base_fetcher import BaseFetcher
from app.services.models import Source, SourceType
from app.core.logger import print_color


@fetcher_class
class WebFetcher(BaseFetcher):
    source_type = SourceType.WEB.value
    env_flag = "WEB_FETCH"

    def extract_article_info(self, url: str, soup: BeautifulSoup) -> dict:
        """
        Extrait les informations d'article d'une page web.
        
        Args:
            url: URL de la page
            soup: Objet BeautifulSoup de la page
            
        Returns:
            dict: Informations de l'article
        """
        # Extraction du titre
        title = soup.title.string if soup.title else "Sans titre"
        
        # Extraction du contenu principal - stratégie multiple
        content = ""
        
        # Stratégie 1: Chercher les balises article/main
        article_tag = soup.find(['article', 'main'])
        if article_tag:
            content = article_tag.get_text(separator="\n", strip=True)
        else:
            # Stratégie 2: Chercher les paragraphes
            paragraphs = soup.find_all('p')
            if paragraphs:
                content = "\n".join([p.get_text(strip=True) for p in paragraphs])
            else:
                # Stratégie 3: Prendre tout le body
                content = soup.body.get_text(separator="\n", strip=True) if soup.body else ""
        
        # Nettoyage du contenu
        content = self.clean_content(content)
        
        return {
            "title": title,
            "summary": content[:500] + "..." if len(content) > 500 else content,
            "link": url,
            "published": datetime.now().isoformat(),  # Date actuelle par défaut
            "source": SourceType.WEB,
        }

    def clean_content(self, text: str) -> str:
        """
        Nettoie le contenu extrait en supprimant les éléments indésirables.
        
        Args:
            text: Texte à nettoyer
            
        Returns:
            str: Texte nettoyé
        """
        # Supprimer les lignes vides excessives
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        cleaned = '\n'.join(lines)
        
        # Supprimer les espaces multiples
        cleaned = ' '.join(cleaned.split())
        
        return cleaned

    def is_valid_url(self, url: str) -> bool:
        """
        Vérifie si une URL est valide et accessible.
        
        Args:
            url: URL à vérifier
            
        Returns:
            bool: True si l'URL est valide et accessible
        """
        try:
            response = requests.head(url, timeout=10, allow_redirects=True)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"URL invalide ou inaccessible {url}: {e}")
            return False

    @measure_time
    def fetch_articles(self, source: Source, max_days: int) -> list[dict]:
        """
        Récupère les articles depuis une URL web.
        
        Args:
            source: Source contenant l'URL à crawler
            max_days: Nombre maximum de jours pour considérer un article comme récent
            
        Returns:
            list[dict]: Liste des articles récupérés
        """
        articles = []
        cutoff_date = datetime.now() - timedelta(days=max_days)
        
        logger.info(
            Fore.BLUE
            + f"Fetch posts WEB de l'URL {source.url} depuis {max_days} jours -> {cutoff_date}"
        )
        
        color = Fore.LIGHTYELLOW_EX
        print_color(color, "=" * 60)
        print_color(color, f"WEB Fetcher fetch_articles {source.url}")
        print_color(color, "=" * 60)
        
        if not self.is_valid_url(source.url):
            logger.warning(f"URL {source.url} invalide ou inaccessible, ignorée")
            return articles
        
        try:
            # Configuration de la requête
            headers = {
                'User-Agent': 'TechnoWatchWebFetcher/1.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            }
            
            response = requests.get(source.url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Analyse du contenu HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extraction des informations de l'article
            article_info = self.extract_article_info(source.url, soup)
            
            # Vérification de la date (utilisation de la date actuelle comme proxy)
            published_time = datetime.now()
            is_recent = published_time >= cutoff_date
            
            logger.debug(
                f"Article: {article_info['title']} "
                f"(publié le {published_time}) : {'récent' if is_recent else 'trop ancien'}"
            )
            
            if is_recent:
                logger.info(Fore.GREEN + f"🆕 Article récent : {article_info['title']} ({source.url})")
                articles.append(article_info)
            else:
                logger.info(Fore.YELLOW + f"⏳ Article trop ancien : {article_info['title']}")
                
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de {source.url}: {e}")
        
        logger.debug(Fore.CYAN + f"{len(articles)} articles récents récupérés")
        return articles