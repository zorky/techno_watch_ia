import aiohttp
from datetime import datetime, timedelta

import logging
logging.basicConfig(level=logging.INFO)

from core.logger import logger, Fore
from core import measure_time

from services.fetchers.base_fetcher import BaseFetcher
from services.models import Source, SourceType

class BlueskyFetcher(BaseFetcher):
    def __init__(self, handle: str = None, password: str = None):
        """
        Bluesky Fetcher utilisant l'AT Protocol
        API https://docs.bsky.app/docs/category/http-reference
        Args:
            handle: Votre handle Bluesky (optionnel pour lecture publique)
            password: Votre mot de passe/app password (optionnel pour lecture publique)
        """
        from atproto import Client
        self.base_url = "https://bsky.social"
        self.session = None
        self.handle = handle
        self.password = password
        self.AGENT = "TechnoWatch/1.0"

        # Headers pour les requêtes
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": self.AGENT
        }
        self.client = Client()
        self.client.login(self.handle, self.password)        
    
    @measure_time
    def fetch_articles(self, source: Source, max_days: int) -> list[dict]:
        """
        Récupère les posts d'un utilisateur Bluesky ou du feed public
        
        source.url peut être :
        - Un handle utilisateur : "@user.bsky.social" 
        - Un DID : "did:plc:..."
        - "firehose" pour le feed public général
        """
        import aiohttp
        from urllib.parse import quote
        
        articles = []        
        logger.info(f'fetch source {source}')

        try:
            if source.url == "firehose" or source.url.startswith("firehose"):
                # Feed public général
                # articles = self._fetch_public_feed(session, max_days)
                ...
            elif source.url.startswith("@") or source.url.startswith("did:"):
                # Posts d'un utilisateur spécifique                
                articles = self._fetch_user_posts(source.url, max_days)
                ...
            elif "bsky.app/profile/" in source.url:
                # URL profile Bluesky
                handle = source.url.split("/profile/")[-1]
                # articles = self._fetch_user_posts(session, handle, max_days)
                ...
            else:
                logger.error(f"Format d'URL Bluesky non supporté: {source.url}")
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération Bluesky: {e}")

        return articles
    
    def _fetch_public_feed(self, session: aiohttp.ClientSession, max_days: int) -> list[dict]:
        """
        Récupère le feed public Bluesky
        """
        articles = []
        cutoff_date = datetime.now() - timedelta(days=max_days)
        
        # Utilise l'endpoint public feed
        url = f"{self.base_url}/xrpc/app.bsky.feed.getTimeline"
        params = {
            "algorithm": "reverse-chronological",
            "limit": 100
        }
        
        with session.get(url, headers=self.headers, params=params) as response:
            if response.status == 200:
                data = response.json()
                feed_items = data.get("feed", [])
                
                for item in feed_items:
                    post = item.get("post", {})
                    record = post.get("record", {})
                    
                    # Filtrage par date
                    created_at = record.get("createdAt")
                    if created_at:
                        post_date = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                        if post_date.replace(tzinfo=None) > cutoff_date:
                            articles.append(self._format_bluesky_post(post, item))
            
            else:
                print(f"Erreur API Bluesky public feed: {response.status}")
        
        return articles
    
    def _fetch_user_posts(self, user_identifier: str, max_days: int) -> list[dict]:
        """
        Récupère les posts d'un utilisateur spécifique
        """        
        articles = []
        cutoff_date = datetime.now() - timedelta(days=max_days)
        
        # Nettoie l'identifiant utilisateur
        if user_identifier.startswith("@"):
            user_identifier = user_identifier[1:]
        
        logger.info(f"posts user_identifier {user_identifier}")

        data = self.client.get_author_feed(actor=user_identifier, limit=10, filter='posts_no_replies')

        feed_items: list = data.feed 
        logger.info(Fore.CYAN + f"posts de {user_identifier}")        
        logger.info(Fore.CYAN + f"{len(feed_items)}")
        for feed in feed_items:
            post = feed.post
            record = post.record
            created_at = record.created_at
            logger.info(Fore.LIGHTMAGENTA_EX + f"\tpost : {post.author} {created_at}\n")
            
            if created_at:
                post_date = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                if post_date.replace(tzinfo=None) > cutoff_date:
                    logger.info(Fore.LIGHTBLUE_EX + f"\t {type(record)} record : {record}\n")
                    logger.info(Fore.LIGHTBLUE_EX + f"\t record : {record.text} le {created_at}\n")
                    logger.info(Fore.LIGHTGREEN_EX + f"\tembed : {record.embed}\n")
                    formatted_post = self._format_bluesky_post(post, feed)                    
                    articles.append(formatted_post)
        
        for article in articles:
            logger.info(Fore.LIGHTGREEN_EX + f"ARTICLE : {article}")

        return articles
    
    def _format_bluesky_post(self, post, feed_item: dict) -> dict:
        """
        Formate un post Bluesky au format unifié
        """
        record = post.record
        author = post.author
        
        # Contenu principal
        text = record.text
        
        # Gestion des liens/embeds
        embed = record.embed
        if embed:
            # if embed.get("$type") == "app.bsky.embed.external":
            if embed.py_type == "app.bsky.embed.external":
                external = embed.external
                if external.title:
                    text += f"\n\n🔗 {external.title}"
                if external.description:
                    text += f"\n{external.description}"
            elif embed.py_type == "app.bsky.embed.images":
                images = embed.images
                if images:
                    text += f"\n\n🖼️ {len(images)} image(s)"
                    for img in images[:3]:  # Max 3 descriptions
                        if img.alt:
                            text += f"\n- {img.alt}"
        
        # Gestion des réponses/citations
        reply = record.reply
        if reply and reply.parent:
            text = f"↳ Réponse à un post\n\n{text}"
        
        # Construction de l'URL
        post_uri = post.uri
        at_url = ""
        if post_uri:
            # Conversion AT URI vers URL web
            parts = post_uri.replace("at://", "").split("/")
            if len(parts) >= 3:
                did, collection, rkey = parts[0], parts[1], parts[2]
                handle = author.handle or did
                at_url = f"https://bsky.app/profile/{handle}/post/{rkey}"
        
        """
        {
                    "title": title,
                    "summary": summary,
                    "link": link,
                    "published": published_time.isoformat() if published_time else None,
                    "score": "0 %",
                    "source": SourceType.RSS,
                }
        """
        # format created_at : 2025-09-23T15:31:04.446738146Z
        logger.info(Fore.RED + f"record created_at {record.created_at}")
                
        published_parsed = datetime.fromisoformat(record.created_at.replace('Z', '+00:00')).timetuple()     
        logger.info(Fore.RED + f"{published_parsed}")           
        published = datetime(*published_parsed[:6])
          
        logger.info(Fore.LIGHTYELLOW_EX + f"{record.created_at} -> {published} - {published.isoformat()}")     

        return {
            'title': text[:100] + "..." if len(text) > 100 else text,  # Titre = début du texte            
            'summary': text,
            'link': at_url,
            'published': published.isoformat(),
            'source_type': "bluesky",
            'source_name': f"@{author.handle or 'unknown'}",
            'author': author.display_name or (author.handle or "Unknown"),
            'likes': post.like_count or 0,
            'reposts': post.repost_count or 0,
            'replies': post.reply_count or 0,
            'score': "0 %",
            'source': SourceType.BLUESKY
        }