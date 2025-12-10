"""Demo runner that directs experiment outputs into Demo/ and records the screen."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Ensure repo root is on sys.path for imports when run directly
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import app.storage as storage_module
from experiments.runner import ExperimentRunner


DEMO_ROOT = REPO_ROOT / "Demo"
DEMO_RUNS_DIR = DEMO_ROOT / "runs"
DEMO_DB_PATH = DEMO_ROOT / "experiments.db"

# Map shorthand experiment codes to their configs
EXPERIMENT_CONFIGS = {
    "1a": REPO_ROOT / "experiments/configs/experiment_1a_multi_agent_scaling.yaml",
    "1b": REPO_ROOT / "experiments/configs/experiment_1b_persona_diversity.yaml",
    "1c": REPO_ROOT / "experiments/configs/experiment_1c_regression_detection.yaml",
    "2": REPO_ROOT / "experiments/configs/experiment_2_price_manipulator.yaml",
    "3": REPO_ROOT / "experiments/configs/experiment_3_webshop.yaml",
}


def apply_demo_storage_patch() -> None:
    """Force SessionStorage to write into Demo/runs instead of results/."""
    original_init = storage_module.SessionStorage.__init__

    def _demo_init(self, base_results_dir: str = str(DEMO_RUNS_DIR)) -> None:  # type: ignore[override]
        return original_init(self, base_results_dir=str(DEMO_RUNS_DIR))

    storage_module.SessionStorage.__init__ = _demo_init  # type: ignore[assignment]


async def run_single_experiment(code: str) -> None:
    """Run one experiment into the Demo database."""
    config_path = EXPERIMENT_CONFIGS[code]
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found for experiment {code}: {config_path}")

    runner = ExperimentRunner(config_path=str(config_path), db_path=str(DEMO_DB_PATH))
    await runner.run_experiment()


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run demo experiments with screen recording.")
    parser.add_argument(
        "--experiments",
        type=str,
        help="Comma/space-separated experiment codes (e.g., '1a,1b,3'). Default: all.",
    )
    args = parser.parse_args()

    if args.experiments:
        raw_parts = args.experiments.replace(",", " ").split()
        experiment_codes = []
        for part in raw_parts:
            code = part.strip().lower()
            if code == "all":
                experiment_codes = list(EXPERIMENT_CONFIGS.keys())
                break
            if code not in EXPERIMENT_CONFIGS:
                raise ValueError(f"Unknown experiment code '{code}'. Valid: {', '.join(EXPERIMENT_CONFIGS)} or 'all'.")
            experiment_codes.append(code)
    else:
        experiment_codes = list(EXPERIMENT_CONFIGS.keys())

    DEMO_ROOT.mkdir(parents=True, exist_ok=True)
    DEMO_RUNS_DIR.mkdir(parents=True, exist_ok=True)

    # Redirect session CSVs/screenshots into Demo/runs
    apply_demo_storage_patch()

    for code in experiment_codes:
        print(f"\n=== Running experiment {code} (Demo output) ===")
        await run_single_experiment(code)


if __name__ == "__main__":
    asyncio.run(main())
