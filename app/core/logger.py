import logging
from colorama import Fore, Style, init

init(autoreset=True)

logging.basicConfig(level=logging.INFO)

def print_color(color, text):
    print(color + text)

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

logger = logging.getLogger(__name__)
logger.propagate = False  # Empêche la propagation aux loggers parents

# Assurez-vous qu'il n'y a qu'un seul handler
if not logger.handlers:
    formatter = ColorFormatter(
        fmt="%(asctime)s - %(levelname)s - %(message)s", datefmt="%d/%m/%Y %H:%M:%S"
    )
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def setup_logger(level=logging.INFO):
    formatter = ColorFormatter(
        fmt="%(asctime)s - %(levelname)s - %(message)s", datefmt="%d/%m/%Y %H:%M:%S"
    )    
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    # logger = logging.getLogger(__name__)
    # logger.setLevel(level)
    # logger.addHandler(handler)
    # logger.propagate = False
    return logger


logger = setup_logger()

def count_by_type_articles(title, articles_by_source, color=Fore.LIGHTYELLOW_EX):
    from collections import Counter

    source_counts = Counter(item["source"].value for item in articles_by_source)
    print_color(color, "=" * 60)
    print_color(color, f"{title} {source_counts}")
    print_color(color, "=" * 60)
