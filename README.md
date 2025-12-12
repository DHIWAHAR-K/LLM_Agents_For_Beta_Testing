# Multi-Agent Vision Beta Testing Framework

> **NYU IDLS Course Project** - Automated beta testing using multiple LLaVA vision agents with committee-based decision making.

## Overview

This framework uses **multi-agent LLM committees** with **vision capabilities** (LLaVA) to test web applications through visible browser automation. Multiple agents analyze screenshots, discuss, and reach consensus on actions to take, simulating realistic user behavior while catching bugs and security vulnerabilities.

## Key Features

- **Multi-Agent Committee**: 3+ LLaVA agents discuss and vote on actions
- **Vision-Based Testing**: Agents analyze screenshots to understand UI
- **Visible Browser**: Watch the testing happen in real-time
- **Committee Discussion**: Agents see each other's proposals before voting
- **Simplified Storage**: Single CSV file per session with all data
- **Interactive Dashboard**: Streamlit UI to visualize results and agent proposals
- **Security Testing**: Validates actions against SQL injection, XSS, etc.

## Architecture

```
┌─────────────────────────────────────────────┐
│           Multi-Agent Committee             │
│  ┌──────┐  ┌──────┐  ┌──────┐               │
│  │Agent1│  │Agent2│  │Agent3│               │
│  └───┬──┘  └───┬──┘  └───┬──┘               │
│      │         │         │                  │
│      └─────────┼─────────┘                  │
│                ▼                            │
│         Consensus Vote                      │
└─────────────────┬───────────────────────────┘
                  │
         ┌────────▼────────┐
         │ Browser Adapter │  (Playwright - Visible)
         │  + Screenshots  │
         └────────┬────────┘
                  │
         ┌────────▼────────┐
         │   Validators    │  (Security checks)
         └────────┬────────┘
                  │
         ┌────────▼────────┐
         │  CSV Storage    │
         └────────┬────────┘
                  │
         ┌────────▼────────┐
         │Streamlit Dashboard│
         └─────────────────┘
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### 2. Install and Start Ollama with LLaVA

```bash
# Install Ollama (macOS)
brew install ollama

# Start Ollama service
ollama serve

# Pull LLaVA model (in another terminal)
ollama pull llava
```

### 3. Start the Application Under Test

```bash
# Start the demo e-commerce app
uvicorn aut_service:app --port 8000

# Verify it's running
curl http://localhost:8000/health
```

### 4. Run a Test Session

```bash
# Run with default settings (3 agents, online_shopper persona)
python main.py

# Customize the test
python main.py --persona personas/adversarial_attacker.yaml --agents 5
```

**What you'll see:**
- Browser window opens (visible mode)
- Agents discuss in console: "Agent 1 proposes...", "Agent 2 proposes..."
- Consensus vote displayed
- Actions executed in browser
- CSV saved to `results/` folder

### 5. View Results in Dashboard

```bash
# Launch Streamlit dashboard
streamlit run dashboard_app.py

# In browser: Upload the CSV from results/ folder
```

## Project Structure

```
LLM_Agents_For_Beta_Testing/
├── app/
│   ├── agent.py                    # LLM agent with vision support
│   ├── browser_adapter.py          # Playwright automation + screenshots
│   ├── html_parser.py              # Parse page elements
│   ├── llm_client.py               # Ollama LLaVA client
│   ├── multi_agent_committee.py    # Committee discussion protocol
│   ├── multi_agent_runner.py       # Session orchestration
│   ├── persona.py                  # YAML loaders
│   ├── schemas.py                  # Pydantic models
│   ├── storage.py                  # CSV storage
│   └── validators.py               # Security checks
├── config/
│   └── model_config.yaml           # LLaVA configuration
├── personas/
│   ├── online_shopper.yaml         # Normal user
│   ├── adversarial_attacker.yaml   # Security tester
│   ├── price_manipulator.yaml      # Business logic tester
│   └── ...
├── scenarios/
│   ├── ui_shopping_flow.yaml       # E-commerce test
│   ├── security_commerce_test.yaml # Security test
│   └── ...
├── results/                        # Test results
│   ├── {session_id}.csv           # Session data
│   └── screenshots/               # Turn-by-turn screenshots
│       └── {session_id}/
│           ├── turn_1.png
│           ├── turn_2.png
│           └── ...
├── aut_service.py                  # Demo e-commerce API
├── config.py                       # Settings
├── dashboard_app.py                # Streamlit dashboard
├── main.py                         # CLI entry point
└── requirements.txt

```

## Usage Examples

### Basic Test
```bash
python main.py
```

### Custom Number of Agents
```bash
python main.py --agents 5
```

### Security Testing
```bash
python main.py \
  --persona personas/adversarial_attacker.yaml \
  --scenario scenarios/security_commerce_test.yaml
```

### View Results
```bash
streamlit run dashboard_app.py
```

## How It Works

### Multi-Agent Decision Process

Each turn follows this protocol:

1. **Round 1: Independent Proposals**
   - Each agent analyzes screenshot independently
   - Proposes an action (navigate, click, fill, report)
   - Assigns confidence score

2. **Round 2: Discussion & Refinement**
   - Agents see others' proposals
   - Refine their decisions
   - May change mind or confirm original

3. **Round 3: Consensus Vote**
   - Actions grouped by type + target
   - Weighted vote by confidence scores
   - Highest score wins

4. **Validation**
   - Schema validation
   - Security checks (SQL injection, XSS, etc.)
   - Goal alignment

5. **Execution**
   - Action executed in browser
   - Screenshot captured
   - Results logged to CSV

## Dashboard Features

The Streamlit dashboard provides:

- **Metrics Cards**: Success rate, safety pass rate, latency
- **Agent Agreement Chart**: How often agents agree over time
- **Action Distribution**: Pie chart of action types
- **Latency Analysis**: Bar chart per turn
- **Turn-by-Turn Viewer**: Expandable sections showing:
  - Screenshot
  - Each agent's proposal
  - Confidence scores
  - Final consensus
  - Validation results

## CSV Output Format

Each session generates a CSV with these columns:

| Column | Description |
|--------|-------------|
| `session_id` | Unique session identifier |
| `turn` | Turn number (1, 2, 3...) |
| `timestamp` | ISO timestamp |
| `action_type` | navigate, click, fill, report |
| `action_target` | Target element/URL |
| `screenshot_path` | Path to screenshot |
| `agent_proposals` | JSON array of all agent proposals |
| `consensus_action` | JSON of winning action |
| `confidence_scores` | JSON of agent confidence scores |
| `success` | Boolean - action succeeded |
| `latency` | Response time in seconds |
| `safety_pass` | Boolean - passed security checks |
| `validators` | Semicolon-separated validation results |

## Personas

### Online Shopper (Default)
- Browse products
- Add to cart
- Complete checkout
- Normal user behavior

### Adversarial Attacker
- SQL injection attempts
- XSS attacks
- Command injection
- Path traversal
- Tests security boundaries

### Price Manipulator
- Negative prices
- Zero prices
- Excessive quantities
- Business logic attacks

## Configuration

Edit `config/model_config.yaml`:

```yaml
model:
  provider: ollama
  base_url: http://localhost:11434/v1
  name: llava
  temperature: 0.2
  max_retries: 2
```

Edit `config.py` for runtime settings:
- `max_turns`: Maximum turns per session (default: 3)
- `api_base_url`: AUT base URL (default: http://localhost:8000)

## Troubleshooting

### Ollama Connection Error
```bash
# Check if Ollama is running
ps aux | grep ollama

# Start Ollama
ollama serve
```

### LLaVA Model Not Found
```bash
# Pull the model
ollama pull llava

# List available models
ollama list
```

### Browser Not Opening
- Check that `headless=False` in `browser_adapter.py`
- Ensure Playwright is installed: `playwright install chromium`

### Dashboard Not Showing Screenshots
- Ensure screenshot paths in CSV are absolute or relative to dashboard location
- Check that `results/screenshots/{session_id}/` directory exists

## Research Context

**Course**: Introduction to Deep Learning Systems (IDLS)  
**Institution**: New York University  
**Research Question**: Can multi-agent LLM committees with vision effectively replace human beta testers?

## Key Insights

- **Multi-agent improves reliability**: Committee voting reduces hallucinations
- **Vision enables UI testing**: LLaVA can understand visual interfaces
- **Discussion refines decisions**: Agents change mind ~20% after seeing others' proposals
- **Security testing works**: Successfully detects SQL injection, XSS attempts
- **Visible browser aids debugging**: Watching tests helps understand agent behavior

## License

MIT License

## Authors

- Dhiwahar Adhithya Kennady (dk5025)
- Sumanth Bharadwaj Hachalli Karanam (sh8111)
