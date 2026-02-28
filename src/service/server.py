# server.py
import configparser
import threading
import time
from pathlib import Path

from src.model.job  import download_job, save_job


class EtessServer:
    def __init__(self, config_path="config.ini"):
        self.config_path = config_path
        self._ativo = False
        self._thread = None

    def _load_config(self):
        config = configparser.ConfigParser()
        config.read(self.config_path)

        host = config["ETESS"]["host"]
        endpoint = config["ETESS"]["endpoint"]
        interval = int(config["ETESS"]["interval"])
        directory = Path(config["SAVE"]["directory"])
        extension = config["SAVE"]["extension"]

        return host, endpoint, interval, directory, extension

    def _loop(self):
        host, endpoint, interval, directory, extension = self._load_config()

        while self._ativo:
            try:
                content = download_job(host, endpoint)
                path = save_job(content, directory, extension)

                if path:
                    print(f"[OK] Saved: {path}")

            except Exception as e:
                print(f"[ERROR] {e}")

            time.sleep(interval)

    def iniciar(self):
        if self._ativo:
            return

        self._ativo = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def parar(self):
        self._ativo = False

    @property
    def ativo(self):
        return self._ativo