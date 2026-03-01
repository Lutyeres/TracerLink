import configparser
from pathlib import Path
from src.config.base import BASE_DIR

CONFIG_FILE = BASE_DIR / "config.ini"

config = configparser.ConfigParser()


def criar_config_padrao():
    config["SERVER"] = {
        "host": "",
        "endpoint": "/jobs/currentJob.oma",
        "ext": "txt",
        "poll_seconds": "5"
    }

    config["STORAGE"] = {
        "pasta": str(BASE_DIR / "FormasTracer")
    }

    salvar_config()


def carregar_config():
    if not CONFIG_FILE.exists():
        criar_config_padrao()
    config.read(CONFIG_FILE)


def atualizar_config(host, endpoint, ext, poll_seconds, pasta):

    if "SERVER" not in config:
        config["SERVER"] = {}

    if "STORAGE" not in config:
        config["STORAGE"] = {}

    config["SERVER"]["host"] = host
    config["SERVER"]["endpoint"] = endpoint
    config["SERVER"]["ext"] = ext
    config["SERVER"]["poll_seconds"] = str(poll_seconds)
    config["STORAGE"]["pasta"] = pasta

    salvar_config()


def salvar_config():
    with open(CONFIG_FILE, "w") as f:
        config.write(f)


def get_host():
    return config["SERVER"].get("host", "")


def get_endpoint():
    return config["SERVER"].get("endpoint", "")


def get_ext():
    return config["SERVER"].get("ext", "txt")


def get_poll_seconds():
    return int(config["SERVER"].get("poll_seconds", 5))


def get_pasta():
    return config["STORAGE"].get("pasta", "")