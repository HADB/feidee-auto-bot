import logging
import os
from logging.handlers import TimedRotatingFileHandler

os.makedirs("logs", exist_ok=True)

log_formatter = logging.Formatter(
    "%(asctime)s [%(levelname)-8s] %(message)s"
)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(log_formatter)
stream_handler.setLevel(logging.INFO)

file_handler = TimedRotatingFileHandler(
    "logs/feidee-auto-bot",
    when="midnight",
    interval=1,
    backupCount=365,
    encoding="utf-8",
)
file_handler.suffix = "%Y%m%d.log"
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.INFO)

logger = logging.getLogger()
logger.setLevel(level=logging.INFO)
logger.addHandler(stream_handler)
logger.addHandler(file_handler)


def debug(msg):
    logger.debug(f"{msg}")


def info(msg):
    logger.info(f"{msg}")


def warn(msg):
    logger.warn(f"{msg}")


def error(msg):
    logger.error(f"{msg}")
