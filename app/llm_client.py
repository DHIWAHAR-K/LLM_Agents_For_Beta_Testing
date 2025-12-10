from __future__ import annotations

import base64
import json
import os
import re
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from openai import OpenAI

from config import load_model_config

# Load environment variables from .env file
load_dotenv(Path(__file__).parent.parent / "config" / ".env")


class LLMClient:
    """Wrapper around LLM providers (OpenAI, Google, Anthropic, xAI, Ollama) with vision support."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        model_cfg: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize LLM client with specific model.
        
        Args:
            model_name: Name of the model to use (e.g., 'gpt-4o', 'gemini-2.0-flash-exp')
            model_cfg: Optional model config dict (loaded from YAML if not provided)
        """
        cfg = model_cfg or load_model_config()
        
        # Find model configuration
        models_list = cfg.get("models", [])
        if model_name:
            model_info = next((m for m in models_list if m.get("name") == model_name), None)
            if not model_info:
                model_info = models_list[0] if models_list else {"name": model_name, "provider": "openai"}
        else:
            model_info = models_list[0] if models_list else {"name": "gpt-4o", "provider": "openai"}
        
        self.model = model_info.get("name", "gpt-4o")
        self.provider = model_info.get("provider", "openai").lower()
        self.temperature = float(cfg.get("temperature", 0.2))
        self.max_retries = int(cfg.get("max_retries", 2))
        
        # Initialize provider-specific clients
        if self.provider == "openai":
            self._init_openai(cfg)
        elif self.provider == "google":
            self._init_google(cfg)
        elif self.provider == "anthropic":
            self._init_anthropic(cfg)
        elif self.provider == "xai":
            self._init_xai(cfg)
        elif self.provider == "ollama":
            self._init_ollama(cfg)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    def _init_openai(self, cfg: dict[str, Any]) -> None:
        """Initialize OpenAI client."""
        api_key = self._get_api_key("OPENAI_API_KEY")
        base_url = cfg.get("providers", {}).get("openai", {}).get("base_url", "https://api.openai.com/v1")
        
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.client_type = "openai"
    
    def _init_google(self, cfg: dict[str, Any]) -> None:
        """Initialize Google Gemini client."""
        try:
            from google import genai
        except ImportError:
            raise ImportError(
                "google-genai package not installed. Install with:\n"
                "pip install google-genai"
            )

        api_key = self._get_api_key("GOOGLE_API_KEY")
        # Use new Google GenAI SDK
        self.client = genai.Client(api_key=api_key)
        self.client_type = "google"
    
    def _init_anthropic(self, cfg: dict[str, Any]) -> None:
        """Initialize Anthropic Claude client."""
        try:
            import anthropic
        except ImportError:
            raise ImportError(
                "anthropic package not installed. Install with:\n"
                "pip install anthropic"
            )
        
        api_key = self._get_api_key("ANTHROPIC_API_KEY")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.client_type = "anthropic"
    
    def _init_xai(self, cfg: dict[str, Any]) -> None:
        """Initialize xAI Grok client (OpenAI-compatible)."""
        api_key = self._get_api_key("XAI_API_KEY")
        base_url = cfg.get("providers", {}).get("xai", {}).get("base_url", "https://api.x.ai/v1")
        
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.client_type = "openai"  # xAI uses OpenAI-compatible API
    
    def _init_ollama(self, cfg: dict[str, Any]) -> None:
        """Initialize Ollama client."""
        base_url = cfg.get("providers", {}).get("ollama", {}).get("base_url", "http://localhost:11434/v1")
        
        self.client = OpenAI(base_url=base_url, api_key="ollama")
        self.client_type = "openai"  # Ollama uses OpenAI-compatible API
    
    def _get_api_key(self, env_var: str) -> str:
        """Get API key from environment or .env file."""
        api_key = os.getenv(env_var)
        
        if not api_key:
            # Try reading directly from .env file as fallback
            env_file = Path(__file__).parent.parent / "config" / ".env"
            if env_file.exists():
                for line in env_file.read_text().splitlines():
                    if line.startswith(f"{env_var}="):
                        api_key = line.split("=", 1)[1].strip()
                        break
        
        if not api_key:
            raise ValueError(
                f"{env_var} not found. Please add it to config/.env file:\n"
                f"{env_var}=your-key-here"
            )
        
        return api_key

    def emit_json(self, system: str, user: str, image_path: Optional[str] = None) -> dict[str, Any]:
        """Request a single JSON object from the model, optionally with vision."""
        
        if self.client_type == "google":
            return self._emit_json_google(system, user, image_path)
        elif self.client_type == "anthropic":
            return self._emit_json_anthropic(system, user, image_path)
        else:
            return self._emit_json_openai(system, user, image_path)
    
    def _emit_json_openai(self, system: str, user: str, image_path: Optional[str] = None) -> dict[str, Any]:
        """OpenAI/Ollama implementation."""
        # Build message content
        if image_path:
            # Vision-enabled message
            user_content = [
                {"type": "text", "text": user},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{self._encode_image(image_path)}"}},
            ]
        else:
            # Text-only message
            user_content = user

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ]

        last_err: Optional[Exception] = None
        for _ in range(self.max_retries + 1):
            try:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    temperature=self.temperature,
                    messages=messages,
                )
                content = resp.choices[0].message.content or ""
                return self._extract_json(content)
            except Exception as exc:
                last_err = exc
        raise RuntimeError(f"emit_json failed after retries. Last error: {last_err}")
    
    def _emit_json_google(self, system: str, user: str, image_path: Optional[str] = None) -> dict[str, Any]:
        """Google Gemini implementation using new google.genai SDK."""
        from google.genai import types

        # Combine system and user prompts for Gemini
        full_prompt = f"{system}\n\n{user}"

        last_err: Optional[Exception] = None
        for _ in range(self.max_retries + 1):
            try:
                if image_path:
                    # Load image as base64 or file
                    with open(image_path, 'rb') as f:
                        image_data = f.read()

                    # Use new API with image
                    response = self.client.models.generate_content(
                        model=self.model,
                        contents=[
                            types.Part.from_text(full_prompt),
                            types.Part.from_bytes(data=image_data, mime_type="image/png")
                        ],
                        config=types.GenerateContentConfig(
                            temperature=self.temperature
                        )
                    )
                else:
                    response = self.client.models.generate_content(
                        model=self.model,
                        contents=full_prompt,
                        config=types.GenerateContentConfig(
                            temperature=self.temperature
                        )
                    )

                content = response.text
                return self._extract_json(content)
            except Exception as exc:
                last_err = exc
        raise RuntimeError(f"emit_json failed after retries. Last error: {last_err}")
    
    def _emit_json_anthropic(self, system: str, user: str, image_path: Optional[str] = None) -> dict[str, Any]:
        """Anthropic Claude implementation."""
        last_err: Optional[Exception] = None
        for _ in range(self.max_retries + 1):
            try:
                if image_path:
                    # Build content with image for Claude
                    with open(image_path, "rb") as image_file:
                        image_data = base64.b64encode(image_file.read()).decode("utf-8")
                    
                    # Determine media type
                    if image_path.lower().endswith('.png'):
                        media_type = "image/png"
                    elif image_path.lower().endswith(('.jpg', '.jpeg')):
                        media_type = "image/jpeg"
                    elif image_path.lower().endswith('.webp'):
                        media_type = "image/webp"
                    else:
                        media_type = "image/png"  # Default
                    
                    content = [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": user
                        }
                    ]
                else:
                    content = user
                
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    temperature=self.temperature,
                    system=system,
                    messages=[
                        {"role": "user", "content": content}
                    ]
                )
                
                content_text = response.content[0].text
                return self._extract_json(content_text)
            except Exception as exc:
                last_err = exc
        raise RuntimeError(f"emit_json failed after retries. Last error: {last_err}")

    @staticmethod
    def _encode_image(image_path: str) -> str:
        """Encode image to base64 string."""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    @staticmethod
    def _extract_json(raw: str) -> dict[str, Any]:
        """Parse the first JSON object within the raw model output."""

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
            if not match:
                raise ValueError(f"No JSON object found in model output: {raw}")
            return json.loads(match.group(0))
