from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Runtime configuration sourced from environment variables."""

    api_base_url: str = "http://localhost:8000"
    max_turns: int = 10
    max_retries: int = 2
    seed: int = 42
    version: str = "v1.0"

    class Config:
        env_file = "config/.env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra fields from .env file


def load_settings() -> Settings:
    """Provide a reusable settings singleton."""

    return Settings()


def load_model_config(path: str | Path = "config/model_config.yaml") -> dict[str, Any]:
    """Load multi-provider model configuration from YAML.

    Returns the full config with providers, temperature, and models list.
    """

    cfg_path = Path(path)
    if not cfg_path.exists():
        raise FileNotFoundError(f"Model config not found at {cfg_path}")

    with cfg_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    if "models" not in data:
        raise ValueError("model_config.yaml must contain a 'models' list.")

    # Multi-provider setup: each model has its own provider
    # Validate that each model has a provider field
    for model in data.get("models", []):
        if "provider" not in model:
            raise ValueError(f"Model '{model.get('name', 'unknown')}' must have a 'provider' field.")

    return data


settings = load_settings()
