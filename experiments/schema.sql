-- SQLite Schema for LLM Beta Testing Framework Experiments
-- Supports multi-tier validation: Your AUT + OWASP Juice Shop + WebShop

-- ============================================================================
-- EXPERIMENTS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS experiments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    tier TEXT NOT NULL CHECK(tier IN ('your_aut', 'owasp', 'webshop')),
    description TEXT,
    research_question TEXT,
    baseline_paper TEXT,
    baseline_score TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- RUNS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_id INTEGER NOT NULL,
    run_number INTEGER NOT NULL,
    seed INTEGER,
    config_json TEXT,  -- JSON serialized configuration

    -- Context
    persona_name TEXT,
    scenario_name TEXT,
    model_provider TEXT,
    num_agents INTEGER DEFAULT 1,
    vision_enabled BOOLEAN DEFAULT 1,
    aut_version TEXT DEFAULT 'v1.0',

    -- Session info
    session_id TEXT,
    total_turns INTEGER,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    duration_seconds REAL,

    -- High-level outcomes
    success BOOLEAN,
    error_message TEXT,

    FOREIGN KEY (experiment_id) REFERENCES experiments(id),
    UNIQUE(experiment_id, run_number, seed)
);

-- ============================================================================
-- METRICS TABLE (Per-run quantitative measurements)
-- ============================================================================
CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,

    -- Task Success Metrics
    task_success_rate REAL,  -- Percentage of successful turns
    total_successful_turns INTEGER,
    total_turns INTEGER,

    -- Safety & Security Metrics
    safety_pass_rate REAL,
    total_safe_turns INTEGER,
    vulnerabilities_detected INTEGER,
    false_positives INTEGER,
    true_positive_rate REAL,
    false_positive_rate REAL,
    f1_score REAL,

    -- Performance Metrics
    avg_latency_seconds REAL,
    p50_latency_seconds REAL,
    p95_latency_seconds REAL,
    p99_latency_seconds REAL,

    -- Multi-Agent Metrics
    avg_committee_agreement REAL,  -- Average agreement % across turns
    consensus_strength REAL,  -- How often consensus reached
    mind_changes INTEGER,  -- Times agents changed proposals after discussion

    -- Vision Metrics
    element_localization_accuracy REAL,
    action_precision REAL,  -- Valid actions / attempted
    false_action_rate REAL,

    -- Cost Metrics
    total_api_calls INTEGER,
    total_cost_usd REAL,
    cost_per_successful_task REAL,

    -- WebShop Specific
    webshop_reward_score REAL,
    action_efficiency REAL,  -- Steps to completion

    -- Behavioral Diversity
    unique_actions INTEGER,
    action_sequence_length INTEGER,
    behavioral_diversity_score REAL,  -- Jaccard distance

    FOREIGN KEY (run_id) REFERENCES runs(id)
);

-- ============================================================================
-- BUGS TABLE (Ground truth and detected bugs)
-- ============================================================================
CREATE TABLE IF NOT EXISTS bugs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER,
    experiment_id INTEGER NOT NULL,

    -- Bug identification
    bug_id TEXT NOT NULL,  -- Unique identifier for injected bugs
    bug_type TEXT NOT NULL CHECK(bug_type IN (
        'functional', 'security', 'business_logic', 'accessibility',
        'performance', 'ui_regression', 'api_regression'
    )),
    bug_category TEXT,  -- More specific: sql_injection, xss, broken_checkout, etc.
    severity TEXT CHECK(severity IN ('low', 'medium', 'high', 'critical')),

    -- Bug details
    description TEXT,
    location TEXT,  -- Endpoint, UI element, function name
    injected_in_version TEXT,  -- Which AUT version has this bug

    -- Detection status
    is_ground_truth BOOLEAN DEFAULT 0,  -- Known injected bug
    detected BOOLEAN DEFAULT 0,
    detected_at_turn INTEGER,
    detected_by_persona TEXT,
    detection_confidence REAL,

    -- False positive tracking
    is_false_positive BOOLEAN DEFAULT 0,

    FOREIGN KEY (run_id) REFERENCES runs(id),
    FOREIGN KEY (experiment_id) REFERENCES experiments(id)
);

-- ============================================================================
-- REGRESSIONS TABLE (Version comparison for Experiment 1D)
-- ============================================================================
CREATE TABLE IF NOT EXISTS regressions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    regression_id TEXT NOT NULL UNIQUE,
    regression_type TEXT CHECK(regression_type IN (
        'breaking_change', 'behavioral_change', 'performance_degradation', 'ui_regression'
    )),
    category TEXT,
    description TEXT,
    location TEXT,
    introduced_in_version TEXT DEFAULT 'v2.0',
    severity TEXT CHECK(severity IN ('low', 'medium', 'high', 'critical')),
    expected_behavior TEXT,
    actual_behavior TEXT
);

-- ============================================================================
-- REGRESSION_DETECTIONS TABLE (Which runs detected which regressions)
-- ============================================================================
CREATE TABLE IF NOT EXISTS regression_detections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    regression_id TEXT NOT NULL,
    detected BOOLEAN NOT NULL,
    detected_at_turn INTEGER,
    confidence REAL,
    evidence TEXT,  -- What made the agent flag this
    is_false_positive BOOLEAN DEFAULT 0,

    FOREIGN KEY (run_id) REFERENCES runs(id),
    FOREIGN KEY (regression_id) REFERENCES regressions(regression_id)
);

-- ============================================================================
-- PROPOSALS TABLE (Individual agent proposals for analysis)
-- ============================================================================
CREATE TABLE IF NOT EXISTS proposals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    turn_number INTEGER NOT NULL,
    round_number INTEGER CHECK(round_number IN (1, 2, 3)),

    -- Agent info
    agent_id INTEGER,
    model_provider TEXT,

    -- Proposal details
    action_type TEXT,
    action_target TEXT,
    action_value TEXT,
    reasoning TEXT,
    confidence_score REAL,

    -- Outcome
    was_selected BOOLEAN DEFAULT 0,
    changed_from_previous_round BOOLEAN DEFAULT 0,

    FOREIGN KEY (run_id) REFERENCES runs(id)
);

-- ============================================================================
-- TURNS TABLE (Detailed turn-by-turn data)
-- ============================================================================
CREATE TABLE IF NOT EXISTS turns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    turn_number INTEGER NOT NULL,

    -- Action taken
    action_type TEXT,
    action_target TEXT,
    action_value TEXT,
    screenshot_path TEXT,

    -- Validation results
    validators_passed TEXT,  -- Semicolon-separated list
    validators_failed TEXT,

    -- Outcome
    success BOOLEAN,
    safety_pass BOOLEAN,
    latency_seconds REAL,

    -- Committee metrics (this turn)
    num_unique_proposals INTEGER,
    agreement_percentage REAL,
    consensus_confidence REAL,

    -- Element localization (for vision analysis)
    element_found BOOLEAN,
    correct_element BOOLEAN,

    FOREIGN KEY (run_id) REFERENCES runs(id),
    UNIQUE(run_id, turn_number)
);

-- ============================================================================
-- OWASP_CHALLENGES TABLE (For OWASP Juice Shop testing)
-- ============================================================================
CREATE TABLE IF NOT EXISTS owasp_challenges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    challenge_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    category TEXT NOT NULL,  -- OWASP Top 10 category
    difficulty TEXT CHECK(difficulty IN ('low', 'medium', 'high', 'expert')),
    description TEXT,
    owasp_category TEXT,  -- A01:2021, A02:2021, etc.
    vulnerability_type TEXT  -- SQL Injection, XSS, etc.
);

-- ============================================================================
-- OWASP_DETECTIONS TABLE (Which challenges were solved)
-- ============================================================================
CREATE TABLE IF NOT EXISTS owasp_detections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    challenge_id TEXT NOT NULL,
    detected BOOLEAN NOT NULL,
    detected_at_turn INTEGER,
    detection_method TEXT,  -- How it was found
    confidence REAL,

    FOREIGN KEY (run_id) REFERENCES runs(id),
    FOREIGN KEY (challenge_id) REFERENCES owasp_challenges(challenge_id)
);

-- ============================================================================
-- WEBSHOP_TASKS TABLE (WebShop benchmark tasks)
-- ============================================================================
CREATE TABLE IF NOT EXISTS webshop_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL UNIQUE,
    instruction TEXT NOT NULL,
    target_attributes TEXT,  -- JSON: required product attributes
    difficulty TEXT CHECK(difficulty IN ('easy', 'medium', 'hard'))
);

-- ============================================================================
-- WEBSHOP_RESULTS TABLE (WebShop task performance)
-- ============================================================================
CREATE TABLE IF NOT EXISTS webshop_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    task_id TEXT NOT NULL,
    success BOOLEAN NOT NULL,
    reward_score REAL,  -- 0.0 to 1.0
    num_steps INTEGER,
    purchased_product TEXT,  -- Product ASIN
    correct_attributes TEXT,  -- Which attributes matched

    FOREIGN KEY (run_id) REFERENCES runs(id),
    FOREIGN KEY (task_id) REFERENCES webshop_tasks(task_id)
);

-- ============================================================================
-- BASELINES TABLE (Store baseline scores for comparison)
-- ============================================================================
CREATE TABLE IF NOT EXISTS baselines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_name TEXT NOT NULL,
    source_paper TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value REAL NOT NULL,
    notes TEXT,

    UNIQUE(experiment_name, source_paper, metric_name)
);

-- ============================================================================
-- INDEXES for Performance
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_runs_experiment ON runs(experiment_id);
CREATE INDEX IF NOT EXISTS idx_runs_session ON runs(session_id);
CREATE INDEX IF NOT EXISTS idx_metrics_run ON metrics(run_id);
CREATE INDEX IF NOT EXISTS idx_bugs_run ON bugs(run_id);
CREATE INDEX IF NOT EXISTS idx_bugs_experiment ON bugs(experiment_id);
CREATE INDEX IF NOT EXISTS idx_proposals_run ON proposals(run_id);
CREATE INDEX IF NOT EXISTS idx_turns_run ON turns(run_id);
CREATE INDEX IF NOT EXISTS idx_regression_detections_run ON regression_detections(run_id);
CREATE INDEX IF NOT EXISTS idx_owasp_detections_run ON owasp_detections(run_id);
CREATE INDEX IF NOT EXISTS idx_webshop_results_run ON webshop_results(run_id);

-- ============================================================================
-- VIEWS for Common Queries
-- ============================================================================

-- View: Experiment Summary
CREATE VIEW IF NOT EXISTS experiment_summary AS
SELECT
    e.name as experiment_name,
    e.tier,
    COUNT(DISTINCT r.id) as total_runs,
    AVG(m.task_success_rate) as avg_success_rate,
    AVG(m.safety_pass_rate) as avg_safety_rate,
    AVG(m.avg_committee_agreement) as avg_agreement,
    AVG(m.total_cost_usd) as avg_cost
FROM experiments e
LEFT JOIN runs r ON e.id = r.experiment_id
LEFT JOIN metrics m ON r.id = m.run_id
GROUP BY e.id;

-- View: Multi-Agent Scaling Analysis
CREATE VIEW IF NOT EXISTS multi_agent_scaling AS
SELECT
    r.num_agents,
    AVG(m.task_success_rate) as avg_success_rate,
    AVG(m.vulnerabilities_detected) as avg_bugs_detected,
    AVG(m.avg_committee_agreement) as avg_agreement,
    AVG(m.total_cost_usd) as avg_cost,
    COUNT(r.id) as num_runs
FROM runs r
JOIN metrics m ON r.id = m.run_id
WHERE r.experiment_id IN (SELECT id FROM experiments WHERE name LIKE '%multi_agent%')
GROUP BY r.num_agents
ORDER BY r.num_agents;

-- View: Persona Coverage Matrix
CREATE VIEW IF NOT EXISTS persona_coverage AS
SELECT
    r.persona_name,
    b.bug_type,
    COUNT(DISTINCT CASE WHEN b.detected = 1 THEN b.bug_id END) as bugs_detected,
    COUNT(DISTINCT CASE WHEN b.is_ground_truth = 1 THEN b.bug_id END) as total_bugs,
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN b.detected = 1 THEN b.bug_id END) /
          NULLIF(COUNT(DISTINCT CASE WHEN b.is_ground_truth = 1 THEN b.bug_id END), 0), 2) as detection_rate
FROM runs r
JOIN bugs b ON r.id = b.run_id
WHERE b.is_ground_truth = 1
GROUP BY r.persona_name, b.bug_type;

-- View: Vision Impact Analysis
CREATE VIEW IF NOT EXISTS vision_impact AS
SELECT
    r.vision_enabled,
    AVG(m.element_localization_accuracy) as avg_localization_accuracy,
    AVG(m.action_precision) as avg_action_precision,
    AVG(m.task_success_rate) as avg_success_rate,
    COUNT(r.id) as num_runs
FROM runs r
JOIN metrics m ON r.id = m.run_id
WHERE r.experiment_id IN (SELECT id FROM experiments WHERE name LIKE '%vision%')
GROUP BY r.vision_enabled;

-- View: Model Provider Comparison
CREATE VIEW IF NOT EXISTS model_comparison AS
SELECT
    r.model_provider,
    AVG(m.task_success_rate) as avg_success_rate,
    AVG(m.vulnerabilities_detected) as avg_bugs_detected,
    AVG(m.safety_pass_rate) as avg_safety_rate,
    AVG(m.total_cost_usd) as avg_cost,
    AVG(m.avg_latency_seconds) as avg_latency,
    COUNT(r.id) as num_runs
FROM runs r
JOIN metrics m ON r.id = m.run_id
WHERE r.num_agents = 1  -- Single agent comparison
GROUP BY r.model_provider;

-- View: OWASP Performance by Category
CREATE VIEW IF NOT EXISTS owasp_performance AS
SELECT
    oc.category,
    oc.owasp_category,
    COUNT(DISTINCT oc.challenge_id) as total_challenges,
    COUNT(DISTINCT CASE WHEN od.detected = 1 THEN oc.challenge_id END) as challenges_solved,
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN od.detected = 1 THEN oc.challenge_id END) /
          COUNT(DISTINCT oc.challenge_id), 2) as detection_rate
FROM owasp_challenges oc
LEFT JOIN owasp_detections od ON oc.challenge_id = od.challenge_id
GROUP BY oc.category, oc.owasp_category;
