from __future__ import annotations

from rich import print as rprint

from .llm_client import LLMClient
from .schemas import Action, Persona


class LLMUserAgent:
    """Single-agent wrapper that prompts an LLM to emit the next JSON action."""

    def __init__(self, persona: Persona, client: LLMClient | None = None) -> None:
        self.persona = persona
        self.client = client or LLMClient()

    def step(self, observation: str, screenshot_path: str | None = None) -> Action:
        """Return the next action proposed by the model, with optional visual analysis."""

        system_prompt = (
            "You are a synthetic beta tester using browser automation. "
            "Respond with ONLY valid JSON matching this EXACT schema:\n"
            '{"type": "string", "target": "string", "payload": object or null}\n\n'
            "Do NOT add any wrapper keys like 'action' or 'action_input'. "
            "Do NOT add explanatory text. Return ONLY the raw JSON object."
        )

        user_prompt = f"""
Persona:
- name: {self.persona.name}
- goals: {self.persona.goals}

Current page observation:
{observation}

Your task: Choose ONE action to make progress toward completing ALL success criteria listed in the observation above.

DECISION PROCESS:
1. Read the "SUCCESS CRITERIA" section in the observation carefully
2. Check the current page state to see which criteria have been completed
3. If ALL success criteria are met, use the "report" action to signal completion
4. If any criteria remain incomplete, take the next logical action to progress toward them

VALID ACTION TYPES:
- "navigate": Navigate to a URL (target: "/path")
- "click": Click an element (target: CSS selector, payload: {{"selector": "..."}})
- "fill": Fill an input field (target: CSS selector, payload: {{"selector": "...", "value": "..."}})
- "scroll": Scroll the page (target: "down" or "up", payload: {{"pixels": 500}})
- "report": Report completion ONLY when ALL success criteria are met (target: "task_complete", payload: {{"issue": "Summary of completed criteria"}})

Examples:
1. Navigate: {{"type": "navigate", "target": "/", "payload": null}}
2. Click button: {{"type": "click", "target": "#add-to-cart", "payload": {{"selector": "#add-to-cart"}}}}
3. Fill form: {{"type": "fill", "target": "#email", "payload": {{"selector": "#email", "value": "test@example.com"}}}}
4. Scroll down: {{"type": "scroll", "target": "down", "payload": {{"pixels": 500}}}}
5. Report (ONLY when done): {{"type": "report", "target": "task_complete", "payload": {{"issue": "Successfully added product to cart and verified cart contents"}}}}

CRITICAL: 
- Return ONLY the JSON object. 
- Look at the screenshot to see the visual state of the page.
- Do NOT use "report" until ALL success criteria are completed.
- Take focused, goal-oriented actions that directly address the remaining success criteria.
"""

        data = self.client.emit_json(system_prompt, user_prompt, image_path=screenshot_path)
        try:
            # Handle various malformed responses from LLM
            # Case 1: LLM wraps in "action" key (extract it)
            if "action" in data and isinstance(data["action"], dict):
                data = data["action"]
            elif "action" in data and isinstance(data["action"], str):
                # If action is a string, use it as type
                action_val = data.pop("action")
                if "type" not in data:
                    data["type"] = action_val

            # Case 2: LLM uses "action_type" instead of "type"
            if "action_type" in data and "type" not in data:
                data["type"] = data.pop("action_type")

            # Case 3: LLM uses "action_input" with nested structure
            if "action_input" in data and isinstance(data["action_input"], dict):
                # Extract target from action_input if present
                if "target" in data["action_input"]:
                    data["target"] = data["action_input"]["target"]
                # Merge action_input into data
                for key, value in data["action_input"].items():
                    if key not in data:
                        data[key] = value
                del data["action_input"]

            # Case 4: If "action" is still a top-level key with string value, treat as "type"
            if "action" in data and "type" not in data:
                data["type"] = data.pop("action")

            # Remove extraneous keys that aren't part of Action schema
            if "method" in data:
                del data["method"]

            # Ensure required fields exist
            if "type" not in data:
                # Try to infer from other fields
                if "navigate" in str(data).lower():
                    data["type"] = "navigate"
                else:
                    data["type"] = "report"

            if "target" not in data:
                data["target"] = "/"

            action = Action(**data)
        except Exception as exc:  # fallback to report
            action = Action(
                type="report",
                target="agent/schema",
                payload={"issue": str(exc), "raw": data},
            )
        rprint("[bold cyan]Proposed Action[/bold cyan]:", action.model_dump())
        return action
