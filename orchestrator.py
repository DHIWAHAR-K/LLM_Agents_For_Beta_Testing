"""
Orchestrator for managing test sessions with multi-agent support.

Coordinates sessions, agents, oracles, and storage with optional committee routing.
"""

from __future__ import annotations

from typing import Any

from agent import LLMUserAgent
from multi_agent_router import AgentPool
from aut_adapter import APIAdapter
from config import settings
from model_registry import ModelRegistry, get_default_registry
from validators import goal_bias_check, schema_check, check_safety, get_safety_profile_for_persona
from schemas import Persona
import storage


def run_session(
    persona: Persona,
    initial_observation: str,
    agent: LLMUserAgent | None = None,
    adapter: APIAdapter | None = None,
    max_turns: int | None = None,
    use_multi_agent: bool = False,
    version: str | None = None,
    scenario: str = "default",
) -> dict[str, Any]:
    """
    Run a complete testing session.
    
    Args:
        persona: Persona to test with
        initial_observation: Initial AUT state
        agent: Single agent (if not using multi-agent mode)
        adapter: AUT adapter
        max_turns: Maximum number of turns
        use_multi_agent: Whether to use multi-agent committee
        version: Version tag for regression tracking
        scenario: Scenario name
        
    Returns:
        dict: Session results with session_id and status
    """
    storage.init_db()
    
    # Use defaults if not provided
    adapter = adapter or APIAdapter()
    turns = max_turns or settings.max_turns
    version = version or settings.version
    
    # Determine model name for logging
    if use_multi_agent:
        model_name = f"committee:{settings.routing_policy}"
        registry = get_default_registry()
        agent_pool = AgentPool(
            registry,
            {
                "policy": settings.routing_policy,
                "models": settings.routing_models,
                "weights": settings.routing_weights,
                "committee_size": settings.committee_size,
                "vote_threshold": settings.committee_threshold,
            },
        )
    else:
        model_name = settings.default_model
        if agent is None:
            raise ValueError("Must provide agent when not using multi-agent mode")
    
    # Start session
    session_id = storage.start_session(
        persona=persona,
        scenario=scenario,
        version=version,
        model_name=model_name,
        seed=settings.seed,
    )
    
    storage.log_event(session_id, "session_start", {
        "persona": persona.name,
        "scenario": scenario,
        "use_multi_agent": use_multi_agent,
    })
    
    observation = initial_observation
    success = True
    
    try:
        for turn_num in range(1, turns + 1):
            storage.log_event(session_id, "turn_start", {"turn": turn_num})
            
            # Generate action (single agent or committee)
            if use_multi_agent:
                pool_result = agent_pool.run_turn(observation, persona, settings.seed + turn_num)
                action = pool_result["verdict"]
                
                # Log committee details
                storage.log_event(session_id, "committee_vote", {
                    "policy": pool_result["routing_policy"],
                    "consensus": pool_result["consensus"],
                    "disagreements": pool_result["disagreements"],
                    "agents_count": len(pool_result["per_agent_results"]),
                })
            else:
                action = agent.step(observation)
            
            # Oracle checks
            schema_valid = schema_check(action)
            goal_valid = goal_bias_check(action, persona)
            
            # Safety check
            safety_profile = get_safety_profile_for_persona(persona)
            safety_result = check_safety(action, observation, persona, safety_profile)
            safety_valid = safety_result["safe"]
            
            oracle_pass = schema_valid and goal_valid and safety_valid
            
            if not oracle_pass:
                # Log failure reason
                failure_reasons = []
                if not schema_valid:
                    failure_reasons.append("schema_check_failed")
                if not goal_valid:
                    failure_reasons.append("goal_bias_check_failed")
                if not safety_valid:
                    failure_reasons.append(f"safety_check_failed: {safety_result['reason']}")
                
                storage.log_event(session_id, "oracle_failure", {
                    "turn": turn_num,
                    "reasons": failure_reasons,
                    "action": action.model_dump(),
                })
                
                # Log the failed turn
                storage.log_step(
                    session_id=session_id,
                    turn_number=turn_num,
                    persona=persona,
                    observation=observation,
                    action=action,
                    latency=0.0,
                    oracle_pass=False,
                )
                
                success = False
                break
            
            # Execute action
            observation, latency = adapter.execute(action)
            
            # Log successful turn
            storage.log_step(
                session_id=session_id,
                turn_number=turn_num,
                persona=persona,
                observation=observation,
                action=action,
                latency=latency,
                oracle_pass=True,
            )
            
            storage.log_event(session_id, "turn_complete", {
                "turn": turn_num,
                "action_type": action.type,
                "latency": latency,
            })
        
        # Session completed all turns
        storage.log_event(session_id, "session_complete", {
            "turns_completed": turn_num if 'turn_num' in locals() else 0,
            "success": success,
        })
        
    except Exception as exc:
        # Log exception
        storage.log_event(session_id, "session_error", {
            "error": str(exc),
            "error_type": type(exc).__name__,
        })
        success = False
        raise
    
    finally:
        # End session
        status = "completed" if success else "failed"
        storage.end_session(session_id, status)
    
    return {
        "session_id": session_id,
        "success": success,
        "status": status,
        "turns_executed": turn_num if 'turn_num' in locals() else 0,
    }
