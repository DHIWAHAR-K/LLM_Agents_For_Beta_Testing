from __future__ import annotations

from statistics import mean
from typing import Any, Dict, List


def task_success_rate(turns: List[Dict[str, Any]]) -> float:
    if not turns:
        return 0.0
    passed = sum(1 for t in turns if t.get("oracle_pass"))
    return passed / len(turns)


def latency_summary(turns: List[Dict[str, Any]]) -> Dict[str, float]:
    latencies = [float(t.get("latency", 0.0)) for t in turns if t.get("latency") is not None]
    if not latencies:
        return {"mean": 0.0, "max": 0.0}
    return {"mean": mean(latencies), "max": max(latencies)}
