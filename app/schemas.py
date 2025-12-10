from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class Persona(BaseModel):
    name: str
    goals: List[str]
    tone: Literal["neutral", "casual", "formal", "impatient"] = "neutral"
    noise_level: float = Field(0.0, ge=0.0, le=1.0)
    traits: Dict[str, Any] = Field(default_factory=dict)


class Action(BaseModel):
    type: Literal["tap", "type", "scroll", "navigate", "upload", "report", "click", "fill"]
    target: str
    payload: Optional[Dict[str, Any]] = None
