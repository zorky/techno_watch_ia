import os
from dotenv import load_dotenv
from functools import wraps
import time
import logging
import argparse
from colorama import Fore, Style, init

# =========================
# Configuration du logging
# Couleurs
# =========================

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
try:
    logger.setLevel(logging.DEBUG if argscli.debug else logging.INFO)
except:
    ...
logger.addHandler(handler)
logger.propagate = False

# =========================
# Parsing des arguments CLI
# =========================
try:
    parser = argparse.ArgumentParser(description="Agent RSS avec résumés LLM")
    parser.add_argument(
        "--debug", action="store_true", help="Active le mode debug détaillé"
    )
    argscli = parser.parse_args()
except Exception as e:
    ...

def measure_time(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        duration = end_time - start_time
        print(f"⏱️  Temps écoulé pour {func.__name__}: {duration:.4f} secondes")
        logger.info(f"⏱️  Temps écoulé pour {func.__name__}: {duration:.4f} secondes")
        return result

    return wrapper

def get_environment_variable(key, default = None):
    load_dotenv()
    return os.getenv(key, default)
