"""
Statistical Analysis Module

Provides statistical tests, confidence intervals, and effect size calculations
for comparing experimental results against baselines.

Usage:
    from experiments.analysis import StatisticalAnalyzer

    analyzer = StatisticalAnalyzer(database_path='experiments/results/experiments.db')
    result = analyzer.compare_groups(experiment_id=1, group_by='num_agents')
    analyzer.print_comparison_report(result)
"""

import sqlite3
import numpy as np
from scipy import stats
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import json


@dataclass
class ComparisonResult:
    """Results from statistical comparison"""
    group1_name: str
    group2_name: str
    group1_mean: float
    group2_mean: float
    group1_std: float
    group2_std: float
    group1_n: int
    group2_n: int

    # Statistical tests
    t_statistic: float
    p_value: float
    significant: bool  # p < 0.05

    # Effect size
    cohens_d: float
    effect_interpretation: str  # small/medium/large

    # Confidence intervals
    group1_ci_lower: float
    group1_ci_upper: float
    group2_ci_lower: float
    group2_ci_upper: float

    # Improvement
    absolute_difference: float
    percent_improvement: float


class StatisticalAnalyzer:
    """Performs statistical analysis on experimental results"""

    def __init__(self, database_path: str):
        self.db_path = database_path

    def get_metric_values(self, experiment_id: int, metric_name: str,
                         group_by: Optional[str] = None,
                         group_value: Optional[str] = None) -> List[float]:
        """Get all values for a metric, optionally filtered by group"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if group_by and group_value is not None:
            cursor.execute(f"""
                SELECT m.{metric_name}
                FROM metrics m
                JOIN runs r ON m.run_id = r.id
                WHERE r.experiment_id = ? AND r.{group_by} = ?
                AND m.{metric_name} IS NOT NULL
            """, (experiment_id, group_value))
        else:
            cursor.execute(f"""
                SELECT {metric_name}
                FROM metrics m
                JOIN runs r ON m.run_id = r.id
                WHERE r.experiment_id = ? AND m.{metric_name} IS NOT NULL
            """, (experiment_id,))

        values = [row[0] for row in cursor.fetchall()]
        conn.close()

        return values

    def bootstrap_confidence_interval(self, data: List[float],
                                     confidence: float = 0.95,
                                     n_bootstrap: int = 10000) -> Tuple[float, float, float]:
        """Calculate bootstrap confidence interval"""
        if not data:
            return 0.0, 0.0, 0.0

        bootstrap_means = []
        for _ in range(n_bootstrap):
            sample = np.random.choice(data, size=len(data), replace=True)
            bootstrap_means.append(np.mean(sample))

        alpha = 1 - confidence
        lower = np.percentile(bootstrap_means, alpha/2 * 100)
        upper = np.percentile(bootstrap_means, (1 - alpha/2) * 100)
        mean = np.mean(data)

        return mean, lower, upper

    def cohens_d(self, group1: List[float], group2: List[float]) -> float:
        """Calculate Cohen's d effect size"""
        if not group1 or not group2:
            return 0.0

        n1, n2 = len(group1), len(group2)
        mean1, mean2 = np.mean(group1), np.mean(group2)
        var1, var2 = np.var(group1, ddof=1), np.var(group2, ddof=1)

        # Pooled standard deviation
        pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))

        if pooled_std == 0:
            return 0.0

        return (mean2 - mean1) / pooled_std

    def interpret_effect_size(self, d: float) -> str:
        """Interpret Cohen's d effect size"""
        abs_d = abs(d)
        if abs_d < 0.2:
            return "negligible"
        elif abs_d < 0.5:
            return "small"
        elif abs_d < 0.8:
            return "medium"
        else:
            return "large"

    def compare_two_groups(self, experiment_id: int, metric_name: str,
                          group_by: str, group1_value: str, group2_value: str,
                          confidence: float = 0.95) -> ComparisonResult:
        """Compare two groups using t-test"""

        # Get data for both groups
        group1_data = self.get_metric_values(experiment_id, metric_name, group_by, group1_value)
        group2_data = self.get_metric_values(experiment_id, metric_name, group_by, group2_value)

        if not group1_data or not group2_data:
            raise ValueError("Insufficient data for comparison")

        # Basic statistics
        mean1, mean2 = np.mean(group1_data), np.mean(group2_data)
        std1, std2 = np.std(group1_data, ddof=1), np.std(group2_data, ddof=1)
        n1, n2 = len(group1_data), len(group2_data)

        # T-test (two-tailed, independent samples)
        t_stat, p_value = stats.ttest_ind(group1_data, group2_data)

        # Effect size
        d = self.cohens_d(group1_data, group2_data)
        effect = self.interpret_effect_size(d)

        # Confidence intervals
        _, ci1_lower, ci1_upper = self.bootstrap_confidence_interval(group1_data, confidence)
        _, ci2_lower, ci2_upper = self.bootstrap_confidence_interval(group2_data, confidence)

        # Improvement calculations
        absolute_diff = mean2 - mean1
        percent_improvement = (absolute_diff / mean1 * 100) if mean1 != 0 else 0.0

        return ComparisonResult(
            group1_name=str(group1_value),
            group2_name=str(group2_value),
            group1_mean=mean1,
            group2_mean=mean2,
            group1_std=std1,
            group2_std=std2,
            group1_n=n1,
            group2_n=n2,
            t_statistic=t_stat,
            p_value=p_value,
            significant=(p_value < 0.05),
            cohens_d=d,
            effect_interpretation=effect,
            group1_ci_lower=ci1_lower,
            group1_ci_upper=ci1_upper,
            group2_ci_lower=ci2_lower,
            group2_ci_upper=ci2_upper,
            absolute_difference=absolute_diff,
            percent_improvement=percent_improvement
        )

    def anova_analysis(self, experiment_id: int, metric_name: str,
                      group_by: str) -> Dict:
        """Perform one-way ANOVA for multiple groups"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get unique group values
        cursor.execute(f"""
            SELECT DISTINCT {group_by}
            FROM runs
            WHERE experiment_id = ?
            ORDER BY {group_by}
        """, (experiment_id,))
        groups = [row[0] for row in cursor.fetchall()]
        conn.close()

        if len(groups) < 2:
            raise ValueError("Need at least 2 groups for ANOVA")

        # Get data for each group
        group_data = []
        for group in groups:
            data = self.get_metric_values(experiment_id, metric_name, group_by, group)
            group_data.append(data)

        # Perform ANOVA
        f_stat, p_value = stats.f_oneway(*group_data)

        # Post-hoc pairwise comparisons (if significant)
        pairwise_comparisons = []
        if p_value < 0.05:
            for i in range(len(groups)):
                for j in range(i + 1, len(groups)):
                    try:
                        comparison = self.compare_two_groups(
                            experiment_id, metric_name, group_by,
                            groups[i], groups[j]
                        )
                        pairwise_comparisons.append(comparison)
                    except ValueError:
                        continue

        return {
            'groups': groups,
            'f_statistic': f_stat,
            'p_value': p_value,
            'significant': (p_value < 0.05),
            'pairwise_comparisons': pairwise_comparisons,
            'group_means': [np.mean(data) if data else 0 for data in group_data],
            'group_stds': [np.std(data, ddof=1) if data else 0 for data in group_data],
            'group_ns': [len(data) for data in group_data]
        }

    def correlation_analysis(self, experiment_id: int,
                            metric1_name: str, metric2_name: str) -> Dict:
        """Calculate correlation between two metrics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(f"""
            SELECT {metric1_name}, {metric2_name}
            FROM metrics m
            JOIN runs r ON m.run_id = r.id
            WHERE r.experiment_id = ?
            AND {metric1_name} IS NOT NULL
            AND {metric2_name} IS NOT NULL
        """, (experiment_id,))

        data = cursor.fetchall()
        conn.close()

        if len(data) < 3:
            raise ValueError("Insufficient data for correlation")

        x = [row[0] for row in data]
        y = [row[1] for row in data]

        # Pearson correlation
        r_pearson, p_pearson = stats.pearsonr(x, y)

        # Spearman correlation (rank-based, more robust)
        r_spearman, p_spearman = stats.spearmanr(x, y)

        return {
            'metric1': metric1_name,
            'metric2': metric2_name,
            'n': len(data),
            'pearson_r': r_pearson,
            'pearson_p': p_pearson,
            'pearson_significant': (p_pearson < 0.05),
            'spearman_r': r_spearman,
            'spearman_p': p_spearman,
            'spearman_significant': (p_spearman < 0.05)
        }

    def baseline_comparison(self, experiment_id: int, metric_name: str,
                          baseline_value: float) -> Dict:
        """Compare experimental results against a baseline value"""

        data = self.get_metric_values(experiment_id, metric_name)

        if not data:
            raise ValueError("No data available")

        mean = np.mean(data)
        std = np.std(data, ddof=1)
        n = len(data)

        # One-sample t-test against baseline
        t_stat, p_value = stats.ttest_1samp(data, baseline_value)

        # Bootstrap CI
        _, ci_lower, ci_upper = self.bootstrap_confidence_interval(data)

        # Improvement over baseline
        absolute_diff = mean - baseline_value
        percent_improvement = (absolute_diff / baseline_value * 100) if baseline_value != 0 else 0.0

        # Effect size (Cohen's d from baseline)
        d = (mean - baseline_value) / std if std > 0 else 0.0

        return {
            'baseline_value': baseline_value,
            'experimental_mean': mean,
            'experimental_std': std,
            'n': n,
            'ci_lower': ci_lower,
            'ci_upper': ci_upper,
            't_statistic': t_stat,
            'p_value': p_value,
            'significant': (p_value < 0.05),
            'cohens_d': d,
            'effect_interpretation': self.interpret_effect_size(d),
            'absolute_improvement': absolute_diff,
            'percent_improvement': percent_improvement,
            'beats_baseline': (mean > baseline_value)
        }

    def print_comparison_report(self, result: ComparisonResult) -> None:
        """Print a formatted comparison report"""
        print("\n" + "="*80)
        print("STATISTICAL COMPARISON REPORT")
        print("="*80)

        print(f"\nGroup 1: {result.group1_name}")
        print(f"  Mean: {result.group1_mean:.2f} ± {result.group1_std:.2f} (n={result.group1_n})")
        print(f"  95% CI: [{result.group1_ci_lower:.2f}, {result.group1_ci_upper:.2f}]")

        print(f"\nGroup 2: {result.group2_name}")
        print(f"  Mean: {result.group2_mean:.2f} ± {result.group2_std:.2f} (n={result.group2_n})")
        print(f"  95% CI: [{result.group2_ci_lower:.2f}, {result.group2_ci_upper:.2f}]")

        print(f"\nDifference:")
        print(f"  Absolute: {result.absolute_difference:+.2f}")
        print(f"  Relative: {result.percent_improvement:+.1f}%")

        print(f"\nStatistical Test (Independent t-test):")
        print(f"  t-statistic: {result.t_statistic:.3f}")
        print(f"  p-value: {result.p_value:.4f}")
        print(f"  Significant: {'YES ✓' if result.significant else 'NO ✗'} (α = 0.05)")

        print(f"\nEffect Size (Cohen's d):")
        print(f"  d = {result.cohens_d:.3f}")
        print(f"  Interpretation: {result.effect_interpretation.upper()}")

        print("\n" + "="*80 + "\n")

    def print_anova_report(self, result: Dict) -> None:
        """Print formatted ANOVA report"""
        print("\n" + "="*80)
        print("ONE-WAY ANOVA REPORT")
        print("="*80)

        print(f"\nGroups: {', '.join(str(g) for g in result['groups'])}")

        print(f"\nGroup Statistics:")
        for i, group in enumerate(result['groups']):
            print(f"  {group}: {result['group_means'][i]:.2f} ± {result['group_stds'][i]:.2f} (n={result['group_ns'][i]})")

        print(f"\nANOVA Results:")
        print(f"  F-statistic: {result['f_statistic']:.3f}")
        print(f"  p-value: {result['p_value']:.4f}")
        print(f"  Significant: {'YES ✓' if result['significant'] else 'NO ✗'} (α = 0.05)")

        if result['pairwise_comparisons']:
            print(f"\nPost-hoc Pairwise Comparisons:")
            for comp in result['pairwise_comparisons']:
                sig_marker = "***" if comp.p_value < 0.001 else "**" if comp.p_value < 0.01 else "*" if comp.p_value < 0.05 else "ns"
                print(f"  {comp.group1_name} vs {comp.group2_name}: {comp.percent_improvement:+.1f}% (p={comp.p_value:.4f}) {sig_marker}")

        print("\n" + "="*80 + "\n")


def calculate_sample_size(effect_size: float, alpha: float = 0.05,
                         power: float = 0.80) -> int:
    """Calculate required sample size for detecting an effect"""
    from scipy.stats import norm

    z_alpha = norm.ppf(1 - alpha/2)
    z_beta = norm.ppf(power)

    n = ((z_alpha + z_beta) ** 2 * 2) / (effect_size ** 2)
    return int(np.ceil(n))


if __name__ == "__main__":
    # Example usage
    print("Statistical Analysis Module")
    print("=" * 60)

    print("\nSupported analyses:")
    print("  - Two-group comparison (t-test)")
    print("  - Multi-group comparison (ANOVA)")
    print("  - Correlation analysis (Pearson, Spearman)")
    print("  - Baseline comparison (one-sample t-test)")
    print("  - Bootstrap confidence intervals")
    print("  - Cohen's d effect size")
    print("  - Sample size calculation")

    print("\nExample effect size calculations:")
    for d in [0.2, 0.5, 0.8]:
        n = calculate_sample_size(d)
        print(f"  d={d} ({['negligible', 'small', 'medium', 'large'][int(d/0.3)]}): n={n} per group")
