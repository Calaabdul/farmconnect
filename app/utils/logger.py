import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logger(name: str = "farmconnect") -> logging.Logger:
    log_file = Path(__file__).resolve().parents[1] / "farmconnect.log"

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    ch.setFormatter(ch_formatter)

    # Rotating file handler
    fh = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=3)
    fh.setLevel(logging.INFO)
    fh.setFormatter(ch_formatter)

    logger.addHandler(ch)
    logger.addHandler(fh)

    return logger


import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "farmconnect.log"


def setup_logger(name: str = "farmconnect") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    fmt = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s", "%Y-%m-%d %H:%M:%S"
    )

    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    fh = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger


# module-level default logger
logger = setup_logger()
