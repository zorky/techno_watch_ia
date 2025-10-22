import os
from dotenv import load_dotenv
from functools import wraps
import time
import logging
import argparse
from colorama import Fore, Style, init
from core.logger import setup_logger

# =========================
# Configuration du logging
# Couleurs
# =========================

def parse_cli_args():
    parser = argparse.ArgumentParser(description="Agent RSS avec résumés LLM")
    parser.add_argument("--debug", action="store_true", help="Active le mode debug détaillé")
    return parser.parse_args()

def configure_logging_from_args():
    args = parse_cli_args()
    level = logging.DEBUG if args.debug else logging.INFO
    return setup_logger(level=level), args

def measure_time(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        from core.logger import logger
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        duration = end_time - start_time
        # print(f"⏱️  Temps écoulé pour {func.__name__}: {duration:.4f} secondes")
        logger.info(f"⏱️  Temps écoulé pour {func.__name__}: {duration:.4f} secondes")
        return result

    return wrapper

def get_environment_variable(key, default = None):
    load_dotenv()
    return os.getenv(key, default)
