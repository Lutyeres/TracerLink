import re
from pathlib import Path
import urllib.request

from src.config import settings
from src.utils.logger import log

TRCFMT_R = "TRCFMT=1;800;E;R;P"
TRCFMT_L = "TRCFMT=1;800;E;L;P"
BLOCK_SIZE = 100


class Job:

    def __init__(self):
        settings.carregar_config()

        self.host = settings.get_host()
        self.endpoint = settings.get_endpoint()
        self.ext = settings.get_ext()
        self.pasta = Path(settings.get_pasta())

        self.pasta.mkdir(parents=True, exist_ok=True)

    # =============================
    # EXECUÇÃO PRINCIPAL
    # =============================

    def run_once(self):

        if not self.host:
            log("Host não configurado.")
            return

        url = f"{self.host}{self.endpoint}"
        log(f"GET {url}")

        try:
            content = self._http_get(url)
        except Exception as e:
            log(f"Erro HTTP: {e}")
            return

        job_id = self._extract_job_id(content)
        if not job_id:
            log("JOB não encontrado.")
            return

        content = self._ensure_complete_file(content)

        file_path = self.pasta / f"{job_id}.{self.ext}"
        file_path.write_text(content, encoding="utf-8")

        log(f"Arquivo salvo: {file_path}")

    # =============================
    # HTTP
    # =============================

    def _http_get(self, url: str) -> str:
        with urllib.request.urlopen(url, timeout=15) as response:
            return response.read().decode("utf-8", errors="replace")

    # =============================
    # EXTRAÇÃO JOB
    # =============================

    def _extract_job_id(self, content: str):
        match = re.search(r"\b(?:JOB|job)\s*=\s*([0-9]+)\b", content)
        return match.group(1) if match else None

    # =============================
    # REGRA PRINCIPAL DE ESPELHO
    # =============================

    def _ensure_complete_file(self, content: str) -> str:

        lines = content.splitlines()

        has_r = TRCFMT_R in lines
        has_l = TRCFMT_L in lines

        # Espelha valores com ";?"
        lines = self._mirror_semicolon_values(lines)

        if has_r and not has_l:
            log("Somente lado R detectado. Criando lado L.")
            lines = self._create_missing_side(
                lines,
                source_header=TRCFMT_R,
                target_header=TRCFMT_L
            )

        elif has_l and not has_r:
            log("Somente lado L detectado. Criando lado R.")
            lines = self._create_missing_side(
                lines,
                source_header=TRCFMT_L,
                target_header=TRCFMT_R
            )

        return "\n".join(lines) + "\n"

    # =============================
    # CRIA LADO FALTANTE
    # =============================

    def _create_missing_side(self, lines, source_header, target_header):

        source_index = lines.index(source_header)

        start = source_index + 1
        end = start + BLOCK_SIZE

        radianos = lines[start:end]

        # Localizar posição após JOB=
        job_index = next(
            i for i, l in enumerate(lines) if l.startswith("JOB=")
        )

        insert_position = job_index + 1

        new_block = [target_header] + radianos

        return (
            lines[:insert_position]
            + new_block
            + lines[insert_position:]
        )

    # =============================
    # ESPELHO DE VALORES ";?"
    # =============================

    def _mirror_semicolon_values(self, lines):

        mirrored = []

        for line in lines:

            if "=" not in line or ";" not in line:
                mirrored.append(line)
                continue

            key, value = line.split("=", 1)

            parts = value.split(";")
            if len(parts) != 2:
                mirrored.append(line)
                continue

            left = parts[0].strip()
            right = parts[1].strip()

            if right == "?" and left != "?":
                mirrored.append(f"{key}={left};{left}")
                continue

            if left == "?" and right != "?":
                mirrored.append(f"{key}={right};{right}")
                continue

            mirrored.append(line)

        return mirrored