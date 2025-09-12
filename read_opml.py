from typing import NamedTuple
import logging
import xml.etree.ElementTree as ET

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.propagate = False


class RSSFeed(NamedTuple):
    titre: str
    lien_rss: str
    lien_web: str


def parse_opml_to_rss_list(opml_file: str) -> list[RSSFeed]:
    """
    Parse un fichier OPML et retourne une liste de RSSFeed (NamedTuple).
    """
    default_list = [
        "http://dotmobo.github.io/feeds/all.atom.xml",
        "https://cert.ssi.gouv.fr/alerte/feed/",
        "https://www.djangoproject.com/rss/community/",
        # "https://cosmo-games.com/sujet/ia/feed/",
        # "https://belowthemalt.com/feed/",
        # "https://www.ajeetraina.com/rss/",
        # "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
    ]
    try:
        tree = ET.parse(opml_file)
        root = tree.getroot()

        rss_feeds = []
        for outline in root.findall(".//outline[@type='rss']"):
            # Gestion des valeurs manquantes
            title = outline.get("title") or outline.get("text") or "Sans titre"
            xml_url = outline.get("xmlUrl")
            html_url = outline.get("htmlUrl") or "Aucun lien web"

            rss_feeds.append(RSSFeed(titre=title, lien_rss=xml_url, lien_web=html_url))
    except (ET.ParseError, FileNotFoundError) as e:
        logger.error(
            f"Erreur lors de la lecture du fichier OPML: {e} - bascule vers les flux par défaut.\n"
        )
        rss_feeds = [
            RSSFeed(titre="Flux par défaut", lien_rss=url, lien_web="Aucun lien web")
            for url in default_list
        ]
    return rss_feeds


def filter_rss_by_keywords(
    rss_list: list[RSSFeed], keywords: list[str]
) -> list[RSSFeed]:
    """
    Filtre les flux RSS dont le titre ou l'URL contient l'un des mots-clés donnés.
    """
    filtered = []
    for feed in rss_list:
        title = feed.titre.lower()
        url = feed.lien_rss.lower()
        if any(
            keyword.lower() in title or keyword.lower() in url for keyword in keywords
        ):
            filtered.append(feed)
    return filtered


if __name__ == "__main__":
    keywords = ["IA", "cybersécurité", "Django", "intelligence artificielle"]
    rss_list = parse_opml_to_rss_list("my.opml")
    filtered_rss = filter_rss_by_keywords(rss_list, keywords)

    for feed in filtered_rss:
        print(f"Titre: {feed.titre}")
        print(f"RSS: {feed.lien_rss}")
        print(f"Web: {feed.lien_web}")
        print("-" * 40)
