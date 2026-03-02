import re
from pathlib import Path
import urllib.request
import hashlib

from src.config.base import BASE_DIR
from src.config import settings
from src.utils.logger import log

TRCFMT_R = "TRCFMT=1;800;E;R;P"
TRCFMT_L = "TRCFMT=1;800;E;L;P"
BLOCK_SIZE = 100


class Job:

    def __init__(self):
        settings.carregar_config()

        self.hash_file = BASE_DIR / ".last_hash"
        self.host = settings.get_host()
        self.endpoint = settings.get_endpoint()
        self.ext = settings.get_ext()
        self.pasta = Path(settings.get_pasta())

        self.pasta.mkdir(parents=True, exist_ok=True)

        # 🔹 Controle de estado (anti-flood)
        self._last_state = None          # NEW | UNCHANGED | NOT_FOUND | ERROR
        self._previous_state = None

    # ==================================================
    # EXECUÇÃO PRINCIPAL
    # ==================================================

    def run_once(self):

        self._last_state = None

        if not self.host:
            self._last_state = "ERROR"
            self._emit_state_log()
            return

        url = f"{self.host}{self.endpoint}"

        try:
            content = self._http_get(url)
        except Exception:
            self._last_state = "ERROR"
            self._emit_state_log()
            return

        job_id = self._extract_job_id(content)
        if not job_id:
            self._last_state = "NOT_FOUND"
            self._emit_state_log()
            return

        content = self._ensure_complete_file(content)
        current_hash = self._generate_hash(content)

        # Verifica hash anterior
        if self.hash_file.exists():
            try:
                last_hash = self.hash_file.read_text().strip()
                if current_hash == last_hash:
                    self._last_state = "UNCHANGED"
                    self._emit_state_log()
                    return
            except Exception:
                pass

        file_path = self.pasta / f"{job_id}.{self.ext}"

        try:
            file_path.write_text(content, encoding="utf-8")
        except Exception:
            self._last_state = "ERROR"
            self._emit_state_log()
            return

        try:
            self.hash_file.write_text(current_hash)
        except Exception:
            pass

        self._last_state = "NEW"
        self._emit_state_log()

    # ==================================================
    # LOG CONTROLADO (ANTI-FLOOD)
    # ==================================================

    def _emit_state_log(self):
        if self._last_state != self._previous_state:
            log(f"Estado alterado para: {self._last_state}")
        self._previous_state = self._last_state

    def get_last_state(self):
        return self._last_state

    # ==================================================
    # AUXILIARES
    # ==================================================

    def _generate_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _http_get(self, url: str) -> str:
        with urllib.request.urlopen(url, timeout=15) as response:
            return response.read().decode("utf-8", errors="replace")

    def _extract_job_id(self, content: str):
        match = re.search(r"\b(?:JOB|job)\s*=\s*([0-9]+)\b", content)
        return match.group(1) if match else None

    # ==================================================
    # REGRA PRINCIPAL DE ESPELHO
    # ==================================================

    def _ensure_complete_file(self, content: str) -> str:

        lines = content.splitlines()
        lines = self._mirror_semicolon_values(lines)

        has_r = TRCFMT_R in lines
        has_l = TRCFMT_L in lines

        r_block = []
        l_block = []

        if has_r:
            r_index = lines.index(TRCFMT_R)
            r_block = lines[r_index: r_index + 1 + BLOCK_SIZE]

        if has_l:
            l_index = lines.index(TRCFMT_L)
            l_block = lines[l_index: l_index + 1 + BLOCK_SIZE]

        if has_r and not has_l:
            l_block = [TRCFMT_L] + r_block[1:]

        elif has_l and not has_r:
            r_block = [TRCFMT_R] + l_block[1:]

        lines_clean = [
            line for line in lines
            if line not in r_block and line not in l_block
        ]

        job_index = next(
            i for i, l in enumerate(lines_clean) if l.startswith("JOB=")
        )

        insert_position = job_index + 1

        new_lines = (
            lines_clean[:insert_position]
            + r_block
            + l_block
            + lines_clean[insert_position:]
        )

        return "\n".join(new_lines) + "\n"

    # ==================================================
    # ESPELHO ";?"
    # ==================================================

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