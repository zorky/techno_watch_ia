"""
Script de test pour analyser et afficher les informations d'un flux RSS ou Atom, notamment le contenu des entrées avec feedparser
https://feedparser.readthedocs.io/en/latest/
"""
import feedparser
from feedparser import FeedParserDict
from bs4 import BeautifulSoup

def strip_html(text: str) -> str:
    return BeautifulSoup(text, "html.parser").get_text()

def get_summary(entry: dict):
    """Affiche le résumé ou le contenu d'une entrée de flux RSS ou Atom
       RSS 2.0: 'summary' : Feed Entry: dict_keys(['title', 'title_detail', 'links', 'link', 'summary', 'summary_detail', 'id', 'guidislink', 'published', 'published_parsed'])
       Atom: 'content' : Feed Entry: dict_keys(['title', 'title_detail', 'links', 'link', 'published', 'published_parsed', 'updated', 'updated_parsed', 'authors', 'author_detail', 'author', 'id', 'guidislink', 'summary', 'summary_detail', 'content', 'tags'])
    """
    if 'content' in entry.keys():
        content: list[FeedParserDict] = entry.get('content', [dict])
        print(type(content))        
        print(type(entry.content[0]))
        print(f"Content keys: {entry.content[0].keys()}")
        # print(f"Content value: {entry.content[0].get('value', 'N/A')}")
        print(f"Content: {strip_html(entry.content[0].get('value', 'N/A'))}")
    else:        
        print(f"Summary: {strip_html(entry.get('summary', 'N/A'))}")
    print(f"-" * 40)

def display_feed_entries(news_feed: FeedParserDict):
    print(f"Feed Entries: {len(news_feed.entries)}")        
    for entry in news_feed.entries:
        print(type(entry))
        print(f"Feed Entry: {entry.keys()}")
        print(f"{entry.title} --> {entry.link}")
        print(f"-" * 40)
        get_summary(entry)        

def fetch_and_print_feed_info(url):
    print(f"\nFetching feed from: {url}")
    feed: FeedParserDict = feedparser.parse(url)
    print(feed.feed.keys())
    print("Feed Title:", feed.feed.get('title', 'N/A'))
    print("Feed Description:", feed.feed.get('description', 'N/A'))
    print("Feed Subtitle:", feed.feed.get('subtitle', 'N/A'))
    print("Feed Link:", feed.feed.get('link', 'N/A'), "\n")
    display_feed_entries(feed)                

if __name__ == "__main__":    
    fetch_and_print_feed_info('https://cert.ssi.gouv.fr/alerte/feed/') # RSS
    fetch_and_print_feed_info('http://dotmobo.github.io/feeds/all.atom.xml') # Atom
