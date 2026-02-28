from configparser import ConfigParser
from pathlib import Path
from src.config.base import BASE_DIR
from typing import Optional

INI_PATH = BASE_DIR / "config.ini"

config = ConfigParser()

def criar_config_padrao():
    config["PARAMETROS"] = {
        "host": "",
        "pasta": "",
        "ext": ""
    }


    with open(INI_PATH, "w") as f:
        config.write(f)


def carregar_config():
    if not INI_PATH.exists():
        criar_config_padrao()

    config.read(INI_PATH)

    # Garante que seções existam
    if "PARAMETROS" not in config:
        config["PASTAS"] = {}

    if "host" not in config["PARAMETROS"]:
        config["PARAMETROS"]["host"] = ""
    if "pasta" not in config["PARAMETROS"]:
        config["PARAMETROS"]["pasta"] = ""
    if "ext" not in config["PARAMETROS"]:
        config["PARAMETROS"]["ext"] = ""

    with open(INI_PATH, "w", encoding="utf-8") as f:
        config.write(f)


# Carrega automaticamente ao importar
carregar_config()


def _get_parametros(nome: str) -> Optional[Path]:
    valor = config.get("PARAMETROS", nome, fallback="").strip()
    if not valor:
        return None
    return Path(valor)


def get_parametros_host() -> Optional[Path]:
    return _get_parametros("host")

def get_parametros_pasta() -> Optional[Path]:
    return _get_parametros("pasta")

def get_parametros_ext() -> Optional[Path]:
    return _get_parametros("ext")



def salvar_config(host, pasta, ext):
    config.set("PARAMETROS", "host", str(host))
    config.set("PARAMETROS", "pasta", str(pasta))
    config.set("PARAMETROS", "ext", str(ext))

    with open(INI_PATH, "w") as f:
        config.write(f)