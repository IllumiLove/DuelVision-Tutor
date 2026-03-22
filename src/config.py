from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DECKS_DIR = DATA_DIR / "decks"
LOGS_DIR = DATA_DIR / "logs"
ASSETS_DIR = PROJECT_ROOT / "assets"
TEMPLATES_DIR = ASSETS_DIR / "templates"


class CaptureConfig(BaseModel):
    target_window: str = "masterduel"
    interval: float = 1.0
    fast_interval: float = 0.5
    base_resolution: list[int] = [1920, 1080]


class OcrConfig(BaseModel):
    engine: str = "paddleocr"
    language: str = "ch"
    use_gpu: bool = True


class DeepSeekConfig(BaseModel):
    model: str = "deepseek-chat"
    base_url: str = "https://api.deepseek.com"
    max_tokens: int = 500
    temperature: float = 0.3


class OllamaConfig(BaseModel):
    model: str = "qwen2.5:7b"
    base_url: str = "http://localhost:11434"


class LLMConfig(BaseModel):
    provider: str = "deepseek"
    deepseek: DeepSeekConfig = DeepSeekConfig()
    ollama: OllamaConfig = OllamaConfig()


class OverlayConfig(BaseModel):
    opacity: float = 0.88
    width: int = 420
    height: int = 500
    font_size: int = 14
    position: str = "right"


class LoggerConfig(BaseModel):
    enabled: bool = True
    max_matches: int = 100
    history_context: int = 3


class DatabaseConfig(BaseModel):
    auto_update: bool = True
    update_interval_days: int = 7


class AppConfig(BaseModel):
    capture: CaptureConfig = CaptureConfig()
    ocr: OcrConfig = OcrConfig()
    llm: LLMConfig = LLMConfig()
    overlay: OverlayConfig = OverlayConfig()
    logger: LoggerConfig = LoggerConfig()
    database: DatabaseConfig = DatabaseConfig()


def load_config(path: Path | None = None) -> AppConfig:
    """Load config from YAML file, falling back to defaults."""
    if path is None:
        path = PROJECT_ROOT / "config.yaml"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        return AppConfig(**raw)
    return AppConfig()


def get_api_key() -> str:
    """Get DeepSeek API key from environment."""
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not key or key == "sk-your-key-here":
        raise ValueError("Please set DEEPSEEK_API_KEY in .env file")
    return key


# Ensure data directories exist
for _d in (DATA_DIR, DECKS_DIR, LOGS_DIR, ASSETS_DIR, TEMPLATES_DIR):
    _d.mkdir(parents=True, exist_ok=True)
