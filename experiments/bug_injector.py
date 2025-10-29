"""
Bug Injection Module for LLM Beta Testing Framework

This module defines ground truth bugs to inject into the AUT for Experiment 1B (Persona Behavioral Diversity).
Bugs are categorized into: Functional, Security, Business Logic, and Accessibility.

Usage:
    from experiments.bug_injector import INJECTED_BUGS, BugInjector

    bugs = BugInjector.get_bugs_by_type('security')
    injector = BugInjector(database_path='experiments/results/experiments.db')
    injector.load_ground_truth()
"""

import sqlite3
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class BugType(Enum):
    FUNCTIONAL = "functional"
    SECURITY = "security"
    BUSINESS_LOGIC = "business_logic"
    ACCESSIBILITY = "accessibility"


class Severity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Bug:
    """Represents a known bug injected for testing"""
    bug_id: str
    bug_type: str
    bug_category: str
    severity: str
    description: str
    location: str
    injected_in_version: str = "v1.0"

    def to_dict(self) -> Dict:
        return asdict(self)


# ============================================================================
# INJECTED BUGS CATALOG (20 total for Experiment 1B)
# ============================================================================

INJECTED_BUGS = [
    # ========== FUNCTIONAL BUGS (5) ==========
    Bug(
        bug_id="FUNC-001",
        bug_type="functional",
        bug_category="broken_checkout",
        severity="high",
        description="Checkout process fails when cart contains more than 5 items",
        location="/api/checkout endpoint"
    ),
    Bug(
        bug_id="FUNC-002",
        bug_type="functional",
        bug_category="incorrect_calculation",
        severity="high",
        description="Cart total calculation ignores tax when shipping address is international",
        location="/api/cart/total endpoint"
    ),
    Bug(
        bug_id="FUNC-003",
        bug_type="functional",
        bug_category="cart_persistence",
        severity="medium",
        description="Items added to cart are lost after user navigates away from page",
        location="/api/cart endpoint, session handling"
    ),
    Bug(
        bug_id="FUNC-004",
        bug_type="functional",
        bug_category="search_failure",
        severity="medium",
        description="Product search returns empty results for queries containing special characters",
        location="/api/products/search endpoint"
    ),
    Bug(
        bug_id="FUNC-005",
        bug_type="functional",
        bug_category="duplicate_orders",
        severity="high",
        description="Double-clicking checkout button creates duplicate orders",
        location="/api/checkout endpoint, no idempotency check"
    ),

    # ========== SECURITY BUGS (7) ==========
    Bug(
        bug_id="SEC-001",
        bug_type="security",
        bug_category="sql_injection",
        severity="critical",
        description="Product search endpoint vulnerable to SQL injection via 'query' parameter",
        location="/api/products/search?query=<injection>"
    ),
    Bug(
        bug_id="SEC-002",
        bug_type="security",
        bug_category="xss",
        severity="high",
        description="Product review submission allows JavaScript execution in review text",
        location="/api/reviews endpoint, review_text field"
    ),
    Bug(
        bug_id="SEC-003",
        bug_type="security",
        bug_category="command_injection",
        severity="critical",
        description="Image upload filename parameter vulnerable to command injection",
        location="/api/upload endpoint, filename parameter"
    ),
    Bug(
        bug_id="SEC-004",
        bug_type="security",
        bug_category="path_traversal",
        severity="high",
        description="Static file endpoint allows directory traversal to read arbitrary files",
        location="/static/<path:filename> endpoint"
    ),
    Bug(
        bug_id="SEC-005",
        bug_type="security",
        bug_category="broken_authentication",
        severity="critical",
        description="Password reset endpoint does not validate token expiration",
        location="/api/auth/reset-password endpoint"
    ),
    Bug(
        bug_id="SEC-006",
        bug_type="security",
        bug_category="insecure_deserialization",
        severity="high",
        description="Session cookie uses pickle deserialization without validation",
        location="Session handling middleware"
    ),
    Bug(
        bug_id="SEC-007",
        bug_type="security",
        bug_category="csrf",
        severity="medium",
        description="State-changing operations lack CSRF token validation",
        location="/api/cart, /api/checkout endpoints"
    ),

    # ========== BUSINESS LOGIC BUGS (4) ==========
    Bug(
        bug_id="BL-001",
        bug_type="business_logic",
        bug_category="price_manipulation",
        severity="critical",
        description="Cart endpoint accepts negative prices, allowing users to add credit to account",
        location="/api/cart/add endpoint, price validation"
    ),
    Bug(
        bug_id="BL-002",
        bug_type="business_logic",
        bug_category="negative_quantity",
        severity="high",
        description="Negative quantities allowed in cart, causing refunds instead of charges",
        location="/api/cart/add endpoint, quantity validation"
    ),
    Bug(
        bug_id="BL-003",
        bug_type="business_logic",
        bug_category="stock_overflow",
        severity="medium",
        description="Users can order more items than available in stock",
        location="/api/cart/add endpoint, stock check"
    ),
    Bug(
        bug_id="BL-004",
        bug_type="business_logic",
        bug_category="discount_stacking",
        severity="medium",
        description="Multiple discount codes can be applied to same order, exceeding maximum discount",
        location="/api/cart/apply-discount endpoint"
    ),

    # ========== ACCESSIBILITY BUGS (4) ==========
    Bug(
        bug_id="A11Y-001",
        bug_type="accessibility",
        bug_category="missing_alt_text",
        severity="medium",
        description="Product images lack alt text, preventing screen reader users from understanding content",
        location="Product list and detail pages, <img> tags"
    ),
    Bug(
        bug_id="A11Y-002",
        bug_type="accessibility",
        bug_category="poor_contrast",
        severity="low",
        description="Primary CTA buttons have insufficient color contrast (WCAG AA failure)",
        location="Checkout button, Add to Cart button CSS"
    ),
    Bug(
        bug_id="A11Y-003",
        bug_type="accessibility",
        bug_category="keyboard_navigation",
        severity="high",
        description="Product carousel cannot be navigated using keyboard (tab key)",
        location="Homepage carousel component"
    ),
    Bug(
        bug_id="A11Y-004",
        bug_type="accessibility",
        bug_category="missing_labels",
        severity="medium",
        description="Form inputs in checkout lack associated labels for screen readers",
        location="Checkout form, shipping address inputs"
    ),
]


# ============================================================================
# BUG INJECTOR CLASS
# ============================================================================

class BugInjector:
    """Manages bug injection and ground truth tracking"""

    def __init__(self, database_path: str):
        self.db_path = database_path
        self.bugs = INJECTED_BUGS

    def load_ground_truth(self, experiment_id: int) -> None:
        """Load all injected bugs into the database as ground truth"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for bug in self.bugs:
            cursor.execute("""
                INSERT OR IGNORE INTO bugs (
                    run_id, experiment_id, bug_id, bug_type, bug_category,
                    severity, description, location, injected_in_version,
                    is_ground_truth, detected
                ) VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?, 1, 0)
            """, (
                experiment_id,
                bug.bug_id,
                bug.bug_type,
                bug.bug_category,
                bug.severity,
                bug.description,
                bug.location,
                bug.injected_in_version
            ))

        conn.commit()
        conn.close()
        print(f"✓ Loaded {len(self.bugs)} ground truth bugs for experiment {experiment_id}")

    def mark_detected(self, run_id: int, bug_id: str, turn: int,
                      persona: str, confidence: float = 1.0) -> None:
        """Mark a bug as detected during a test run"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE bugs
            SET detected = 1,
                detected_at_turn = ?,
                detected_by_persona = ?,
                detection_confidence = ?,
                run_id = ?
            WHERE bug_id = ? AND (run_id IS NULL OR run_id = ?)
        """, (turn, persona, confidence, run_id, bug_id, run_id))

        conn.commit()
        conn.close()

    def add_false_positive(self, run_id: int, bug_type: str, bug_category: str,
                          description: str, turn: int, persona: str) -> None:
        """Record a false positive (bug reported but not in ground truth)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Generate bug_id for false positive
        cursor.execute("SELECT COUNT(*) FROM bugs WHERE run_id = ? AND is_false_positive = 1", (run_id,))
        fp_count = cursor.fetchone()[0]
        bug_id = f"FP-{run_id}-{fp_count + 1}"

        cursor.execute("""
            INSERT INTO bugs (
                run_id, experiment_id, bug_id, bug_type, bug_category,
                severity, description, location,
                is_ground_truth, detected, is_false_positive,
                detected_at_turn, detected_by_persona
            ) SELECT
                ?, experiment_id, ?, ?, ?, 'unknown', ?, 'unknown',
                0, 1, 1, ?, ?
            FROM runs WHERE id = ?
        """, (run_id, bug_id, bug_type, bug_category, description, turn, persona, run_id))

        conn.commit()
        conn.close()

    @staticmethod
    def get_bugs_by_type(bug_type: str) -> List[Bug]:
        """Get all bugs of a specific type"""
        return [bug for bug in INJECTED_BUGS if bug.bug_type == bug_type]

    @staticmethod
    def get_bugs_by_severity(severity: str) -> List[Bug]:
        """Get all bugs of a specific severity"""
        return [bug for bug in INJECTED_BUGS if bug.severity == severity]

    @staticmethod
    def get_bug_by_id(bug_id: str) -> Optional[Bug]:
        """Get a specific bug by ID"""
        for bug in INJECTED_BUGS:
            if bug.bug_id == bug_id:
                return bug
        return None

    def get_detection_stats(self, experiment_id: int) -> Dict:
        """Calculate detection statistics across all runs"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Total ground truth bugs
        cursor.execute("""
            SELECT COUNT(*) FROM bugs
            WHERE experiment_id = ? AND is_ground_truth = 1
        """, (experiment_id,))
        total_bugs = cursor.fetchone()[0]

        # Detected bugs
        cursor.execute("""
            SELECT COUNT(DISTINCT bug_id) FROM bugs
            WHERE experiment_id = ? AND is_ground_truth = 1 AND detected = 1
        """, (experiment_id,))
        detected_bugs = cursor.fetchone()[0]

        # False positives
        cursor.execute("""
            SELECT COUNT(*) FROM bugs
            WHERE experiment_id = ? AND is_false_positive = 1
        """, (experiment_id,))
        false_positives = cursor.fetchone()[0]

        # True positive rate
        tpr = (detected_bugs / total_bugs * 100) if total_bugs > 0 else 0

        # False positive rate (FP / (FP + TN))
        # Approximation: Assume large number of possible non-bugs
        total_possible_reports = detected_bugs + false_positives
        fpr = (false_positives / total_possible_reports * 100) if total_possible_reports > 0 else 0

        conn.close()

        return {
            "total_ground_truth_bugs": total_bugs,
            "bugs_detected": detected_bugs,
            "false_positives": false_positives,
            "true_positive_rate": round(tpr, 2),
            "false_positive_rate": round(fpr, 2),
            "detection_rate": round(tpr, 2)
        }

    def get_persona_coverage_matrix(self, experiment_id: int) -> Dict:
        """Get bug detection breakdown by persona and bug type"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                detected_by_persona as persona,
                bug_type,
                COUNT(DISTINCT bug_id) as bugs_detected
            FROM bugs
            WHERE experiment_id = ? AND detected = 1 AND is_ground_truth = 1
            GROUP BY detected_by_persona, bug_type
        """, (experiment_id,))

        results = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return results


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def print_bug_summary():
    """Print a summary of all injected bugs"""
    from collections import Counter

    print("\n" + "="*80)
    print("BUG INJECTION CATALOG SUMMARY")
    print("="*80)

    type_counts = Counter(bug.bug_type for bug in INJECTED_BUGS)
    severity_counts = Counter(bug.severity for bug in INJECTED_BUGS)

    print(f"\nTotal Bugs: {len(INJECTED_BUGS)}")
    print("\nBy Type:")
    for bug_type, count in type_counts.items():
        print(f"  {bug_type}: {count}")

    print("\nBy Severity:")
    for severity, count in severity_counts.items():
        print(f"  {severity}: {count}")

    print("\nDetailed List:")
    print("-" * 80)
    for bug in INJECTED_BUGS:
        print(f"[{bug.bug_id}] {bug.bug_category} ({bug.severity})")
        print(f"  {bug.description}")
        print(f"  Location: {bug.location}")
        print()


if __name__ == "__main__":
    print_bug_summary()
