from functools import lru_cache
import os
from pathlib import Path
import urllib.error
import urllib.request


BASE_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BASE_DIR.parent


def _ollama_has_model(base_url: str, model: str) -> bool:
    try:
        request = urllib.request.Request(
            f"{base_url.rstrip('/')}/api/show",
            data=(f'{{"name":"{model}"}}').encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=0.2) as response:
            return response.status == 200
    except (OSError, urllib.error.URLError):
        return False


def _default_ollama_model() -> str:
    if os.getenv("OLLAMA_MODEL"):
        return os.environ["OLLAMA_MODEL"]
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    if _ollama_has_model(base_url, "circuitsage:latest"):
        return "circuitsage:latest"
    return "gemma4:e4b"


class Settings:
    app_name: str = "CircuitSage"
    database_path: Path = Path(os.getenv("CIRCUITSAGE_DATABASE_PATH", BASE_DIR / "app" / "data" / "circuitsage.db"))
    upload_dir: Path = Path(os.getenv("CIRCUITSAGE_UPLOAD_DIR", BASE_DIR / "app" / "uploads"))
    sample_data_dir: Path = PROJECT_ROOT / "sample_data" / "op_amp_lab"
    frontend_dist_dir: Path = PROJECT_ROOT / "frontend" / "dist"
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model: str = _default_ollama_model()
    ollama_vision_model: str = os.getenv("OLLAMA_VISION_MODEL", "gemma3:4b")
    ollama_embed_model: str = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
    dev_mode: bool = os.getenv("CIRCUITSAGE_DEV", "1") == "1"
    frontend_origin: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
    hosted_demo: bool = os.getenv("CIRCUITSAGE_HOSTED", "0") == "1"
    hosted_rate_limit_per_minute: int = int(os.getenv("CIRCUITSAGE_HOSTED_RATE_LIMIT_PER_MINUTE", "30"))


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    return settings
