import re
import time
from pathlib import Path
import urllib.request
import hashlib

from src.config.base import BASE_DIR
from src.config import settings
from src.utils.logger import log

TRCFMT_R = "TRCFMT=1;800;E;R;P"
TRCFMT_L = "TRCFMT=1;800;E;L;P"

BLOCK_SIZE = 100
TOTAL_POINTS = 800
VALUES_PER_LINE = 8


class Job:

    def __init__(self):
        settings.carregar_config()

        self.hash_file = BASE_DIR / ".last_hash"
        self.host = settings.get_host()
        self.endpoint = settings.get_endpoint()
        self.ext = settings.get_ext()
        self.pasta = Path(settings.get_pasta())
        self.pasta_formas_siou = Path(settings.get_pasta_formas_siou())

        if not str(self.pasta_formas_siou).strip():
            self.pasta_formas_siou = self._resolve_formas_siou_folder()

        self.pasta.mkdir(parents=True, exist_ok=True)

        self._last_state = None
        self._previous_state = None

    def _resolve_formas_siou_folder(self) -> Path:
        candidates = [
            BASE_DIR / "formas siou",
            BASE_DIR / "Formas Siou",
            BASE_DIR / "FormasSiou",
            self.pasta.parent / "formas siou",
            self.pasta.parent / "Formas Siou",
            self.pasta.parent / "FormasSiou",
        ]

        for candidate in candidates:
            if candidate.exists() and candidate.is_dir():
                return candidate

        return candidates[0]

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

        log(f"Job salvo: {file_path.name}")
        time.sleep(25)
        self._process_formas_siou_files(job_id)

        try:
            self.hash_file.write_text(current_hash)
        except Exception:
            pass

        self._last_state = "NEW"
        self._emit_state_log()

    # ==================================================
    # LOG CONTROLADO
    # ==================================================

    def _emit_state_log(self):
        if self._last_state == "UNCHANGED":
            self._previous_state = self._last_state
            return

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

    def _process_formas_siou_files(self, job_id: str):
        if not self.pasta_formas_siou.exists():
            log(f"Pasta 'formas siou' não encontrada: {self.pasta_formas_siou}")
            return

        padded_job_id = str(job_id).zfill(6)
        transformed_job_id = f"{padded_job_id[0]}T{padded_job_id[2:]}"

        for side in ("L", "R"):
            source = self.pasta_formas_siou / f"{side}{padded_job_id}.dat"
            target = self.pasta_formas_siou / f"{side}{transformed_job_id}.dat"

            if not source.exists():
                log(f"Arquivo não encontrado em formas siou: {source.name}")
                continue

            try:
                target.write_bytes(source.read_bytes())
                log(f"Arquivo gerado em formas siou: {target.name}")
            except Exception as e:
                log(f"Erro ao gerar arquivo '{target.name}': {e}")

    # ==================================================
    # REGRA PRINCIPAL DE ESPELHO
    # ==================================================

    def _extract_block(self, lines, start_index, prefix):

        block = [lines[start_index]]

        for line in lines[start_index + 1:]:

            if line.startswith(prefix):
                block.append(line)
            else:
                break

        return block

    def _ensure_complete_file(self, content: str) -> str:

        lines = content.splitlines()
        lines = self._mirror_semicolon_values(lines)

        trc_r_index = None
        trc_l_index = None
        z_r_index = None
        z_l_index = None

        # --------------------------------------
        # Detectar blocos
        # --------------------------------------

        for i, line in enumerate(lines):

            if line.startswith("TRCFMT"):
                parts = line.split(";")
                if len(parts) >= 4:
                    side = parts[3]

                    if side == "R":
                        trc_r_index = i

                    if side == "L":
                        trc_l_index = i

            if line.startswith("ZFMT"):
                parts = line.split(";")
                if len(parts) >= 4:
                    side = parts[3]

                    if side == "R":
                        z_r_index = i

                    if side == "L":
                        z_l_index = i

        # --------------------------------------
        # Extrair blocos existentes
        # --------------------------------------

        r_block = []
        l_block = []

        zr_block = []
        zl_block = []

        if trc_r_index is not None:
            r_block = lines[trc_r_index: trc_r_index + 1 + BLOCK_SIZE]

        if trc_l_index is not None:
            l_block = lines[trc_l_index: trc_l_index + 1 + BLOCK_SIZE]

        if z_r_index is not None:
            zr_block = self._extract_block(lines, z_r_index, "Z=")

        if z_l_index is not None:
            zl_block = self._extract_block(lines, z_l_index, "Z=")

        # --------------------------------------
        # Espelhar TRCFMT se necessário
        # --------------------------------------

        if r_block and not l_block:
            new_header = r_block[0].replace(";R;", ";L;")
            l_block = self._mirror_block(r_block, new_header)

        if l_block and not r_block:
            new_header = l_block[0].replace(";L;", ";R;")
            r_block = self._mirror_block(l_block, new_header)

        # --------------------------------------
        # Espelhar ZFMT se necessário
        # --------------------------------------

        if zr_block and not zl_block:
            new_header = zr_block[0].replace(";R;", ";L;")
            zl_block = [new_header] + zr_block[1:]

        if zl_block and not zr_block:
            new_header = zl_block[0].replace(";L;", ";R;")
            zr_block = [new_header] + zl_block[1:]

        # --------------------------------------
        # Limpar blocos antigos
        # --------------------------------------

        blocks_to_remove = (
                r_block + l_block + zr_block + zl_block
        )

        lines_clean = [
            l for l in lines
            if l not in blocks_to_remove
        ]

        # --------------------------------------
        # Inserir novos blocos após JOB
        # --------------------------------------

        job_index = next(
            i for i, l in enumerate(lines_clean)
            if l.startswith("JOB=")
        )

        insert_pos = job_index + 1

        new_lines = (
                lines_clean[:insert_pos]
                + r_block
                + l_block
                + zr_block
                + zl_block
                + lines_clean[insert_pos:]
        )

        return "\n".join(new_lines) + "\n"

    # ==================================================
    # ESPELHO CIRCULAR REAL (800 PONTOS)
    # ==================================================

    def _mirror_block(self, block: list[str], new_header: str) -> list[str]:

        values = []

        for line in block[1:]:
            if line.startswith("R="):
                nums = line[2:].split(";")
                values.extend(int(n) for n in nums if n.strip())

        if len(values) != TOTAL_POINTS:
            raise ValueError(
                f"Esperado {TOTAL_POINTS} pontos, encontrado {len(values)}"
            )

        # Espelhamento angular real
        mirrored = [
            values[(400 - i) % 800]
            for i in range(800)
        ]

        new_lines = []

        for i in range(0, TOTAL_POINTS, VALUES_PER_LINE):
            chunk = mirrored[i:i + VALUES_PER_LINE]
            line = "R=" + ";".join(str(v) for v in chunk)
            new_lines.append(line)
        print("espelhado")
        return [new_header] + new_lines

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
