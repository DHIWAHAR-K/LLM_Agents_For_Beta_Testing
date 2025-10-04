"""
Model registry for multi-agent support with reproducible configuration.

Manages multiple LLM backends (OpenAI, open-source models, etc.) with deterministic settings.
"""

from __future__ import annotations

import hashlib
from typing import Any, Literal

from pydantic import BaseModel, Field

from config import settings
from llm import LLM


class ModelSpec(BaseModel):
    """Specification for an LLM model."""
    
    name: str = Field(..., description="Unique model identifier")
    family: Literal["openai", "anthropic", "open-source", "local"] = "openai"
    source: str = Field(..., description="Model source/provider")
    checkpoint: str = Field(..., description="Model checkpoint/path")
    tokenizer: str | None = Field(None, description="Tokenizer name if different from checkpoint")
    temperature: float = Field(0.2, ge=0.0, le=2.0)
    max_tokens: int | None = Field(None, description="Max tokens to generate")
    top_p: float | None = Field(None, ge=0.0, le=1.0)
    safety_profile: str = Field("balanced", description="Safety profile (strict|balanced|neutral)")
    default_seed: int = Field(42, description="Default random seed for reproducibility")
    extra_params: dict[str, Any] = Field(default_factory=dict, description="Additional model-specific params")
    
    def get_hash(self) -> str:
        """Generate deterministic hash of model config for reproducibility."""
        config_str = f"{self.name}|{self.checkpoint}|{self.temperature}|{self.default_seed}"
        return hashlib.sha256(config_str.encode()).hexdigest()[:16]


# Predefined model specs - 5 local 3B models via Ollama
DEFAULT_MODELS = [
    ModelSpec(
        name="phi3-mini",
        family="local",
        source="ollama",
        checkpoint="phi3",
        temperature=0.2,
        safety_profile="balanced",
        extra_params={"size": "3.8B", "provider": "Microsoft"},
    ),
    ModelSpec(
        name="llama3.2-3b",
        family="local",
        source="ollama",
        checkpoint="llama3.2:3b",
        temperature=0.2,
        safety_profile="balanced",
        extra_params={"size": "3B", "provider": "Meta"},
    ),
    ModelSpec(
        name="gemma2-2b",
        family="local",
        source="ollama",
        checkpoint="gemma2:2b",
        temperature=0.3,
        safety_profile="strict",
        extra_params={"size": "2.6B", "provider": "Google"},
    ),
    ModelSpec(
        name="qwen2.5-3b",
        family="local",
        source="ollama",
        checkpoint="qwen2.5:3b",
        temperature=0.2,
        safety_profile="balanced",
        extra_params={"size": "3B", "provider": "Alibaba"},
    ),
    ModelSpec(
        name="stablelm2-1.6b",
        family="local",
        source="ollama",
        checkpoint="stablelm2:1.6b",
        temperature=0.3,
        safety_profile="neutral",
        extra_params={"size": "1.6B", "provider": "Stability AI"},
    ),
]


class ModelRegistry:
    """
    Registry for managing multiple LLM backends.
    
    Provides deterministic model configuration and instantiation.
    """
    
    def __init__(self, specs: list[ModelSpec] | None = None):
        """
        Initialize registry with model specifications.
        
        Args:
            specs: List of ModelSpec objects. Defaults to DEFAULT_MODELS.
        """
        self.specs = specs or DEFAULT_MODELS
        self._models: dict[str, ModelSpec] = {spec.name: spec for spec in self.specs}
        self._instances: dict[str, LLM] = {}
    
    def get(self, name: str) -> LLM:
        """
        Get or create an LLM instance for the specified model.
        
        Args:
            name: Model name from registry
            
        Returns:
            LLM: Configured LLM instance compatible with existing LLM class
            
        Raises:
            ValueError: If model name not found in registry
        """
        if name not in self._models:
            available = ", ".join(self._models.keys())
            raise ValueError(f"Model '{name}' not found in registry. Available: {available}")
        
        # Return cached instance if exists
        if name in self._instances:
            return self._instances[name]
        
        # Create new instance
        spec = self._models[name]

        # All models now use Ollama via OpenAI-compatible interface
        llm = LLM(
            model=spec.checkpoint,
            temperature=spec.temperature,
            max_retries=settings.max_retries,
        )
        
        self._instances[name] = llm
        return llm
    
    def list_models(self) -> list[str]:
        """Get list of available model names."""
        return list(self._models.keys())
    
    def get_spec(self, name: str) -> ModelSpec:
        """Get model specification."""
        if name not in self._models:
            raise ValueError(f"Model '{name}' not found in registry")
        return self._models[name]
    
    def add_model(self, spec: ModelSpec) -> None:
        """Add a new model to the registry."""
        if spec.name in self._models:
            raise ValueError(f"Model '{spec.name}' already exists in registry")
        self._models[spec.name] = spec
        self.specs.append(spec)
    
    def get_model_info(self, name: str) -> dict[str, Any]:
        """
        Get complete model information including hash.
        
        Args:
            name: Model name
            
        Returns:
            dict: Model info with hash for reproducibility tracking
        """
        spec = self.get_spec(name)
        return {
            "name": spec.name,
            "family": spec.family,
            "source": spec.source,
            "checkpoint": spec.checkpoint,
            "temperature": spec.temperature,
            "safety_profile": spec.safety_profile,
            "config_hash": spec.get_hash(),
        }


# Global default registry
_default_registry: ModelRegistry | None = None


def get_default_registry() -> ModelRegistry:
    """Get or create the default global model registry."""
    global _default_registry
    if _default_registry is None:
        _default_registry = ModelRegistry()
    return _default_registry

