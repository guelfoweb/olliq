# Changelog

## Unreleased

- Made the `ollama` dependency optional in package metadata so `pip install .` can succeed even on environments where the official client is harder to install.
- Renamed the project package and CLI from `ollamabridge` to `olliq`.
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
- Kept `create_ollama_config` as a backward-compatible alias.
- Added CLI support for piped `stdin`, including combined instruction plus input flows.
- Added interactive `OLLAMA_API_KEY` prompting for cloud mode when running in a TTY.
