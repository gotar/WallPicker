"""Application logging setup.

Writes INFO+ logs to a rotating file under the wallpicker cache dir so issues
can be diagnosed after the fact, and mirrors WARNING+ to stderr.
"""

import logging
import logging.handlers
from pathlib import Path

LOG_DIR = Path.home() / ".cache" / "wallpicker" / "logs"
LOG_FILE = LOG_DIR / "wallpicker.log"
MAX_BYTES = 2 * 1024 * 1024
BACKUP_COUNT = 2

_configured = False


def setup_logging(level: int = logging.INFO) -> Path:
    """Configure root logging once; returns the log file path."""
    global _configured
    log_dir = Path(LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = Path(LOG_FILE)

    if _configured:
        return log_file

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.WARNING)

    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(file_handler)
    root.addHandler(console_handler)

    _configured = True
    return log_file
