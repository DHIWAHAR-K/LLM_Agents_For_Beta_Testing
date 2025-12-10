from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml

from .schemas import Persona


def load_yaml(path: str | Path) -> Dict[str, Any]:
    """Generic YAML loader with sensible defaults."""

    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_persona(path: str | Path) -> Persona:
    """Load a persona definition from YAML and convert to Persona model."""

    data = load_yaml(path)
    return Persona(
        name=data.get("name", "Synthetic Tester"),
        goals=data.get("goals", ["Explore functionality"]),
        tone=data.get("tone", "neutral"),
        noise_level=float(data.get("noise_level", 0.0)),
        traits=data.get("traits", {}),
    )


def load_scenario(path: str | Path) -> Dict[str, Any]:
    """Load scenario metadata (initial observation, success criteria, etc.)."""

    return load_yaml(path)
