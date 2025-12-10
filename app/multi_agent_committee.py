"""Multi-agent committee with discussion protocol and consensus voting."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple

from rich import print as rprint

from config import load_model_config
from .agent import LLMUserAgent
from .llm_client import LLMClient
from .schemas import Action, Persona


class AgentProposal:
    """Represents a single agent's action proposal with confidence."""

    def __init__(self, agent_id: int, action: Action, confidence: float, reasoning: str):
        self.agent_id = agent_id
        self.action = action
        self.confidence = confidence
        self.reasoning = reasoning

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "action": self.action.model_dump(),
            "confidence": self.confidence,
            "reasoning": self.reasoning,
        }


class MultiAgentCommittee:
    """Committee of multiple vision model agents that discuss and reach consensus."""

    def __init__(self, persona: Persona, num_agents: int = 4, models: List[str] | None = None):
        """Initialize committee with multiple agent instances, each using a different model.
        
        Args:
            persona: The persona each agent will adopt
            num_agents: Number of agents (defaults to 4 models from OpenAI, Google, Anthropic, xAI)
            models: Optional list of specific model names to use. If not provided, cycles through all available models.
        """
        self.persona = persona
        self.num_agents = num_agents
        
        # Load model configuration
        model_cfg = load_model_config()
        all_models_list = model_cfg.get("models", [])
        
        # If specific models are provided, use those; otherwise use all available models
        if models:
            # Map model names to model info from config
            model_name_to_info = {m.get("name"): m for m in all_models_list}
            models_list = []
            for model_name in models:
                if model_name in model_name_to_info:
                    models_list.append(model_name_to_info[model_name])
                else:
                    rprint(f"[yellow]Warning: Model '{model_name}' not found in config, skipping.[/yellow]")
        else:
            models_list = all_models_list
        
        if len(models_list) < num_agents:
            rprint(f"[yellow]Warning: Only {len(models_list)} models available but {num_agents} agents requested.[/yellow]")
            rprint(f"[yellow]Some agents will use duplicate models.[/yellow]")
        
        # Create agents with different models
        self.agents = []
        self.agent_models = []  # Track which model each agent uses
        
        for i in range(num_agents):
            # Cycle through available models if we have more agents than models
            model_info = models_list[i % len(models_list)]
            model_name = model_info.get("name")
            
            # Create LLM client with specific model
            client = LLMClient(model_name=model_name)
            agent = LLMUserAgent(persona, client=client)
            
            self.agents.append(agent)
            self.agent_models.append(model_name)
        
        rprint(f"[bold green]Multi-Agent Committee initialized with {num_agents} agents using different models:[/bold green]")
        for i, model_name in enumerate(self.agent_models):
            rprint(f"  [cyan]Agent {i+1}:[/cyan] {model_name}")

    def decide(self, observation: str, screenshot_path: str | None = None) -> Tuple[Action, List[Dict[str, Any]], Dict[str, float]]:
        """
        Multi-round committee decision process.
        
        Returns:
            Tuple of (consensus_action, all_proposals, confidence_scores)
        """
        rprint("\n[bold cyan]═══ COMMITTEE DISCUSSION ═══[/bold cyan]")
        
        # Round 1: Independent proposals
        rprint("\n[yellow]Round 1: Independent Proposals[/yellow]")
        round1_proposals = self._round1_independent(observation, screenshot_path)
        
        # Round 2: Discussion and refinement
        rprint("\n[yellow]Round 2: Discussion & Refinement[/yellow]")
        round2_proposals = self._round2_discussion(observation, screenshot_path, round1_proposals)
        
        # Round 3: Final consensus vote
        rprint("\n[yellow]Round 3: Consensus Vote[/yellow]")
        consensus_action, confidence_scores = self._round3_consensus(round2_proposals)
        
        # Collect all proposals for logging
        all_proposals = [p.to_dict() for p in round1_proposals + round2_proposals]
        
        rprint(f"\n[bold green]✓ Consensus reached: {consensus_action.type} → {consensus_action.target}[/bold green]")
        return consensus_action, all_proposals, confidence_scores

    def _round1_independent(self, observation: str, screenshot_path: str | None) -> List[AgentProposal]:
        """Round 1: Each agent proposes independently."""
        proposals = []
        
        for i, agent in enumerate(self.agents):
            try:
                action = agent.step(observation, screenshot_path)
                # Assign default confidence (can be extracted from model output in future)
                confidence = 0.8
                model_name = self.agent_models[i]
                reasoning = f"Agent {i+1} ({model_name}) independent analysis"
                proposal = AgentProposal(i + 1, action, confidence, reasoning)
                proposals.append(proposal)
                rprint(f"  [cyan]Agent {i+1} ({model_name}):[/cyan] {action.type} → {action.target[:50]}... (conf: {confidence:.2f})")
            except Exception as e:
                rprint(f"  [red]Agent {i+1} ({self.agent_models[i]}) failed:[/red] {e}")
        
        return proposals

    def _round2_discussion(
        self, 
        observation: str,
        screenshot_path: str | None,
        round1_proposals: List[AgentProposal]
    ) -> List[AgentProposal]:
        """Round 2: Agents see others' proposals and refine."""
        refined_proposals = []
        
        # Build discussion context
        proposals_summary = "\n".join([
            f"Agent {p.agent_id}: {p.action.type} → {p.action.target}"
            for p in round1_proposals
        ])
        
        discussion_context = f"""
Previous proposals from the committee:
{proposals_summary}

After reviewing the other agents' proposals, refine your decision.
Consider: Are you changing your mind? Sticking with your original proposal?
"""
        
        for i, agent in enumerate(self.agents):
            try:
                # Add discussion context to observation
                enhanced_observation = f"{observation}\n\n{discussion_context}"
                action = agent.step(enhanced_observation, screenshot_path)
                
                # Check if agent changed their mind
                original = round1_proposals[i] if i < len(round1_proposals) else None
                changed = original and (original.action.type != action.type or original.action.target != action.target)
                
                confidence = 0.9 if not changed else 0.85  # Higher confidence after discussion
                model_name = self.agent_models[i]
                reasoning = f"Agent {i+1} ({model_name}) refined after discussion" + (" (changed mind)" if changed else " (confirmed original)")
                
                proposal = AgentProposal(i + 1, action, confidence, reasoning)
                refined_proposals.append(proposal)
                
                status = "[yellow]changed[/yellow]" if changed else "[green]confirmed[/green]"
                rprint(f"  [cyan]Agent {i+1} ({model_name}):[/cyan] {action.type} → {action.target[:50]}... ({status})")
            except Exception as e:
                rprint(f"  [red]Agent {i+1} ({self.agent_models[i]}) failed in discussion:[/red] {e}")
        
        return refined_proposals

    def _round3_consensus(self, proposals: List[AgentProposal]) -> Tuple[Action, Dict[str, float]]:
        """Round 3: Vote for consensus based on confidence scores."""
        
        # Group proposals by action type and target
        action_votes: Dict[str, List[AgentProposal]] = {}
        
        for proposal in proposals:
            key = f"{proposal.action.type}::{proposal.action.target}"
            if key not in action_votes:
                action_votes[key] = []
            action_votes[key].append(proposal)
        
        # Calculate weighted votes (confidence * count)
        vote_scores = {}
        for key, voters in action_votes.items():
            total_confidence = sum(p.confidence for p in voters)
            vote_scores[key] = total_confidence
            rprint(f"  [dim]{key}[/dim] → {len(voters)} votes, total confidence: {total_confidence:.2f}")
        
        # Winner is highest confidence score
        winning_key = max(vote_scores, key=vote_scores.get)
        winning_proposals = action_votes[winning_key]
        consensus_action = winning_proposals[0].action  # Use first proposal of winning group
        
        # Calculate confidence scores per agent
        confidence_scores = {
            f"agent_{p.agent_id}": p.confidence
            for p in proposals
        }
        confidence_scores["consensus_strength"] = vote_scores[winning_key] / len(proposals)
        
        rprint(f"  [bold]Winner:[/bold] {winning_key} (score: {vote_scores[winning_key]:.2f})")
        
        return consensus_action, confidence_scores

