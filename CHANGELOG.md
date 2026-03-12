# Changelog

## Unreleased

- Renamed the project package and CLI from `ollamabridge` to `olliq`.
- Set the package license to MIT.
- Added packaging metadata for the public repository `https://github.com/guelfoweb/olliq`.
- Added GitHub Actions workflows for CI and PyPI Trusted Publishing.
- Simplified the CLI cloud switch so `--cloud` directly enables cloud mode.
- Kept the package version at `0.1.0` until public distribution.
- Added project attribution for Gianni Amato in package metadata and documentation.
- Clarified the project goal in documentation: `olliq` simplifies and standardizes use of the official Ollama client rather than replacing it.
- Simplified the preferred Python API around `generate(prompt, config, stream=False)` while keeping older helper names as backward-compatible aliases.
- Updated the CLI startup flow to accept either `config.json` in the current directory or environment variables before suggesting `--config`.
- Refactored package internals to split configuration logic into `olliq._config` and keep `olliq._core` focused on client and generation behavior.
- Rewrote the README to document the package scope, capability map, local/cloud usage, streaming, and CLI behavior more clearly.
- Changed the CLI default flow to look for `config.json` in the current directory and ask for `--config` when it is missing.
- Added package-specific exceptions: `ConfigError`, `AuthError`, and `GenerationError`.
- Added streaming APIs: `generate_stream` and `generate_prompt_stream`.
- Moved the CLI into `olliq.cli` to keep `_core.py` focused on reusable API logic.
- Added CLI streaming with `--stream`.
- Shortened and simplified the README around the main usage paths.
- Improved generation errors for missing models with hints to use `--list`.
- Added optional `system_prompt` support in config, environment, CLI, and generation flow.
- Added `create_config` as the preferred public configuration constructor.
- Removed separate `create_local_config` and `create_cloud_config` helpers in favor of `create_config(cloud=True)`.
- Kept `create_ollama_config` as a backward-compatible alias.
- Added CLI support for piped `stdin`, including combined instruction plus input flows.
- Restricted interactive `OLLAMA_API_KEY` prompting to the CLI, while keeping library code deterministic.
