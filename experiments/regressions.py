"""
Regression Definitions for AUT v2.0

This module defines 15 intentional regressions to inject into v2.0 for Experiment 1D.
Regressions are categorized into: Breaking Changes, Behavioral Changes, Performance Degradation, UI Regressions.

Usage:
    from experiments.regressions import REGRESSIONS, RegressionManager

    manager = RegressionManager(database_path='experiments/results/experiments.db')
    manager.load_regressions()
"""

import sqlite3
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class RegressionType(Enum):
    BREAKING_CHANGE = "breaking_change"
    BEHAVIORAL_CHANGE = "behavioral_change"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    UI_REGRESSION = "ui_regression"


class Severity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Regression:
    """Represents a regression introduced in v2.0"""
    regression_id: str
    regression_type: str
    category: str
    severity: str
    description: str
    location: str
    expected_behavior: str
    actual_behavior: str

    def to_dict(self) -> Dict:
        return asdict(self)


# ============================================================================
# REGRESSION CATALOG (15 total for Experiment 1D)
# ============================================================================

REGRESSIONS = [
    # ========== BREAKING CHANGES (5) ==========
    Regression(
        regression_id="REG-BC-001",
        regression_type="breaking_change",
        category="removed_endpoint",
        severity="critical",
        description="Product review endpoint removed in v2.0",
        location="/api/reviews",
        expected_behavior="POST /api/reviews creates a new review and returns 201",
        actual_behavior="POST /api/reviews returns 404 Not Found"
    ),
    Regression(
        regression_id="REG-BC-002",
        regression_type="breaking_change",
        category="changed_response_format",
        severity="high",
        description="Cart endpoint response format changed from array to object",
        location="/api/cart GET response",
        expected_behavior="Returns {\"items\": [{...}], \"total\": 99.99}",
        actual_behavior="Returns {\"data\": {\"cart_items\": [{...}], \"amount\": 99.99}}"
    ),
    Regression(
        regression_id="REG-BC-003",
        regression_type="breaking_change",
        category="required_parameter_added",
        severity="high",
        description="Checkout endpoint now requires 'payment_method' parameter",
        location="/api/checkout POST request",
        expected_behavior="Checkout succeeds with address and items only",
        actual_behavior="Returns 400 Bad Request: 'payment_method' is required"
    ),
    Regression(
        regression_id="REG-BC-004",
        regression_type="breaking_change",
        category="authentication_requirement",
        severity="high",
        description="Product search now requires authentication token",
        location="/api/products/search",
        expected_behavior="Anonymous users can search products",
        actual_behavior="Returns 401 Unauthorized without auth token"
    ),
    Regression(
        regression_id="REG-BC-005",
        regression_type="breaking_change",
        category="status_code_change",
        severity="medium",
        description="Empty cart now returns 204 instead of 200",
        location="/api/cart GET with empty cart",
        expected_behavior="Returns 200 with empty items array",
        actual_behavior="Returns 204 No Content with no body"
    ),

    # ========== BEHAVIORAL CHANGES (5) ==========
    Regression(
        regression_id="REG-BEH-001",
        regression_type="behavioral_change",
        category="modified_calculation",
        severity="high",
        description="Shipping cost calculation changed, now charges 2x previous amount",
        location="/api/cart/total shipping calculation",
        expected_behavior="Shipping cost: $5.99 for orders under $50",
        actual_behavior="Shipping cost: $11.98 for orders under $50"
    ),
    Regression(
        regression_id="REG-BEH-002",
        regression_type="behavioral_change",
        category="workflow_change",
        severity="medium",
        description="Product images now require explicit opt-in to load",
        location="/api/products response",
        expected_behavior="Product images included by default in response",
        actual_behavior="Product images only included if include_images=true parameter set"
    ),
    Regression(
        regression_id="REG-BEH-003",
        regression_type="behavioral_change",
        category="sorting_change",
        severity="medium",
        description="Product search results now sorted by price (low to high) instead of relevance",
        location="/api/products/search result ordering",
        expected_behavior="Results sorted by search relevance score",
        actual_behavior="Results sorted by price ascending, ignoring relevance"
    ),
    Regression(
        regression_id="REG-BEH-004",
        regression_type="behavioral_change",
        category="validation_tightened",
        severity="medium",
        description="Email validation now rejects emails with '+' character",
        location="/api/auth/register email validation",
        expected_behavior="Accepts emails like user+tag@example.com",
        actual_behavior="Rejects emails with '+', returns validation error"
    ),
    Regression(
        regression_id="REG-BEH-005",
        regression_type="behavioral_change",
        category="session_timeout",
        severity="low",
        description="Session timeout reduced from 30 minutes to 5 minutes",
        location="Session management middleware",
        expected_behavior="Sessions persist for 30 minutes of inactivity",
        actual_behavior="Sessions expire after 5 minutes of inactivity"
    ),

    # ========== PERFORMANCE DEGRADATION (3) ==========
    Regression(
        regression_id="REG-PERF-001",
        regression_type="performance_degradation",
        category="slow_response",
        severity="high",
        description="Product search now takes 5-10 seconds instead of <1 second",
        location="/api/products/search",
        expected_behavior="Search returns results in <1 second (p95)",
        actual_behavior="Search takes 5-10 seconds (p95), added unoptimized query"
    ),
    Regression(
        regression_id="REG-PERF-002",
        regression_type="performance_degradation",
        category="timeout",
        severity="high",
        description="Checkout endpoint times out for carts with >3 items",
        location="/api/checkout",
        expected_behavior="Checkout completes in <2 seconds regardless of cart size",
        actual_behavior="Checkout takes >30 seconds and times out for large carts"
    ),
    Regression(
        regression_id="REG-PERF-003",
        regression_type="performance_degradation",
        category="memory_leak",
        severity="medium",
        description="Cart operations cause memory leak, slowing down over time",
        location="/api/cart/* endpoints",
        expected_behavior="Consistent response times across multiple cart operations",
        actual_behavior="Response times increase linearly with number of operations"
    ),

    # ========== UI REGRESSIONS (2) ==========
    Regression(
        regression_id="REG-UI-001",
        regression_type="ui_regression",
        category="broken_layout",
        severity="high",
        description="Product grid layout broken on homepage, items overlap",
        location="/ (homepage) product grid CSS",
        expected_behavior="Products displayed in clean 3-column grid",
        actual_behavior="Products overlap each other, grid layout broken"
    ),
    Regression(
        regression_id="REG-UI-002",
        regression_type="ui_regression",
        category="missing_element",
        severity="medium",
        description="Add to Cart button missing from product detail page",
        location="/product/<id> page",
        expected_behavior="Prominent 'Add to Cart' button below product details",
        actual_behavior="No 'Add to Cart' button rendered, only 'View Details' link"
    ),
]


# ============================================================================
# REGRESSION MANAGER CLASS
# ============================================================================

class RegressionManager:
    """Manages regression tracking and detection"""

    def __init__(self, database_path: str):
        self.db_path = database_path
        self.regressions = REGRESSIONS

    def load_regressions(self) -> None:
        """Load all regressions into the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for regression in self.regressions:
            cursor.execute("""
                INSERT OR REPLACE INTO regressions (
                    regression_id, regression_type, category, severity,
                    description, location, introduced_in_version,
                    expected_behavior, actual_behavior
                ) VALUES (?, ?, ?, ?, ?, ?, 'v2.0', ?, ?)
            """, (
                regression.regression_id,
                regression.regression_type,
                regression.category,
                regression.severity,
                regression.description,
                regression.location,
                regression.expected_behavior,
                regression.actual_behavior
            ))

        conn.commit()
        conn.close()
        print(f"✓ Loaded {len(self.regressions)} regressions for v2.0")

    def mark_detected(self, run_id: int, regression_id: str, turn: int,
                      confidence: float, evidence: str) -> None:
        """Mark a regression as detected during a test run"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO regression_detections (
                run_id, regression_id, detected, detected_at_turn,
                confidence, evidence, is_false_positive
            ) VALUES (?, ?, 1, ?, ?, ?, 0)
        """, (run_id, regression_id, turn, confidence, evidence))

        conn.commit()
        conn.close()

    def mark_false_positive(self, run_id: int, regression_id: str, turn: int,
                           confidence: float, evidence: str) -> None:
        """Mark a false positive regression detection"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO regression_detections (
                run_id, regression_id, detected, detected_at_turn,
                confidence, evidence, is_false_positive
            ) VALUES (?, ?, 1, ?, ?, ?, 1)
        """, (run_id, regression_id, turn, confidence, evidence))

        conn.commit()
        conn.close()

    def get_detection_stats(self) -> Dict:
        """Calculate regression detection statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Total regressions
        total_regressions = len(self.regressions)

        # Detected regressions (true positives)
        cursor.execute("""
            SELECT COUNT(DISTINCT regression_id)
            FROM regression_detections
            WHERE detected = 1 AND is_false_positive = 0
        """)
        detected = cursor.fetchone()[0]

        # False positives
        cursor.execute("""
            SELECT COUNT(*)
            FROM regression_detections
            WHERE is_false_positive = 1
        """)
        false_positives = cursor.fetchone()[0]

        # Detection rate
        detection_rate = (detected / total_regressions * 100) if total_regressions > 0 else 0

        # False positive rate
        total_reports = detected + false_positives
        fpr = (false_positives / total_reports * 100) if total_reports > 0 else 0

        conn.close()

        return {
            "total_regressions": total_regressions,
            "regressions_detected": detected,
            "false_positives": false_positives,
            "detection_rate": round(detection_rate, 2),
            "false_positive_rate": round(fpr, 2)
        }

    def get_detection_by_type(self) -> Dict:
        """Get detection breakdown by regression type"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                r.regression_type,
                COUNT(DISTINCT r.regression_id) as total,
                COUNT(DISTINCT CASE WHEN rd.detected = 1 AND rd.is_false_positive = 0
                                    THEN r.regression_id END) as detected,
                ROUND(100.0 * COUNT(DISTINCT CASE WHEN rd.detected = 1 AND rd.is_false_positive = 0
                                    THEN r.regression_id END) / COUNT(DISTINCT r.regression_id), 2) as detection_rate
            FROM regressions r
            LEFT JOIN regression_detections rd ON r.regression_id = rd.regression_id
            GROUP BY r.regression_type
        """)

        results = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return results

    @staticmethod
    def get_regressions_by_type(regression_type: str) -> List[Regression]:
        """Get all regressions of a specific type"""
        return [r for r in REGRESSIONS if r.regression_type == regression_type]

    @staticmethod
    def get_regressions_by_severity(severity: str) -> List[Regression]:
        """Get all regressions of a specific severity"""
        return [r for r in REGRESSIONS if r.severity == severity]

    @staticmethod
    def get_regression_by_id(regression_id: str) -> Optional[Regression]:
        """Get a specific regression by ID"""
        for regression in REGRESSIONS:
            if regression.regression_id == regression_id:
                return regression
        return None


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def print_regression_summary():
    """Print a summary of all regressions"""
    from collections import Counter

    print("\n" + "="*80)
    print("REGRESSION CATALOG SUMMARY (v2.0)")
    print("="*80)

    type_counts = Counter(r.regression_type for r in REGRESSIONS)
    severity_counts = Counter(r.severity for r in REGRESSIONS)

    print(f"\nTotal Regressions: {len(REGRESSIONS)}")
    print("\nBy Type:")
    for reg_type, count in type_counts.items():
        print(f"  {reg_type}: {count}")

    print("\nBy Severity:")
    for severity, count in severity_counts.items():
        print(f"  {severity}: {count}")

    print("\nDetailed List:")
    print("-" * 80)
    for regression in REGRESSIONS:
        print(f"[{regression.regression_id}] {regression.category} ({regression.severity})")
        print(f"  {regression.description}")
        print(f"  Location: {regression.location}")
        print(f"  Expected: {regression.expected_behavior}")
        print(f"  Actual: {regression.actual_behavior}")
        print()


def create_regression_test_checklist():
    """Generate a markdown checklist for manual regression testing"""
    print("\n# Regression Testing Checklist (v1.0 → v2.0)\n")
    print("Test each regression to verify detection capability:\n")

    for regression in REGRESSIONS:
        print(f"- [ ] **{regression.regression_id}**: {regression.description}")
        print(f"  - **Type**: {regression.regression_type}")
        print(f"  - **Severity**: {regression.severity}")
        print(f"  - **Location**: {regression.location}")
        print(f"  - **Expected**: {regression.expected_behavior}")
        print(f"  - **Actual (v2.0)**: {regression.actual_behavior}")
        print()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "checklist":
        create_regression_test_checklist()
    else:
        print_regression_summary()
