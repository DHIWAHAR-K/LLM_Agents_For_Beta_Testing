from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Runtime configuration sourced from environment variables."""

    # Local model settings (Ollama)
    ollama_base_url: str = "http://localhost:11434/v1"
    default_model: str = "phi3"
    temperature: float = 0.2
    
    # Storage settings
    db_path: str = "agent_runs.sqlite"
    
    # AUT settings
    api_base_url: str = "http://localhost:8000"
    
    # Session settings
    max_turns: int = 3
    max_retries: int = 2
    seed: int = 42
    version: str = "unknown"
    
    # Latency thresholds (seconds)
    latency_max: float = 5.0
    latency_p50_max: float = 2.0
    latency_p95_max: float = 4.0
    latency_mean_max: float = 2.5
    
    # Safety settings
    safety_profile: str = "balanced"  # strict|balanced|neutral
    
    # Multi-agent routing settings
    routing_policy: str = "round_robin"  # round_robin|weighted|failover|committee
    routing_models: list[str] = ["phi3-mini", "llama3.2-3b", "gemma2-2b", "qwen2.5-3b", "stablelm2-1.6b"]
    routing_weights: list[float] | None = None
    committee_size: int = 3
    committee_threshold: int = 2
    
    # Report settings
    reports_dir: str = "reports"
    
    class Config:
        env_file = "config/.env"
        env_file_encoding = "utf-8"


def load_settings() -> "Settings":
    """Provide a reusable settings singleton."""

    return Settings()


settings = load_settings()
