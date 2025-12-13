# Multi‑Agent Vision Beta Testing Framework – Detailed Run Guide

This guide walks you step‑by‑step through installing, configuring, and running the **LLM_Agents_For_Beta_Testing** project, from a single demo run to full experimental pipelines.

It assumes you just cloned the repo:

```bash
git clone https://github.com/DHIWAHAR-K/LLM_Agents_For_Beta_Testing.git
cd LLM_Agents_For_Beta_Testing
```

---

## 1. Prerequisites

- **OS:** macOS, Linux, or WSL2 on Windows
- **Python:** `3.10` or newer (see `pyproject.toml: requires-python >= 3.10`)
- **Package manager:** `pip` (or `uv`/`pipx` if you prefer)
- **Browser automation:** Playwright (installed below)
- **Optional:** API keys for one or more cloud LLM providers
  - OpenAI (`OPENAI_API_KEY`)
  - Google Gemini (`GOOGLE_API_KEY`)
  - Anthropic (`ANTHROPIC_API_KEY`)
  - xAI Grok (`XAI_API_KEY`)

You do **not** need keys for all providers to run the project; you can start with a single provider and update the config later.

---

## 2. Create and Activate a Virtual Environment

From the project root:

```bash
# Create a virtualenv (choose one of the following)
python3 -m venv .venv              # Standard venv
# or: python -m venv .venv

# Activate it
source .venv/bin/activate          # macOS / Linux / WSL
# On Windows (PowerShell):
# .venv\Scripts\Activate.ps1
```

You should see `(.venv)` at the start of your shell prompt after activation.

---

## 3. Install Dependencies

### 3.1 Python packages

Install the project’s Python dependencies:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3.2 Playwright browser

Playwright is used to drive a **real browser** for UI testing:

```bash
python -m playwright install chromium
```

This downloads the Chromium browser binary that Playwright will control.

---

## 4. Configure Models and API Keys

The project supports multiple providers and models, configured in `config/model_config.yaml`.

### 4.1 Set API keys via environment

Create a `.env` file in the `config/` directory (this is referenced by the config file comments):

```bash
cp config/.env.example config/.env   # if example exists
# otherwise create it:
touch config/.env
```

Edit `config/.env` and add any keys you have:

```env
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=AIza...
ANTHROPIC_API_KEY=sk-ant-...
XAI_API_KEY=xai-...
```

Alternatively, you can export them directly in your shell:

```bash
export OPENAI_API_KEY=sk-...
export GOOGLE_API_KEY=AIza...
export ANTHROPIC_API_KEY=sk-ant-...
export XAI_API_KEY=xai-...
```

> **Tip:** You can start with **only one** provider (e.g., OpenAI) and comment out the others in `config/model_config.yaml` if needed.

### 4.2 Adjusting model_config.yaml (optional)

Open `config/model_config.yaml`:

```yaml
models:
  - name: gpt-4o
    provider: openai
  - name: gemini-1.5-flash
    provider: google
  - name: gemini-2.5-flash
    provider: google
  - name: claude-opus-4-1
    provider: anthropic
  - name: grok-2-vision-1212
    provider: xai
```

If you only have, for example, OpenAI and Google keys, you can comment out the Anthropic/xAI blocks or reduce the list to just the models you want to use.

---

## 5. Start the Application Under Test (AUT)

The **AUT** is a FastAPI‑based e‑commerce app defined in `aut_service.py`. It must be running before you start a multi‑agent testing session.

From the project root (with your virtualenv active):

```bash
uvicorn aut_service:app --reload --port 8000
```

This should show a startup log similar to:

```text
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

You can visit `http://localhost:8000` in your browser to confirm the app is up.

Leave this server running in its own terminal window/tab while you run agents from another terminal.

---

## 6. Run a Single Multi‑Agent Test Session

The main entry point for a single test session is `main.py`, which orchestrates a committee of agents against one persona and one scenario.

### 6.1 Default run

Open a **new terminal**, activate your virtualenv again, `cd` into the project, and run:

```bash
python main.py
```

This uses:
- Persona: `personas/online_shopper.yaml`
- Scenario: `scenarios/ui_shopping_flow.yaml`
- Agents: `4` (one per configured provider by default)

You should see log output as the agents take turns, propose actions, and the browser opens/headless Chromium is driven by Playwright.

At the end you’ll see a summary like:

```text
🎉 Testing completed successfully!

📁 Results saved to: results/online_shopper_ui-based_shopping_flow/online_shopper_ui-based_shopping_flow.csv
🚀 To view results, run: streamlit run dashboard_app.py
```

### 6.2 Custom persona, scenario, and agent count

You can override the defaults using CLI flags:

```bash
# Adversarial attacker persona on e-commerce security scenario, 3 agents
python main.py \
  --persona personas/adversarial_attacker.yaml \
  --scenario scenarios/security_commerce_test.yaml \
  --agents 3
```

Other useful combinations:

```bash
# UX researcher on UI shopping flow
python main.py --persona personas/ux_researcher.yaml --scenario scenarios/ui_shopping_flow.yaml

# Price manipulator persona (business logic / security focus)
python main.py --persona personas/price_manipulator.yaml --scenario scenarios/security_commerce_test.yaml
```

> **Note:** If you reduce `--agents`, the runner will use a subset of the configured models; if you increase it beyond available models, it may reuse some models.

---

## 7. Inspect Results with the Dashboard

Each run writes:
- A **CSV file** with the turn‑by‑turn transcript and actions.
- A **screenshots** directory with the browser screenshots per turn.

Results are stored in `results/<persona>_<scenario>/...`, for example:

- `results/online_shopper_ui-based_shopping_flow/online_shopper_ui-based_shopping_flow.csv`
- `results/online_shopper_ui-based_shopping_flow/screenshots/turn_1.png`, `turn_2.png`, …

### 7.1 Launch the Streamlit dashboard

From the project root:

```bash
streamlit run dashboard_app.py
```

This will open a local dashboard (usually at `http://localhost:8501`) where you can:
- Browse runs and personas.
- View agent discussions and committee decisions per turn.
- Inspect screenshots alongside actions and model outputs.

If a browser tab doesn’t open automatically, copy the shown URL into your browser.

---

## 8. Running Research Experiments

The `experiments/` directory contains a full experimental framework (batch runner + metrics + database).

### 8.1 Ensure prerequisites

- The AUT (`uvicorn aut_service:app --port 8000`) should be running.
- Your API keys and `config/model_config.yaml` should be configured.
- The same Python environment created earlier should be active.

### 8.2 Experiment runner

The main entry point is `experiments/runner.py`. It takes either a named experiment (`--experiment`) or a specific YAML config (`--config`).

Examples:

```bash
# Dry run: validate setup without executing full runs
python experiments/runner.py --experiment 1a --dry-run

# Experiment 1A: multi-agent scaling
python experiments/runner.py --experiment 1a

# Experiment 1B: persona diversity
python experiments/runner.py --experiment 1b

# Experiment 1C: vision impact
python experiments/runner.py --experiment 1c

# Experiment 1D: regression detection
python experiments/runner.py --experiment 1d

# Custom configuration YAML
python experiments/runner.py --config experiments/configs/experiment_2_owasp_juice_shop.yaml
```

Experiment outputs (metrics + run metadata) are written to the database and to per‑run folders under `results/` or `experiments/results/` depending on the configuration.

### 8.3 Inspecting experiment results in SQLite

You can query the experiment database directly:

```bash
sqlite3 experiments/results/experiments.db

-- inside sqlite:
.tables
SELECT * FROM runs LIMIT 5;
SELECT * FROM metrics LIMIT 5;
.quit
```

Refer to `experiments/README.md` for example SQL queries and the full schema.

---

## 9. Common Issues and Troubleshooting

### 9.1 Playwright / browser errors

- **Symptom:** Errors like “browser not found” or “Executable doesn’t exist”.
- **Fix:** Re‑run `python -m playwright install chromium` inside your virtualenv, then retry.

### 9.2 Missing or invalid API keys

- **Symptom:** HTTP 401/403 errors, or stack traces mentioning unauthenticated requests.
- **Fix:** Double‑check your `.env` or exported environment variables and ensure they match the provider names in `config/model_config.yaml`.
- **Tip:** Start by enabling only one provider (e.g., OpenAI) to debug connectivity before adding others.

### 9.3 AUT not reachable

- **Symptom:** Errors about failing to connect to `http://localhost:8000` or timeouts from the browser adapter.
- **Fix:** Make sure `uvicorn aut_service:app --port 8000` is running and reachable in a separate terminal; verify in a browser that `http://localhost:8000` loads.

### 9.4 Permissions / firewall issues (macOS)

- **Symptom:** Browser windows not opening or blocked, automation failing silently.
- **Fix:** Ensure your OS allows Playwright/Chromium to open windows and control them; if prompted, grant screen recording or automation permissions.

---

## 10. Suggested First Workflow (End‑to‑End)

1. **Clone and enter the repo**
   ```bash
   git clone https://github.com/DHIWAHAR-K/LLM_Agents_For_Beta_Testing.git
   cd LLM_Agents_For_Beta_Testing
   ```
2. **Create and activate a virtualenv**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   python -m playwright install chromium
   ```
3. **Configure at least one API key** in `config/.env` or your shell (e.g., `OPENAI_API_KEY`).
4. **Start the AUT**
   ```bash
   uvicorn aut_service:app --reload --port 8000
   ```
5. **Run a default multi‑agent session**
   ```bash
   python main.py
   ```
6. **Open the dashboard to inspect results**
   ```bash
   streamlit run dashboard_app.py
   ```

After this basic flow works, you can explore custom personas/scenarios and the full experiment runner to replicate the research results described in the project.
