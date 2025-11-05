# Project Workflow Documentation

## Overview

This document describes the complete workflow of the Multi-Agent LLM Beta Testing Framework, from experiment execution to paper generation.

## System Architecture Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    Experiment Configuration                 │
│              (YAML files in experiments/configs/)           │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              Experiment Runner (experiments/runner.py)      │
│  - Loads YAML configuration                                 │
│  - Registers experiment in database                         │
│  - Loads ground truth bugs/regressions                      │
│  - Orchestrates multiple runs with different seeds          │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│         Multi-Agent Session Runner (multi_agent_runner.py)  │
│  - Initializes browser (Playwright)                         │
│  - Creates multi-agent committee                            │
│  - Manages testing loop (turns)                             │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   Browser    │ │   Committee  │ │   Storage    │
│   Adapter    │ │   (Voting)   │ │   (Session)  │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                │
       │                │                │
       └────────────────┼────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                    Turn Execution Loop                      │
│  1. Capture screenshot                                      │
│  2. Get browser state                                       │
│  3. Committee decides (3-round voting)                      │
│  4. Execute consensus action                                │
│  5. Validate action (safety checks)                         │
│  6. Log turn to storage                                     │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              Metrics Collection (metrics_collector.py)      │
│  - Calculates task success rate                             │
│  - Computes latency statistics                              │
│  - Tracks committee agreement                               │
│  - Records security detections                              │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              Database Storage (experiments.db)              │
│  - experiments table: Experiment metadata                   │
│  - runs table: Individual run records                       │
│  - metrics table: Quantitative measurements                 │
│  - turns table: Turn-by-turn execution details              │
│  - proposals table: Agent proposals and voting              │
│  - bugs table: Ground truth and detected bugs               │
│  - regressions table: Version comparison data               │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│         Statistical Analysis (experiments/analysis.py)      │
│  - ANOVA tests for multi-agent scaling                      │
│  - T-tests for baseline comparisons                         │
│  - Confidence intervals                                     │
│  - Effect sizes (Cohen's d)                                 │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│         Figure Generation (experiments/generate_figures.py) │
│  - Extracts data from database                              │
│  - Generates publication-quality figures                    │
│  - Saves PDF and PNG versions                               │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              Paper Writing (paper/main.tex)                 │
│  - Results section with actual data                         │
│  - Statistical analysis integration                         │
│  - Figure references                                        │
│  - Tables with real statistics                              │
└─────────────────────────────────────────────────────────────┘
```

## Detailed Workflow Steps

### Phase 1: Experiment Configuration

1. **Define Experiment** (`experiments/configs/*.yaml`)
   - Specify experiment name, tier, research question
   - Define configurations (personas, committee sizes, models)
   - List test scenarios
   - Set execution parameters (seeds, runs per config)

2. **Load Ground Truth** (if applicable)
   - Bug injection: `experiments/bug_injector.py` loads 20 ground truth bugs
   - Regression definitions: `experiments/regressions.py` loads 15 regressions

### Phase 2: Experiment Execution

1. **Run Experiment** (`experiments/runner.py`)
   ```bash
   python experiments/runner.py --config experiments/configs/experiment_1a_multi_agent_scaling.yaml
   ```

2. **For Each Run:**
   - Load persona and scenario
   - Initialize browser (Playwright)
   - Create multi-agent committee
   - Execute testing loop:
     - **Turn 1-N:**
       - Capture screenshot
       - Get browser state (HTML, URL)
       - Committee decides via 3-round voting:
         - Round 1: Independent proposals
         - Round 2: Discussion and refinement
         - Round 3: Consensus vote
       - Execute consensus action
       - Validate action (safety checks)
       - Log turn to database
   - Calculate metrics
   - Store results in database

### Phase 3: Multi-Agent Committee Decision Process

**3-Round Voting Protocol:**

1. **Round 1: Independent Proposals**
   - Each agent analyzes screenshot and browser state independently
   - Each proposes an action with confidence score
   - No agent sees others' proposals yet

2. **Round 2: Discussion & Refinement**
   - All agents see Round 1 proposals
   - Each agent can:
     - Strengthen confidence if others agree
     - Change proposal if convinced by better reasoning
     - Maintain position if confident
   - Agents refine their proposals

3. **Round 3: Consensus Vote**
   - Aggregate confidence-weighted votes
   - Select action with highest score
   - Execute consensus action

### Phase 4: Data Collection

**Metrics Collected Per Run:**
- Task success rate (% successful turns)
- Total turns executed
- Latency statistics (mean, P50, P95, P99)
- Committee agreement (%)
- Consensus strength
- Security detections (vulnerabilities, false positives)
- Vision metrics (element localization accuracy)
- Cost metrics (API calls, USD cost)
- Behavioral diversity scores

**Turn-Level Data:**
- Action type, target, success/failure
- Agent proposals (all rounds)
- Confidence scores
- Safety validation results
- Screenshot paths

### Phase 5: Statistical Analysis

**Analysis Tools** (`experiments/analysis.py`):
- Two-group comparison (t-tests)
- Multi-group comparison (ANOVA)
- Baseline comparison (one-sample t-test)
- Correlation analysis
- Bootstrap confidence intervals
- Effect size calculations (Cohen's d)

**Usage:**
```python
from experiments.analysis import StatisticalAnalyzer

analyzer = StatisticalAnalyzer('experiments/results/experiments.db')
result = analyzer.compare_two_groups(
    experiment_id=1,
    metric_name='task_success_rate',
    group_by='num_agents',
    group1_value='1',
    group2_value='4'
)
analyzer.print_comparison_report(result)
```

### Phase 6: Figure Generation

**Figure Generation Script** (`experiments/generate_figures.py`):
- Connects to database
- Extracts data via SQL queries
- Generates publication-quality figures:
  - `architecture.pdf` - System architecture diagram
  - `voting_protocol.pdf` - 3-round voting flowchart
  - `action_distribution.pdf` - Action types vs success rates
  - `baseline_comparison.pdf` - Our results vs published baselines
  - `persona_results.pdf` - Persona performance heatmap
  - `multi_agent_scaling.pdf` - Committee size vs performance

**Usage:**
```bash
python experiments/generate_figures.py
```

### Phase 7: Paper Writing

**Paper Structure** (`paper/main.tex`):
1. Abstract - Summary of contributions and results
2. Introduction - Motivation and research questions
3. Related Work - Positioning against prior work
4. Methodology - System architecture and voting protocol
5. Experimental Setup - Models, scenarios, metrics
6. Results - Actual data from database with statistical tests
7. Discussion - Interpretation of results
8. Conclusion - Summary and future work

**Data Integration:**
- Extract statistics from `results.md`
- Reference generated figures
- Include statistical test results
- Update tables with real data

## Key Components

### Core Framework (`app/`)
- `multi_agent_runner.py` - Main session orchestrator
- `multi_agent_committee.py` - Voting protocol implementation
- `browser_adapter.py` - Playwright browser automation
- `agent.py` - Individual LLM agent wrapper
- `llm_client.py` - Multi-provider LLM interface
- `schemas.py` - Data models (Persona, Action)
- `validators.py` - Safety and action validation
- `storage.py` - Session storage (CSV)
- `metrics.py` - Metrics calculation utilities

### Experimental Infrastructure (`experiments/`)
- `runner.py` - Experiment orchestrator
- `metrics_collector.py` - Comprehensive metrics calculation
- `bug_injector.py` - Ground truth bug management
- `regressions.py` - Regression detection framework
- `analysis.py` - Statistical analysis tools
- `generate_figures.py` - Figure generation script
- `schema.sql` - Database schema definition

### Application Under Test (`aut_service.py`)
- FastAPI e-commerce application
- Intentional bugs for testing
- Security vulnerabilities for OWASP testing

## Data Flow

1. **Configuration → Execution**
   - YAML config → Experiment Runner → Multi-Agent Runner

2. **Execution → Storage**
   - Turn data → Session Storage → Database

3. **Storage → Analysis**
   - Database queries → Statistical Analyzer → Results

4. **Analysis → Visualization**
   - Results → Figure Generator → PDF/PNG files

5. **Visualization → Paper**
   - Figures + Results → LaTeX Paper → PDF

## Reproducibility

- **Seeding**: All runs use fixed random seeds (42, 123, 456, 789, 1024)
- **Configuration**: All experiment configs stored in YAML
- **Database**: Complete execution history in SQLite
- **Code**: Version-controlled with git
- **Environment**: Requirements documented in `requirements.txt`

## Execution Commands

```bash
# Run single experiment
python experiments/runner.py --config experiments/configs/experiment_1a_multi_agent_scaling.yaml

# Generate all figures
python experiments/generate_figures.py

# Run statistical analysis
python -c "from experiments.analysis import StatisticalAnalyzer; analyzer = StatisticalAnalyzer('experiments/results/experiments.db'); ..."

# Compile paper
cd paper && pdflatex main.tex && bibtex main && pdflatex main.tex && pdflatex main.tex
```

## Output Artifacts

1. **Database**: `experiments/results/experiments.db`
   - All experimental data
   - Turn-by-turn execution logs
   - Metrics and statistics

2. **Figures**: `paper/figures/*.pdf` and `*.png`
   - Publication-ready visualizations

3. **Paper**: `paper/main.pdf`
   - Compiled NeurIPS paper

4. **Documentation**:
   - `workflow.md` (this file)
   - `code_structure.md` (code documentation)
   - `results.md` (experimental results summary)

