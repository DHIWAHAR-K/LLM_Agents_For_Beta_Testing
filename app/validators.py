from __future__ import annotations

import re
from typing import Dict, List, Tuple

from .schemas import Action, Persona

VALID_TYPES = {"tap", "type", "scroll", "navigate", "upload", "report", "click", "fill"}

# Safety patterns for adversarial testing
SQL_INJECTION_PATTERNS = [
    r"'\s*OR\s+1\s*=\s*1",
    r"';\s*DROP\s+TABLE",
    r"--",
    r"'\s*OR\s+'1'\s*=\s*'1",
    r"UNION\s+SELECT",
    r"';",
]

XSS_PATTERNS = [
    r"<script[^>]*>",
    r"javascript:",
    r"onerror\s*=",
    r"onload\s*=",
    r"<iframe",
]

COMMAND_INJECTION_PATTERNS = [
    r";\s*rm\s+-rf",
    r"\|\s*cat\s+/etc/passwd",
    r"&&",
    r"\|\|",
    r"`.*`",
    r"\$\(.*\)",
]

PATH_TRAVERSAL_PATTERNS = [
    r"\.\./",
    r"\.\.",
    r"\\\\\.\.\\\\",
]

# E-commerce specific validation patterns
PRICE_MANIPULATION_PATTERNS = [
    r"price[\"']?\s*:\s*-",  # Negative price
    r"price[\"']?\s*:\s*0(?:\.0+)?(?![0-9])",  # Zero price
    r"price[\"']?\s*:\s*9{5,}",  # Excessive price (99999+)
]

QUANTITY_MANIPULATION_PATTERNS = [
    r"quantity[\"']?\s*:\s*-",  # Negative quantity
    r"quantity[\"']?\s*:\s*0(?![0-9])",  # Zero quantity
    r"quantity[\"']?\s*:\s*\d{3,}",  # Excessive quantity (100+)
]

STOCK_MANIPULATION_PATTERNS = [
    r"stock[\"']?\s*:\s*-",  # Negative stock
]


def _check_safety(action: Action) -> List[str]:
    """Check action for security vulnerabilities."""
    safety_reasons = []

    # Extract all text content from the action
    text_to_check = []
    if action.target:
        text_to_check.append(action.target)

    if action.payload:
        for key, value in action.payload.items():
            if isinstance(value, str):
                text_to_check.append(value)
            elif isinstance(value, dict):
                # Handle nested JSON payloads
                for nested_key, nested_value in value.items():
                    if isinstance(nested_value, str):
                        text_to_check.append(nested_value)

    # Check each text field for security patterns
    for text in text_to_check:
        # SQL Injection
        for pattern in SQL_INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                safety_reasons.append(f"safety:sql_injection:{pattern}")
                break

        # XSS
        for pattern in XSS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                safety_reasons.append(f"safety:xss:{pattern}")
                break

        # Command Injection
        for pattern in COMMAND_INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                safety_reasons.append(f"safety:command_injection:{pattern}")
                break

        # Path Traversal
        for pattern in PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                safety_reasons.append(f"safety:path_traversal:{pattern}")
                break

        # Price Manipulation
        for pattern in PRICE_MANIPULATION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                safety_reasons.append(f"safety:price_manipulation:{pattern}")
                break

        # Quantity Manipulation
        for pattern in QUANTITY_MANIPULATION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                safety_reasons.append(f"safety:quantity_manipulation:{pattern}")
                break

        # Stock Manipulation
        for pattern in STOCK_MANIPULATION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                safety_reasons.append(f"safety:stock_manipulation:{pattern}")
                break

    return safety_reasons


def validate_action(action: Action, persona: Persona, disable_safety_checks: bool = False) -> Tuple[bool, List[str], List[str]]:
    """
    Validate action with schema, goal alignment, and safety checks.

    Args:
        action: The action to validate
        persona: The persona performing the action
        disable_safety_checks: If True, skip safety validation (for security testing scenarios)

    Returns:
        Tuple of (passed, all_reasons, safety_reasons)
        - passed: True if all validations pass
        - all_reasons: List of all validation failures
        - safety_reasons: List of safety-specific failures (subset of all_reasons)
    """
    reasons: List[str] = []

    # Schema validation
    if action.type not in VALID_TYPES:
        reasons.append(f"invalid_type:{action.type}")

    if not action.target:
        reasons.append("missing_target")

    # Goal alignment check - removed overly restrictive report validation
    # Agents should be able to report bugs as they discover them during testing
    # The original check was: if "create" in goals and action.type == "report" then block
    # This was too aggressive and prevented legitimate intermediate bug reports

    # Safety validation (skip for security testing scenarios)
    safety_reasons = []
    if not disable_safety_checks:
        safety_reasons = _check_safety(action)
        reasons.extend(safety_reasons)

    return (len(reasons) == 0), reasons, safety_reasons
