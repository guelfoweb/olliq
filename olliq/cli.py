"""Command-line interface for ``olliq``."""

from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path
from typing import Any, Iterable

from ._config import (
    DEFAULT_CONFIG_PATH,
    ENV_API_KEY,
    _coerce_temperature,
    _has_any_config,
    _normalize_optional_string,
    load_config,
    resolve_config,
)
from ._core import build_client, generate, list_models
from ._exceptions import ConfigError, OlliqError


def main(argv: list[str] | None = None) -> int:
    """Run the command-line interface."""

    parser = _build_argument_parser()
    args = parser.parse_args(argv)

    try:
        config = _resolve_cli_config(args)
        client = build_client(config, api_key=_resolve_cli_api_key(config))

        if args.list:
            _print_model_names(list_models(config, client=client))
            return 0

        prompt = _resolve_cli_prompt(args.prompt)
        if args.stream:
            _print_stream(generate(prompt, config, client=client, stream=True))
            return 0

        print(generate(prompt, config, client=client, stream=False))
        return 0
    except OlliqError as exc:
        print(f"Ollama error: {exc}", file=sys.stderr)
        return 1


def _build_argument_parser() -> argparse.ArgumentParser:
    """Build and return the CLI argument parser."""

    parser = argparse.ArgumentParser(
        prog="olliq",
        description=(
            "Minimal CLI for local and cloud Ollama.\n\n"
            "Main operations:\n"
            "  - send one prompt\n"
            "  - stream one response\n"
            "  - list available models"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=(
            "Configuration order:\n"
            "  1. CLI flags\n"
            "  2. Environment variables\n"
            "  3. config.json\n"
            "  4. Built-in defaults\n\n"
            "Defaults:\n"
            "  - local mode\n"
            "  - local URL: http://localhost:11434\n"
            "  - temperature: 0.2\n\n"
            "Local mode:\n"
            "  - default mode\n"
            "  - uses your local Ollama server\n"
            "  - accepts --url\n\n"
            "Cloud mode:\n"
            "  - enable with --cloud\n"
            "  - uses https://ollama.com\n"
            "  - ignores --url\n"
            "  - requires OLLAMA_API_KEY\n"
            "  - prompts for OLLAMA_API_KEY only in the CLI and only in an interactive terminal\n\n"
            "Prompt input:\n"
            "  - use the positional prompt argument\n"
            "  - or pipe text through stdin\n"
            "  - if both are provided, the final prompt is:\n"
            "      <prompt>\\n\\n<stdin content>\n\n"
            "Examples:\n"
            "  Local prompt:\n"
            '    olliq --model qwen3:latest "Hello"\n\n'
            "  Cloud prompt:\n"
            '    olliq --cloud --model gpt-oss:20b "Hello"\n\n'
            "  Stream output:\n"
            '    olliq --stream --model qwen3:latest "Tell me a story"\n\n'
            "  List models:\n"
            "    olliq --list\n\n"
            "  Summarize piped text:\n"
            '    cat filename.txt | olliq --model qwen3:latest "summarize"'
        ),
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        help="Prompt text to send to the model. Optional when stdin is piped or --list is used.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available models instead of sending a prompt.",
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Stream the response to stdout instead of waiting for the final text.",
    )
    parser.add_argument(
        "--cloud",
        action="store_const",
        const=True,
        default=None,
        help="Use Ollama Cloud for this command.",
    )
    parser.add_argument(
        "--model",
        help="Model name to use for this command, for example qwen3:latest or gpt-oss:20b.",
    )
    parser.add_argument(
        "--url",
        help="Local Ollama server URL. Ignored in cloud mode.",
    )
    parser.add_argument(
        "--temperature",
        help="Generation temperature. Lower values are usually more deterministic.",
    )
    parser.add_argument(
        "--system-prompt",
        help="Optional system prompt prepended before the user prompt.",
    )
    parser.add_argument(
        "--config",
        default=DEFAULT_CONFIG_PATH,
        help="Path to config.json. Default: config.json.",
    )
    return parser


def _resolve_cli_config(args: argparse.Namespace):
    """Resolve CLI configuration from flags, environment, and optional file."""

    config_path = Path(args.config)
    cli_overrides = _parse_cli_overrides(args)
    base_config = load_config(args.config)

    if (
        args.config == DEFAULT_CONFIG_PATH
        and not config_path.exists()
        and not _has_any_config(cli_overrides)
        and base_config is None
    ):
        raise _config_error(
            "No config.json found in "
            f"{Path.cwd()}. Specify it with --config /path/to/config.json or use environment variables."
        )

    if base_config is None and not _has_any_config(cli_overrides):
        raise _config_error(
            f"No Ollama configuration found at {args.config}. "
            "Specify it with --config or use environment variables."
        )

    resolved_config = _resolve_cli_config_values(
        config_path=args.config,
        cli_overrides=cli_overrides,
    )
    if resolved_config is None:
        raise _config_error(
            f"No Ollama configuration found at {args.config}. "
            "Specify it with --config or use environment variables."
        )
    return resolved_config


def _resolve_cli_config_values(*, config_path: str, cli_overrides: dict[str, Any]):
    """Resolve configuration values from CLI overrides and non-CLI sources."""

    return resolve_config(
        config_path,
        model=cli_overrides.get("model"),
        cloud=cli_overrides.get("cloud"),
        url=cli_overrides.get("url"),
        temperature=cli_overrides.get("temperature"),
        system_prompt=cli_overrides.get("system_prompt"),
    )


def _parse_cli_overrides(args: argparse.Namespace) -> dict[str, Any]:
    """Parse only the CLI arguments explicitly provided by the user."""

    overrides: dict[str, Any] = {}
    model_name = _normalize_optional_string(args.model)
    host_url = _normalize_optional_string(args.url)

    if model_name is not None:
        overrides["model"] = model_name
    if args.cloud is not None:
        overrides["cloud"] = True
    if host_url is not None:
        overrides["url"] = host_url
    if args.temperature is not None:
        overrides["temperature"] = _coerce_temperature(args.temperature)
    system_prompt = _normalize_optional_string(args.system_prompt)
    if system_prompt is not None:
        overrides["system_prompt"] = system_prompt

    return overrides


def _resolve_cli_prompt(prompt: str | None) -> str:
    """Resolve the final prompt from the positional argument and optional stdin."""

    prompt_text = _normalize_optional_string(prompt)
    stdin_text = _read_stdin_text()

    if prompt_text and stdin_text:
        return f"{prompt_text}\n\n{stdin_text}"
    if prompt_text:
        return prompt_text
    if stdin_text:
        return stdin_text
    raise _config_error("prompt is required unless --list is used or stdin is piped in.")


def _read_stdin_text() -> str | None:
    """Read stdin text when input is piped into the CLI."""

    if sys.stdin.isatty():
        return None
    return _normalize_optional_string(sys.stdin.read())


def _print_model_names(model_names: list[str]) -> None:
    """Print model names one per line."""

    for model_name in model_names:
        print(model_name)


def _print_stream(chunks: Iterable[str]) -> None:
    """Print streaming output while preserving the final trailing newline."""

    wrote_output = False
    for chunk in chunks:
        wrote_output = True
        print(chunk, end="", flush=True)
    if wrote_output:
        print()


def _config_error(message: str):
    """Create a configuration error with a consistent type."""

    return ConfigError(message)


def _resolve_cli_api_key(config) -> str | None:
    """Resolve an API key for CLI cloud usage, prompting only in interactive mode."""

    if not config.cloud:
        return None

    configured_api_key = _normalize_optional_string(os.getenv(ENV_API_KEY))
    if configured_api_key is not None:
        return configured_api_key

    if not sys.stdin.isatty():
        raise _config_error("OLLAMA_API_KEY is required for Ollama Cloud.")

    prompted_api_key = _normalize_optional_string(
        getpass.getpass("Enter your Ollama Cloud API key: ")
    )
    if prompted_api_key is None:
        raise _config_error("OLLAMA_API_KEY is required for Ollama Cloud.")
    return prompted_api_key
