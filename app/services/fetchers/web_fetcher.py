#########################################################
# Fetcher pour les sites web génériques (blogs, changelogs, bulletins de sécurité)
# - Extraction adaptative selon le type de contenu (article unique, liste, CVE, etc.)
# - Détection de changements pour éviter les doublons
# - Nettoyage du contenu pour améliorer la qualité des résumés
# - Utilisation de trafilatura en fallback pour les pages difficiles à parser
# 
# Exemples de sources à tester :
#  https://archives-cert.univ-amu.fr/courant/index.html
#  https://kubernetes.io/docs/setup/release/notes/
#  https://www.nginx.com/blog/
#
# Claude : https://claude.ai/chat/0dd0c328-fd66-4944-9d94-7ca49977e5e1
# Mistral : https://chat.mistral.ai/chat/9ad499e7-d4ed-490e-b11e-75d5001723a9
#########################################################

import hashlib
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from pathlib import Path
import json

import logging
logging.basicConfig(level=logging.INFO)

from app.core.logger import logger, Fore
from app.core import measure_time

from app.services.decorators import fetcher_class
from app.services.fetchers.base_fetcher import BaseFetcher
from app.services.models import Source, SourceType
from app.core.logger import print_color

CACHE_CRAWL = False  # Activer le cache pour les pages web afin de détecter les changements

@fetcher_class
class WebFetcher(BaseFetcher):
    source_type = SourceType.WEB.value
    env_flag = "WEB_FETCH"

    def __init__(self):
        super().__init__()
        self.cache_dir = Path("data/web_cache")
        self.cache_dir.mkdir(exist_ok=True)

    def _get_page_hash(self, content: str) -> str:
        """Génère un hash du contenu pour détecter les changements."""
        return hashlib.md5(content.encode()).hexdigest()
    
    def _has_changed(self, url: str, content: str) -> bool:
        """Vérifie si la page a changé depuis la dernière visite."""

        if not CACHE_CRAWL:
            return True
        
        cache_file = self.cache_dir / f"{hashlib.md5(url.encode()).hexdigest()}.json"
        current_hash = self._get_page_hash(content)
        
        if cache_file.exists():
            with open(cache_file) as f:
                cached_data = json.load(f)
                if cached_data.get('hash') == current_hash:
                    logger.info(f"Aucun changement détecté pour {url}")
                    return False
        
        # Sauvegarder le nouveau hash
        with open(cache_file, 'w') as f:
            json.dump({
                'hash': current_hash,
                'last_check': datetime.now().isoformat(),
                'url': url
            }, f)
        
        return True
            
    def _extract_with_trafilatura(self, url: str) -> dict:
        """Utilise trafilatura pour extraire le contenu."""
        import trafilatura
        import json
        downloaded = trafilatura.fetch_url(url)
        
        # Extraction du texte principal
        text = trafilatura.extract(downloaded, 
                                    include_links=True,
                                    include_tables=True,
                                    output_format='json')
        
        if text:
            data = json.loads(text)
            return {
                "title": data.get('title', 'Sans titre'),
                "summary": data.get('text', '')[:500],
                "link": url,
                "published": data.get('date', datetime.now().isoformat()),
                "source": SourceType.WEB,
            }
        return None
    
    def _is_cve_page(self, soup: BeautifulSoup) -> bool:
        """Détecte si c'est une page de liste CVE."""
        text = soup.get_text()
        cve_count = len(re.findall(r'CVE-\d{4}-\d{4,}', text))
        return cve_count > 3  # Si plus de 3 CVE, c'est probablement une liste

    def _extract_article_links(self, soup: BeautifulSoup, base_url: str) -> list[str]:
        """Extrait les liens vers des articles depuis une page index."""
        from urllib.parse import urljoin, urlparse
        links = set()
        
        # Chercher les liens dans les zones de contenu
        for link in soup.find_all('a', href=True):
            href = link['href']
            
            # Filtrer les liens de navigation/footer
            if any(skip in href.lower() for skip in ['#', 'javascript:', 'mailto:', '/tag/', '/category/']):
                continue
            
            # Construire l'URL absolue
            from urllib.parse import urljoin
            full_url = urljoin(base_url, href)
            
            # Vérifier que c'est du même domaine
            if urlparse(full_url).netloc == urlparse(base_url).netloc:
                links.add(full_url)
        
        return list(links)[:20]  # Limiter à 20 articles max

    def _extract_article_info(self, url: str, soup: BeautifulSoup) -> dict:
        """
        Extrait les informations d'article d'une page web.
        
        Args:
            url: URL de la page
            soup: Objet BeautifulSoup de la page
            
        Returns:
            dict: Informations de l'article
        """
        print_color(Fore.MAGENTA, f"Extraction des informations de l'article depuis {url}   ")
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
        content = self._clean_content(content)
        
        return {
            "title": title,
            "summary": content[:500] + "..." if len(content) > 500 else content,
            "link": url,
            "published": datetime.now().isoformat(),  # Date actuelle par défaut
            "source": SourceType.WEB,
        }

    def _clean_content(self, text: str) -> str:
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

    def _is_valid_url(self, url: str) -> bool:
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

    def _detect_content_type(self, soup: BeautifulSoup, url: str) -> str:
        """Détecte le type de contenu de la page."""
        text = soup.get_text()
        
        # CVE/Security advisories
        if re.search(r'CVE-\d{4}-\d{4,}', text) or \
           any(keyword in text.lower() for keyword in ['security advisory', 'vulnerability', 'patch']):
            return 'security_bulletin'
        
        # Changelog/Release notes
        if any(keyword in text.lower() for keyword in ['changelog', 'release notes', 'version', 'what\'s new']):
            return 'changelog'
        
        # Blog article
        if soup.find('article') or soup.find(class_=re.compile(r'post|article|entry')):
            return 'article'
        
        # Liste/Index
        if len(soup.find_all(['ul', 'ol', 'table'])) > 3:
            return 'list'
        
        return 'generic'
    
    def _extract_structured_items(self, soup: BeautifulSoup, url: str) -> list[dict]:
        """Extrait des items structurés (pour listes, bulletins, etc.)."""
        articles = []
        
        # Chercher des patterns de listes
        containers = soup.find_all(['li', 'tr', 'div'], class_=re.compile(r'item|entry|row'))
        
        if not containers:
            # Fallback: chercher toutes les listes
            for ul in soup.find_all(['ul', 'ol']):
                containers.extend(ul.find_all('li'))
            
            # Tables
            for table in soup.find_all('table'):
                containers.extend(table.find_all('tr')[1:])  # Skip header
        
        for idx, container in enumerate(containers[:50]):  # Limite à 50 items
            text = container.get_text(strip=True)
            
            if len(text) < 10:  # Ignorer les entrées trop courtes
                continue
            
            # Chercher un lien
            link_tag = container.find('a', href=True)
            item_link = link_tag['href'] if link_tag else f"{url}#item-{idx}"
            if link_tag and not item_link.startswith('http'):
                from urllib.parse import urljoin
                item_link = urljoin(url, item_link)
            
            # Extraire une date si possible
            date_match = re.search(r'\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}', text)
            published = date_match.group(0) if date_match else datetime.now().isoformat()
            
            # Titre: première ligne ou texte tronqué
            title = text.split('\n')[0][:100]
            
            articles.append({
                "title": title,
                "link": item_link,
                "summary": text[:500],
                "score": "0",
                "published": published,
                "source": SourceType.WEB,
            })
        
        return articles
    
    def extract_single_article(self, soup: BeautifulSoup, url: str) -> dict:
        """Extrait une page comme un article unique."""
        title = soup.title.string if soup.title else url.split('/')[-1]
        
        # Chercher le contenu principal
        main_content = None
        for selector in ['article', 'main', '[role="main"]', '.content', '#content']:
            main_content = soup.select_one(selector)
            if main_content:
                break
        
        if not main_content:
            main_content = soup.body
        
        content = main_content.get_text(separator="\n", strip=True) if main_content else ""
        content = self._clean_content(content)
        
        # Extraire date de publication
        published = datetime.now().isoformat()
        for meta in soup.find_all('meta'):
            if meta.get('property') in ['article:published_time', 'datePublished'] or \
               meta.get('name') in ['publish-date', 'date']:
                published = meta.get('content', published)
                break
        
        return {
            "title": title,
            "summary": content[:500] + "..." if len(content) > 500 else content,
            "link": url,
            "published": published,
            "source": SourceType.WEB,
        }
    
    @measure_time
    def fetch_articles(self, source: Source, max_days: int) -> list[dict]:
        """Récupère les articles avec stratégie adaptative."""
        articles = []        

        color = Fore.LIGHTYELLOW_EX
        print_color(color, "=" * 60)
        print_color(color, f"WEB Fetcher fetch_articles {source.url}")
        print_color(color, "=" * 60)
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; TechWatchBot/1.0)',
                'Accept': 'text/html,application/xhtml+xml',
            }
            
            response = requests.get(source.url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Vérifier si la page a changé
            if not self._has_changed(source.url, response.text):
                logger.info(f"Page inchangée, pas de nouveaux articles: {source.url}")
                return articles
            
            soup = BeautifulSoup(response.text, 'html.parser')
            content_type = self._detect_content_type(soup, source.url)
            
            logger.info(f"Type de contenu détecté: {content_type}")
            
            # Stratégie selon le type
            if content_type in ['security_bulletin', 'changelog', 'list']:
                articles = self._extract_structured_items(soup, source.url)
            else:
                # Article unique
                article = self._extract_single_article(soup, source.url)
                articles = [article]
            
            logger.info(f"✅ {len(articles)} article(s) extrait(s) de {source.url}")
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la récupération de {source.url}: {e}")
        
        return articles
    
    # @measure_time
    # def fetch_articles(self, source: Source, max_days: int) -> list[dict]:
    #     """
    #     Récupère les articles depuis une URL web.
        
    #     Args:
    #         source: Source contenant l'URL à crawler
    #         max_days: Nombre maximum de jours pour considérer un article comme récent
            
    #     Returns:
    #         list[dict]: Liste des articles récupérés
    #     """
    #     articles = []
    #     cutoff_date = datetime.now() - timedelta(days=max_days)
        
    #     logger.info(
    #         Fore.BLUE
    #         + f"Fetch posts WEB de l'URL {source.url} depuis {max_days} jours -> {cutoff_date}"
    #     )
        
    #     color = Fore.LIGHTYELLOW_EX
    #     print_color(color, "=" * 60)
    #     print_color(color, f"WEB Fetcher fetch_articles {source.url}")
    #     print_color(color, "=" * 60)
        
    #     if not self._is_valid_url(source.url):
    #         logger.warning(f"URL {source.url} invalide ou inaccessible, ignorée")
    #         return articles
        
    #     try:
    #         # Configuration de la requête
    #         headers = {
    #             'User-Agent': 'TechnoWatchWebFetcher/1.0',
    #             'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    #             # 'Accept-Language': 'en-US,en;q=0.5',
    #         }
            
    #         response = requests.get(source.url, headers=headers, timeout=30)
    #         response.raise_for_status()
            
    #         # Analyse du contenu HTML
    #         soup = BeautifulSoup(response.text, 'html.parser')
            
    #         # Extraction des informations de l'article
    #         article_info = self._extract_article_info(source.url, soup)
    #         extract_with_trafilatura = self._extract_with_trafilatura(source.url)
    #         if extract_with_trafilatura:
    #             print_color(Fore.GREEN, f"Extraction avec trafilatura réussie pour {source.url} : {extract_with_trafilatura}")
    #             # article_info = extract_with_trafilatura
            
    #         # Vérification de la date (utilisation de la date actuelle comme proxy)
    #         published_time = datetime.now()
    #         is_recent = published_time >= cutoff_date
            
    #         logger.debug(
    #             f"Article: {article_info['title']} "
    #             f"(publié le {published_time}) : {'récent' if is_recent else 'trop ancien'}"
    #         )
            
    #         if is_recent:
    #             logger.info(Fore.GREEN + f"🆕 Article récent : {article_info['title']} ({source.url})")
    #             articles.append(article_info)
    #         else:
    #             logger.info(Fore.YELLOW + f"⏳ Article trop ancien : {article_info['title']}")
                
    #     except Exception as e:
    #         logger.error(f"Erreur lors de la récupération de {source.url}: {e}")
        
    #     logger.debug(Fore.CYAN + f"{len(articles)} articles récents récupérés")
    #     return articles