from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from ._exceptions import ConfigError


DEFAULT_LOCAL_OLLAMA_URL = "http://localhost:11434"
DEFAULT_CLOUD_OLLAMA_URL = "https://ollama.com"
DEFAULT_TEMPERATURE = 0.2
DEFAULT_CONFIG_PATH = "config.json"

ENV_MODEL = "OLLAMA_MODEL"
ENV_CLOUD = "OLLAMA_CLOUD"
ENV_URL = "OLLAMA_URL"
ENV_TEMPERATURE = "OLLAMA_TEMPERATURE"
ENV_SYSTEM_PROMPT = "OLLAMA_SYSTEM_PROMPT"
ENV_API_KEY = "OLLAMA_API_KEY"

ENV_CONFIG_KEYS = {
    "model": ENV_MODEL,
    "cloud": ENV_CLOUD,
    "url": ENV_URL,
    "temperature": ENV_TEMPERATURE,
    "system_prompt": ENV_SYSTEM_PROMPT,
}


@dataclass(slots=True)
class OllamaConfig:
    """Store runtime settings for Ollama operations."""

    model: str | None
    url: str
    cloud: bool
    temperature: float = DEFAULT_TEMPERATURE
    system_prompt: str | None = None


def create_config(
    *,
    model: str | None = None,
    cloud: bool = False,
    url: str | None = None,
    temperature: float = DEFAULT_TEMPERATURE,
    system_prompt: str | None = None,
) -> OllamaConfig:
    """Create a validated configuration from explicit parameters."""

    return _build_config(
        _build_config_values(
            model=model,
            cloud=cloud,
            url=url,
            temperature=temperature,
            system_prompt=system_prompt,
        )
    )


def create_ollama_config(
    *,
    model: str | None = None,
    cloud: bool = False,
    url: str | None = None,
    temperature: float = DEFAULT_TEMPERATURE,
    system_prompt: str | None = None,
) -> OllamaConfig:
    """Backward-compatible alias for :func:`create_config`."""

    return create_config(
        model=model,
        cloud=cloud,
        url=url,
        temperature=temperature,
        system_prompt=system_prompt,
    )


def load_config(config_path: Path | str = DEFAULT_CONFIG_PATH) -> OllamaConfig | None:
    """Load configuration from environment variables and an optional JSON file."""

    config_file_path = Path(config_path)
    merged_config = _merge_env_config(_load_raw_ollama_config(config_file_path))

    if not config_file_path.exists() and not _has_any_config(merged_config):
        return None

    return _build_config(merged_config)


def resolve_config(
    config_path: Path | str = DEFAULT_CONFIG_PATH,
    *,
    model: str | None = None,
    cloud: bool | None = None,
    url: str | None = None,
    temperature: float | None = None,
    system_prompt: str | None = None,
) -> OllamaConfig | None:
    """Resolve configuration from explicit arguments, environment, and JSON.

    Explicit arguments override environment variables and config file values.
    Environment variables override values loaded from the JSON file.

    Args:
        config_path: Path to the optional JSON configuration file.
        model: Optional explicit model override.
        cloud: Optional explicit cloud-mode override.
        url: Optional explicit local URL override.
        temperature: Optional explicit temperature override.
        system_prompt: Optional explicit system prompt override.

    Returns:
        A resolved ``OllamaConfig`` instance, or ``None`` when no source
        provides any configuration value.
    """

    base_config = load_config(config_path)
    explicit_config = _build_config_values(
        model=model,
        cloud=cloud,
        url=url,
        temperature=temperature,
        system_prompt=system_prompt,
    )

    if base_config is None and not _has_any_config(explicit_config):
        return None

    merged_config: dict[str, Any] = {}
    if base_config is not None:
        merged_config.update(_config_to_dict(base_config))
    merged_config.update(explicit_config)
    return _build_config(merged_config)


def _load_raw_ollama_config(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        return {}

    try:
        raw_config = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON in {config_path}: {exc.msg}.") from exc

    if not isinstance(raw_config, dict):
        raise ConfigError("config.json must contain a JSON object.")

    ollama_config = raw_config.get("ollama", raw_config)
    if not isinstance(ollama_config, dict):
        raise ConfigError("config.json must contain an 'ollama' object or top-level Ollama settings.")

    return dict(ollama_config)


def _merge_env_config(raw_config: Mapping[str, Any]) -> dict[str, Any]:
    """Merge environment variables into raw configuration values."""

    merged_config = dict(raw_config)
    for field_name, env_var in ENV_CONFIG_KEYS.items():
        env_value = _normalize_optional_string(os.getenv(env_var))
        if env_value is not None:
            merged_config[field_name] = env_value
    return merged_config


def _build_config_values(
    *,
    model: str | None,
    cloud: bool | None,
    url: str | None,
    temperature: float | None,
    system_prompt: str | None,
) -> dict[str, Any]:
    """Build a raw configuration dictionary from explicit arguments."""

    explicit_config: dict[str, Any] = {}
    if model is not None:
        explicit_config["model"] = model
    if cloud is not None:
        explicit_config["cloud"] = cloud
    if url is not None:
        explicit_config["url"] = url
    if temperature is not None:
        explicit_config["temperature"] = temperature
    if system_prompt is not None:
        explicit_config["system_prompt"] = system_prompt
    return explicit_config


def _config_to_dict(config: OllamaConfig) -> dict[str, Any]:
    """Convert a validated config object back to a plain mapping."""

    return {
        "model": config.model,
        "cloud": config.cloud,
        "url": config.url,
        "temperature": config.temperature,
        "system_prompt": config.system_prompt,
    }


def _build_config(raw_config: Mapping[str, Any]) -> OllamaConfig:
    """Validate raw values and return an ``OllamaConfig`` instance."""

    cloud_mode = _coerce_bool(raw_config.get("cloud", False), field_name="cloud")
    return OllamaConfig(
        model=_optional_model(raw_config.get("model")),
        url=_resolve_ollama_url(raw_config, cloud_mode),
        cloud=cloud_mode,
        temperature=_coerce_temperature(raw_config.get("temperature", DEFAULT_TEMPERATURE)),
        system_prompt=_normalize_optional_string(raw_config.get("system_prompt")),
    )


def _resolve_ollama_url(raw_config: Mapping[str, Any], cloud: bool) -> str:
    """Resolve the Ollama host URL for local or cloud mode."""

    if cloud:
        return DEFAULT_CLOUD_OLLAMA_URL

    configured_url = _normalize_optional_string(raw_config.get("url"))
    if configured_url is not None:
        return configured_url
    return DEFAULT_LOCAL_OLLAMA_URL


def _has_any_config(raw_config: Mapping[str, Any]) -> bool:
    """Return whether the mapping contains at least one configured value."""

    for value in raw_config.values():
        if isinstance(value, bool):
            return True
        if _normalize_optional_string(value) is not None:
            return True
    return False


def _optional_model(raw_value: Any) -> str | None:
    """Normalize an optional model value."""

    return _normalize_optional_string(raw_value)


def _require_model(raw_value: Any) -> str:
    """Return a required model value or raise ``ConfigError``."""

    model_name = _normalize_optional_string(raw_value)
    if model_name is None:
        raise ConfigError("Ollama model must be a non-empty string.")
    return model_name


def _coerce_temperature(raw_value: Any) -> float:
    """Validate and normalize a temperature value."""

    try:
        temperature = float(raw_value)
    except (TypeError, ValueError) as exc:
        raise ConfigError("Ollama temperature must be a number.") from exc

    if temperature < 0:
        raise ConfigError("Ollama temperature must be greater than or equal to zero.")
    return temperature


def _coerce_bool(raw_value: Any, *, field_name: str) -> bool:
    """Validate and normalize a boolean-like configuration value."""

    if isinstance(raw_value, bool):
        return raw_value
    if isinstance(raw_value, str):
        normalized_value = raw_value.strip().lower()
        if normalized_value in {"true", "1", "yes", "on"}:
            return True
        if normalized_value in {"false", "0", "no", "off", ""}:
            return False
    raise ConfigError(f"Ollama {field_name} must be a boolean.")


def _normalize_optional_string(raw_value: Any) -> str | None:
    """Return a stripped string or ``None`` when the value is empty."""

    if raw_value is None:
        return None
    normalized_value = str(raw_value).strip()
    if not normalized_value:
        return None
    return normalized_value


def _normalize_required_text(raw_value: Any, *, field_name: str) -> str:
    """Return a required stripped string or raise ``ConfigError``."""

    normalized_value = _normalize_optional_string(raw_value)
    if normalized_value is None:
        raise ConfigError(f"{field_name.capitalize()} must be a non-empty string.")
    return normalized_value
