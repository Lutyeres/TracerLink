from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Optional, Callable
from src.config.base import BASE_DIR

_log_lock = Lock()
_panel_callback: Optional[Callable[[str], None]] = None

LOG_FILE = BASE_DIR / "log.txt"


def set_panel_callback(callback: Callable[[str], None]):
    global _panel_callback
    _panel_callback = callback


def log(message: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {message}"

    with _log_lock:
        print(formatted)

        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")

        if _panel_callback:
            _panel_callback(formatted)