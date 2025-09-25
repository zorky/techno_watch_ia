import praw
from datetime import datetime, timedelta
import logging

from services.base_fetcher import BaseFetcher
from services.models import Source

logging.basicConfig(level=logging.INFO)
from core.logger import logger

class RedditFetcher(BaseFetcher):
    def __init__(self, client_id: str, client_secret: str, user_agent: str):
        self.reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent
        )
    
    def fetch_articles(self, source: Source, max_days: int) -> list[dict]:
        articles = []
        cutoff_date = datetime.now() - timedelta(days=max_days)        
        subreddit = self.reddit.subreddit(source.subreddit)
        logger.info(f"Fetch des posts du sub r/{source.subreddit} (cutoff date: {cutoff_date})")        
        
        # Récupération selon le tri choisi
        if source.sort_by == "hot":
            posts = subreddit.hot(limit=100)
        elif source.sort_by == "new":
            posts = subreddit.new(limit=100)
        elif source.sort_by == "top":
            posts = subreddit.top(time_filter=source.time_filter, limit=100)
        else:
            posts = subreddit.rising(limit=100)
        
        for post in posts:
            post_date = datetime.fromtimestamp(post.created_utc)
            
            if post_date > cutoff_date:
                # Contenu : titre + selftext + premiers commentaires top
                content = post.title
                if post.selftext:
                    content += f"\n\n{post.selftext}"
                
                # Ajouter les meilleurs commentaires comme contexte
                post.comments.replace_more(limit=0)
                top_comments = sorted(post.comments.list()[:5], 
                                    key=lambda x: x.score, reverse=True)
                if top_comments:
                    content += "\n\nTop comments:\n"
                    for comment in top_comments[:3]:
                        if hasattr(comment, 'body') and len(comment.body) < 200:
                            content += f"- {comment.body}\n"
                
                articles.append({
                    'title': post.title,
                    'summary': content,
                    'link': f"https://reddit.com{post.permalink}",
                    'published': post_date.isoformat(),
                    'source_type': 'reddit',
                    'source_name': f"r/{source.subreddit}",
                    'score': post.score,
                    'num_comments': post.num_comments
                })
        logger.info(f"{len(articles)} articles récents récupérés de r/{source.subreddit}")  

        return articles
