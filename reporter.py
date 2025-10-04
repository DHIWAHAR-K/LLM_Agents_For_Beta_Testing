"""
Reporter module for aggregating metrics and generating reports.

Produces JSON artifacts and Markdown summaries for runs and regression comparisons.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import metrics
import storage


def build_run_report(run_id: str) -> dict[str, Any]:
    """
    Build complete report for a single run (session).
    
    Args:
        run_id: Session ID
        
    Returns:
        dict: Complete report with metrics, session info, and turn details
    """
    # Get session metadata
    session = storage.get_session(run_id)
    if not session:
        return {"error": f"Session {run_id} not found"}
    
    # Get all turns
    turns = storage.get_turns(run_id)
    
    # Get events
    events = storage.get_events(run_id)
    
    # Calculate metrics
    tsr = metrics.task_success_rate(turns)
    latency_stats = metrics.latency_stats(turns)
    
    # Per-agent breakdown if multiple models
    by_model = metrics.aggregate_by_model(turns)
    per_agent_metrics = {}
    for model_name, model_runs in by_model.items():
        per_agent_metrics[model_name] = {
            "tsr": metrics.task_success_rate(model_runs),
            "latency": metrics.latency_stats(model_runs),
            "turn_count": len(model_runs),
        }
    
    # Summary statistics
    total_turns = len(turns)
    passed_turns = sum(1 for t in turns if t.get("oracle_pass", 0) == 1)
    failed_turns = total_turns - passed_turns
    
    return {
        "session_id": run_id,
        "metadata": {
            "persona_name": session.get("persona_name"),
            "scenario": session.get("scenario"),
            "version": session.get("version"),
            "model_name": session.get("model_name"),
            "seed": session.get("seed"),
            "start_ts": session.get("start_ts"),
            "end_ts": session.get("end_ts"),
            "status": session.get("status"),
            "duration_seconds": (session.get("end_ts", 0) - session.get("start_ts", 0)) if session.get("end_ts") else None,
        },
        "summary": {
            "total_turns": total_turns,
            "passed_turns": passed_turns,
            "failed_turns": failed_turns,
            "pass_rate": passed_turns / total_turns if total_turns > 0 else 0.0,
        },
        "metrics": {
            "task_success_rate": tsr,
            "latency": latency_stats,
        },
        "per_agent_metrics": per_agent_metrics,
        "events_count": len(events),
        "turns": turns[:10],  # Include first 10 turns for preview
        "generated_at": datetime.now().isoformat(),
    }


def build_regression_diff(baseline_run_id: str, candidate_run_id: str) -> dict[str, Any]:
    """
    Build regression comparison report between two runs.
    
    Args:
        baseline_run_id: Baseline session ID
        candidate_run_id: Candidate session ID
        
    Returns:
        dict: Regression analysis with deltas and flipped scenarios
    """
    # Get runs
    baseline_turns = storage.get_turns(baseline_run_id)
    candidate_turns = storage.get_turns(candidate_run_id)
    
    baseline_session = storage.get_session(baseline_run_id)
    candidate_session = storage.get_session(candidate_run_id)
    
    if not baseline_session or not candidate_session:
        return {"error": "One or both sessions not found"}
    
    # Calculate metrics for each
    baseline_tsr = metrics.task_success_rate(baseline_turns)
    candidate_tsr = metrics.task_success_rate(candidate_turns)
    
    baseline_latency = metrics.latency_stats(baseline_turns)
    candidate_latency = metrics.latency_stats(candidate_turns)
    
    # Regression delta
    regression = metrics.regression_delta(baseline_turns, candidate_turns)
    
    # Build report
    return {
        "baseline": {
            "session_id": baseline_run_id,
            "version": baseline_session.get("version"),
            "tsr": baseline_tsr,
            "latency": baseline_latency,
            "turn_count": len(baseline_turns),
        },
        "candidate": {
            "session_id": candidate_run_id,
            "version": candidate_session.get("version"),
            "tsr": candidate_tsr,
            "latency": candidate_latency,
            "turn_count": len(candidate_turns),
        },
        "deltas": {
            "tsr_change": candidate_tsr - baseline_tsr,
            "latency_p50_change": candidate_latency["p50"] - baseline_latency["p50"],
            "latency_p95_change": candidate_latency["p95"] - baseline_latency["p95"],
            "regression": regression,
        },
        "verdict": "REGRESSION" if regression["net_regression"] > 0 else "IMPROVEMENT" if regression["net_regression"] < 0 else "NO_CHANGE",
        "generated_at": datetime.now().isoformat(),
    }


def save_reports(artifacts: dict[str, Any], out_dir: str = "reports") -> None:
    """
    Save report artifacts to disk.
    
    Args:
        artifacts: Dict with report data
        out_dir: Output directory for reports
    """
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    # Determine filename
    if "session_id" in artifacts:
        # Single run report
        session_id = artifacts["session_id"]
        json_file = out_path / f"{session_id}.json"
        md_file = out_path / f"{session_id}.md"
        
        # Save JSON
        with open(json_file, "w") as f:
            json.dump(artifacts, f, indent=2)
        
        # Save Markdown
        md_content = _render_run_markdown(artifacts)
        with open(md_file, "w") as f:
            f.write(md_content)
    
    elif "baseline" in artifacts and "candidate" in artifacts:
        # Regression diff report
        baseline_id = artifacts["baseline"]["session_id"]
        candidate_id = artifacts["candidate"]["session_id"]
        filename = f"diff_{baseline_id[:8]}_vs_{candidate_id[:8]}"
        
        json_file = out_path / f"{filename}.json"
        md_file = out_path / f"{filename}.md"
        
        # Save JSON
        with open(json_file, "w") as f:
            json.dump(artifacts, f, indent=2)
        
        # Save Markdown
        md_content = _render_diff_markdown(artifacts)
        with open(md_file, "w") as f:
            f.write(md_content)


def _render_run_markdown(report: dict[str, Any]) -> str:
    """Render run report as Markdown."""
    md = f"# Run Report: {report['session_id']}\n\n"
    
    # Metadata
    md += "## Metadata\n\n"
    meta = report["metadata"]
    md += f"- **Persona**: {meta.get('persona_name')}\n"
    md += f"- **Scenario**: {meta.get('scenario')}\n"
    md += f"- **Version**: {meta.get('version')}\n"
    md += f"- **Model**: {meta.get('model_name')}\n"
    md += f"- **Seed**: {meta.get('seed')}\n"
    md += f"- **Status**: {meta.get('status')}\n"
    if meta.get("duration_seconds"):
        md += f"- **Duration**: {meta['duration_seconds']:.2f}s\n"
    md += "\n"
    
    # Summary
    md += "## Summary\n\n"
    summary = report["summary"]
    md += f"- **Total Turns**: {summary['total_turns']}\n"
    md += f"- **Passed**: {summary['passed_turns']}\n"
    md += f"- **Failed**: {summary['failed_turns']}\n"
    md += f"- **Pass Rate**: {summary['pass_rate']:.1%}\n\n"
    
    # Metrics
    md += "## Metrics\n\n"
    md += f"- **Task Success Rate**: {report['metrics']['task_success_rate']:.1%}\n\n"
    
    latency = report['metrics']['latency']
    md += "### Latency\n\n"
    md += f"- **p50**: {latency['p50']:.3f}s\n"
    md += f"- **p95**: {latency['p95']:.3f}s\n"
    md += f"- **Mean**: {latency['mean']:.3f}s\n"
    md += f"- **Max**: {latency['max']:.3f}s\n\n"
    
    # Per-agent metrics
    if report.get("per_agent_metrics"):
        md += "## Per-Agent Metrics\n\n"
        for model, agent_metrics in report["per_agent_metrics"].items():
            md += f"### {model}\n\n"
            md += f"- **TSR**: {agent_metrics['tsr']:.1%}\n"
            md += f"- **Latency p50**: {agent_metrics['latency']['p50']:.3f}s\n"
            md += f"- **Turns**: {agent_metrics['turn_count']}\n\n"
    
    md += f"\n---\n\n*Generated at: {report['generated_at']}*\n"
    
    return md


def _render_diff_markdown(report: dict[str, Any]) -> str:
    """Render regression diff as Markdown."""
    baseline = report["baseline"]
    candidate = report["candidate"]
    deltas = report["deltas"]
    
    md = f"# Regression Diff: {baseline['session_id'][:8]} vs {candidate['session_id'][:8]}\n\n"
    
    md += f"## Verdict: **{report['verdict']}**\n\n"
    
    # Comparison table
    md += "## Comparison\n\n"
    md += "| Metric | Baseline | Candidate | Delta |\n"
    md += "|--------|----------|-----------|-------|\n"
    md += f"| TSR | {baseline['tsr']:.1%} | {candidate['tsr']:.1%} | {deltas['tsr_change']:+.1%} |\n"
    md += f"| Latency p50 | {baseline['latency']['p50']:.3f}s | {candidate['latency']['p50']:.3f}s | {deltas['latency_p50_change']:+.3f}s |\n"
    md += f"| Latency p95 | {baseline['latency']['p95']:.3f}s | {candidate['latency']['p95']:.3f}s | {deltas['latency_p95_change']:+.3f}s |\n"
    md += f"| Turns | {baseline['turn_count']} | {candidate['turn_count']} | {candidate['turn_count'] - baseline['turn_count']:+d} |\n\n"
    
    # Regression details
    regression = deltas["regression"]
    md += "## Regression Analysis\n\n"
    md += f"- **Pass→Fail**: {regression['pass_to_fail']:.1%}\n"
    md += f"- **Fail→Pass**: {regression['fail_to_pass']:.1%}\n"
    md += f"- **Net Regression**: {regression['net_regression']:.1%}\n\n"
    
    if regression["details"]:
        md += "### Flipped Scenarios\n\n"
        for detail in regression["details"]:
            md += f"- `{detail['scenario']}`: {detail['change']}\n"
        md += "\n"
    
    md += f"\n---\n\n*Generated at: {report['generated_at']}*\n"
    
    return md

