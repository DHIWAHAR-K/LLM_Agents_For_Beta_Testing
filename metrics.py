"""
Metrics computation for LLM beta testing framework.

Implements the 6 core metrics from the proposal:
1. Task Success Rate (TSR)
2. Robustness Delta  
3. Safety Pass Rate
4. Regression Delta
5. Latency Statistics (p50, p95)
6. Human-Agent Agreement
"""

from __future__ import annotations

import json
import statistics
from typing import Any


def task_success_rate(runs: list[dict[str, Any]]) -> float:
    """
    Calculate Task Success Rate: percentage of sessions that completed successfully.
    
    A session is successful if all turns passed oracles and completed the full turn budget.
    
    Args:
        runs: List of run dictionaries from storage.get_runs()
        
    Returns:
        float: TSR between 0.0 and 1.0
    """
    if not runs:
        return 0.0
    
    # Group by session_id
    sessions: dict[str, list[dict]] = {}
    for run in runs:
        session_id = run.get("session_id", "unknown")
        if session_id not in sessions:
            sessions[session_id] = []
        sessions[session_id].append(run)
    
    if not sessions:
        return 0.0
    
    successful = 0
    for session_id, session_runs in sessions.items():
        # Session successful if all turns passed oracles
        if all(run.get("oracle_pass", 0) == 1 for run in session_runs):
            successful += 1
    
    return successful / len(sessions)


def robustness_delta(clean_runs: list[dict[str, Any]], noisy_runs: list[dict[str, Any]]) -> float:
    """
    Calculate Robustness Delta: change in TSR when using noisy vs clean personas.
    
    Args:
        clean_runs: Runs with clean/standard personas
        noisy_runs: Runs with noisy personas (typos, slang, paraphrasing)
        
    Returns:
        float: Delta (clean_TSR - noisy_TSR), positive means degradation with noise
    """
    clean_tsr = task_success_rate(clean_runs)
    noisy_tsr = task_success_rate(noisy_runs)
    return clean_tsr - noisy_tsr


def safety_pass_rate(runs: list[dict[str, Any]]) -> float:
    """
    Calculate Safety Pass Rate: percentage of adversarial/unsafe inputs correctly handled.
    
    Looks for runs with adversarial personas where unsafe actions should be blocked.
    
    Args:
        runs: List of run dictionaries
        
    Returns:
        float: Safety pass rate between 0.0 and 1.0
    """
    if not runs:
        return 1.0  # No unsafe content = perfect safety
    
    adversarial_runs = []
    for run in runs:
        try:
            persona_data = json.loads(run.get("persona", "{}"))
            traits = persona_data.get("traits", {})
            if traits.get("adversarial") or traits.get("safety_test"):
                adversarial_runs.append(run)
        except (json.JSONDecodeError, KeyError):
            continue
    
    if not adversarial_runs:
        return 1.0  # No adversarial runs
    
    # Count how many adversarial actions were blocked (oracle_pass=0 is good here)
    blocked = sum(1 for run in adversarial_runs if run.get("oracle_pass", 1) == 0)
    
    return blocked / len(adversarial_runs)


def regression_delta(baseline_runs: list[dict[str, Any]], candidate_runs: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Calculate Regression Delta: proportion of scenarios that flipped Pass→Fail or Fail→Pass.
    
    Args:
        baseline_runs: Runs from baseline version
        candidate_runs: Runs from candidate version
        
    Returns:
        dict: {
            'pass_to_fail': float,  # Proportion that regressed
            'fail_to_pass': float,  # Proportion that improved
            'net_regression': float, # pass_to_fail - fail_to_pass
            'details': list[dict]    # Per-scenario details
        }
    """
    # Group by scenario/persona combination
    def _group_key(run: dict) -> str:
        try:
            persona_data = json.loads(run.get("persona", "{}"))
            name = persona_data.get("name", "unknown")
            return f"{name}_{run.get('session_id', '')[:8]}"
        except (json.JSONDecodeError, KeyError):
            return f"unknown_{run.get('session_id', '')[:8]}"
    
    baseline_results: dict[str, bool] = {}
    for run in baseline_runs:
        key = _group_key(run)
        # Session passed if oracle_pass=1
        passed = run.get("oracle_pass", 0) == 1
        baseline_results[key] = baseline_results.get(key, True) and passed
    
    candidate_results: dict[str, bool] = {}
    for run in candidate_runs:
        key = _group_key(run)
        passed = run.get("oracle_pass", 0) == 1
        candidate_results[key] = candidate_results.get(key, True) and passed
    
    # Find common scenarios
    common_keys = set(baseline_results.keys()) & set(candidate_results.keys())
    
    if not common_keys:
        return {
            "pass_to_fail": 0.0,
            "fail_to_pass": 0.0,
            "net_regression": 0.0,
            "details": [],
        }
    
    pass_to_fail = 0
    fail_to_pass = 0
    details = []
    
    for key in common_keys:
        baseline_passed = baseline_results[key]
        candidate_passed = candidate_results[key]
        
        if baseline_passed and not candidate_passed:
            pass_to_fail += 1
            details.append({"scenario": key, "change": "pass_to_fail"})
        elif not baseline_passed and candidate_passed:
            fail_to_pass += 1
            details.append({"scenario": key, "change": "fail_to_pass"})
    
    total = len(common_keys)
    return {
        "pass_to_fail": pass_to_fail / total,
        "fail_to_pass": fail_to_pass / total,
        "net_regression": (pass_to_fail - fail_to_pass) / total,
        "details": details,
    }


def latency_stats(runs: list[dict[str, Any]]) -> dict[str, float]:
    """
    Calculate latency statistics: p50, p95, mean, max.
    
    Args:
        runs: List of run dictionaries
        
    Returns:
        dict: {
            'p50': float,    # Median
            'p95': float,    # 95th percentile
            'mean': float,   # Average
            'max': float,    # Maximum
            'count': int     # Number of samples
        }
    """
    latencies = [run.get("latency", 0.0) for run in runs if run.get("latency") is not None]
    
    if not latencies:
        return {"p50": 0.0, "p95": 0.0, "mean": 0.0, "max": 0.0, "count": 0}
    
    latencies.sort()
    
    return {
        "p50": statistics.median(latencies),
        "p95": latencies[int(len(latencies) * 0.95)] if len(latencies) > 1 else latencies[0],
        "mean": statistics.mean(latencies),
        "max": max(latencies),
        "count": len(latencies),
    }


def human_agent_agreement(agent_labels: list[bool], human_labels: list[bool]) -> dict[str, float]:
    """
    Calculate Human-Agent Agreement: correlation between LLM agent verdicts and human evaluations.
    
    Args:
        agent_labels: List of boolean labels from agent (True=pass, False=fail)
        human_labels: List of boolean labels from humans (same order)
        
    Returns:
        dict: {
            'agreement_rate': float,  # Simple agreement percentage
            'kappa': float,           # Cohen's kappa (inter-rater reliability)
            'precision': float,       # Agent precision vs human gold labels
            'recall': float           # Agent recall vs human gold labels
        }
    """
    if not agent_labels or not human_labels or len(agent_labels) != len(human_labels):
        return {"agreement_rate": 0.0, "kappa": 0.0, "precision": 0.0, "recall": 0.0}
    
    n = len(agent_labels)
    
    # Agreement rate
    agreements = sum(1 for a, h in zip(agent_labels, human_labels) if a == h)
    agreement_rate = agreements / n
    
    # Cohen's Kappa
    # Observed agreement
    po = agreement_rate
    
    # Expected agreement by chance
    agent_pos = sum(agent_labels) / n
    human_pos = sum(human_labels) / n
    pe = agent_pos * human_pos + (1 - agent_pos) * (1 - human_pos)
    
    kappa = (po - pe) / (1 - pe) if pe < 1.0 else 1.0
    
    # Precision and Recall (treating human as gold standard)
    true_positives = sum(1 for a, h in zip(agent_labels, human_labels) if a and h)
    false_positives = sum(1 for a, h in zip(agent_labels, human_labels) if a and not h)
    false_negatives = sum(1 for a, h in zip(agent_labels, human_labels) if not a and h)
    
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
    
    return {
        "agreement_rate": agreement_rate,
        "kappa": kappa,
        "precision": precision,
        "recall": recall,
    }


# Utility function for per-agent vs pooled views
def aggregate_by_model(runs: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """
    Group runs by model name for per-agent analysis.
    
    Args:
        runs: List of run dictionaries
        
    Returns:
        dict: {model_name: [runs for that model]}
    """
    by_model: dict[str, list[dict[str, Any]]] = {}
    
    for run in runs:
        # Try to get model name from session
        session_id = run.get("session_id")
        model_name = "unknown"
        
        # In a full implementation, we'd join with sessions table
        # For now, try to extract from run data
        if "model_name" in run:
            model_name = run["model_name"]
        
        if model_name not in by_model:
            by_model[model_name] = []
        by_model[model_name].append(run)
    
    return by_model

