from __future__ import annotations

import os
from typing import Any, Iterator, TypeAlias

from ._config import ENV_API_KEY, OllamaConfig, _normalize_optional_string, _normalize_required_text, _require_model
from ._exceptions import AuthError, ConfigError, GenerationError


Message: TypeAlias = dict[str, str]


def build_client(config: OllamaConfig, *, api_key: str | None = None):
    """Build an ``ollama.Client`` instance for the provided configuration."""

    client_class = _import_ollama_client()
    headers: dict[str, str] | None = None
    if config.cloud:
        resolved_api_key = _resolve_api_key(api_key=api_key)
        headers = {"Authorization": f"Bearer {resolved_api_key}"}
    return client_class(host=config.url, headers=headers)


def generate(
    prompt: str,
    config: OllamaConfig,
    *,
    client: Any | None = None,
    stream: bool = False,
) -> str | Iterator[str]:
    """Generate a response from a single prompt.

    When ``stream`` is ``False``, returns the final response text.
    When ``stream`` is ``True``, returns an iterator of response chunks.
    """

    prompt_text = _normalize_required_text(prompt, field_name="prompt")
    messages = [{"role": "user", "content": prompt_text}]
    if stream:
        return _generate_stream_from_messages(messages, config, client=client)
    return _generate_from_messages(messages, config, client=client)


def _generate_from_messages(
    messages: list[Message],
    config: OllamaConfig,
    *,
    client: Any | None = None,
) -> str:
    """Generate a non-streaming chat response from an explicit message list."""

    response = _chat(messages, config, client=client, stream=False)
    response_text = _extract_response_text(response).strip()
    if not response_text:
        raise GenerationError("The Ollama response did not contain any message content.")
    return response_text


def _generate_stream_from_messages(
    messages: list[Message],
    config: OllamaConfig,
    *,
    client: Any | None = None,
) -> Iterator[str]:
    """Yield streaming response chunks from an explicit message list."""

    stream = _chat(messages, config, client=client, stream=True)
    emitted_chunk = False
    for chunk in stream:
        chunk_text = _extract_response_text(chunk)
        if chunk_text:
            emitted_chunk = True
            yield chunk_text
    if not emitted_chunk:
        raise GenerationError("The Ollama stream did not contain any message content.")


def generate_prompt(prompt: str, config: OllamaConfig, *, client: Any | None = None) -> str:
    """Backward-compatible alias for :func:`generate`."""

    return generate(prompt, config, client=client, stream=False)


def generate_prompt_stream(
    prompt: str,
    config: OllamaConfig,
    *,
    client: Any | None = None,
) -> Iterator[str]:
    """Backward-compatible streaming alias for :func:`generate`."""

    return generate(prompt, config, client=client, stream=True)


def generate_stream(
    messages: list[Message],
    config: OllamaConfig,
    *,
    client: Any | None = None,
) -> Iterator[str]:
    """Backward-compatible alias for explicit message-list streaming."""

    return _generate_stream_from_messages(messages, config, client=client)


def list_models(config: OllamaConfig, *, client: Any | None = None) -> list[str]:
    """List model names from the configured Ollama endpoint."""

    ollama_client = client or build_client(config)
    try:
        return _extract_model_names(ollama_client.list())
    except Exception as exc:
        raise GenerationError(f"Unable to list models from {config.url}: {exc}") from exc


def _chat(
    messages: list[Message],
    config: OllamaConfig,
    *,
    client: Any | None,
    stream: bool,
):
    """Send a chat request to Ollama and normalize request errors."""

    normalized_messages = _normalize_messages(messages)
    request_messages = _apply_system_prompt(normalized_messages, config.system_prompt)
    ollama_client = client or build_client(config)
    model_name = _require_model(config.model)

    try:
        return ollama_client.chat(
            model=model_name,
            messages=request_messages,
            options={"temperature": config.temperature},
            stream=stream,
        )
    except Exception as exc:
        raise GenerationError(_format_generation_error(exc, model_name=model_name)) from exc


def _normalize_messages(messages: list[Message]) -> list[Message]:
    """Validate and normalize an explicit message list."""

    if not isinstance(messages, list) or not messages:
        raise ConfigError("Messages must be a non-empty list.")

    normalized_messages: list[Message] = []
    for index, message in enumerate(messages, start=1):
        if not isinstance(message, dict):
            raise ConfigError(f"Message {index} must be a dictionary.")

        normalized_messages.append(
            {
                "role": _normalize_required_text(message.get("role"), field_name=f"message {index} role"),
                "content": _normalize_required_text(
                    message.get("content"),
                    field_name=f"message {index} content",
                ),
            }
        )

    return normalized_messages


def _apply_system_prompt(messages: list[Message], system_prompt: str | None) -> list[Message]:
    """Prepend the configured system prompt when present."""

    if system_prompt is None:
        return messages
    return [{"role": "system", "content": system_prompt}, *messages]


def _resolve_api_key(*, api_key: str | None = None) -> str:
    """Resolve the cloud API key from an explicit argument or the environment."""

    normalized_api_key = _normalize_optional_string(api_key)
    if normalized_api_key is not None:
        return normalized_api_key

    env_api_key = _normalize_optional_string(os.getenv(ENV_API_KEY))
    if env_api_key is not None:
        return env_api_key

    raise AuthError("OLLAMA_API_KEY is required for Ollama Cloud.")


def _import_ollama_client():
    """Import the official Ollama client lazily."""

    try:
        from ollama import Client
    except ImportError as exc:
        raise GenerationError("The 'ollama' package is required for Ollama generation.") from exc
    return Client


def _extract_response_text(response: Any) -> str:
    """Extract text from an Ollama response or response chunk."""

    if isinstance(response, dict):
        message = response.get("message", {})
        if isinstance(message, dict):
            return str(message.get("content", ""))

    message = getattr(response, "message", None)
    if message is None:
        return ""
    return str(getattr(message, "content", ""))


def _extract_model_names(response: Any) -> list[str]:
    """Extract model names from the Ollama model listing response."""

    if isinstance(response, dict):
        raw_models = response.get("models", [])
    else:
        raw_models = getattr(response, "models", [])

    model_names: list[str] = []
    for raw_model in raw_models or []:
        if isinstance(raw_model, dict):
            model_name = _normalize_optional_string(raw_model.get("model"))
        else:
            model_name = _normalize_optional_string(getattr(raw_model, "model", None))
        if model_name is not None:
            model_names.append(model_name)
    return model_names


def _format_generation_error(exc: Exception, *, model_name: str) -> str:
    """Convert a generation exception into a clearer runtime error message."""

    error_message = str(exc).strip() or exc.__class__.__name__
    normalized_error = error_message.lower()
    if "model" in normalized_error and any(
        token in normalized_error for token in {"not found", "no such", "unknown", "missing"}
    ):
        return f"{error_message} Use --list to inspect available models."
    return f"Generation failed for model '{model_name}': {error_message}"
