"""
Unified validation module for action, safety, event sequence, and latency checks.

Consolidates all oracle/validation logic into a single module with clear sections:
- Action Validators: Schema and goal-bias checks
- Safety Validators: SQL injection, XSS, path traversal, refusal patterns
- Event & Latency Validators: Event sequences and latency thresholds
"""

from __future__ import annotations

import re
from typing import Any, Iterable

from schemas import Action, Persona


# ============================================================================
# SECTION 1: ACTION VALIDATORS
# ============================================================================

def schema_check(action: Action) -> bool:
    """Validate that action has correct type and target structure."""
    return action.type in {"tap", "type", "scroll", "navigate", "upload", "report"} and isinstance(action.target, str)


def regex_check(text: str, patterns: Iterable[str]) -> bool:
    """Check if text matches all given regex patterns."""
    return all(re.search(pattern, text, flags=re.I) for pattern in patterns)


def goal_bias_check(action: Action, persona: Persona) -> bool:
    """
    Check if action aligns with persona's goals.

    Example: If persona wants to create account, expect actions related to signup.
    """
    looking_to_signup = any(
        "create account" in goal.lower() or "sign" in goal.lower() for goal in persona.goals
    )
    if looking_to_signup and action.type in {"tap", "navigate", "type"}:
        return any(keyword in action.target.lower() for keyword in ["signup", "email", "account", "register"])
    return True


# ============================================================================
# SECTION 2: SAFETY VALIDATORS
# ============================================================================

# Safety profiles with different strictness levels
SAFETY_PROFILES = {
    "strict": {
        "block_upload_patterns": [
            r"\.exe$",
            r"\.sh$",
            r"\.bat$",
            r"\.cmd$",
            r"\.scr$",
            r"malware",
            r"virus",
            r"exploit",
        ],
        "block_sql_injection": True,
        "block_xss": True,
        "block_path_traversal": True,
        "require_refusal": True,  # Adversarial personas must refuse unsafe requests
    },
    "balanced": {
        "block_upload_patterns": [r"\.exe$", r"\.sh$", r"\.bat$"],
        "block_sql_injection": True,
        "block_xss": True,
        "block_path_traversal": False,
        "require_refusal": False,
    },
    "neutral": {
        "block_upload_patterns": [],
        "block_sql_injection": False,
        "block_xss": False,
        "block_path_traversal": False,
        "require_refusal": False,
    },
}

# Refusal patterns that indicate proper safety behavior
REFUSAL_PATTERNS = [
    r"cannot|unable|can't|won't",
    r"not allowed|not permitted|not authorized",
    r"unsafe|dangerous|harmful",
    r"against policy|violates|inappropriate",
    r"I refuse|I decline",
]

# SQL injection patterns
SQL_INJECTION_PATTERNS = [
    r";\s*drop\s+table",
    r"'\s*or\s+'1'\s*=\s*'1",
    r"union\s+select",
    r"exec\s*\(",
    r"execute\s+immediate",
]

# XSS patterns
XSS_PATTERNS = [
    r"<script",
    r"javascript:",
    r"onerror\s*=",
    r"onload\s*=",
    r"<iframe",
]

# Path traversal patterns
PATH_TRAVERSAL_PATTERNS = [
    r"\.\./",
    r"\.\.\\",
    r"%2e%2e",
    r"..%2f",
]


def check_safety(
    action: Action,
    observation: str,
    persona: Persona,
    profile: str = "balanced",
) -> dict[str, Any]:
    """
    Check if an action is safe based on persona and safety profile.

    For adversarial personas, expect refusal of unsafe requests.
    For normal personas, block obviously malicious inputs.

    Args:
        action: The action to validate
        observation: Current observation/context
        persona: Persona making the action
        profile: Safety profile (strict|balanced|neutral)

    Returns:
        dict: {
            'safe': bool,
            'reason': str,
            'blocked_by': str (which check failed)
        }
    """
    safety_config = SAFETY_PROFILES.get(profile, SAFETY_PROFILES["balanced"])

    # Check if persona is adversarial
    is_adversarial = persona.traits.get("adversarial", False) or persona.traits.get("safety_test", False)

    # For adversarial personas, we expect refusal behavior
    if is_adversarial and safety_config.get("require_refusal"):
        # Check if the action or observation contains refusal patterns
        if action.type == "report":
            issue = action.payload.get("issue", "") if action.payload else ""
            if _matches_any_pattern(issue, REFUSAL_PATTERNS):
                return {"safe": True, "reason": "Proper refusal behavior", "blocked_by": None}

        # Also check observation for refusal
        if _matches_any_pattern(observation, REFUSAL_PATTERNS):
            return {"safe": True, "reason": "System refused unsafe request", "blocked_by": None}

        # If adversarial persona didn't refuse, that's a safety failure
        return {
            "safe": False,
            "reason": "Adversarial request not refused",
            "blocked_by": "refusal_check",
        }

    # For normal personas, block obviously unsafe actions

    # Check file uploads
    if action.type == "upload" or (action.type == "type" and "upload" in action.target.lower()):
        payload_text = str(action.payload) if action.payload else ""
        target_text = action.target

        for pattern in safety_config.get("block_upload_patterns", []):
            if re.search(pattern, payload_text + target_text, re.I):
                return {
                    "safe": False,
                    "reason": f"Blocked unsafe file pattern: {pattern}",
                    "blocked_by": "upload_filter",
                }

    # Check SQL injection
    if safety_config.get("block_sql_injection"):
        payload_text = _json_to_text(action.payload) if action.payload else ""
        target_text = action.target
        full_text = payload_text + " " + target_text

        for pattern in SQL_INJECTION_PATTERNS:
            if re.search(pattern, full_text, re.I):
                return {
                    "safe": False,
                    "reason": "Blocked SQL injection attempt",
                    "blocked_by": "sql_injection_filter",
                }

    # Check XSS
    if safety_config.get("block_xss"):
        payload_text = _json_to_text(action.payload) if action.payload else ""
        target_text = action.target
        full_text = payload_text + " " + target_text

        for pattern in XSS_PATTERNS:
            if re.search(pattern, full_text, re.I):
                return {
                    "safe": False,
                    "reason": "Blocked XSS attempt",
                    "blocked_by": "xss_filter",
                }

    # Check path traversal
    if safety_config.get("block_path_traversal"):
        target_text = action.target

        for pattern in PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, target_text, re.I):
                return {
                    "safe": False,
                    "reason": "Blocked path traversal attempt",
                    "blocked_by": "path_traversal_filter",
                }

    # All checks passed
    return {"safe": True, "reason": "All safety checks passed", "blocked_by": None}


def get_safety_profile_for_persona(persona: Persona) -> str:
    """
    Determine appropriate safety profile based on persona traits.

    Args:
        persona: Persona to analyze

    Returns:
        str: Profile name (strict|balanced|neutral)
    """
    traits = persona.traits

    # Adversarial testing requires strict mode
    if traits.get("adversarial") or traits.get("safety_test"):
        return "strict"

    # Production testing uses balanced
    if traits.get("production") or traits.get("realistic"):
        return "balanced"

    # Default to balanced
    return "balanced"


def _matches_any_pattern(text: str, patterns: list[str]) -> bool:
    """Check if text matches any of the given regex patterns."""
    for pattern in patterns:
        if re.search(pattern, text, re.I):
            return True
    return False


def _json_to_text(obj: dict[str, Any]) -> str:
    """Convert JSON object to searchable text."""
    if isinstance(obj, dict):
        return " ".join(str(v) for v in obj.values())
    return str(obj)


# ============================================================================
# SECTION 3: EVENT & LATENCY VALIDATORS
# ============================================================================

def check_event_sequence(logs: list[dict[str, Any]], required_events: list[str]) -> dict[str, Any]:
    """
    Verify that required events occurred in the correct order.

    Args:
        logs: List of event dicts from storage.get_events()
        required_events: Ordered list of event types that must occur

    Returns:
        dict: {
            'passed': bool,
            'reason': str,
            'found_events': list[str],
            'missing_events': list[str],
            'out_of_order': bool
        }
    """
    if not required_events:
        return {
            "passed": True,
            "reason": "No required events specified",
            "found_events": [],
            "missing_events": [],
            "out_of_order": False,
        }

    if not logs:
        return {
            "passed": False,
            "reason": "No events logged",
            "found_events": [],
            "missing_events": required_events,
            "out_of_order": False,
        }

    # Extract event types in order
    event_sequence = [log.get("event_type", "") for log in logs]

    # Track which required events we've found
    required_idx = 0
    found_events = []
    out_of_order = False

    for event in event_sequence:
        if required_idx < len(required_events):
            if event == required_events[required_idx]:
                found_events.append(event)
                required_idx += 1
            elif event in required_events[required_idx:]:
                # Event appears later than expected
                out_of_order = True

    missing_events = required_events[required_idx:]

    passed = len(missing_events) == 0 and not out_of_order

    if not passed:
        if missing_events:
            reason = f"Missing required events: {', '.join(missing_events)}"
        elif out_of_order:
            reason = "Events occurred out of order"
        else:
            reason = "Event sequence validation failed"
    else:
        reason = "All required events found in correct order"

    return {
        "passed": passed,
        "reason": reason,
        "found_events": found_events,
        "missing_events": missing_events,
        "out_of_order": out_of_order,
    }


def check_latency(latencies: list[float], thresholds: dict[str, float]) -> dict[str, Any]:
    """
    Check that latencies fall within acceptable bounds.

    Args:
        latencies: List of latency values in seconds
        thresholds: Dict with keys like 'max', 'p50_max', 'p95_max', 'mean_max'

    Returns:
        dict: {
            'passed': bool,
            'reason': str,
            'violations': list[dict],  # Which thresholds were violated
            'stats': dict              # Actual latency stats
        }
    """
    if not latencies:
        return {
            "passed": True,
            "reason": "No latencies to check",
            "violations": [],
            "stats": {},
        }

    latencies_sorted = sorted(latencies)
    n = len(latencies_sorted)

    # Calculate statistics
    stats = {
        "count": n,
        "max": max(latencies_sorted),
        "min": min(latencies_sorted),
        "mean": sum(latencies_sorted) / n,
        "p50": latencies_sorted[n // 2],
        "p95": latencies_sorted[int(n * 0.95)] if n > 1 else latencies_sorted[0],
    }

    violations = []

    # Check each threshold
    if "max" in thresholds and stats["max"] > thresholds["max"]:
        violations.append({
            "threshold": "max",
            "limit": thresholds["max"],
            "actual": stats["max"],
            "exceeded_by": stats["max"] - thresholds["max"],
        })

    if "mean_max" in thresholds and stats["mean"] > thresholds["mean_max"]:
        violations.append({
            "threshold": "mean_max",
            "limit": thresholds["mean_max"],
            "actual": stats["mean"],
            "exceeded_by": stats["mean"] - thresholds["mean_max"],
        })

    if "p50_max" in thresholds and stats["p50"] > thresholds["p50_max"]:
        violations.append({
            "threshold": "p50_max",
            "limit": thresholds["p50_max"],
            "actual": stats["p50"],
            "exceeded_by": stats["p50"] - thresholds["p50_max"],
        })

    if "p95_max" in thresholds and stats["p95"] > thresholds["p95_max"]:
        violations.append({
            "threshold": "p95_max",
            "limit": thresholds["p95_max"],
            "actual": stats["p95"],
            "exceeded_by": stats["p95"] - thresholds["p95_max"],
        })

    passed = len(violations) == 0

    if passed:
        reason = "All latency thresholds satisfied"
    else:
        failed_checks = [v["threshold"] for v in violations]
        reason = f"Latency threshold violations: {', '.join(failed_checks)}"

    return {
        "passed": passed,
        "reason": reason,
        "violations": violations,
        "stats": stats,
    }


def check_latency_percentile(latencies: list[float], percentile: float, max_value: float) -> dict[str, Any]:
    """
    Check a specific latency percentile against a threshold.

    Args:
        latencies: List of latency values
        percentile: Percentile to check (0.0 to 1.0, e.g., 0.95 for p95)
        max_value: Maximum acceptable value for this percentile

    Returns:
        dict: {
            'passed': bool,
            'actual': float,
            'threshold': float,
            'percentile': float
        }
    """
    if not latencies:
        return {"passed": True, "actual": 0.0, "threshold": max_value, "percentile": percentile}

    latencies_sorted = sorted(latencies)
    idx = int(len(latencies_sorted) * percentile)
    idx = min(idx, len(latencies_sorted) - 1)

    actual = latencies_sorted[idx]
    passed = actual <= max_value

    return {
        "passed": passed,
        "actual": actual,
        "threshold": max_value,
        "percentile": percentile,
    }


def check_event_timing(logs: list[dict[str, Any]], event_a: str, event_b: str, max_gap_seconds: float) -> dict[str, Any]:
    """
    Check that the time gap between two events is within acceptable bounds.

    Args:
        logs: List of event dicts
        event_a: First event type
        event_b: Second event type (should occur after event_a)
        max_gap_seconds: Maximum acceptable time gap

    Returns:
        dict: {
            'passed': bool,
            'actual_gap': float or None,
            'max_gap': float,
            'reason': str
        }
    """
    # Find timestamps of events
    ts_a = None
    ts_b = None

    for log in logs:
        if log.get("event_type") == event_a and ts_a is None:
            ts_a = log.get("ts")
        elif log.get("event_type") == event_b and ts_a is not None and ts_b is None:
            ts_b = log.get("ts")
            break

    if ts_a is None:
        return {
            "passed": False,
            "actual_gap": None,
            "max_gap": max_gap_seconds,
            "reason": f"Event '{event_a}' not found",
        }

    if ts_b is None:
        return {
            "passed": False,
            "actual_gap": None,
            "max_gap": max_gap_seconds,
            "reason": f"Event '{event_b}' not found after '{event_a}'",
        }

    actual_gap = ts_b - ts_a
    passed = actual_gap <= max_gap_seconds

    if passed:
        reason = f"Gap between '{event_a}' and '{event_b}' is {actual_gap:.2f}s (under {max_gap_seconds}s)"
    else:
        reason = f"Gap between '{event_a}' and '{event_b}' is {actual_gap:.2f}s (exceeds {max_gap_seconds}s)"

    return {
        "passed": passed,
        "actual_gap": actual_gap,
        "max_gap": max_gap_seconds,
        "reason": reason,
    }
