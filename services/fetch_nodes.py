from services.models import SourceType, UnifiedState
from services.factory_fetcher import FetcherFactory

from core.logger import logger

# def unified_fetch_node(state: UnifiedState) -> UnifiedState:
#     all_articles = []
    
#     # Configuration des fetchers
#     fetchers = {
#         SourceType.RSS: FetcherFactory.create_fetcher(SourceType.RSS),
#         SourceType.REDDIT: FetcherFactory.create_fetcher(
#             SourceType.REDDIT,
#             client_id="your_reddit_client_id",
#             client_secret="your_reddit_client_secret",
#             user_agent="your_app_name v1.0"
#         )
#     }
    
#     for source in state.sources:
#         try:
#             fetcher = fetchers.get(source.type)
#             if fetcher:
#                 articles = fetcher.fetch_articles(source, max_days=7)
#                 all_articles.extend(articles)
#                 logger.info(f"{len(articles)} articles récents de {source.name or source.url}")
#         except Exception as e:
#             logger.error(f"Error fetching from {source.url}: {e}")
    
#     return UnifiedState(
#         sources=state.sources,
#         keywords=state.keywords,
#         articles=all_articles,
#         filtered_articles=state.filtered_articles,
#         summaries=state.summaries
#     )