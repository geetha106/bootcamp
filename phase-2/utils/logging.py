from rich.logging import RichHandler
from rich.console import Console
import logging


def get_logger(name="figurex"):
    # Create a console with pager disabled
    console = Console(force_terminal=True, force_interactive=False)

    # Create a RichHandler with our custom console
    handler = RichHandler(
        console=console,
        rich_tracebacks=True,
        # Disable markup in log messages (optional)
        markup=False,
        # Disable the pager
        show_path=False,
    )

    # Set up the logger
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)

    return logger