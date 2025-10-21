import logging
from colorama import Fore, Style, init

init(autoreset=True)

logging.basicConfig(level=logging.INFO)

# =========================
# Formatter coloré
# =========================
class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: Fore.CYAN,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.RED + Style.BRIGHT,
    }

    def format(self, record):
        color = self.COLORS.get(record.levelno, "")
        levelname_color = color + record.levelname + Style.RESET_ALL
        record.levelname = levelname_color
        return super().format(record)


formatter = ColorFormatter(
    fmt="%(asctime)s - %(levelname)s - %(message)s", datefmt="%d/%m/%Y %H:%M:%S"
)

handler = logging.StreamHandler()
handler.setFormatter(formatter)

logger = logging.getLogger(__name__)

# logger.setLevel(logging.INFO)
# try:
#     logger.setLevel(logging.DEBUG if argscli.debug else logging.INFO)
# except:
#     ...
logger.addHandler(handler)
logger.propagate = False

def print_color(color, text):
    print(color + text)

def count_by_type_articles(title, articles_by_source, color=Fore.LIGHTYELLOW_EX):
    from collections import Counter
    from core.logger import print_color
    source_counts = Counter(item['source'].value for item in articles_by_source)    
    print_color(color, "=" * 60)
    print_color(color, f"{title} {source_counts}")
    print_color(color, "=" * 60)