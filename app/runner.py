from __future__ import annotations

from typing import Dict, Optional

from config import settings
from .agent import LLMUserAgent
from .aut_adapter import RESTAdapter
from .schemas import Persona
from .storage import end_session, init_storage, log_event, log_turn, start_session
from .validators import validate_action


def run_session(
    persona: Persona,
    scenario: Dict[str, object],
    adapter: Optional[RESTAdapter] = None,
    agent: Optional[LLMUserAgent] = None,
) -> dict[str, object]:
    """Execute a full test session for the given persona."""

    init_storage()
    adapter = adapter or RESTAdapter()
    agent = agent or LLMUserAgent(persona)

    session_id = start_session(
        persona=persona,
        scenario=scenario.get("name", "scenario"),
        version=settings.version,
        model_name="ollama",
    )

    log_event(session_id, "session_start", {"persona": persona.name})

    observation = scenario.get("initial_observation", "System ready.")
    max_turns = settings.max_turns
    success = True
    turns_executed = 0

    for turn_idx in range(1, max_turns + 1):
        turns_executed = turn_idx
        log_event(session_id, "turn_start", {"turn": turn_idx})

        action = agent.step(observation)
        passed, reasons = validate_action(action, persona)

        if not passed:
            log_event(
                session_id,
                "validation_failed",
                {"turn": turn_idx, "reasons": reasons, "action": action.model_dump()},
            )
            log_turn(
                session_id=session_id,
                turn_number=turn_idx,
                persona=persona,
                observation=observation,
                action=action,
                latency=0.0,
                oracle_pass=False,
                validations=reasons,
            )
            success = False
            break

        observation, latency = adapter.execute(action)
        log_turn(
            session_id=session_id,
            turn_number=turn_idx,
            persona=persona,
            observation=observation,
            action=action,
            latency=latency,
            oracle_pass=True,
            validations=["ok"],
        )

    status = "completed" if success else "failed"
    end_session(session_id, status=status)
    log_event(session_id, "session_end", {"status": status})

    return {
        "session_id": session_id,
        "status": status,
        "success": success,
        "turns_executed": turns_executed,
        "persona": persona.model_dump(),
        "scenario": scenario,
    }
