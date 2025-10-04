"""
Agent pool for multi-agent orchestration with committee routing.

Supports multiple routing policies:
- round_robin: Rotate through agents
- weighted: Sample based on weights
- failover: Try agents in order until success
- committee: Get votes from N agents and use majority
"""

from __future__ import annotations

import random
from collections import Counter
from typing import Any, Literal

from agent import LLMUserAgent
from model_registry import ModelRegistry
from validators import schema_check, goal_bias_check
from schemas import Action, Persona


RoutingPolicy = Literal["round_robin", "weighted", "failover", "committee"]


class AgentPool:
    """
    Pool of multiple LLM agents with flexible routing policies.
    
    Enables committee-based decision making and failover strategies.
    """
    
    def __init__(self, registry: ModelRegistry, routing_cfg: dict[str, Any]):
        """
        Initialize agent pool.
        
        Args:
            registry: ModelRegistry instance
            routing_cfg: Configuration dict with:
                - policy: Routing policy name
                - models: List of model names to use
                - weights: Optional weights for weighted routing
                - committee_size: For committee routing, how many agents to consult
                - vote_threshold: Minimum votes needed for committee consensus
        """
        self.registry = registry
        self.policy: RoutingPolicy = routing_cfg.get("policy", "round_robin")
        self.model_names: list[str] = routing_cfg.get("models", ["gpt-4o-mini"])
        self.weights: list[float] | None = routing_cfg.get("weights")
        self.committee_size: int = routing_cfg.get("committee_size", len(self.model_names))
        self.vote_threshold: int = routing_cfg.get("vote_threshold", (self.committee_size // 2) + 1)
        
        self._round_robin_idx = 0
        self._agents_cache: dict[str, LLMUserAgent] = {}
    
    def _get_agent(self, model_name: str, persona: Persona) -> LLMUserAgent:
        """Get or create agent for model."""
        cache_key = f"{model_name}_{persona.name}"
        
        if cache_key not in self._agents_cache:
            llm = self.registry.get(model_name)
            self._agents_cache[cache_key] = LLMUserAgent(llm, persona)
        
        return self._agents_cache[cache_key]
    
    def run_turn(
        self,
        observation: str,
        persona: Persona,
        seed: int | None = None,
    ) -> dict[str, Any]:
        """
        Execute a turn using the configured routing policy.
        
        Args:
            observation: Current observation from AUT
            persona: Persona making the decision
            seed: Random seed for reproducibility
            
        Returns:
            dict: {
                'verdict': Action,                    # Final action to execute
                'per_agent_results': list[dict],      # Individual agent results
                'routing_policy': str,                 # Policy used
                'consensus': bool,                     # Whether agents agreed
                'disagreements': list[dict]            # If any disagreements
            }
        """
        if seed is not None:
            random.seed(seed)
        
        if self.policy == "round_robin":
            return self._run_round_robin(observation, persona)
        elif self.policy == "weighted":
            return self._run_weighted(observation, persona)
        elif self.policy == "failover":
            return self._run_failover(observation, persona)
        elif self.policy == "committee":
            return self._run_committee(observation, persona)
        else:
            raise ValueError(f"Unknown routing policy: {self.policy}")
    
    def _run_round_robin(self, observation: str, persona: Persona) -> dict[str, Any]:
        """Round-robin: rotate through agents."""
        model_name = self.model_names[self._round_robin_idx % len(self.model_names)]
        self._round_robin_idx += 1
        
        agent = self._get_agent(model_name, persona)
        action = agent.step(observation)
        
        return {
            "verdict": action,
            "per_agent_results": [
                {
                    "model": model_name,
                    "action": action,
                    "selected": True,
                }
            ],
            "routing_policy": "round_robin",
            "consensus": True,
            "disagreements": [],
        }
    
    def _run_weighted(self, observation: str, persona: Persona) -> dict[str, Any]:
        """Weighted: sample based on weights."""
        weights = self.weights or [1.0] * len(self.model_names)
        model_name = random.choices(self.model_names, weights=weights)[0]
        
        agent = self._get_agent(model_name, persona)
        action = agent.step(observation)
        
        return {
            "verdict": action,
            "per_agent_results": [
                {
                    "model": model_name,
                    "action": action,
                    "selected": True,
                }
            ],
            "routing_policy": "weighted",
            "consensus": True,
            "disagreements": [],
        }
    
    def _run_failover(self, observation: str, persona: Persona) -> dict[str, Any]:
        """Failover: try agents in order until one passes oracles."""
        per_agent_results = []
        
        for model_name in self.model_names:
            agent = self._get_agent(model_name, persona)
            action = agent.step(observation)
            
            # Check if action passes oracles
            schema_valid = schema_check(action)
            goal_valid = goal_bias_check(action, persona)
            passed = schema_valid and goal_valid
            
            per_agent_results.append({
                "model": model_name,
                "action": action,
                "schema_valid": schema_valid,
                "goal_valid": goal_valid,
                "selected": passed,
            })
            
            if passed:
                return {
                    "verdict": action,
                    "per_agent_results": per_agent_results,
                    "routing_policy": "failover",
                    "consensus": True,
                    "disagreements": [],
                }
        
        # All agents failed, use last one
        return {
            "verdict": per_agent_results[-1]["action"],
            "per_agent_results": per_agent_results,
            "routing_policy": "failover",
            "consensus": False,
            "disagreements": ["All agents failed oracle checks"],
        }
    
    def _run_committee(self, observation: str, persona: Persona) -> dict[str, Any]:
        """Committee: get votes from multiple agents and use majority."""
        # Sample agents for committee
        committee_models = random.sample(
            self.model_names,
            min(self.committee_size, len(self.model_names)),
        )
        
        per_agent_results = []
        actions_list = []
        
        # Collect votes from each agent
        for model_name in committee_models:
            agent = self._get_agent(model_name, persona)
            action = agent.step(observation)
            
            # Check if action passes oracles
            schema_valid = schema_check(action)
            goal_valid = goal_bias_check(action, persona)
            
            per_agent_results.append({
                "model": model_name,
                "action": action,
                "schema_valid": schema_valid,
                "goal_valid": goal_valid,
                "selected": False,  # Will update for winning action
            })
            
            if schema_valid and goal_valid:
                actions_list.append(action)
        
        if not actions_list:
            # No valid actions, use first agent's action
            verdict = per_agent_results[0]["action"]
            per_agent_results[0]["selected"] = True
            consensus = False
            disagreements = ["No agents produced valid actions"]
        else:
            # Vote by action type + target (simplified voting)
            action_keys = [f"{a.type}:{a.target}" for a in actions_list]
            vote_counts = Counter(action_keys)
            winning_key, winning_votes = vote_counts.most_common(1)[0]
            
            # Find corresponding action
            verdict = next(
                a for a, k in zip(actions_list, action_keys) if k == winning_key
            )
            
            # Mark winning agents
            for result, key in zip(per_agent_results, action_keys):
                if key == winning_key:
                    result["selected"] = True
            
            # Check consensus
            consensus = winning_votes >= self.vote_threshold
            
            # Find disagreements
            disagreements = []
            if len(vote_counts) > 1:
                for key, count in vote_counts.items():
                    if key != winning_key:
                        disagreements.append({
                            "action_key": key,
                            "votes": count,
                        })
        
        return {
            "verdict": verdict,
            "per_agent_results": per_agent_results,
            "routing_policy": "committee",
            "consensus": consensus,
            "disagreements": disagreements,
        }

