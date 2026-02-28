# job.py
import re
import requests
from pathlib import Path


def extract_job_number(text: str) -> str | None:
    match = re.search(r"job\s*=\s*(\d+)", text, re.IGNORECASE)
    return match.group(1) if match else None


def download_job(host: str, endpoint: str) -> bytes:
    url = f"http://{host}{endpoint}"
    response = requests.get(url, timeout=3)
    response.raise_for_status()
    return response.content


def save_job(content: bytes, save_dir: Path, extension: str) -> str | None:
    text = content.decode(errors="ignore")
    job_number = extract_job_number(text)

    if not job_number:
        return None

    save_dir.mkdir(parents=True, exist_ok=True)
    file_path = save_dir / f"{job_number}.{extension}"
    file_path.write_bytes(content)

    return str(file_path)