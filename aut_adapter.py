from __future__ import annotations

import time
from typing import Tuple

from config import settings
from schemas import Action


class APIAdapter:
    """Map actions to HTTP calls (mocked for demo)."""

    def __init__(self, base_url: str | None = None, timeout: float = 10.0) -> None:
        self.base_url = (base_url or settings.api_base_url).rstrip("/")
        self.timeout = timeout

    def execute(self, action: Action) -> Tuple[str, float]:
        """Return a tuple of (observation, latency_seconds)."""

        start = time.time()
        if action.type == "navigate":
            obs = f"GET {self.base_url}{action.target} -> 200 OK (mock)"
        elif action.type == "type":
            text = action.payload.get("text", "") if action.payload else ""
            obs = f"Typed into {action.target}: {text}"
        elif action.type == "tap":
            obs = f"Tapped {action.target}"
        elif action.type == "scroll":
            obs = f"Scrolled on {action.target}"
        elif action.type == "upload":
            filename = action.payload.get("filename", "file.txt") if action.payload else "file.txt"
            obs = f"Uploaded {filename} to {action.target}"
        else:
            issue = action.payload.get("issue", "") if action.payload else ""
            obs = f"Report: {issue}"
        return obs, time.time() - start
