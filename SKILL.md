---
name: olliq
description: Use this skill when working on the olliq Python package, its CLI, packaging, tests, README, or GitHub/PyPI release workflow. This skill is for changes to local/cloud Ollama integration, configuration handling, public API behavior, and project maintenance for the olliq repository.
---

# olliq

Use this skill for work inside the `olliq` repository and for integrating
`olliq` into other Python projects.

`olliq` is a small Python package that provides a thin integration layer around
the official Python `ollama.Client`. The main goal is Python reuse from other
projects, with a small CLI kept only as a convenience layer.

When this skill is used outside the `olliq` repository, the default assumption
should be: prefer importing `olliq` from application code instead of re-creating
Ollama setup logic manually.

## Project shape

- Package code lives in `olliq/`.
- Tests live in `tests/test_olliq.py`.
- Packaging metadata lives in `pyproject.toml`.
- User-facing documentation lives in `README.md`.
- CI and PyPI publishing workflows live in `.github/workflows/`.

Read these files first when the task touches them:

- `README.md` for public usage and documented behavior
- `pyproject.toml` for package metadata and console script
- `tests/test_olliq.py` for expected behavior
- `olliq/cli.py` for CLI behavior
- `olliq/_config.py` for config loading and resolution
- `olliq/_core.py` for client construction, generation, streaming, and model listing

## Working rules

- Keep the package minimal and explicit.
- Prefer readability over clever abstractions.
- Preserve the main public API unless the task explicitly changes it.
- Keep local/cloud switching easy to understand.
- Do not add application-specific logic such as retrieval, indexing, OCR, or RAG.
- Keep all project text in English.

## What `olliq` is for

Use `olliq` when a project needs one or more of these:

- a small reusable bridge around the official Python `ollama.Client`
- consistent local/cloud switching
- configuration from code, environment variables, or `config.json`
- a single place to resolve model, host, temperature, and cloud auth

Do not use `olliq` as a general LLM framework. It is intentionally narrow.

## Public API expectations

The primary public API is intentionally small:

- `create_config(...)`
- `load_config(...)`
- `resolve_config(...)`
- `generate(...)`
- `list_models(...)`

Compatibility aliases may exist, but avoid expanding the public surface unless
there is a clear migration need.

## How to integrate `olliq` in another project

Prefer `from olliq import ...` imports from the public package root.

Use these patterns:

- `create_config(...)` for explicit in-code setup
- `load_config(...)` for environment-driven or `config.json`-driven setup
- `resolve_config(...)` when explicit overrides must win over env or file config
- `generate(...)` as the main text generation entrypoint
- `list_models(...)` when the caller needs the available models for the selected target

Use these minimal examples when wiring `olliq` into another project.

Explicit local setup:

```python
from olliq import create_config, generate

config = create_config(
    model="qwen3:latest",
    url="http://localhost:11434",
)

response = generate("Say hello.", config)
```

Explicit cloud setup:

```python
from olliq import create_config, generate

config = create_config(
    model="gpt-oss:20b",
    cloud=True,
)

response = generate("Summarize this text.", config)
```

Environment or file-driven setup:

```python
from olliq import load_config, generate

config = load_config()
if config is None:
    raise RuntimeError("Missing Ollama configuration.")

response = generate("Say hello.", config)
```

Mixed setup with explicit overrides:

```python
from olliq import resolve_config, generate

config = resolve_config(
    "config.json",
    model="qwen3:latest",
    cloud=False,
)
if config is None:
    raise RuntimeError("Missing Ollama configuration.")

response = generate("Say hello.", config)
```

Model listing:

```python
from olliq import create_config, list_models

config = create_config(cloud=True, model="gpt-oss:20b")
models = list_models(config)
```

## API choice guide

Choose the simplest correct entrypoint:

- Use `create_config(...)` when the caller already knows the model, mode, and optional URL.
- Use `load_config(...)` when the project should rely on environment variables or `config.json`.
- Use `resolve_config(...)` when code-level overrides must be merged on top of env or file values.

Avoid bypassing `olliq` internals from other projects:

- do not import `olliq._config`
- do not import `olliq._core`
- do not import `olliq.cli`

Stick to the public package exports unless you are changing `olliq` itself.

## What not to do

- Do not rebuild Ollama setup logic manually if `olliq` can already express it.
- Do not import private modules from application code.
- Do not add RAG, retrieval, indexing, OCR, note-processing, or vector-store logic to `olliq`.
- Do not put interactive prompting in reusable library code.
- Do not assume local and cloud expose the same models.
- Do not assume installing `olliq` is enough to get real responses.
- Do not change public behavior without updating tests and `README.md`.
- Do not widen the public API unless there is a clear maintenance or migration reason.
- Do not bypass `create_config`, `load_config`, or `resolve_config` unless the task is specifically about `olliq` internals.

## Quick integration checklist

When integrating `olliq` into another project, verify these points:

1. `olliq` is installed in the target environment.
2. The project imports only from the public package root.
3. The selected config path matches the application style:
   - explicit code config
   - environment or `config.json`
   - mixed config with explicit overrides
4. The chosen model exists in the actual target environment.
5. The local Ollama server or Ollama Cloud endpoint is reachable.
6. `OLLAMA_API_KEY` is available for cloud mode.

If any of these are missing, expect runtime failure and state that clearly.

## Runtime model

Do not assume the package alone can produce real responses.

- Local mode requires a reachable Ollama server, usually `http://localhost:11434`.
- Cloud mode requires `OLLAMA_API_KEY`.
- The requested model must exist in the target environment.

Library code should stay deterministic. Interactive prompting belongs in the
CLI, not in the reusable core.

When integrating into another project, document these constraints explicitly for
the caller instead of assuming they are obvious.

## CLI notes

The CLI is secondary to the Python API. Treat it as a convenience layer.

Important CLI behavior:

- `--cloud` enables cloud mode for that command
- `--list` lists models for the configured target
- `--model`, `--url`, `--temperature`, and `--system-prompt` act as CLI overrides
- `--config` points to `config.json`
- stdin can be combined with a positional prompt

Cloud CLI behavior:

- cloud mode uses `https://ollama.com`
- cloud mode requires `OLLAMA_API_KEY`
- the CLI may prompt for `OLLAMA_API_KEY` only in an interactive terminal

Do not move that interactive behavior into the core library.

## Common failure modes

When `olliq` fails, check these first:

- missing `OLLAMA_MODEL`
- missing `OLLAMA_API_KEY` in cloud mode
- local Ollama server not running or not reachable
- invalid `config.json`
- model not available in the selected local/cloud target
- tests relying on local environment values instead of explicit test setup

When fixing tests, prefer mocking explicit inputs over depending on the current shell environment.

## Change workflow

1. Inspect the relevant code and tests before editing.
2. Keep responsibilities separated:
   - `_config.py` for configuration parsing and resolution
   - `_core.py` for client and generation behavior
   - `cli.py` for user interaction and command-line behavior
3. Update tests whenever behavior changes.
4. Update `README.md` when the public behavior, install flow, or examples change.
5. Keep GitHub Actions and PyPI workflow aligned with current packaging.

## Preferred implementation style

- Keep functions small and single-purpose.
- Separate configuration logic from runtime logic and from CLI interaction.
- Prefer explicit argument passing over hidden behavior.
- Prefer deterministic library behavior.
- Keep examples short and copyable.
- Match documented behavior in `README.md`, tests, and package exports.

## Validation

Run the smallest useful validation set after changes:

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile olliq/__init__.py olliq/__main__.py olliq/_config.py olliq/_core.py olliq/_exceptions.py olliq/cli.py
```

When packaging changes:

```bash
python3 -m build
python3 -m twine check dist/*
```

If `python3 -m build` is unavailable in the current environment, note that
explicitly instead of pretending packaging was verified.

## Git and release notes

- The GitHub repository is `https://github.com/guelfoweb/olliq`.
- The published package is `https://pypi.org/project/olliq/`.
- CI should stay green on `main`.
- PyPI publishing is handled by GitHub Actions via Trusted Publishing.

If you change workflows, verify both CI behavior and release behavior remain
consistent with the package metadata.
