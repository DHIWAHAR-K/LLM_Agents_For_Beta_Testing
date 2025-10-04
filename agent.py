from rich import print as rprint

from llm import LLM
from schemas import Action, Persona


class LLMUserAgent:
    def __init__(self, llm: LLM, persona: Persona) -> None:
        self.llm = llm
        self.persona = persona

    def step(self, observation: str) -> Action:
        system = (
            "You are a synthetic beta tester for an application under test (AUT). "
            "Emit exactly one next action by calling the provided function. Follow the schema strictly."
        )
        user = f"""
Persona:
- name: {self.persona.name}
- goals: {self.persona.goals}
- tone: {self.persona.tone}
- noise_level: {self.persona.noise_level}

Observation:
"""{observation}"""

Guidelines:
- Choose ONE best next step toward persona goals.
- Keep 'target' short (e.g., '#signup-button', 'input#email', '/api/signup').
- If type='type', include payload={{"text":"..."}}.
- If type='report', include payload={{"issue":"..."}}.
"""
        data = self.llm.emit_action(system, user)
        try:
            action = Action(**data)
        except Exception as exc:  # noqa: BLE001 - convert to report
            action = Action(
                type="report",
                target="agent/schema",
                payload={"issue": str(exc), "raw": data},
            )
        rprint("[bold cyan]Proposed Action[/bold cyan]:", action.model_dump())
        return action
