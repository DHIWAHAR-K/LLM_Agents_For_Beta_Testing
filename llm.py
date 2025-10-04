from __future__ import annotations

import json
from typing import Optional

from openai import OpenAI

from config import settings


class LLM:
    """Wrapper around local Ollama models with structured output via function calling."""

    def __init__(
        self,
        model: str | None = None,
        temperature: float | None = None,
        max_retries: int | None = None,
    ) -> None:
        # Use Ollama's OpenAI-compatible API
        self.client = OpenAI(
            base_url=settings.ollama_base_url,
            api_key="ollama"  # Ollama doesn't need a real API key
        )
        self.model = model or settings.default_model
        self.temperature = temperature if temperature is not None else settings.temperature
        self.max_retries = max_retries if max_retries is not None else settings.max_retries

    def emit_action(self, system: str, user: str) -> dict:
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "emit_action",
                    "description": "Emit exactly one next action for the test agent.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["tap", "type", "scroll", "navigate", "upload", "report"],
                            },
                            "target": {"type": "string"},
                            "payload": {"type": "object", "additionalProperties": True},
                        },
                        "required": ["type", "target"],
                        "additionalProperties": False,
                    },
                },
            }
        ]

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        last_err: Optional[Exception] = None
        for _ in range(self.max_retries + 1):
            try:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    temperature=self.temperature,
                    messages=messages,
                    tools=tools,
                    tool_choice={"type": "function", "function": {"name": "emit_action"}},
                )
                tcalls = resp.choices[0].message.tool_calls or []
                if not tcalls:
                    raise ValueError("No tool call returned.")
                return json.loads(tcalls[0].function.arguments)
            except Exception as exc:  # noqa: PERF203 - clarity
                last_err = exc
        raise RuntimeError(f"emit_action failed after retries. Last error: {last_err}")
