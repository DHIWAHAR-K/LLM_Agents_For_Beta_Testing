"""
Experiment Runner Framework

Orchestrates experiment execution with configuration-driven approach.
Handles seeding, parallel/sequential execution, result logging, and checkpointing.

Usage:
    python experiments/runner.py --config experiments/configs/experiment_1a_multi_agent_scaling.yaml
    python experiments/runner.py --experiment 1a --runs 5
"""

import sys
import os
import argparse
import yaml
import sqlite3
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import time

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.multi_agent_runner import run_multi_agent_session
from app.browser_adapter import BrowserAdapter
from app.storage import SessionStorage
from app.multi_agent_committee import MultiAgentCommittee
from app.schemas import Persona
from experiments.metrics_collector import MetricsCollector
from experiments.bug_injector import BugInjector
from experiments.regressions import RegressionManager


class ExperimentRunner:
    """Manages experiment execution"""

    def __init__(self, config_path: str, db_path: str = "experiments/results/experiments.db"):
        self.config_path = config_path
        self.db_path = db_path
        self.config = self._load_config()
        self._init_database()

        self.metrics_collector = MetricsCollector(db_path)
        self.bug_injector = BugInjector(db_path)
        self.regression_manager = RegressionManager(db_path)

    def _load_config(self) -> Dict:
        """Load experiment configuration from YAML"""
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)

    def _init_database(self) -> None:
        """Initialize database with schema"""
        conn = sqlite3.connect(self.db_path)

        # Read and execute schema
        schema_path = Path(__file__).parent / "schema.sql"
        with open(schema_path, 'r') as f:
            conn.executescript(f.read())

        conn.close()

    def register_experiment(self) -> int:
        """Register experiment in database and return experiment_id"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check if experiment already exists
        cursor.execute("SELECT id FROM experiments WHERE name = ?", (self.config['name'],))
        existing = cursor.fetchone()
        
        if existing:
            experiment_id = existing[0]
            print(f"✓ Using existing experiment: {self.config['name']} (ID: {experiment_id})")
            conn.close()
            return experiment_id

        # Register new experiment
        baseline_info = self.config.get('baseline', {})
        baseline_str = f"{baseline_info.get('paper', 'N/A')}: {baseline_info.get('value', 'N/A')}"

        cursor.execute("""
            INSERT INTO experiments (name, tier, description, research_question, baseline_paper, baseline_score)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            self.config['name'],
            self.config['tier'],
            self.config['description'],
            self.config['research_question'],
            baseline_info.get('paper', ''),
            baseline_str
        ))

        experiment_id = cursor.lastrowid
        conn.commit()
        conn.close()

        print(f"✓ Registered experiment: {self.config['name']} (ID: {experiment_id})")
        return experiment_id

    def load_ground_truth(self, experiment_id: int) -> None:
        """Load ground truth bugs/regressions if applicable"""
        if self.config['tier'] == 'your_aut':
            if 'persona_diversity' in self.config['name'] or 'security' in self.config['name']:
                self.bug_injector.load_ground_truth(experiment_id)

            if 'regression' in self.config['name']:
                self.regression_manager.load_regressions()

    async def run_experiment(self) -> None:
        """Execute all runs for this experiment"""
        experiment_id = self.register_experiment()
        self.load_ground_truth(experiment_id)

        configurations = self.config['configurations']
        scenarios = self.config['test_scenarios']
        seeds = self.config['execution']['seeds']
        runs_per_config = self.config['execution']['runs_per_configuration']

        total_runs = len(configurations) * len(scenarios) * runs_per_config
        current_run = 0
        successful_runs = 0

        print(f"\n{'='*80}")
        print(f"Starting Experiment: {self.config['name']}")
        print(f"Total Configurations: {len(configurations)}")
        print(f"Total Scenarios: {len(scenarios)}")
        print(f"Runs per Config: {runs_per_config}")
        print(f"Total Runs: {total_runs}")
        print(f"{'='*80}\n")

        for config in configurations:
            for scenario in scenarios:
                for run_num, seed in enumerate(seeds[:runs_per_config], 1):
                    current_run += 1
                    print(f"\n[{current_run}/{total_runs}] Running: {config['name']} × {scenario['name']} (seed={seed})")

                    try:
                        # Check if run already exists and is complete
                        conn = sqlite3.connect(self.db_path)
                        cursor = conn.cursor()
                        cursor.execute("""
                            SELECT id, success, end_time FROM runs 
                            WHERE experiment_id = ? AND run_number = ? AND seed = ?
                        """, (experiment_id, current_run, seed))
                        existing_run = cursor.fetchone()
                        conn.close()

                        if existing_run:
                            run_id, success, end_time = existing_run
                            if end_time is not None:  # Run is complete
                                print(f"  ⊙ Run {run_id} already completed, skipping...")
                                if success:
                                    successful_runs += 1
                                continue

                        run_id = await self._execute_single_run(
                            experiment_id=experiment_id,
                            config=config,
                            scenario=scenario,
                            seed=seed,
                            run_number=current_run  # Use global run number instead of per-config
                        )

                        # Calculate and save metrics
                        print(f"  → Calculating metrics for run {run_id}...")
                        metrics = self.metrics_collector.calculate_run_metrics(run_id)
                        self.metrics_collector.save_metrics(run_id, metrics)

                        print(f"  ✓ Run {run_id} completed successfully")
                        print(f"    Success Rate: {metrics.task_success_rate:.2f}%")
                        print(f"    Safety Rate: {metrics.safety_pass_rate:.2f}%")
                        print(f"    Latency (P95): {metrics.p95_latency_seconds:.2f}s")
                        successful_runs += 1

                    except Exception as e:
                        import traceback
                        print(f"  ✗ Run failed: {str(e)}")
                        print(f"  Traceback: {traceback.format_exc()}")
                        continue

        print(f"\n{'='*80}")
        print(f"Experiment Complete: {self.config['name']}")
        print(f"Successful Runs: {successful_runs}/{total_runs}")
        print(f"{'='*80}\n")

    async def _execute_single_run(self, experiment_id: int, config: Dict, scenario: Dict,
                           seed: int, run_number: int) -> int:
        """Execute a single test run"""

        # Create run record
        run_id = self._create_run_record(experiment_id, config, scenario, seed, run_number)

        # Load persona
        persona_name = config.get('persona') or scenario.get('persona')
        persona_path = f"personas/{persona_name}.yaml"
        with open(persona_path, 'r') as f:
            persona_data = yaml.safe_load(f)
            persona = Persona(**persona_data)

        # Load scenario
        scenario_path = f"scenarios/{scenario['name']}.yaml"
        with open(scenario_path, 'r') as f:
            scenario_data = yaml.safe_load(f)

        try:
            # Use existing run_multi_agent_session function
            # Note: This uses your existing infrastructure
            num_agents = config['num_agents']
            models = config.get('models')  # Get models list from config if specified

            result = await run_multi_agent_session(
                persona=persona,
                scenario=scenario_data,
                num_agents=num_agents,
                models=models
            )

            # Parse CSV to log turns to database
            csv_path = result.get('csv_path')
            if csv_path and Path(csv_path).exists():
                self._import_csv_to_database(run_id, csv_path)
            else:
                print(f"  ⚠ Warning: CSV file not found at {csv_path}, skipping database import")

            # Update run completion
            self._update_run_completion(run_id, success=result['success'])

        except Exception as e:
            self._update_run_completion(run_id, success=False, error=str(e))
            raise

        return run_id

    def _create_run_record(self, experiment_id: int, config: Dict, scenario: Dict,
                          seed: int, run_number: int) -> int:
        """Create a run record in database, or return existing if it already exists"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check if run already exists
        cursor.execute("""
            SELECT id FROM runs 
            WHERE experiment_id = ? AND run_number = ? AND seed = ?
        """, (experiment_id, run_number, seed))
        
        existing = cursor.fetchone()
        if existing:
            run_id = existing[0]
            conn.close()
            return run_id

        # Create new run record
        session_id = f"exp{experiment_id}_run{run_number}_s{seed}"

        cursor.execute("""
            INSERT INTO runs (
                experiment_id, run_number, seed, config_json,
                persona_name, scenario_name, model_provider, num_agents,
                vision_enabled, aut_version, session_id, start_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            experiment_id,
            run_number,
            seed,
            json.dumps(config),
            config.get('persona', scenario.get('persona')),
            scenario['name'],
            config['models'][0] if len(config['models']) == 1 else 'committee',
            config['num_agents'],
            config.get('vision_enabled', True),
            config.get('aut_version', 'v1.0'),
            session_id,
            datetime.now().isoformat()
        ))

        run_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return run_id

    def _import_csv_to_database(self, run_id: int, csv_path: str) -> None:
        """Import CSV data from existing run into database"""
        import csv

        if not Path(csv_path).exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Parse turn data
                turn = int(row.get('turn', 0))

                # Parse confidence scores - can be JSON dict or simple value
                confidence_score = 1.0
                if row.get('confidence_scores'):
                    try:
                        scores = json.loads(row['confidence_scores'])
                        if isinstance(scores, dict):
                            # Take first/max confidence score from dict
                            confidence_score = max(scores.values()) if scores else 1.0
                        elif isinstance(scores, (list, tuple)) and len(scores) > 0:
                            confidence_score = float(scores[0])
                        else:
                            confidence_score = float(scores)
                    except (json.JSONDecodeError, ValueError, TypeError):
                        confidence_score = 1.0

                # Insert into turns table
                cursor.execute("""
                    INSERT INTO turns (
                        run_id, turn_number, action_type, action_target, action_value,
                        screenshot_path, validators_passed, validators_failed,
                        success, safety_pass, latency_seconds,
                        num_unique_proposals, agreement_percentage, consensus_confidence,
                        element_found, correct_element
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    run_id,
                    turn,
                    row.get('action_type', ''),
                    row.get('action_target', ''),
                    row.get('action_value', ''),
                    row.get('screenshot_path', ''),
                    row.get('validators', ''),
                    '',
                    row.get('success', 'False') == 'True',
                    row.get('safety_pass', 'True') == 'True',
                    float(row.get('latency', 0.0) or 0.0),
                    len(json.loads(row.get('agent_proposals', '[]'))) if row.get('agent_proposals') else 1,
                    100.0,  # Calculate from proposals if needed
                    confidence_score,
                    True,
                    True
                ))

                # Parse and insert proposals
                if row.get('agent_proposals'):
                    try:
                        proposals = json.loads(row['agent_proposals'])
                        for i, proposal in enumerate(proposals):
                            cursor.execute("""
                                INSERT INTO proposals (
                                    run_id, turn_number, round_number, agent_id, model_provider,
                                    action_type, action_target, action_value, reasoning,
                                    confidence_score, was_selected, changed_from_previous_round
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                run_id, turn, proposal.get('round', 1), i,
                                proposal.get('model', 'unknown'),
                                proposal.get('action', {}).get('type', ''),
                                proposal.get('action', {}).get('target', ''),
                                proposal.get('action', {}).get('value', ''),
                                proposal.get('reasoning', ''),
                                proposal.get('confidence_score', 0.5),
                                False,
                                False
                            ))
                    except (json.JSONDecodeError, KeyError) as e:
                        print(f"Warning: Could not parse proposals for turn {turn}: {e}")

        conn.commit()
        conn.close()

    def _update_run_completion(self, run_id: int, success: bool, error: Optional[str] = None) -> None:
        """Update run completion status"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE runs
            SET end_time = ?,
                success = ?,
                error_message = ?,
                total_turns = (SELECT COUNT(*) FROM turns WHERE run_id = ?),
                duration_seconds = (
                    julianday(?) - julianday(start_time)
                ) * 86400.0
            WHERE id = ?
        """, (
            datetime.now().isoformat(),
            success,
            error,
            run_id,
            datetime.now().isoformat(),
            run_id
        ))

        conn.commit()
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Run experiments for LLM Beta Testing Framework")
    parser.add_argument('--config', type=str, help='Path to experiment config YAML')
    parser.add_argument('--experiment', type=str, help='Experiment shorthand (1a, 1b, 1c, etc.)')
    parser.add_argument('--db', type=str, default='experiments/results/experiments.db',
                       help='Path to SQLite database')
    parser.add_argument('--dry-run', action='store_true', help='Print config without running')

    args = parser.parse_args()

    # Map experiment shorthands to config files
    experiment_map = {
        '1a': 'experiments/configs/experiment_1a_multi_agent_scaling.yaml',
        '1b': 'experiments/configs/experiment_1b_persona_diversity.yaml',
        '1c': 'experiments/configs/experiment_1c_regression_detection.yaml',
        '2': 'experiments/configs/experiment_2_owasp_juice_shop.yaml',
        '3': 'experiments/configs/experiment_3_webshop.yaml',
    }

    if args.experiment:
        config_path = experiment_map.get(args.experiment)
        if not config_path:
            print(f"Error: Unknown experiment '{args.experiment}'")
            print(f"Available: {', '.join(experiment_map.keys())}")
            return
    elif args.config:
        config_path = args.config
    else:
        print("Error: Must specify either --config or --experiment")
        return

    if not os.path.exists(config_path):
        print(f"Error: Config file not found: {config_path}")
        return

    # Create results directory
    os.makedirs("experiments/results", exist_ok=True)

    runner = ExperimentRunner(config_path=config_path, db_path=args.db)

    if args.dry_run:
        print("\n" + "="*80)
        print("DRY RUN - Experiment Configuration")
        print("="*80)
        print(yaml.dump(runner.config, default_flow_style=False))
        return

    asyncio.run(runner.run_experiment())


if __name__ == "__main__":
    main()
