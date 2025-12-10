"""Simplified CSV storage for test sessions."""
from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4


class SessionStorage:
    """Handles CSV storage for test sessions."""

    def __init__(self, base_results_dir: str = "results"):
        self.base_results_dir = Path(base_results_dir)
        self.test_folder: Optional[Path] = None
        self.current_session_id: str | None = None
        self.current_rows: List[Dict[str, Any]] = []
        # Store persona and scenario metadata
        self.persona_name: str = ""
        self.persona_goals: List[str] = []
        self.scenario_name: str = ""
        self.scenario_description: str = ""
        self.test_objective: str = ""

    def _generate_test_name(self) -> str:
        """Generate test folder/file name from persona and scenario names."""
        persona = self.persona_name.lower().replace(" ", "_")
        scenario = self.scenario_name.lower().replace(" ", "_")
        return f"{persona}_{scenario}"

    def start_session(self, persona: Any = None, scenario: Dict[str, Any] = None) -> str:
        """Start a new session and return session ID.
        
        Args:
            persona: Persona object with name and goals attributes
            scenario: Scenario dict with name, description, and test_objective keys
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid4())[:8]
        self.current_session_id = f"{timestamp}_{unique_id}"
        self.current_rows = []
        
        # Store metadata for use in all log_turn calls
        if persona:
            self.persona_name = getattr(persona, "name", "Unknown")
            self.persona_goals = getattr(persona, "goals", [])
        
        if scenario:
            self.scenario_name = scenario.get("name", "Unknown")
            self.scenario_description = scenario.get("description", "")
            self.test_objective = scenario.get("test_objective", "")
        
        # Create test-specific folder
        test_name = self._generate_test_name()
        self.test_folder = self.base_results_dir / test_name
        self.test_folder.mkdir(parents=True, exist_ok=True)
        
        return self.current_session_id

    def log_turn(
        self,
        turn: int,
        action_type: str,
        action_target: str,
        screenshot_path: str,
        agent_proposals: List[Dict[str, Any]],
        consensus_action: Dict[str, Any],
        confidence_scores: Dict[str, float],
        success: bool,
        latency: float,
        safety_pass: bool,
        validators: List[str],
        conclusion: str = "",
        page_state: str = "",
        issues_found: str = "",
        issues_description: str = "",
    ) -> None:
        """Log a single turn to the session.
        
        Args:
            conclusion: The final report message from agents (empty for non-report actions)
            page_state: Optional snapshot of the page/app state after the action
            issues_found: Optional string describing issues discovered on this turn
            issues_description: Optional detailed description of issues found on this turn
        """
        if not self.current_session_id:
            raise RuntimeError("No active session. Call start_session() first.")

        row = {
            "session_id": self.current_session_id,
            "turn": turn,
            "timestamp": datetime.now().isoformat(),
            "action_type": action_type,
            "action_target": action_target,
            "screenshot_path": screenshot_path,
            "agent_proposals": json.dumps(agent_proposals),
            "consensus_action": json.dumps(consensus_action),
            "confidence_scores": json.dumps(confidence_scores),
            "success": success,
            "latency": round(latency, 3),
            "safety_pass": safety_pass,
            "validators": ";".join(validators) if validators else "",
            # Metadata columns (duplicated in every row)
            "persona_name": self.persona_name,
            "persona_goals": json.dumps(self.persona_goals),
            "scenario_name": self.scenario_name,
            "scenario_description": self.scenario_description,
            "test_objective": self.test_objective,
            "conclusion": conclusion,
            "page_state": page_state,
            "issues_found": issues_found,
            "issues_description": issues_description,
        }
        self.current_rows.append(row)

    def end_session(self) -> str:
        """End the session and write CSV file. Returns path to CSV."""
        if not self.current_session_id:
            raise RuntimeError("No active session to end.")
        
        if not self.test_folder:
            raise RuntimeError("Test folder not initialized.")

        # Save CSV in the test folder with test name
        test_name = self._generate_test_name()
        csv_path = self.test_folder / f"{test_name}.csv"

        # Write CSV
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            if self.current_rows:
                fieldnames = list(self.current_rows[0].keys())
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.current_rows)

        # Reset
        self.current_session_id = None
        self.current_rows = []

        return str(csv_path)
    
    def get_screenshots_dir(self) -> str:
        """Get the screenshots directory for this test."""
        if not self.test_folder:
            raise RuntimeError("Test folder not initialized.")
        screenshots_dir = self.test_folder / "screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        return str(screenshots_dir)
