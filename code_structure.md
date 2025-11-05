# Code Structure Documentation

This document provides a comprehensive overview of all files in the Multi-Agent LLM Beta Testing Framework codebase, explaining their purpose, key functions, and relationships.

## Directory Structure

```
.
├── app/                    # Core framework modules
├── experiments/            # Experimental infrastructure
├── paper/                  # NeurIPS paper LaTeX files
├── personas/               # Persona YAML definitions
├── scenarios/              # Test scenario YAML definitions
├── config/                 # Configuration files
├── templates/              # HTML templates for AUT
├── static/                 # Static assets
├── results/                # Session results (CSV files)
├── main.py                 # Entry point for single sessions
├── app.py                  # FastAPI application (AUT)
├── aut_service.py          # Application Under Test service
├── dashboard_app.py        # Streamlit dashboard
└── config.py               # Configuration management
```

## Core Framework (`app/`)

### `app/__init__.py`
- Package initialization file
- Exports main components

### `app/multi_agent_runner.py`
**Purpose**: Main orchestrator for multi-agent testing sessions

**Key Functions**:
- `run_multi_agent_session()`: Async function that orchestrates the complete testing session
  - Initializes browser, committee, and storage
  - Manages the turn-by-turn testing loop
  - Tracks success criteria completion
  - Handles security testing scenarios

**Dependencies**: `browser_adapter`, `multi_agent_committee`, `storage`, `validators`

### `app/multi_agent_committee.py`
**Purpose**: Implements the 3-round voting protocol for multi-agent consensus

**Key Classes**:
- `AgentProposal`: Represents an agent's action proposal with confidence and reasoning
- `MultiAgentCommittee`: Manages committee of agents and voting process

**Key Methods**:
- `decide()`: Main entry point for committee decision-making
- `_round1_independent()`: Round 1 - independent proposals
- `_round2_discussion()`: Round 2 - discussion and refinement
- `_round3_consensus()`: Round 3 - consensus vote with confidence weighting

**Dependencies**: `agent`, `llm_client`, `schemas`

### `app/agent.py`
**Purpose**: Individual LLM agent wrapper that converts observations to actions

**Key Classes**:
- `LLMUserAgent`: Single agent that uses LLM to propose actions

**Key Methods**:
- `step()`: Takes observation and screenshot, returns Action
  - Constructs system and user prompts
  - Calls LLM client with vision support
  - Parses JSON response into Action schema

**Dependencies**: `llm_client`, `schemas`

### `app/llm_client.py`
**Purpose**: Multi-provider LLM interface supporting OpenAI, Google, Anthropic, xAI, and Ollama

**Key Classes**:
- `LLMClient`: Unified interface for multiple LLM providers

**Key Methods**:
- `emit_json()`: Main method to get JSON-structured responses from LLM
- `_call_openai()`, `_call_google()`, `_call_anthropic()`, `_call_xai()`, `_call_ollama()`: Provider-specific implementations
- `_encode_image()`: Base64 encodes images for vision models

**Features**:
- Vision support (screenshot analysis)
- JSON mode enforcement
- Retry logic with exponential backoff
- Multi-provider abstraction

**Dependencies**: `config` (for model configuration)

### `app/browser_adapter.py`
**Purpose**: Browser automation using Playwright for UI-based testing

**Key Classes**:
- `BrowserAdapter`: Executes actions against web UI

**Key Methods**:
- `start()`: Launches Playwright browser
- `stop()`: Closes browser
- `execute()`: Executes an Action and returns observation + latency
- `capture_screenshot()`: Captures full-page screenshot
- `get_current_state()`: Returns formatted page state for agents
- `_handle_navigate()`, `_handle_click()`, `_handle_fill()`, `_handle_scroll()`: Action-specific handlers

**Dependencies**: `playwright`, `html_parser`, `schemas`

### `app/html_parser.py`
**Purpose**: Parses HTML pages to extract UI structure and elements

**Key Classes**:
- `HTMLParser`: Extracts actionable UI elements from HTML

**Key Methods**:
- `fetch_and_parse()`: Fetches HTML and extracts structure
- `format_for_agent()`: Formats parsed data for LLM consumption
- `_extract_links()`, `_extract_buttons()`, `_extract_forms()`, `_extract_inputs()`, `_extract_products()`, `_extract_cart_info()`: Element extraction methods

**Dependencies**: `requests`, `beautifulsoup4`

### `app/schemas.py`
**Purpose**: Pydantic data models for type safety

**Key Classes**:
- `Persona`: Persona definition with name, goals, tone, noise_level, traits
- `Action`: Action schema with type, target, and optional payload

**Action Types**: `tap`, `type`, `scroll`, `navigate`, `upload`, `report`, `click`, `fill`

### `app/validators.py`
**Purpose**: Validates actions for schema compliance, goal alignment, and security

**Key Functions**:
- `validate_action()`: Main validation function
  - Schema validation (valid action type, required fields)
  - Goal alignment checks
  - Safety validation (SQL injection, XSS, command injection, path traversal, price/quantity/stock manipulation)

**Security Patterns**: Regex patterns for detecting various attack vectors

**Dependencies**: `schemas`

### `app/storage.py`
**Purpose**: Session storage using CSV files

**Key Classes**:
- `SessionStorage`: Manages CSV storage for test sessions

**Key Methods**:
- `start_session()`: Creates new session and returns session ID
- `log_turn()`: Logs a single turn with all metadata
- `end_session()`: Finalizes session and saves CSV file
- `get_screenshots_dir()`: Returns path to screenshots directory

**Storage Format**: CSV with columns for session metadata, turn data, agent proposals, consensus actions, confidence scores, success/failure, latency, safety validation

### `app/persona.py`
**Purpose**: YAML loading utilities for personas and scenarios

**Key Functions**:
- `load_persona()`: Loads persona from YAML and converts to Persona model
- `load_scenario()`: Loads scenario metadata from YAML
- `load_yaml()`: Generic YAML loader

**Dependencies**: `yaml`, `schemas`

### `app/metrics.py`
**Purpose**: Simple metrics calculation utilities

**Key Functions**:
- `task_success_rate()`: Calculates percentage of successful turns
- `latency_summary()`: Computes mean and max latency

### `app/aut_adapter.py`
**Purpose**: REST API adapter for API-based testing (alternative to browser)

**Key Classes**:
- `RESTAdapter`: Executes actions against REST API

**Key Methods**:
- `execute()`: Executes Action via HTTP request
- `_build_url()`, `_prepare_request_kwargs()`, `_format_response()`: Helper methods

**Dependencies**: `requests`, `schemas`

### `app/runner.py`
**Purpose**: Single-agent session runner (legacy, replaced by multi_agent_runner)

**Key Functions**:
- `run_session()`: Runs single-agent testing session

## Experimental Infrastructure (`experiments/`)

### `experiments/runner.py`
**Purpose**: Experiment orchestrator that manages multiple runs with different configurations

**Key Classes**:
- `ExperimentRunner`: Manages experiment execution

**Key Methods**:
- `register_experiment()`: Registers experiment in database
- `load_ground_truth()`: Loads bugs/regressions for experiment
- `run_experiment()`: Executes all runs for experiment configuration
- `_run_single_run()`: Executes a single run with specific configuration

**Features**:
- Configuration-driven execution (YAML)
- Seeding for reproducibility
- Checkpointing (resume incomplete runs)
- Parallel/sequential execution modes

**Dependencies**: `multi_agent_runner`, `metrics_collector`, `bug_injector`, `regressions`

### `experiments/metrics_collector.py`
**Purpose**: Comprehensive metrics calculation for experimental runs

**Key Classes**:
- `RunMetrics`: Dataclass with all metric fields
- `MetricsCollector`: Calculates and saves metrics

**Key Methods**:
- `calculate_run_metrics()`: Computes all metrics for a run
  - Task success metrics
  - Safety/security metrics
  - Performance metrics (latency percentiles)
  - Multi-agent metrics (agreement, consensus)
  - Vision metrics
  - Cost metrics
  - Behavioral diversity metrics
- `save_metrics()`: Saves metrics to database

**Dependencies**: `sqlite3`, `numpy`

### `experiments/analysis.py`
**Purpose**: Statistical analysis tools for comparing experimental results

**Key Classes**:
- `ComparisonResult`: Results from statistical comparison
- `StatisticalAnalyzer`: Performs statistical tests

**Key Methods**:
- `compare_two_groups()`: T-test comparison between two groups
- `anova_analysis()`: One-way ANOVA for multiple groups
- `baseline_comparison()`: One-sample t-test against baseline
- `correlation_analysis()`: Pearson and Spearman correlation
- `bootstrap_confidence_interval()`: Bootstrap CI calculation
- `cohens_d()`: Effect size calculation

**Statistical Tests**: t-tests, ANOVA, correlation, confidence intervals, effect sizes

### `experiments/bug_injector.py`
**Purpose**: Manages ground truth bugs for testing

**Key Classes**:
- `BugInjector`: Manages bug definitions and detection tracking

**Key Methods**:
- `load_ground_truth()`: Loads 20 ground truth bugs into database
- `check_detection()`: Checks if bugs were detected in a run
- `get_persona_coverage_matrix()`: Gets bug detection by persona

**Bug Types**: functional, security, business_logic, accessibility, performance, ui_regression, api_regression

### `experiments/regressions.py`
**Purpose**: Manages regression definitions for version comparison testing

**Key Classes**:
- `RegressionManager`: Manages regression definitions and detection

**Key Methods**:
- `load_regressions()`: Loads 15 regression definitions
- `check_regression()`: Checks if regression detected in run
- `get_detection_stats()`: Gets regression detection statistics

**Regression Types**: breaking_change, behavioral_change, performance_degradation, ui_regression

### `experiments/schema.sql`
**Purpose**: SQLite database schema definition

**Key Tables**:
- `experiments`: Experiment metadata
- `runs`: Individual run records
- `metrics`: Quantitative measurements per run
- `turns`: Turn-by-turn execution details
- `proposals`: Agent proposals and voting data
- `bugs`: Ground truth and detected bugs
- `regressions`: Regression definitions and detections
- `owasp_challenges`, `owasp_detections`: OWASP-specific data
- `webshop_tasks`, `webshop_results`: WebShop-specific data

### `experiments/generate_figures.py`
**Purpose**: Generates publication-quality figures from database (to be created)

**Key Functions** (planned):
- `generate_action_distribution()`: Bar chart of action types vs success rates
- `generate_baseline_comparison()`: Comparison with published baselines
- `generate_persona_results()`: Persona performance visualization
- `generate_multi_agent_scaling()`: Committee size vs performance
- `generate_voting_protocol()`: Algorithm flowchart
- `generate_architecture()`: System architecture diagram

## Configuration Files

### `config.py`
**Purpose**: Configuration management and model loading

**Key Classes**:
- `Settings`: Runtime configuration (base URL, max turns, seed, version)

**Key Functions**:
- `load_settings()`: Loads settings from environment
- `load_model_config()`: Loads model configuration from YAML

**Dependencies**: `pydantic_settings`, `yaml`

### `config/model_config.yaml`
**Purpose**: Multi-provider LLM model configuration

**Structure**:
- `models`: List of model definitions
  - Each model has: `name`, `provider`, optional `base_url`
- `temperature`: Default temperature
- `max_retries`: Retry configuration

### `config/.env`
**Purpose**: Environment variables (API keys, settings)

**Variables**: `OPENAI_API_KEY`, `GOOGLE_API_KEY`, `ANTHROPIC_API_KEY`, `XAI_API_KEY`, etc.

## Application Under Test

### `aut_service.py`
**Purpose**: FastAPI e-commerce application for testing

**Features**:
- Product catalog
- Shopping cart
- Checkout flow
- User authentication
- Intentional bugs for testing
- Security vulnerabilities for OWASP testing

**Endpoints**: `/`, `/products`, `/product/{id}`, `/cart`, `/checkout`, `/api/*`

### `app.py`
**Purpose**: Alternative FastAPI application setup

### `templates/*.html`
**Purpose**: HTML templates for AUT frontend

**Files**: `index.html`, `products.html`, `product-detail.html`, `cart.html`, `checkout.html`, `search.html`, etc.

## Entry Points

### `main.py`
**Purpose**: Entry point for running single multi-agent sessions

**Usage**:
```bash
python main.py --persona personas/online_shopper.yaml --scenario scenarios/ui_shopping_flow.yaml --agents 4
```

**Dependencies**: `multi_agent_runner`, `persona`

### `dashboard_app.py`
**Purpose**: Streamlit dashboard for visualizing results

**Features**:
- Session overview
- Action distribution charts
- Latency analysis
- Agent proposal visualization
- Screenshot gallery

**Dependencies**: `streamlit`, `plotly`, `pandas`

## Personas (`personas/`)

YAML files defining different testing personas:
- `online_shopper.yaml`: Typical e-commerce user
- `adversarial_attacker.yaml`: Security-focused tester
- `accessibility_tester.yaml`: Accessibility-focused tester
- `malicious_user.yaml`: Malicious user persona
- `mobile_shopper.yaml`: Mobile user persona
- `price_manipulator.yaml`: Price manipulation tester
- `project_manager.yaml`: Efficiency-focused tester
- `ux_researcher.yaml`: UX-focused tester
- `curious_blogger.yaml`: Exploratory tester

## Scenarios (`scenarios/`)

YAML files defining test scenarios:
- `ui_shopping_flow.yaml`: UI-based shopping flow
- `security_commerce_test.yaml`: Security testing scenario
- `juice_shop_security_audit.yaml`: OWASP Juice Shop audit
- `webshop_easy_001.yaml`: WebShop benchmark task

## Paper (`paper/`)

### `paper/main.tex`
**Purpose**: Main LaTeX file for NeurIPS paper

**Sections**: Abstract, Introduction, Related Work, Methodology, Experimental Setup, Results, Discussion, Conclusion

### `paper/bibliography.bib`
**Purpose**: BibTeX bibliography file

**Citations**: WebShop, ReAct, OWASP, Constitutional AI, GPT-4V, Gemini, Playwright, etc.

### `paper/figures/`
**Purpose**: Directory for paper figures (PDF and PNG)

**Files**: `architecture.pdf`, `voting_protocol.pdf`, `action_distribution.pdf`, `baseline_comparison.pdf`, `persona_results.pdf`

## Data Flow

1. **Configuration** → `experiments/runner.py` loads YAML config
2. **Execution** → `app/multi_agent_runner.py` orchestrates session
3. **Decision** → `app/multi_agent_committee.py` manages voting
4. **Action** → `app/browser_adapter.py` executes actions
5. **Storage** → `app/storage.py` logs to CSV, `experiments/runner.py` logs to database
6. **Metrics** → `experiments/metrics_collector.py` calculates metrics
7. **Analysis** → `experiments/analysis.py` performs statistical tests
8. **Visualization** → `experiments/generate_figures.py` creates figures
9. **Paper** → `paper/main.tex` integrates results

## Key Design Patterns

- **Async/Await**: Browser operations and LLM calls are async
- **Multi-Provider Abstraction**: `LLMClient` abstracts provider differences
- **Schema Validation**: Pydantic models ensure type safety
- **Configuration-Driven**: Experiments defined in YAML
- **Modular Design**: Clear separation of concerns (browser, agents, storage, metrics)
- **Reproducibility**: Seeding and checkpointing for exact reproduction

## Dependencies

**Core**:
- `playwright`: Browser automation
- `pydantic`: Data validation
- `requests`: HTTP client
- `beautifulsoup4`: HTML parsing
- `yaml`: Configuration loading

**LLM Providers**:
- `openai`: OpenAI API
- `google-generativeai`: Google Gemini API
- `anthropic`: Anthropic Claude API
- `xai`: xAI Grok API

**Analysis**:
- `numpy`: Numerical operations
- `scipy`: Statistical tests
- `pandas`: Data manipulation
- `matplotlib`, `seaborn`: Visualization

**UI**:
- `streamlit`: Dashboard
- `plotly`: Interactive charts
- `rich`: Terminal formatting

