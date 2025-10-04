from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml

from schemas import Persona


def load_yaml(path: str | Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def compose_persona(yaml_path: str | Path) -> Persona:
    data = load_yaml(yaml_path)
    return Persona(
        name=data.get("name", "New User"),
        goals=data.get("goals", ["Explore", "Sign up"]),
        tone=data.get("tone", "neutral"),
        noise_level=float(data.get("noise_level", 0.1)),
        traits=data.get("traits", {}),
    )
