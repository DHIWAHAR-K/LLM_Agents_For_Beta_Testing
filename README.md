# LLM Agents as Beta Testers

Automated beta testing framework using LLM agents as synthetic users. Supports multi-agent committees, comprehensive metrics, regression testing, and safety validation.

## Features

- **Persona-Driven Testing**: Define test users via YAML with goals, tone, and traits
- **Multi-Agent Support**: Committee-based decision making with multiple LLM backends
- **Comprehensive Metrics**: TSR, robustness, safety, regression delta, latency analysis
- **Oracle Validation**: Schema, goal alignment, safety, event sequence, and latency checks
- **Automated Reporting**: JSON artifacts + Markdown summaries + HTML dashboards
- **Regression Testing**: Version comparison with Pass→Fail tracking
- **Session Tracking**: Full reproducibility with seeds, metadata, and event logging

## Project Structure

**Unified Pipeline (17→14 files)**

```
├── main.py               # CLI entry point (formerly run_demo.py)
├── config.py             # Runtime settings with thresholds
├── config/               # Configuration files
│   ├── .env              # Environment variables
│   ├── default.yaml      # Default persona
│   └── scenario_demo.yaml# Demo scenario
│
├── Core Components:
│   ├── agent.py          # Single LLM agent with persona awareness
│   ├── multi_agent_router.py # Multi-agent committee routing (formerly agent_pool.py)
│   ├── orchestrator.py   # Session coordinator
│   ├── aut_adapter.py    # Application Under Test adapter (formerly api_adapter.py)
│
├── Model & Data:
│   ├── llm.py            # Ollama wrapper for local 3B models
│   ├── model_registry.py # Multi-model management (5 local 3B models)
│   ├── schemas.py        # Data models (Persona, Action)
│   ├── persona_loader.py # YAML persona loader (formerly persona_composer.py)
│
├── Validation & Analysis:
│   ├── validators.py     # All validation logic (consolidated from 3 oracle files)
│   ├── metrics.py        # Core metrics calculation (TSR, robustness, etc.)
│   ├── storage.py        # SQLite persistence with session tracking
│   ├── reporter.py       # Report generation (JSON + Markdown)
│
├── Dashboards:
│   └── dashboards/
│       └── build_dashboard.py # HTML visualization builder
│
└── Documentation:
    ├── description.txt   # Plain English guide to every file
    └── pyproject.toml    # Python project configuration
```

**Changes from Original:**
- ✅ Merged 3 oracle files → `validators.py`
- ✅ `run_demo.py` → `main.py`
- ✅ `persona_composer.py` → `persona_loader.py`
- ✅ `agent_pool.py` → `multi_agent_router.py`
- ✅ `api_adapter.py` → `aut_adapter.py`
- ✅ Removed `ui_adapter.py` stub
- ✅ Removed `workflow.md` (content moved to README)
- ✅ Switched from OpenAI API → 5 local Ollama 3B models

## How It Works

### System Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│  1. ENTRY POINT (main.py)                                       │
│  • Parse command line arguments                                 │
│  • Load persona from YAML (via persona_loader.py)              │
│  • Load scenario configuration                                  │
│  • Choose single-agent or multi-agent mode                     │
└────────────────────────┬────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. SESSION SETUP (orchestrator.py)                             │
│  • Initialize SQLite database (storage.py)                      │
│  • Start new testing session with metadata                      │
│  • Create agent(s) with persona and local models               │
│  • Create application adapter (aut_adapter.py)                 │
└────────────────────────┬────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. TESTING LOOP (for each turn)                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 3a. AGENT DECISION                                       │  │
│  │ • Single: agent.py generates action                      │  │
│  │ • Multi: multi_agent_router.py coordinates 5 models     │  │
│  │ • Models use llm.py to connect to Ollama                │  │
│  │ • Action includes type, target, and payload             │  │
│  └──────────────────────────────────────────────────────────┘  │
│                         ▼                                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 3b. VALIDATION (validators.py)                           │  │
│  │ • Schema check: valid action type and structure          │  │
│  │ • Goal alignment: matches persona's objectives           │  │
│  │ • Safety check: no SQL injection, XSS, etc.             │  │
│  │ • If validation fails: log failure and end session      │  │
│  └──────────────────────────────────────────────────────────┘  │
│                         ▼                                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 3c. EXECUTION (aut_adapter.py)                           │  │
│  │ • Execute action on application                          │  │
│  │ • Measure execution time (latency)                       │  │
│  │ • Capture new observation/state                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                         ▼                                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 3d. LOGGING (storage.py)                                 │  │
│  │ • Save turn data to SQLite                               │  │
│  │ • Record action, observation, latency                    │  │
│  │ • Log events and metadata                                │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  Repeat for max_turns (default: 3)                             │
└────────────────────────┬────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. SESSION COMPLETION (orchestrator.py)                        │
│  • Mark session as completed or failed                          │
│  • Close database connections                                   │
│  • Return session results                                       │
└────────────────────────┬────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  5. REPORTING (if --report flag used)                           │
│  • metrics.py: Calculate TSR, latency, safety rates            │
│  • reporter.py: Generate JSON and Markdown reports             │
│  • Save to reports/ directory                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow Example

**Single Turn Workflow:**

```
Persona: "First-time user wants to create account"
Observation: "Welcome screen with signup button"

    ↓ (agent.py uses llm.py to query local model)

Action: {type: "tap", target: "signup_button"}

    ↓ (validators.py checks)

✓ Schema valid (tap is allowed action type)
✓ Goal alignment (signup matches "create account" goal)
✓ Safety check (no malicious patterns)

    ↓ (aut_adapter.py executes)

New Observation: "Signup form with email and password fields"
Latency: 0.234 seconds

    ↓ (storage.py logs)

Database: Turn 1 saved with all metadata
```

### Multi-Agent Committee Example

When using `--multi-agent`, the system coordinates multiple models:

```
Observation → multi_agent_router.py
    ↓
    ├─> phi3-mini:        Action A (tap signup)
    ├─> llama3.2-3b:      Action A (tap signup)
    ├─> gemma2-2b:        Action B (tap login)
    ├─> qwen2.5-3b:       Action A (tap signup)
    └─> stablelm2-1.6b:   Action A (tap signup)

    ↓ (majority voting: 4 vs 1)

Final Verdict: Action A (tap signup)
Consensus: HIGH (4/5 agents agreed)
Logged: All 5 opinions + disagreements
```

### Component Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                    LAYERS & RESPONSIBILITIES                    │
└────────────────────────────────────────────────────────────────┘

Layer 1: ENTRY & CONFIGURATION
├─ main.py ..................... CLI interface and argument parsing
├─ config.py ................... Centralized settings management
└─ persona_loader.py ........... YAML to Python object conversion

Layer 2: ORCHESTRATION & CONTROL
└─ orchestrator.py ............. Master controller for testing sessions

Layer 3: AGENT INTELLIGENCE
├─ agent.py .................... Single agent with persona-driven decisions
├─ multi_agent_router.py ....... Committee coordination with voting
├─ llm.py ...................... Ollama API wrapper for local models
└─ model_registry.py ........... Model catalog and instance management

Layer 4: DATA & SCHEMAS
├─ schemas.py .................. Pydantic models for type safety
└─ storage.py .................. SQLite database operations

Layer 5: VALIDATION & SAFETY
└─ validators.py ............... All validation logic (schema, safety, events, latency)

Layer 6: EXECUTION
└─ aut_adapter.py .............. Application interaction and response capture

Layer 7: ANALYSIS & REPORTING
├─ metrics.py .................. Statistical calculations
└─ reporter.py ................. Report generation and formatting
```

### Key Design Principles

1. **Separation of Concerns**: Each file has one clear responsibility
2. **Local-First**: All models run locally via Ollama (no API costs)
3. **Validation-Driven**: Every action validated before execution
4. **Full Traceability**: Everything logged to SQLite with timestamps
5. **Committee Consensus**: Multiple models reduce individual model bias
6. **Type Safety**: Pydantic schemas enforce correctness
7. **Extensible**: Easy to add new models, validators, or adapters

## Quick Start

### 1. Installation

```bash
# Install dependencies
pip install -e .

# Install Ollama (for local models)
curl -fsSL https://ollama.com/install.sh | sh

# Pull the 5 local 3B models
ollama pull phi3
ollama pull llama3.2:3b
ollama pull gemma2:2b
ollama pull qwen2.5:3b
ollama pull stablelm2:1.6b
```

### 2. Run Single-Agent Test

```bash
python main.py --report
```

### 3. Run Multi-Agent Committee

```bash
python main.py --multi-agent --report
```

### 4. Compare Versions (Regression)

```bash
# Run baseline
python main.py --version v1.0 --report

# Run candidate
python main.py --version v2.0 --report

# Compare
python main.py --baseline <session_id_1> --candidate <session_id_2>
```

### 5. Generate Dashboard

```bash
python dashboards/build_dashboard.py reports
# Open dashboards/out/index.html in browser
```

## Usage Examples

### Custom Persona

Create `config/my_persona.yaml`:

```yaml
name: Impatient Power User
goals:
  - Complete task quickly
  - Skip unnecessary steps
  - Report any friction
tone: impatient
noise_level: 0.2
traits:
  expertise: advanced
  patience: low
```

Run with:
```bash
python main.py --persona config/my_persona.yaml --report
```

### Multi-Agent Configuration

Edit `config/.env` or environment variables:

```bash
ROUTING_POLICY=committee
ROUTING_MODELS=["phi3-mini", "llama3.2-3b", "gemma2-2b"]
COMMITTEE_SIZE=3
COMMITTEE_THRESHOLD=2
```

### Safety Testing

Create adversarial persona:

```yaml
name: Adversarial Tester
goals:
  - Test security boundaries
  - Attempt SQL injection
  - Upload malicious files
tone: neutral
noise_level: 0.0
traits:
  adversarial: true
  safety_test: true
```

The safety validators will validate proper refusal behavior.

## Metrics

### Core Metrics (Automatically Calculated)

1. **Task Success Rate (TSR)**: % of sessions completing successfully
2. **Robustness Delta**: TSR degradation with noisy personas
3. **Safety Pass Rate**: % of adversarial inputs properly blocked
4. **Regression Delta**: Pass→Fail changes across versions
5. **Latency Stats**: p50, p95, mean, max response times
6. **Human-Agent Agreement**: Correlation with human evaluations

### Viewing Metrics

```bash
# Generate report for session
python main.py --report

# View JSON
cat reports/<session_id>.json

# View Markdown
cat reports/<session_id>.md

# View dashboard
python dashboards/build_dashboard.py
open dashboards/out/index.html
```

## Configuration

### Key Settings (`config.py`)

```python
# Local model settings
ollama_base_url = "http://localhost:11434/v1"
default_model = "phi3"
temperature = 0.2

# Session settings
max_turns = 3              # Turns per session
seed = 42                  # Random seed for reproducibility
version = "v1.0"           # Version tag

# Latency thresholds (seconds)
latency_max = 5.0
latency_p50_max = 2.0
latency_p95_max = 4.0

# Safety profile
safety_profile = "balanced"  # strict|balanced|neutral

# Multi-agent routing
routing_policy = "round_robin"  # round_robin|weighted|failover|committee
routing_models = ["phi3-mini", "llama3.2-3b", "gemma2-2b", "qwen2.5-3b", "stablelm2-1.6b"]
committee_size = 3
committee_threshold = 2
```

## Validation Checks

### Available Validators (in `validators.py`)

**Section 1: Action Validators**
- **schema_check()**: Validates action type and structure
- **goal_bias_check()**: Ensures actions align with persona goals
- **regex_check()**: Pattern matching utility

**Section 2: Safety Validators**
- **check_safety()**: Comprehensive safety validation
  - SQL injection detection
  - XSS prevention
  - Path traversal blocking
  - Unsafe file upload filtering
  - Refusal pattern matching (for adversarial testing)
- **get_safety_profile_for_persona()**: Determines safety strictness level

**Section 3: Event & Latency Validators**
- **check_event_sequence()**: Verifies required events occur in order
- **check_latency()**: Validates response times within thresholds
- **check_latency_percentile()**: Specific percentile checks
- **check_event_timing()**: Time gap validation between events

### Adding Custom Validators

```python
# In validators.py
def my_custom_check(action: Action, persona: Persona) -> bool:
    # Your validation logic
    return True

# In orchestrator.py
from validators import my_custom_check
custom_valid = my_custom_check(action, persona)
oracle_pass = schema_valid and goal_valid and safety_valid and custom_valid
```

## Multi-Agent Routing Policies

### Round Robin
Cycles through agents in order.

### Weighted
Samples agents based on weights.

### Failover
Tries agents in order until one passes validators.

### Committee
Gets votes from N agents and uses majority consensus.

## Action Types

- `navigate`: Navigate to URL or endpoint
- `tap`: Click button or element
- `type`: Fill input field
- `scroll`: Scroll to element
- `upload`: Upload file
- `report`: Report issue or bug

## Key Components

1. **Persona Loader** (persona_loader.py): Loads YAML personas into structured objects
2. **Orchestrator** (orchestrator.py): Manages sessions and coordinates all components
3. **Agents** (agent.py, multi_agent_router.py): Generate actions (single or committee)
4. **Validators** (validators.py): Validate actions against schema, goals, and safety rules
5. **AUT Adapter** (aut_adapter.py): Executes actions on Application Under Test
6. **Storage** (storage.py): Logs all data to SQLite with full traceability
7. **Metrics & Reporter** (metrics.py, reporter.py): Calculate statistics and generate reports

## Extending the Framework

### Add New Local Model

```bash
# First, pull the model with Ollama
ollama pull mistral:7b

# Then add to model_registry.py
from model_registry import get_default_registry, ModelSpec

registry = get_default_registry()
registry.add_model(ModelSpec(
    name="mistral-7b",
    family="local",
    source="ollama",
    checkpoint="mistral:7b",
    temperature=0.2,
    safety_profile="balanced",
    extra_params={"size": "7B", "provider": "Mistral AI"},
))
```

### Add New Validator

```python
# In validators.py (add to Section 1 or create Section 4)
def custom_business_rule_check(action: Action, persona: Persona) -> bool:
    """Check custom business rules specific to your application."""
    # Example: Power users can access admin features
    if action.target.startswith("admin_") and not persona.traits.get("power_user"):
        return False
    return True

# Then use in orchestrator.py
from validators import custom_business_rule_check
business_valid = custom_business_rule_check(action, persona)
oracle_pass = schema_valid and goal_valid and safety_valid and business_valid
```

### Add New AUT Adapter (Real UI Testing)

```python
# In aut_adapter.py, add UIAdapter class
from playwright.sync_api import sync_playwright
from schemas import Action
import time

class UIAdapter:
    """Real browser automation adapter using Playwright."""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch()
        self.page = self.browser.new_page()

    def execute(self, action: Action) -> tuple[str, float]:
        start_time = time.time()

        if action.type == "navigate":
            self.page.goto(f"{self.base_url}/{action.target}")
            observation = self.page.title()

        elif action.type == "tap":
            self.page.click(f"[data-testid='{action.target}']")
            observation = self.page.content()

        elif action.type == "type":
            text = action.payload.get("text", "")
            self.page.fill(f"[data-testid='{action.target}']", text)
            observation = f"Typed into {action.target}"

        latency = time.time() - start_time
        return observation, latency
```

### Connect Multiple Models to Router

```python
# In config.py or .env, configure routing
ROUTING_POLICY=committee
ROUTING_MODELS=["phi3-mini", "llama3.2-3b", "qwen2.5-3b", "mistral-7b"]
COMMITTEE_SIZE=4
COMMITTEE_THRESHOLD=3  # 3 out of 4 must agree
```

## Troubleshooting

### No reports generated
Ensure you run with `--report` flag:
```bash
python run_demo.py --report
```

### Validation failures
Check logs in SQLite:
```sql
sqlite3 agent_runs.sqlite
SELECT * FROM events WHERE event_type = 'oracle_failure';
```

### Multi-agent not working
Ensure all 5 models are pulled in Ollama:
```bash
ollama list  # Check installed models
```
Verify `config.py` has all models in `routing_models` list.

### Ollama connection errors
```bash
# Check if Ollama is running
curl http://localhost:11434/v1/models

# Start Ollama if not running
ollama serve
```

## Production Deployment Checklist

This is a research framework. For production use:

**Required Changes:**
1. ✅ Already using local models (no API costs)
2. 🔧 Replace APIAdapter mock with real HTTP client in `aut_adapter.py`
3. 🔧 Implement UIAdapter with Playwright/Selenium for browser testing
4. 🔧 Add authentication/authorization to AUT adapter
5. 🔧 Implement retry logic with exponential backoff in `llm.py`
6. 🔧 Add monitoring and alerting for session failures
7. 🔧 Set up CI/CD pipeline for automated testing
8. 🔧 Configure database backups for `agent_runs.sqlite`

**Scalability:**
- Run multiple sessions in parallel with process pools
- Use faster GPU models if available via Ollama
- Increase `max_turns` for complex workflows
- Implement session caching for repeated scenarios

## Citation

If you use this framework in your research, please cite:

```
@misc{llm_beta_testers_2025,
  title={LLM Agents as Beta Testers for Applications},
  author={Your Name},
  year={2025},
  institution={NYU}
}
```

## License

MIT License - See LICENSE file for details.
