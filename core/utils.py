import logging
from colorama import Fore, Style
import time
import argparse
from functools import wraps

from sklearn import logger

logging.basicConfig(level=logging.INFO)

parser = argparse.ArgumentParser(description="Agent RSS avec résumés LLM")
parser.add_argument(
    "--debug", action="store_true", help="Active le mode debug détaillé"
)
args = parser.parse_args()

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
    fmt="%(asctime)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S"
)

handler = logging.StreamHandler()
handler.setFormatter(formatter)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG if args.debug else logging.INFO)
logger.addHandler(handler)
logger.propagate = False


def measure_time(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        duration = end_time - start_time
        logger.info(f"⏱️  Temps écoulé pour {func.__name__}: {duration:.4f} secondes")
        return result

    return wrapper    