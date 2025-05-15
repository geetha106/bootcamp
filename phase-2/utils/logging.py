from rich.logging import RichHandler
import logging

def get_logger(name="figurex"):
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = RichHandler()
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)
    return logger
