# AGENTS.md

This file provides instructions for AI coding agents working on the standalone `olliq` module.

The goal of this directory is to evolve `olliq.py` into a reusable Python module that provides a clean bridge to Ollama for both local and cloud execution.

The project was ideated by Gianni Amato.

## Project Goal

Build a small, reusable Python module that:

1. Loads Ollama configuration from JSON
2. Supports both local and cloud Ollama execution
3. Uses the native Python `ollama.Client`
4. Handles API key lookup for cloud mode
5. Exposes a minimal programmatic API
6. Exposes a minimal CLI entrypoint for standalone testing

The module exists to simplify and standardize the use of the official Ollama Python client, not to replace it or mirror its full surface area.

The module must stay generic and must not depend on any Obsidian, RAG, FAISS, OCR, or project-specific logic.

## Design Constraints

- Keep the module focused only on Ollama integration
- Do not embed retrieval, prompt orchestration, or note-processing logic
- Keep local/cloud switching explicit and easy to understand
- Prefer clarity and maintainability over abstraction
- Keep the public API small and stable
- Keep configuration, core generation logic, and CLI responsibilities separated

## Expected Responsibilities

The module may handle:

- config loading
- local/cloud URL resolution
- cloud API key handling
- Ollama client construction
- chat generation
- chat streaming
- optional system prompt handling
- minimal standalone testing through `python -m`

The module must not handle:

- document retrieval
- prompt building tied to a specific application
- source ranking
- file indexing
- OCR
- vector databases

## Coding Standards

- Follow PEP 8
- Use small functions with a single responsibility
- Use descriptive names
- Add docstrings to public functions and classes
- Write comments only in English
- Validate external input
- Raise clear exceptions
- Avoid unnecessary dependencies and prefer lazy imports when a dependency is optional for installation

## Packaging Direction

This directory should be easy to turn into a standalone distributable package.

Preferred future additions:

- `pyproject.toml`
- `README.md`
- `tests/`
- package layout if needed

## Configuration

The module should support a `config.json` structure like:

```json
{
  "ollama": {
    "model": "qwen3:latest",
    "cloud": false,
    "url": "http://localhost:11434",
    "temperature": 0.2
  }
}
```

Rules:

- if `cloud` is `true`, use `https://ollama.com`
- if `cloud` is `true`, use `OLLAMA_API_KEY` from the environment or ask for it interactively
- if `cloud` is `false`, use `url` from config or default to `http://localhost:11434`
- the CLI should look for `config.json` in the current directory by default and ask for `--config` if it is missing and no overrides were provided

## Summary

`olliq` is a standalone Ollama integration layer.

Its purpose is to make local/cloud Ollama usage simpler, more consistent, and more reusable from other Python projects while keeping the client surface small.

## API Naming Notes

- Prefer `create_config` as the primary public constructor name
- Prefer `generate(prompt, config, stream=False)` as the primary public generation entrypoint
- Keep backward-compatible aliases only when they reduce migration friction
- Keep the CLI thin; prefer improving API behavior and errors over adding many flags
- Prefer refactors that reduce internal coupling without expanding the public surface
