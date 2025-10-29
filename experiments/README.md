# LLM Beta Testing Framework - Experimental Infrastructure

This directory contains the complete experimental framework for conducting rigorous evaluations and writing the NeurIPS-format paper.

## 📁 Directory Structure

```
experiments/
├── schema.sql                  # SQLite database schema (15+ tables)
├── runner.py                   # Main experiment orchestrator
├── bug_injector.py            # 20 ground truth bugs for testing
├── regressions.py             # 15 regressions for v1.0 → v2.0 testing
├── metrics_collector.py       # Comprehensive metrics calculation
├── analysis.py                # Statistical analysis (TODO)
├── plots.py                   # Visualization suite (TODO)
├── configs/                   # Experiment configurations
│   ├── experiment_1a_multi_agent_scaling.yaml
│   ├── experiment_1b_persona_diversity.yaml
│   ├── experiment_1c_vision_impact.yaml
│   └── experiment_1d_regression_detection.yaml
├── benchmarks/                # External benchmark integrations
│   ├── juice_shop.py          # OWASP Juice Shop adapter (TODO)
│   └── webshop.py             # WebShop adapter (TODO)
├── results/                   # Experiment outputs
│   ├── experiments.db         # SQLite database
│   └── runs/                  # Per-run data and screenshots
└── README.md                  # This file
```

## ✅ Completed Components

### 1. Database Schema ([schema.sql](schema.sql))
Comprehensive SQLite schema supporting:
- **Experiments**: Metadata, research questions, baselines
- **Runs**: Individual test executions with seeds
- **Metrics**: 28 quantitative measurements per run
- **Bugs**: Ground truth (20 bugs) and detection tracking
- **Regressions**: Version comparison (15 regressions)
- **Proposals**: Multi-agent proposal logging
- **Turns**: Turn-by-turn execution details
- **OWASP/WebShop**: Benchmark-specific tables
- **Views**: Pre-built queries for analysis

### 2. Bug Injection Module ([bug_injector.py](bug_injector.py))
**20 Ground Truth Bugs:**
- 5 Functional bugs (broken checkout, cart issues, search failures)
- 7 Security bugs (SQL injection, XSS, command injection, path traversal, CSRF)
- 4 Business Logic bugs (price manipulation, negative quantities, stock overflow)
- 4 Accessibility bugs (missing alt text, poor contrast, keyboard nav)

**Features:**
- Automatic ground truth loading
- Detection tracking (TP, FP)
- Persona coverage matrix calculation
- TPR/FPR/F1 score computation

### 3. Regression Definitions ([regressions.py](regressions.py))
**15 Intentional Regressions for v2.0:**
- 5 Breaking changes (removed endpoints, changed formats, new requirements)
- 5 Behavioral changes (calculation changes, workflow modifications)
- 3 Performance degradations (timeouts, slow responses, memory leaks)
- 2 UI regressions (broken layouts, missing elements)

**Features:**
- Regression detection tracking
- Statistics by regression type
- False positive handling

### 4. Metrics Collection ([metrics_collector.py](metrics_collector.py))
**28 Metrics Tracked:**

**Task Success:**
- Task success rate, total successful turns

**Security:**
- Safety pass rate, vulnerabilities detected
- True positive rate, false positive rate, F1 score

**Performance:**
- Average latency, P50/P95/P99 latencies

**Multi-Agent:**
- Committee agreement, consensus strength, mind changes

**Vision:**
- Element localization accuracy, action precision, false action rate

**Cost:**
- Total API calls, total cost USD, cost per successful task

**Behavioral:**
- Unique actions, behavioral diversity score

### 5. Experiment Configurations

#### Experiment 1A: Multi-Agent Committee Scaling
- **Research Question**: Does committee size improve testing quality?
- **Baseline**: Self-Collaboration paper (10-15% improvement)
- **Configurations**: 1, 2, 3, 4 agents
- **Total Runs**: 60 (4 configs × 3 scenarios × 5 runs)

#### Experiment 1B: Persona Behavioral Diversity
- **Research Question**: Do different personas find distinct bugs?
- **Baseline**: Wang et al. coverage (60-80%)
- **Configurations**: 9 personas
- **Total Runs**: 27 (9 personas × 3 runs)

#### Experiment 1C: Vision-Enabled Testing Impact
- **Research Question**: Does vision improve testing accuracy?
- **Baseline**: VisualWebArena (38.2% success, 65.7% element accuracy)
- **Configurations**: Vision vs text-only, 4 models
- **Total Runs**: 120 (6 configs × 4 scenarios × 5 runs)

#### Experiment 1D: Regression Detection
- **Research Question**: Can agents detect regressions across versions?
- **Baseline**: Novel contribution (no prior work)
- **Configurations**: v1.0 vs v2.0, 3 personas
- **Total Runs**: 90 (6 configs × 3 scenarios × 5 runs)

### 6. Experiment Runner ([runner.py](runner.py))
Orchestrates experiment execution with:
- Configuration-driven approach (YAML)
- Seed management for reproducibility
- Database logging (runs, turns, proposals, metrics)
- Automatic metrics calculation
- Error handling and checkpointing
- Dry-run mode for validation

## 🚀 Quick Start

### Setup Database
```bash
# Database is automatically initialized on first run
python experiments/runner.py --experiment 1a --dry-run
```

### Run Experiments

```bash
# Run Experiment 1A (Multi-Agent Scaling)
python experiments/runner.py --experiment 1a

# Run Experiment 1B (Persona Diversity)
python experiments/runner.py --experiment 1b

# Run Experiment 1C (Vision Impact)
python experiments/runner.py --experiment 1c

# Run Experiment 1D (Regression Detection)
python experiments/runner.py --experiment 1d

# Run custom config
python experiments/runner.py --config experiments/configs/my_experiment.yaml

# Dry run (validate config without executing)
python experiments/runner.py --experiment 1a --dry-run
```

### Query Results

```bash
# Open database
sqlite3 experiments/results/experiments.db

# View experiment summary
SELECT * FROM experiment_summary;

# View multi-agent scaling results
SELECT * FROM multi_agent_scaling;

# View persona coverage
SELECT * FROM persona_coverage;

# Custom query
SELECT
    num_agents,
    AVG(task_success_rate) as avg_success,
    AVG(total_cost_usd) as avg_cost
FROM runs r
JOIN metrics m ON r.id = m.run_id
GROUP BY num_agents;
```

## 📊 Metrics & Analysis

### Available Metrics (Per Run)
```python
from experiments.metrics_collector import MetricsCollector

collector = MetricsCollector("experiments/results/experiments.db")

# Calculate metrics for a run
metrics = collector.calculate_run_metrics(run_id=1)
print(metrics.task_success_rate)  # 75.5%
print(metrics.true_positive_rate)  # 62.3%
print(metrics.avg_committee_agreement)  # 85.2%

# Aggregate across experiment
stats = collector.calculate_aggregate_metrics(experiment_id=1)
print(stats['avg_success_rate'])  # 72.8%

# Confidence intervals
mean, lower, upper = collector.calculate_confidence_intervals(
    experiment_id=1,
    metric_name='task_success_rate',
    confidence=0.95
)
print(f"{mean:.2f}% [95% CI: {lower:.2f}%, {upper:.2f}%]")
```

### Comparison Analysis
```python
# Compare configurations (e.g., by num_agents)
results = collector.compare_configurations(
    experiment_id=1,
    group_by='num_agents'
)

for result in results:
    print(f"Agents: {result['num_agents']}, Success: {result['avg_success_rate']:.2f}%")
```

## 🐛 Bug Detection Analysis

```python
from experiments.bug_injector import BugInjector

injector = BugInjector("experiments/results/experiments.db")

# Get detection statistics
stats = injector.get_detection_stats(experiment_id=2)
print(f"Bugs detected: {stats['bugs_detected']}/{stats['total_ground_truth_bugs']}")
print(f"TPR: {stats['true_positive_rate']:.2f}%")
print(f"FPR: {stats['false_positive_rate']:.2f}%")

# Get persona coverage matrix
coverage = injector.get_persona_coverage_matrix(experiment_id=2)
for row in coverage:
    print(f"{row['persona']} found {row['bugs_detected']} {row['bug_type']} bugs")
```

## 🔄 Regression Detection Analysis

```python
from experiments.regressions import RegressionManager

manager = RegressionManager("experiments/results/experiments.db")

# Get regression detection stats
stats = manager.get_detection_stats()
print(f"Regressions detected: {stats['regressions_detected']}/{stats['total_regressions']}")
print(f"Detection rate: {stats['detection_rate']:.2f}%")

# Breakdown by type
by_type = manager.get_detection_by_type()
for row in by_type:
    print(f"{row['regression_type']}: {row['detection_rate']:.2f}%")
```

## 📈 Expected Timeline

| Phase | Task | Duration |
|-------|------|----------|
| 1 | Run Experiment 1A (Multi-Agent) | 2-4 hours |
| 2 | Run Experiment 1B (Personas) | 1-2 hours |
| 3 | Run Experiment 1C (Vision) | 3-5 hours |
| 4 | Run Experiment 1D (Regressions) | 3-4 hours |
| 5 | Statistical Analysis | 2-3 hours |
| 6 | Generate Visualizations | 2-3 hours |
| 7 | Write NeurIPS Paper | 8-12 hours |
| **Total** | | **21-33 hours** |

## 📝 Next Steps

### Immediate (Required for Core Experiments)
1. ✅ Database schema
2. ✅ Bug injection module
3. ✅ Regression definitions
4. ✅ Metrics collector
5. ✅ Experiment configs (1A-1D)
6. ✅ Experiment runner
7. ⏳ **Statistical analysis module** (t-tests, ANOVA, effect sizes)
8. ⏳ **Visualization suite** (matplotlib/seaborn plots)

### Extended (For Benchmark Validation)
9. ⏳ OWASP Juice Shop integration
10. ⏳ WebShop integration
11. ⏳ Run Experiment 2 (OWASP)
12. ⏳ Run Experiment 3 (WebShop)

### Final (For Paper)
13. ⏳ NeurIPS LaTeX setup
14. ⏳ Generate all figures/tables
15. ⏳ Write paper sections
16. ⏳ Create supplementary material

## 🎯 Key Claims for Paper

Based on your experiments, you'll be able to claim:

### Novel Contributions
1. **"Multi-agent committee improves task success by X% over single agent"** (Exp 1A vs Self-Collaboration baseline)
2. **"Persona-based testing achieves Y% higher coverage than single persona"** (Exp 1B)
3. **"Vision-enabled agents achieve Z% better element localization"** (Exp 1C vs VisualWebArena)
4. **"First demonstration of automated regression detection: W% detection rate"** (Exp 1D - novel)

### Validated Against Benchmarks
5. **"Achieves A% TPR on OWASP Juice Shop (baseline: 40-60%)"** (Exp 2)
6. **"Achieves B% task success on WebShop (baseline: 50.1%)"** (Exp 3)

## 💡 Tips for Running Experiments

1. **Start Small**: Run with `--dry-run` first to validate configs
2. **Use Seeds**: Ensure reproducibility with fixed seeds
3. **Monitor Resources**: Watch API costs and rate limits
4. **Checkpoint Progress**: Database auto-saves, safe to interrupt
5. **Analyze Incrementally**: Check metrics after each experiment
6. **Document Anomalies**: Note any unexpected results

## 🆘 Troubleshooting

### Database Issues
```bash
# Check if database exists
ls -lh experiments/results/experiments.db

# Verify schema
sqlite3 experiments/results/experiments.db ".schema"

# Reset database (WARNING: deletes all data)
rm experiments/results/experiments.db
```

### Run Failures
- Check API keys in `config/.env`
- Verify persona/scenario files exist
- Check browser adapter (Playwright) installation
- Review error messages in database: `SELECT * FROM runs WHERE success = 0`

### Metrics Issues
- Ensure runs completed successfully
- Check that turns were logged
- Verify ground truth was loaded for bug/regression experiments

## 📚 References

All baseline papers and metrics are documented in experiment configs:
- Self-Collaboration (2023): Multi-agent improvement
- VisualWebArena (2024): Vision-based web agents
- Wang et al. (2024): LLM testing survey
- OWASP Benchmark: Security tool evaluation
- WebShop (2022): E-commerce agent tasks

---

**Ready to run experiments and generate results for your NeurIPS paper!** 🚀
