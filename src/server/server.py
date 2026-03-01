import threading
import time
from src.domain.job import Job
from src.config import settings
from src.utils.logger import log


class Server:

    def __init__(self):
        self._thread = None
        self._stop_event = threading.Event()
        self._running = False

    def start(self):

        if self._running:
            return

        settings.carregar_config()

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

        self._running = True
        log("Server iniciado.")

    def _loop(self):

        poll_seconds = settings.get_poll_seconds()
        job = Job()

        while not self._stop_event.is_set():
            try:
                job.run_once()
            except Exception as e:
                log(f"Erro inesperado: {e}")

            time.sleep(poll_seconds)

    def stop(self):

        if not self._running:
            return

        self._stop_event.set()
        self._running = False
        log("Server parado.")

    def is_running(self):
        return self._running