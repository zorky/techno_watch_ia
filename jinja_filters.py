from jinja2 import Environment
from markupsafe import Markup
from datetime import datetime, timezone

#
# Filtres pour les templates jinja2 
# champ | filtre
# 
def format_date(value):
    """filtre jinga2 pour formatage de la date en FR"""
    if isinstance(value, str):
        date_obj = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
        return date_obj.strftime("%d/%m/%Y")
    return value.strftime("%d/%m/%Y")

def format_local_datetime(utc_datetime, tz: str = "Europe/Paris"):
    """filtre de conversion UTC -> heure Paris"""    
    import pytz
    if not utc_datetime:
        return "N/A"
    # Convertit UTC → Europe/Paris
    local_tz = pytz.timezone(tz)
    local_datetime = utc_datetime.replace(tzinfo=timezone.utc).astimezone(local_tz)
    return local_datetime.strftime('%d/%m/%Y à %H:%M')

def nl2br(value):
    """Convertit les retours chariots en <br>."""
    if value is None:
        return ""
    return Markup(value.replace('\n', '<br>\n'))


JINJA_FILTERS = {
    'format_local_datetime': format_local_datetime,
    'format_date': format_date,
    'truncate': lambda s, length: s[:length] + '...' if len(s) > length else s,
    'nl2br': nl2br
}

def register_jinja_filters(env: Environment):
    for name, func in JINJA_FILTERS.items():
        env.filters[name] = func
        