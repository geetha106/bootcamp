# logging.py
from rich.logging import RichHandler
import logging
import sys

# Store loggers to avoid duplicate handlers
_loggers = {}


def get_logger(name="figurex"):
    """
    Get a logger with consistent formatting using Rich.
    This avoids duplicate log messages.
    """
    global _loggers

    if name in _loggers:
        return _loggers[name]

    # Create new logger
    logger = logging.getLogger(name)

    # Remove any existing handlers to avoid duplicates
    while logger.handlers:
        logger.removeHandler(logger.handlers[0])

    # Configure handler with rich formatting
    handler = RichHandler(
        rich_tracebacks=True,
        show_path=False,
        omit_repeated_times=True
    )

    # Format: no need for timestamp/level as RichHandler adds these
    formatter = logging.Formatter("%(message)s")
    handler.setFormatter(formatter)

    # Add handler and set level
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    # Don't propagate to avoid duplicate logs
    logger.propagate = False

    # Store for future reference
    _loggers[name] = logger

    return logger