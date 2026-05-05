from functools import lru_cache
import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BASE_DIR.parent


class Settings:
    app_name: str = "CircuitSage"
    database_path: Path = BASE_DIR / "app" / "data" / "circuitsage.db"
    upload_dir: Path = BASE_DIR / "app" / "uploads"
    sample_data_dir: Path = PROJECT_ROOT / "sample_data" / "op_amp_lab"
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "gemma3:4b")
    ollama_vision_model: str = os.getenv("OLLAMA_VISION_MODEL", "gemma3:4b")
    ollama_embed_model: str = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
    dev_mode: bool = os.getenv("CIRCUITSAGE_DEV", "1") == "1"
    frontend_origin: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    return settings
