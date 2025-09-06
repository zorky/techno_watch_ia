from typing import NamedTuple
import xml.etree.ElementTree as ET

class RSSFeed(NamedTuple):
    titre: str
    lien_rss: str
    lien_web: str
    
def parse_opml_to_rss_list(opml_file: str) -> list[RSSFeed]:
    """
    Parse un fichier OPML et retourne une liste de RSSFeed (NamedTuple).
    """
    default_list = [
        "https://cert.ssi.gouv.fr/alerte/feed/",
        "https://www.djangoproject.com/rss/community/",
        "https://cosmo-games.com/sujet/ia/feed/",
        "https://belowthemalt.com/feed/",
        "https://www.ajeetraina.com/rss/",
        "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml"
    ]
    tree = ET.parse(opml_file)
    root = tree.getroot()

    rss_feeds = []
    for outline in root.findall(".//outline[@type='rss']"):
        # Gestion des valeurs manquantes
        title = outline.get('title') or outline.get('text') or "Sans titre"
        xml_url = outline.get('xmlUrl')
        html_url = outline.get('htmlUrl') or "Aucun lien web"

        rss_feeds.append(
            RSSFeed(titre=title, lien_rss=xml_url, lien_web=html_url)
        )

    return rss_feeds

def filter_rss_by_keywords(rss_list: list[RSSFeed], keywords: list[str]) -> list[RSSFeed]:
    """
    Filtre les flux RSS dont le titre ou l'URL contient l'un des mots-clés donnés.
    """
    filtered = []
    for feed in rss_list:
        title = feed.titre.lower()
        url = feed.lien_rss.lower()
        if any(keyword.lower() in title or keyword.lower() in url for keyword in keywords):
            filtered.append(feed)
    return filtered

if __name__ == "__main__":
    keywords = ["IA", "cybersécurité", "Django", "intelligence artificielle"]
    rss_list = parse_opml_to_rss_list('my-err.opml')
    filtered_rss = filter_rss_by_keywords(rss_list, keywords)

    for feed in filtered_rss:
        print(f"Titre: {feed.titre}")
        print(f"RSS: {feed.lien_rss}")
        print(f"Web: {feed.lien_web}")
        print("-" * 40)