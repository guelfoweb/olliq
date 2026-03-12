# olliq

`olliq` is a small Python package for local and cloud Ollama.

It is meant to solve a narrow problem well:
- load configuration from code, environment variables, or `config.json`
- switch cleanly between local and cloud execution
- build the official Python `ollama.Client`
- generate text or stream responses
- expose a small CLI for quick manual use when needed

It does not handle retrieval, indexing, OCR, vector stores, or application-specific orchestration.

The primary goal of the project is Python reuse:

- import `olliq` from other projects
- keep local/cloud switching explicit
- avoid repeating Ollama setup code across applications

## Prerequisites

`olliq` is a thin integration layer around Ollama. It does not provide models
or a backend by itself.

To get real responses, you must have:

- a reachable local Ollama server, or access to Ollama Cloud
- a valid model name available in the target environment
- a valid `OLLAMA_API_KEY` when using cloud mode

In local mode, the default server URL is `http://localhost:11434`.

## Install

Install from PyPI with `pip`:

```bash
pip install olliq
```

Install from PyPI with `pipx`:

```bash
pipx install olliq
```

Install from a local checkout:

```bash
pip install .
```

Install directly from GitHub:

```bash
pip install git+https://github.com/guelfoweb/olliq.git
```

Install the CLI from a local checkout with isolated environment:

```bash
pipx install .
```

CLI install directly from GitHub:

```bash
pipx install git+https://github.com/guelfoweb/olliq.git
```

## Mental Model

There are three main Python usage paths:

1. Use explicit Python config with `create_config(...)`.
2. Load configuration from environment variables or `config.json` with `load_config(...)`.
3. Combine explicit overrides, environment, and `config.json` with `resolve_config(...)`.

The main package API is:

```python
generate(prompt, config, stream=False)
```

Recommended import style:

```python
from olliq import create_config, generate, load_config, resolve_config
```

## Configuration

Example `config.json`:

```json
{
  "ollama": {
    "model": "qwen3:latest",
    "cloud": false,
    "url": "http://localhost:11434",
    "temperature": 0.2,
    "system_prompt": "You are a concise assistant."
  }
}
```

Configuration order:

1. Explicit function arguments
2. Environment variables
3. `config.json`
4. Built-in defaults

Built-in defaults:

- local mode
- local URL: `http://localhost:11434`
- temperature: `0.2`

This means:

- `create_config(...)` uses local mode by default
- you only need `cloud=True` when you want Ollama Cloud

Supported environment variables:

- `OLLAMA_MODEL`
- `OLLAMA_CLOUD`
- `OLLAMA_URL`
- `OLLAMA_TEMPERATURE`
- `OLLAMA_SYSTEM_PROMPT`
- `OLLAMA_API_KEY`

Cloud behavior:

- when `cloud=True`, the host is always `https://ollama.com`
- when `cloud=True`, `OLLAMA_API_KEY` is required
- library code never prompts for `OLLAMA_API_KEY`
- the CLI can prompt for `OLLAMA_API_KEY` only in an interactive terminal

`load_config()` and `resolve_config()` differ slightly:

- `load_config(path)` reads environment variables and `config.json`
- `resolve_config(path, ...)` also applies explicit function arguments on top

## Python Usage

This is the main intended use of `olliq`.

### Recommended import

```python
from olliq import create_config, generate
```

### Local

```python
from olliq import create_config, generate

config = create_config(
    model="qwen3:latest",
    url="http://localhost:11434",
    temperature=0.2,
)

print(generate("Say hello.", config))
```

### Cloud

```python
from olliq import create_config, generate

config = create_config(
    model="gpt-oss:20b",
    cloud=True,
    temperature=0.2,
    system_prompt="You are a concise assistant.",
)

print(generate("Summarize this text.", config))
```

### Environment only

If you want to use only environment variables, do not provide a real `config.json`
or pass a path that does not exist:

```python
from olliq import generate, load_config

config = load_config("missing.json")
if config is None:
    raise RuntimeError("Missing configuration")

print(generate("Say hello.", config))
```

Example environment:

```bash
export OLLAMA_MODEL=qwen3:latest
export OLLAMA_CLOUD=false
export OLLAMA_URL=http://localhost:11434
export OLLAMA_TEMPERATURE=0.2
```

### Resolve from file, env, and explicit overrides

```python
from olliq import generate, resolve_config

config = resolve_config(
    "config.json",
    model="qwen3:latest",
    cloud=False,
)

if config is None:
    raise RuntimeError("Missing configuration")

print(generate("Say hello.", config))
```

### Stream

```python
from olliq import create_config, generate

config = create_config(model="qwen3:latest")

for chunk in generate("Tell me a story.", config, stream=True):
    print(chunk, end="", flush=True)
print()
```

### List models

```python
from olliq import create_config, list_models

config = create_config()
print(list_models(config))
```

## CLI Usage

The CLI is a convenience layer around the same package behavior.

### Basic local prompt

```bash
olliq --model qwen3:latest "Say hello"
```

### Cloud prompt

```bash
olliq --cloud --model gpt-oss:20b "Summarize this text"
```

### Stream output

```bash
olliq --stream --model qwen3:latest "Tell me a story"
```

### List models

```bash
olliq --list
```

### Use a config file explicitly

```bash
olliq --config /path/to/config.json "Say hello"
```

### Pipe stdin

```bash
cat filename.txt | olliq --model qwen3:latest "summarize"
```

If both a positional prompt and piped `stdin` are provided, the final prompt is:

```text
<prompt>

<stdin content>
```

## Public API

Preferred API:

- `create_config`
- `load_config`
- `resolve_config`
- `generate`
- `list_models`

Compatibility aliases:

- `create_ollama_config`
- `generate_prompt`
- `generate_stream`
- `generate_prompt_stream`

Exceptions:

- `ConfigError`
- `AuthError`
- `GenerationError`

Created by Gianni Amato.
