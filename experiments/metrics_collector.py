"""
Enhanced Metrics Collection Module

Calculates comprehensive metrics for all experiments including:
- Task success metrics
- Security/safety metrics
- Performance metrics (latency, percentiles)
- Multi-agent metrics (agreement, consensus)
- Vision metrics (element localization, action precision)
- Cost metrics
- Behavioral diversity metrics

Usage:
    from experiments.metrics_collector import MetricsCollector

    collector = MetricsCollector(database_path='experiments/results/experiments.db')
    metrics = collector.calculate_run_metrics(run_id=1)
    collector.save_metrics(run_id=1, metrics)
"""

import sqlite3
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import json


@dataclass
class RunMetrics:
    """Complete metrics for a single run"""
    # Task Success
    task_success_rate: float = 0.0
    total_successful_turns: int = 0
    total_turns: int = 0

    # Safety & Security
    safety_pass_rate: float = 0.0
    total_safe_turns: int = 0
    vulnerabilities_detected: int = 0
    false_positives: int = 0
    true_positive_rate: float = 0.0
    false_positive_rate: float = 0.0
    f1_score: float = 0.0

    # Performance
    avg_latency_seconds: float = 0.0
    p50_latency_seconds: float = 0.0
    p95_latency_seconds: float = 0.0
    p99_latency_seconds: float = 0.0

    # Multi-Agent
    avg_committee_agreement: float = 0.0
    consensus_strength: float = 0.0
    mind_changes: int = 0

    # Vision
    element_localization_accuracy: float = 0.0
    action_precision: float = 0.0
    false_action_rate: float = 0.0

    # Cost
    total_api_calls: int = 0
    total_cost_usd: float = 0.0
    cost_per_successful_task: float = 0.0

    # WebShop Specific
    webshop_reward_score: float = 0.0
    action_efficiency: float = 0.0

    # Behavioral Diversity
    unique_actions: int = 0
    action_sequence_length: int = 0
    behavioral_diversity_score: float = 0.0

    def to_dict(self) -> Dict:
        return asdict(self)


class MetricsCollector:
    """Collects and calculates metrics from test runs"""

    # API pricing per 1M tokens (as of 2024)
    PRICING = {
        'gpt-4o': {'input': 2.50, 'output': 10.00},
        'gemini-2.5-pro': {'input': 1.25, 'output': 5.00},
        'claude-opus-4-1': {'input': 15.00, 'output': 75.00},
        'grok-2-vision-1212': {'input': 2.00, 'output': 10.00},
    }

    def __init__(self, database_path: str):
        self.db_path = database_path

    def calculate_run_metrics(self, run_id: int) -> RunMetrics:
        """Calculate all metrics for a single run"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        metrics = RunMetrics()

        # Get run info
        cursor.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
        run = cursor.fetchone()
        if not run:
            conn.close()
            return metrics

        # Get all turns for this run
        cursor.execute("SELECT * FROM turns WHERE run_id = ? ORDER BY turn_number", (run_id,))
        turns = [dict(row) for row in cursor.fetchall()]

        if not turns:
            conn.close()
            return metrics

        # === Task Success Metrics ===
        metrics.total_turns = len(turns)
        metrics.total_successful_turns = sum(1 for t in turns if t['success'])
        metrics.task_success_rate = (metrics.total_successful_turns / metrics.total_turns * 100) if metrics.total_turns > 0 else 0

        # === Safety Metrics ===
        metrics.total_safe_turns = sum(1 for t in turns if t['safety_pass'])
        metrics.safety_pass_rate = (metrics.total_safe_turns / metrics.total_turns * 100) if metrics.total_turns > 0 else 0

        # === Security Bug Detection ===
        cursor.execute("""
            SELECT COUNT(*) FROM bugs
            WHERE run_id = ? AND detected = 1 AND is_ground_truth = 1
        """, (run_id,))
        metrics.vulnerabilities_detected = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) FROM bugs
            WHERE run_id = ? AND is_false_positive = 1
        """, (run_id,))
        metrics.false_positives = cursor.fetchone()[0]

        # Calculate TPR and FPR
        cursor.execute("""
            SELECT COUNT(*) FROM bugs
            WHERE experiment_id = (SELECT experiment_id FROM runs WHERE id = ?)
            AND is_ground_truth = 1
        """, (run_id,))
        total_ground_truth = cursor.fetchone()[0]

        if total_ground_truth > 0:
            metrics.true_positive_rate = (metrics.vulnerabilities_detected / total_ground_truth) * 100

        total_detections = metrics.vulnerabilities_detected + metrics.false_positives
        if total_detections > 0:
            metrics.false_positive_rate = (metrics.false_positives / total_detections) * 100

            # F1 Score
            precision = metrics.vulnerabilities_detected / total_detections if total_detections > 0 else 0
            recall = metrics.vulnerabilities_detected / total_ground_truth if total_ground_truth > 0 else 0
            if precision + recall > 0:
                metrics.f1_score = 2 * (precision * recall) / (precision + recall)

        # === Performance Metrics ===
        latencies = [t['latency_seconds'] for t in turns if t['latency_seconds'] is not None]
        if latencies:
            metrics.avg_latency_seconds = np.mean(latencies)
            metrics.p50_latency_seconds = np.percentile(latencies, 50)
            metrics.p95_latency_seconds = np.percentile(latencies, 95)
            metrics.p99_latency_seconds = np.percentile(latencies, 99)

        # === Multi-Agent Metrics ===
        if run['num_agents'] > 1:
            agreements = [t['agreement_percentage'] for t in turns if t['agreement_percentage'] is not None]
            if agreements:
                metrics.avg_committee_agreement = np.mean(agreements)

            # Consensus strength: percentage of turns where consensus was reached (>50% agreement)
            consensus_turns = sum(1 for a in agreements if a > 50)
            metrics.consensus_strength = (consensus_turns / len(agreements) * 100) if agreements else 0

            # Mind changes
            cursor.execute("""
                SELECT COUNT(*) FROM proposals
                WHERE run_id = ? AND changed_from_previous_round = 1
            """, (run_id,))
            metrics.mind_changes = cursor.fetchone()[0]

        # === Vision Metrics ===
        if run['vision_enabled']:
            elements_found = sum(1 for t in turns if t['element_found'])
            correct_elements = sum(1 for t in turns if t['correct_element'])

            if elements_found > 0:
                metrics.element_localization_accuracy = (correct_elements / elements_found) * 100

            # Action precision: successful actions / total actions
            metrics.action_precision = metrics.task_success_rate  # Same as task success for now
            metrics.false_action_rate = 100 - metrics.action_precision

        # === Cost Metrics ===
        cursor.execute("""
            SELECT COUNT(*) FROM proposals WHERE run_id = ?
        """, (run_id,))
        metrics.total_api_calls = cursor.fetchone()[0]

        # Estimate cost (rough approximation based on model)
        model_provider = run['model_provider']
        if model_provider in self.PRICING:
            # Assume avg 500 input tokens, 200 output tokens per call
            avg_input_tokens = 500
            avg_output_tokens = 200
            pricing = self.PRICING[model_provider]
            cost_per_call = (avg_input_tokens * pricing['input'] + avg_output_tokens * pricing['output']) / 1_000_000
            metrics.total_cost_usd = metrics.total_api_calls * cost_per_call

            if metrics.total_successful_turns > 0:
                metrics.cost_per_successful_task = metrics.total_cost_usd / metrics.total_successful_turns

        # === WebShop Metrics ===
        cursor.execute("""
            SELECT AVG(reward_score), AVG(num_steps)
            FROM webshop_results
            WHERE run_id = ?
        """, (run_id,))
        webshop_result = cursor.fetchone()
        if webshop_result[0] is not None:
            metrics.webshop_reward_score = webshop_result[0]
            metrics.action_efficiency = webshop_result[1]

        # === Behavioral Diversity ===
        cursor.execute("""
            SELECT DISTINCT action_type FROM turns WHERE run_id = ?
        """, (run_id,))
        metrics.unique_actions = len(cursor.fetchall())
        metrics.action_sequence_length = metrics.total_turns

        # Jaccard diversity would require comparison with other runs
        # For now, use unique actions / total turns as a proxy
        metrics.behavioral_diversity_score = metrics.unique_actions / metrics.total_turns if metrics.total_turns > 0 else 0

        conn.close()
        return metrics

    def save_metrics(self, run_id: int, metrics: RunMetrics) -> None:
        """Save calculated metrics to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO metrics (
                run_id, task_success_rate, total_successful_turns, total_turns,
                safety_pass_rate, total_safe_turns, vulnerabilities_detected,
                false_positives, true_positive_rate, false_positive_rate, f1_score,
                avg_latency_seconds, p50_latency_seconds, p95_latency_seconds, p99_latency_seconds,
                avg_committee_agreement, consensus_strength, mind_changes,
                element_localization_accuracy, action_precision, false_action_rate,
                total_api_calls, total_cost_usd, cost_per_successful_task,
                webshop_reward_score, action_efficiency,
                unique_actions, action_sequence_length, behavioral_diversity_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id,
            metrics.task_success_rate, metrics.total_successful_turns, metrics.total_turns,
            metrics.safety_pass_rate, metrics.total_safe_turns, metrics.vulnerabilities_detected,
            metrics.false_positives, metrics.true_positive_rate, metrics.false_positive_rate, metrics.f1_score,
            metrics.avg_latency_seconds, metrics.p50_latency_seconds, metrics.p95_latency_seconds, metrics.p99_latency_seconds,
            metrics.avg_committee_agreement, metrics.consensus_strength, metrics.mind_changes,
            metrics.element_localization_accuracy, metrics.action_precision, metrics.false_action_rate,
            metrics.total_api_calls, metrics.total_cost_usd, metrics.cost_per_successful_task,
            metrics.webshop_reward_score, metrics.action_efficiency,
            metrics.unique_actions, metrics.action_sequence_length, metrics.behavioral_diversity_score
        ))

        conn.commit()
        conn.close()

    def calculate_aggregate_metrics(self, experiment_id: int) -> Dict:
        """Calculate aggregate metrics across all runs in an experiment"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                AVG(task_success_rate) as avg_success_rate,
                AVG(safety_pass_rate) as avg_safety_rate,
                AVG(true_positive_rate) as avg_tpr,
                AVG(false_positive_rate) as avg_fpr,
                AVG(f1_score) as avg_f1,
                AVG(avg_latency_seconds) as avg_latency,
                AVG(p95_latency_seconds) as avg_p95_latency,
                AVG(avg_committee_agreement) as avg_agreement,
                AVG(total_cost_usd) as avg_cost,
                COUNT(*) as num_runs
            FROM metrics m
            JOIN runs r ON m.run_id = r.id
            WHERE r.experiment_id = ?
        """, (experiment_id,))

        result = dict(cursor.fetchone())
        conn.close()

        return result

    def calculate_confidence_intervals(self, experiment_id: int, metric_name: str, confidence: float = 0.95) -> Tuple[float, float, float]:
        """Calculate confidence interval for a metric using bootstrap"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(f"""
            SELECT {metric_name}
            FROM metrics m
            JOIN runs r ON m.run_id = r.id
            WHERE r.experiment_id = ?
        """, (experiment_id,))

        values = [row[0] for row in cursor.fetchall() if row[0] is not None]
        conn.close()

        if not values:
            return 0.0, 0.0, 0.0

        # Bootstrap confidence interval
        n_bootstrap = 10000
        bootstrap_means = []

        for _ in range(n_bootstrap):
            sample = np.random.choice(values, size=len(values), replace=True)
            bootstrap_means.append(np.mean(sample))

        alpha = 1 - confidence
        lower = np.percentile(bootstrap_means, alpha/2 * 100)
        upper = np.percentile(bootstrap_means, (1 - alpha/2) * 100)
        mean = np.mean(values)

        return mean, lower, upper

    def compare_configurations(self, experiment_id: int, group_by: str) -> List[Dict]:
        """Compare metrics across different configurations (e.g., by num_agents, model_provider)"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(f"""
            SELECT
                r.{group_by},
                AVG(m.task_success_rate) as avg_success_rate,
                AVG(m.vulnerabilities_detected) as avg_bugs_detected,
                AVG(m.avg_committee_agreement) as avg_agreement,
                AVG(m.total_cost_usd) as avg_cost,
                COUNT(*) as num_runs
            FROM runs r
            JOIN metrics m ON r.id = m.run_id
            WHERE r.experiment_id = ?
            GROUP BY r.{group_by}
            ORDER BY r.{group_by}
        """, (experiment_id,))

        results = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return results

    def calculate_jaccard_similarity(self, run_id1: int, run_id2: int) -> float:
        """Calculate Jaccard similarity between action sequences of two runs"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT action_type FROM turns WHERE run_id = ? ORDER BY turn_number
        """, (run_id1,))
        actions1 = set(row[0] for row in cursor.fetchall())

        cursor.execute("""
            SELECT action_type FROM turns WHERE run_id = ? ORDER BY turn_number
        """, (run_id2,))
        actions2 = set(row[0] for row in cursor.fetchall())

        conn.close()

        if not actions1 and not actions2:
            return 1.0

        intersection = len(actions1.intersection(actions2))
        union = len(actions1.union(actions2))

        return intersection / union if union > 0 else 0.0


def calculate_improvement_percentage(baseline: float, experimental: float) -> float:
    """Calculate percentage improvement over baseline"""
    if baseline == 0:
        return 0.0
    return ((experimental - baseline) / baseline) * 100


def format_metrics_summary(metrics: RunMetrics) -> str:
    """Format metrics as a readable summary"""
    summary = f"""
Metrics Summary
{'='*60}
Task Success: {metrics.task_success_rate:.2f}% ({metrics.total_successful_turns}/{metrics.total_turns})
Safety Pass: {metrics.safety_pass_rate:.2f}%
Vulnerabilities Detected: {metrics.vulnerabilities_detected}
  - True Positive Rate: {metrics.true_positive_rate:.2f}%
  - False Positive Rate: {metrics.false_positive_rate:.2f}%
  - F1 Score: {metrics.f1_score:.4f}

Performance:
  - Avg Latency: {metrics.avg_latency_seconds:.2f}s
  - P95 Latency: {metrics.p95_latency_seconds:.2f}s

Multi-Agent:
  - Avg Agreement: {metrics.avg_committee_agreement:.2f}%
  - Consensus Strength: {metrics.consensus_strength:.2f}%
  - Mind Changes: {metrics.mind_changes}

Vision:
  - Element Localization: {metrics.element_localization_accuracy:.2f}%
  - Action Precision: {metrics.action_precision:.2f}%

Cost:
  - Total API Calls: {metrics.total_api_calls}
  - Total Cost: ${metrics.total_cost_usd:.4f}
  - Cost per Success: ${metrics.cost_per_successful_task:.4f}
"""
    return summary


if __name__ == "__main__":
    # Example usage
    collector = MetricsCollector("experiments/results/experiments.db")

    # This would work after experiments are run
    # metrics = collector.calculate_run_metrics(run_id=1)
    # print(format_metrics_summary(metrics))

    print("MetricsCollector module loaded successfully")
    print("\nSupported metrics:")
    print("  - Task success rate, safety pass rate")
    print("  - Security bug detection (TPR, FPR, F1)")
    print("  - Performance (latency percentiles)")
    print("  - Multi-agent (agreement, consensus, mind changes)")
    print("  - Vision (element localization, action precision)")
    print("  - Cost (API calls, USD, cost per success)")
    print("  - Behavioral diversity (Jaccard similarity)")
