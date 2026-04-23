import logging
import os
import sys
from datetime import datetime
from config.config import Config


def setup_logger(name=__name__):
    """
    Setup and configure a professional dual-handler logger.
    Writes to both daily rotating files and stdout (for Railway visibility).
    """
    # Create logs directory if it doesn't exist
    if not os.path.exists(Config.LOG_DIR):
        os.makedirs(Config.LOG_DIR)

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, Config.LOG_LEVEL, logging.INFO))

    # Avoid duplicate handlers if called multiple times
    if logger.handlers:
        return logger

    # ── File handler (daily rotation by filename) ──
    log_filename = os.path.join(
        Config.LOG_DIR,
        f"bot_{datetime.now().strftime('%Y-%m-%d')}.log"
    )
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setLevel(getattr(logging, Config.LOG_LEVEL, logging.INFO))

    # ── Console handler (Railway reads stdout) ──
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, Config.LOG_LEVEL, logging.INFO))

    # ── Formatter ──
    formatter = logging.Formatter(
        '%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
