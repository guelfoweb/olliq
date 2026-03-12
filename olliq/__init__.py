"""Reusable Ollama bridge for local and cloud execution."""

__version__ = "0.1.0"

from ._config import (
    DEFAULT_CLOUD_OLLAMA_URL,
    DEFAULT_CONFIG_PATH,
    DEFAULT_LOCAL_OLLAMA_URL,
    DEFAULT_TEMPERATURE,
    OllamaConfig,
    create_config,
    create_ollama_config,
    load_config,
    resolve_config,
)
from ._core import (
    generate,
    generate_prompt,
    generate_prompt_stream,
    generate_stream,
    list_models,
)
from ._exceptions import AuthError, ConfigError, GenerationError, OlliqError

__all__ = [
    "AuthError",
    "ConfigError",
    "DEFAULT_CLOUD_OLLAMA_URL",
    "DEFAULT_CONFIG_PATH",
    "DEFAULT_LOCAL_OLLAMA_URL",
    "DEFAULT_TEMPERATURE",
    "GenerationError",
    "OllamaConfig",
    "OlliqError",
    "__version__",
    "create_config",
    "create_ollama_config",
    "generate",
    "generate_prompt",
    "generate_prompt_stream",
    "generate_stream",
    "list_models",
    "load_config",
    "resolve_config",
]
