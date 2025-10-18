import praw
from datetime import datetime, timedelta

import logging
logging.basicConfig(level=logging.INFO)

from services.annotations import fetcher_class
from services.fetchers.base_fetcher import BaseFetcher
from services.models import Source, SourceType

from core.logger import logger, Fore
from core.utils import get_environment_variable
from core import measure_time

@fetcher_class
class RedditFetcher(BaseFetcher):
    source_type = SourceType.REDDIT.value
    env_flag = "REDDIT_FETCH"

    def __init__(self, client_id: str, client_secret: str, user_agent: str):        
        self.reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent
        )
        self.max_fetch = int(get_environment_variable("REDDIT_MAX_FETCH", 10))
    
    @measure_time
    def fetch_articles(self, source: Source, max_days: int) -> list[dict]:
        from core.logger import print_color
        articles = []
        cutoff_date = datetime.now() - timedelta(days=max_days)        
        subreddit = self.reddit.subreddit(source.subreddit)
        logger.info(Fore.BLUE + f"Fetch des posts du sub r/{source.subreddit} depuis la date : depuis {max_days} jours -> {cutoff_date}")        
        color = Fore.LIGHTCYAN_EX
        print_color(color, "=" * 60)
        print_color(color, f"REDDIT Fetcher fetch_articles {source.url}")
        print_color(color, "=" * 60)
        source.sort_by = 'new' # for test purpose

        # Récupération selon le tri choisi
        if source.sort_by == "hot":
            posts = subreddit.hot(limit=self.max_fetch)
        elif source.sort_by == "new":
            posts = subreddit.new(limit=self.max_fetch)
        elif source.sort_by == "top":
            posts = subreddit.top(time_filter=source.time_filter, limit=self.max_fetch)
        else:
            posts = subreddit.rising(limit=self.max_fetch)
        
        for post in posts:
            post_date = datetime.fromtimestamp(post.created_utc)
            
            if post_date > cutoff_date:
                logger.info(Fore.LIGHTYELLOW_EX + f"Post récent: {post.title} (publié le {post_date})")
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
                    'num_comments': post.num_comments,
                    "source": SourceType.REDDIT,
                })
        logger.info(Fore.CYAN + f"{len(articles)} articles récents récupérés de r/{source.subreddit}")  

        return articles
