from jinja2 import Environment
from markupsafe import Markup
from datetime import datetime, timezone
from pathlib import Path
from functools import lru_cache
import base64
import logging

from app.services.models import SourceType

logging.basicConfig(level=logging.INFO)


#######################################################
# Filtres pour les templates jinja2 mail ou web
# champ | filtre
#######################################################

def format_date(value):
    """
    filtre jinga2 pour formatage de la date en FR
    Args:
        value: une date au format ISO ou un objet datetime
    Returns:
        une date formatée en "dd/mm/yyyy" ou "N/A" si la date est invalide ou manquante

    la date peut être au format ISO (ex: "2024-06-01T12:34:56") ou un objet datetime, s'il y a des microsecondes, elles seront ignorées (ex: "2026-02-07T13:58:36.252626")
    """
    logging.info(f"format_date: value={value} ({type(value)})")
    
    if not value:
        return "N/A"
    
    try:
        if isinstance(value, str):            
            if '.' in value: # supprime les microsecondes si présentes
                value = value.split('.')[0]
            date_obj = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
            return date_obj.strftime("%d/%m/%Y")
        return value.strftime("%d/%m/%Y")
    except Exception as e:
        logging.error(f"Erreur format_date: {e} pour value={value}")
        return "N/A"


def format_local_datetime(utc_datetime, tz: str = "Europe/Paris"):
    """filtre de conversion UTC -> heure Paris"""
    import pytz

    if not utc_datetime:
        return "N/A"
    # Convertit UTC → Europe/Paris
    local_tz = pytz.timezone(tz)
    local_datetime = utc_datetime.replace(tzinfo=timezone.utc).astimezone(local_tz)
    return local_datetime.strftime("%d/%m/%Y à %H:%M")


def nl2br(value):
    """Convertit les retours chariots en <br>."""
    if value is None:
        return ""
    return Markup(value.replace("\n", "<br>\n"))


@lru_cache(maxsize=32)
def get_svg_base64(source: str) -> str:
    """cache des icones SVG en base64 pour les emails."""
    icon_path = Path(__file__).parent / "templates" / "web" / "icons" / f"{source}.svg"
    with open(icon_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def icon_html(source: SourceType, size: int = 24, email: bool = False) -> str:
    """Génère le HTML d'une icône SVG pour le web ou les emails.

    Args:
        source: Type de source ("bluesky", "reddit", "rss", "linkedin", "twitter").
        size: Taille en pixels (défaut: 24).
        email: Si True, retourne une balise <img> avec SVG en base64.
    """
    logging.debug(f"icon_html: source={source}, size={size}, email={email}")
    icon_path = Path(__file__).parent / "templates" / "web" / "icons" / f"{source}.svg"
    FALLBACK_EMOJIS = {
        "rss": "📡",
        "bluesky": "🐦",
        "reddit": "👽",
        "linkedin": "💼",
        "twitter": "🐦",
    }
    # logging.info(f"icon_html: icon_path={icon_path}")

    if not icon_path.exists():  # fallback si le chemin n'existe pas
        logging.error(f"Le chemin des icônes n'existe pas: {icon_path}")
        if email:
            return Markup(
                f'<span style="font-size: {size}px;">{FALLBACK_EMOJIS.get(source, "🔗")}</span>'
            )
        else:
            return Markup(
                f'<span class="text-{size // 4}">{FALLBACK_EMOJIS.get(source, "🔗")}</span>'
            )

    if email:
        logging.debug(f"icon_html: icon_path={icon_path}")
        with open(icon_path, "rb") as f:
            svg_base64 = base64.b64encode(f.read()).decode("utf-8")
            return Markup(
                f'<img src="data:image/svg+xml;base64,{svg_base64}" alt="{source}" width="{size}" height="{size}" style="vertical-align: middle;">'
            )

    html = f"""
        <svg class="w-{size // 4} h-{size // 4} text-{source}" aria-hidden="true">
          <use xlink:href="#icon-{source}"></use>
        </svg>
        """.replace("\n", "")
    return Markup(html)


JINJA_FILTERS = {
    "format_local_datetime": format_local_datetime,
    "format_date": format_date,
    "truncate": lambda s, length: s[:length] + "..." if len(s) > length else s,
    "nl2br": nl2br,
    "icon_html": icon_html,
}


def register_jinja_filters(env: Environment):
    for name, func in JINJA_FILTERS.items():
        env.filters[name] = func
