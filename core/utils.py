from functools import wraps
import time
import logging
logger = logging.getLogger(__name__)

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