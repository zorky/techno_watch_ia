import aiohttp
from typing import Optional
from datetime import datetime, timedelta

from services.base_fetcher import BaseFetcher
from services.models import Source, SourceType

class BlueskyFetcher(BaseFetcher):
    def __init__(self, handle: str = None, password: str = None):
        """
        Bluesky Fetcher utilisant l'AT Protocol
        
        Args:
            handle: Votre handle Bluesky (optionnel pour lecture publique)
            password: Votre mot de passe/app password (optionnel pour lecture publique)
        """
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
    
    def _authenticate(self) -> Optional[str]:
        """
        Authentification optionnelle pour accès complet
        """
        if not self.handle or not self.password:
            return None
            
        import aiohttp
        
        auth_data = {
            "identifier": self.handle,
            "password": self.password
        }
        
        with aiohttp.ClientSession() as session:
            with session.post(
                f"{self.base_url}/xrpc/com.atproto.server.createSession",
                json=auth_data,
                headers=self.headers
            ) as response:
                if response.status == 200:
                    result = response.json()
                    return result.get("accessJwt")
                else:
                    print(f"Bluesky auth failed: {response.status}")
                    return None
    
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
        cutoff_date = datetime.now() - timedelta(days=max_days)
        
        # Authentification optionnelle
        access_token = self._authenticate()
        if access_token:
            self.headers["Authorization"] = f"Bearer {access_token}"
        
        with aiohttp.ClientSession() as session:
            try:
                if source.url == "firehose" or source.url.startswith("firehose"):
                    # Feed public général
                    articles = self._fetch_public_feed(session, max_days)
                elif source.url.startswith("@") or source.url.startswith("did:"):
                    # Posts d'un utilisateur spécifique
                    articles = self._fetch_user_posts(session, source.url, max_days)
                elif "bsky.app/profile/" in source.url:
                    # URL profile Bluesky
                    handle = source.url.split("/profile/")[-1]
                    articles = self._fetch_user_posts(session, handle, max_days)
                else:
                    print(f"Format d'URL Bluesky non supporté: {source.url}")
                    
            except Exception as e:
                print(f"Erreur lors de la récupération Bluesky: {e}")
        
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
    
    def _fetch_user_posts(self, session: aiohttp.ClientSession, user_identifier: str, max_days: int) -> list[dict]:
        """
        Récupère les posts d'un utilisateur spécifique
        """
        articles = []
        cutoff_date = datetime.now() - timedelta(days=max_days)
        
        # Nettoie l'identifiant utilisateur
        if user_identifier.startswith("@"):
            user_identifier = user_identifier[1:]
        
        # Récupère le profil pour obtenir le DID
        profile_url = f"{self.base_url}/xrpc/app.bsky.actor.getProfile"
        profile_params = {"actor": user_identifier}
        
        with session.get(profile_url, headers=self.headers, params=profile_params) as response:
            if response.status != 200:
                print(f"Impossible de récupérer le profil {user_identifier}: {response.status}")
                return articles
                
            profile_data = response.json()
            user_did = profile_data.get("did")
            display_name = profile_data.get("displayName", user_identifier)
        
        # Récupère les posts de l'utilisateur
        posts_url = f"{self.base_url}/xrpc/app.bsky.feed.getAuthorFeed"
        posts_params = {
            "actor": user_did,
            "limit": 100,
            "filter": "posts_no_replies"  # Seulement les posts originaux
        }
        
        with session.get(posts_url, headers=self.headers, params=posts_params) as response:
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
                            formatted_post = self._format_bluesky_post(post, item)
                            formatted_post["source_name"] = f"@{display_name}"
                            articles.append(formatted_post)
            else:
                print(f"Erreur API Bluesky posts: {response.status}")
        
        return articles
    
    def _format_bluesky_post(self, post: dict, feed_item: dict) -> dict:
        """
        Formate un post Bluesky au format unifié
        """
        record = post.get("record", {})
        author = post.get("author", {})
        
        # Contenu principal
        text = record.get("text", "")
        
        # Gestion des liens/embeds
        embed = record.get("embed")
        if embed:
            if embed.get("$type") == "app.bsky.embed.external":
                external = embed.get("external", {})
                if external.get("title"):
                    text += f"\n\n🔗 {external['title']}"
                if external.get("description"):
                    text += f"\n{external['description']}"
            elif embed.get("$type") == "app.bsky.embed.images":
                images = embed.get("images", [])
                if images:
                    text += f"\n\n🖼️ {len(images)} image(s)"
                    for img in images[:3]:  # Max 3 descriptions
                        if img.get("alt"):
                            text += f"\n- {img['alt']}"
        
        # Gestion des réponses/citations
        reply = record.get("reply")
        if reply and reply.get("parent"):
            text = f"↳ Réponse à un post\n\n{text}"
        
        # Construction de l'URL
        post_uri = post.get("uri", "")
        at_url = ""
        if post_uri:
            # Conversion AT URI vers URL web
            parts = post_uri.replace("at://", "").split("/")
            if len(parts) >= 3:
                did, collection, rkey = parts[0], parts[1], parts[2]
                handle = author.get("handle", did)
                at_url = f"https://bsky.app/profile/{handle}/post/{rkey}"
        
        return {
            'title': text[:100] + "..." if len(text) > 100 else text,  # Titre = début du texte            
            'summary': text,
            'link': at_url,
            'published': record.get("createdAt", datetime.now().isoformat()),
            'source_type': 'bluesky',
            'source_name': f"@{author.get('handle', 'unknown')}",
            'author': author.get("displayName", author.get("handle", "Unknown")),
            'likes': post.get("likeCount", 0),
            'reposts': post.get("repostCount", 0),
            'replies': post.get("replyCount", 0)
        }