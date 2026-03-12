import os
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import olliq
import olliq.cli
from olliq import AuthError, ConfigError, GenerationError, OllamaConfig


ENV_KEYS = {
    "OLLAMA_MODEL": "",
    "OLLAMA_CLOUD": "",
    "OLLAMA_URL": "",
    "OLLAMA_TEMPERATURE": "",
    "OLLAMA_SYSTEM_PROMPT": "",
    "OLLAMA_API_KEY": "",
}


class FakeClient:
    def __init__(self, host, headers=None):
        self.host = host
        self.headers = headers
        self.chat_calls = []

    def chat(self, **kwargs):
        self.chat_calls.append(kwargs)
        return {"message": {"content": "hello back"}}

    def list(self):
        return {
            "models": [
                {"model": "qwen3:latest"},
                {"model": "gpt-oss:20b"},
                {"model": "llama3.2:cloud"},
            ]
        }


class FakeStreamClient(FakeClient):
    def chat(self, **kwargs):
        self.chat_calls.append(kwargs)
        if kwargs["stream"]:
            return iter(
                [
                    {"message": {"content": "hello "}},
                    {"message": {"content": "stream"}},
                ]
            )
        return {"message": {"content": "hello stream"}}


class FailingModelClient(FakeClient):
    def chat(self, **kwargs):
        raise RuntimeError(f"model '{kwargs['model']}' not found")


class OlliqTests(unittest.TestCase):
    def make_config(self, **overrides) -> OllamaConfig:
        config = {
            "model": "qwen3:latest",
            "url": olliq.DEFAULT_LOCAL_OLLAMA_URL,
            "cloud": False,
            "temperature": olliq.DEFAULT_TEMPERATURE,
            "system_prompt": None,
        }
        config.update(overrides)
        return OllamaConfig(**config)

    def make_temp_config(self, content: str) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        config_path = Path(temp_dir.name) / "config.json"
        config_path.write_text(content, encoding="utf-8")
        return config_path

    def test_load_config_from_nested_section(self):
        config_path = self.make_temp_config(
            """
            {
              "ollama": {
                "model": "qwen3:latest",
                "cloud": false,
                "url": "http://127.0.0.1:11434",
                "temperature": 0.4,
                "system_prompt": "Be concise."
              }
            }
            """
        )

        with patch.dict(os.environ, ENV_KEYS, clear=True):
            config = olliq.load_config(config_path)

        self.assertEqual(config.model, "qwen3:latest")
        self.assertEqual(config.url, "http://127.0.0.1:11434")
        self.assertFalse(config.cloud)
        self.assertEqual(config.temperature, 0.4)
        self.assertEqual(config.system_prompt, "Be concise.")

    def test_load_config_uses_cloud_defaults(self):
        config_path = self.make_temp_config(
            """
            {
              "ollama": {
                "model": "llama3.2",
                "cloud": true
              }
            }
            """
        )

        with patch.dict(os.environ, ENV_KEYS, clear=True):
            config = olliq.load_config(config_path)

        self.assertEqual(config.url, olliq.DEFAULT_CLOUD_OLLAMA_URL)
        self.assertTrue(config.cloud)

    def test_load_config_uses_default_local_url(self):
        config_path = self.make_temp_config(
            """
            {
              "model": "qwen3:latest",
              "cloud": false
            }
            """
        )

        with patch.dict(os.environ, ENV_KEYS, clear=True):
            config = olliq.load_config(config_path)

        self.assertEqual(config.url, olliq.DEFAULT_LOCAL_OLLAMA_URL)

    def test_load_config_can_use_environment_only(self):
        with patch.dict(
            os.environ,
            ENV_KEYS | {
                "OLLAMA_MODEL": "qwen3:latest",
                "OLLAMA_CLOUD": "false",
                "OLLAMA_URL": "http://localhost:33445",
                "OLLAMA_TEMPERATURE": "0.6",
                "OLLAMA_SYSTEM_PROMPT": "Answer briefly.",
            },
            clear=True,
        ):
            config = olliq.load_config("missing.json")

        self.assertIsNotNone(config)
        self.assertEqual(config.model, "qwen3:latest")
        self.assertEqual(config.url, "http://localhost:33445")
        self.assertFalse(config.cloud)
        self.assertEqual(config.temperature, 0.6)
        self.assertEqual(config.system_prompt, "Answer briefly.")

    def test_environment_overrides_json_values(self):
        config_path = self.make_temp_config(
            """
            {
              "ollama": {
                "model": "json-model",
                "cloud": false,
                "url": "http://json-host:11434",
                "temperature": 0.2,
                "system_prompt": "From json."
              }
            }
            """
        )

        with patch.dict(
            os.environ,
            ENV_KEYS | {
                "OLLAMA_MODEL": "env-model",
                "OLLAMA_CLOUD": "true",
                "OLLAMA_URL": "http://ignored-in-cloud.example",
                "OLLAMA_TEMPERATURE": "0.9",
                "OLLAMA_SYSTEM_PROMPT": "From env.",
            },
            clear=True,
        ):
            config = olliq.load_config(config_path)

        self.assertEqual(config.model, "env-model")
        self.assertTrue(config.cloud)
        self.assertEqual(config.url, olliq.DEFAULT_CLOUD_OLLAMA_URL)
        self.assertEqual(config.temperature, 0.9)
        self.assertEqual(config.system_prompt, "From env.")

    def test_missing_model_returns_none_when_no_sources_exist(self):
        with patch.dict(os.environ, ENV_KEYS, clear=True):
            config = olliq.load_config("missing.json")

        self.assertIsNone(config)

    def test_create_config_accepts_explicit_parameters(self):
        config = olliq.create_config(
            model="qwen3:latest",
            cloud=False,
            url="http://localhost:22434",
            temperature=0.7,
            system_prompt="Be precise.",
        )

        self.assertEqual(config.model, "qwen3:latest")
        self.assertEqual(config.url, "http://localhost:22434")
        self.assertFalse(config.cloud)
        self.assertEqual(config.temperature, 0.7)
        self.assertEqual(config.system_prompt, "Be precise.")

    def test_create_ollama_config_remains_an_alias(self):
        config = olliq.create_ollama_config(
            model="qwen3:latest",
            cloud=False,
            url="http://localhost:22434",
            temperature=0.7,
            system_prompt="Be precise.",
        )

        self.assertEqual(config.model, "qwen3:latest")
        self.assertEqual(config.url, "http://localhost:22434")
        self.assertFalse(config.cloud)
        self.assertEqual(config.temperature, 0.7)
        self.assertEqual(config.system_prompt, "Be precise.")

    def test_build_client_uses_api_key_for_cloud(self):
        config = self.make_config(url=olliq.DEFAULT_CLOUD_OLLAMA_URL, cloud=True)

        with patch("olliq._core._import_ollama_client", return_value=FakeClient):
            with patch.dict(os.environ, ENV_KEYS | {"OLLAMA_API_KEY": "secret"}, clear=True):
                client = olliq._core.build_client(config)

        self.assertEqual(client.host, olliq.DEFAULT_CLOUD_OLLAMA_URL)
        self.assertEqual(client.headers, {"Authorization": "Bearer secret"})

    def test_build_client_fails_without_api_key_in_cloud_mode(self):
        config = self.make_config(url=olliq.DEFAULT_CLOUD_OLLAMA_URL, cloud=True)

        with patch("olliq._core._import_ollama_client", return_value=FakeClient):
            with patch.dict(os.environ, ENV_KEYS, clear=True):
                with self.assertRaises(AuthError):
                    olliq._core.build_client(config)

    def test_generate_uses_client_chat(self):
        config = self.make_config()
        client = FakeClient(host=config.url)

        response = olliq.generate("Hello", config, client=client)

        self.assertEqual(response, "hello back")
        self.assertEqual(client.chat_calls[0]["model"], "qwen3:latest")
        self.assertEqual(
            client.chat_calls[0]["messages"],
            [{"role": "user", "content": "Hello"}],
        )

    def test_generate_prepends_system_prompt_when_configured(self):
        config = self.make_config(system_prompt="Be concise.")
        client = FakeClient(host=config.url)

        response = olliq.generate("Hello", config, client=client)

        self.assertEqual(response, "hello back")
        self.assertEqual(
            client.chat_calls[0]["messages"],
            [
                {"role": "system", "content": "Be concise."},
                {"role": "user", "content": "Hello"},
            ],
        )

    def test_generate_prompt_rejects_empty_prompt(self):
        config = self.make_config()

        with self.assertRaises(ConfigError):
            olliq.generate_prompt("   ", config, client=FakeClient(host=config.url))

    def test_generate_rejects_invalid_messages(self):
        config = self.make_config()

        with self.assertRaises(ConfigError):
            olliq.generate("   ", config, client=FakeClient(host=config.url))

    def test_generate_stream_yields_response_chunks(self):
        config = self.make_config()

        chunks = list(
            olliq.generate("Hello", config, client=FakeStreamClient(host=config.url), stream=True)
        )

        self.assertEqual(chunks, ["hello ", "stream"])

    def test_generate_prompt_stream_yields_response_chunks(self):
        config = self.make_config()

        chunks = list(
            olliq.generate_prompt_stream(
                "Hello",
                config,
                client=FakeStreamClient(host=config.url),
            )
        )

        self.assertEqual(chunks, ["hello ", "stream"])

    def test_generate_stream_alias_still_accepts_message_lists(self):
        config = self.make_config()

        chunks = list(
            olliq.generate_stream(
                [{"role": "user", "content": "Hello"}],
                config,
                client=FakeStreamClient(host=config.url),
            )
        )

        self.assertEqual(chunks, ["hello ", "stream"])

    def test_list_models_returns_model_names(self):
        config = self.make_config(model=None)

        models = olliq.list_models(config, client=FakeClient(host=config.url))

        self.assertEqual(models, ["qwen3:latest", "gpt-oss:20b", "llama3.2:cloud"])

    def test_list_models_returns_cloud_host_listing_without_name_filter(self):
        config = self.make_config(model=None, url=olliq.DEFAULT_CLOUD_OLLAMA_URL, cloud=True)

        models = olliq.list_models(config, client=FakeClient(host=config.url))

        self.assertEqual(models, ["qwen3:latest", "gpt-oss:20b", "llama3.2:cloud"])

    def test_main_supports_cloud_override_for_list(self):
        fake_client = FakeClient(host=olliq.DEFAULT_CLOUD_OLLAMA_URL)

        with patch("olliq.cli.build_client", return_value=fake_client):
            with patch("builtins.print") as mock_print:
                exit_code = olliq.cli.main(["--cloud", "--list"])

        self.assertEqual(exit_code, 0)
        printed_lines = [call.args[0] for call in mock_print.call_args_list]
        self.assertEqual(printed_lines, ["qwen3:latest", "gpt-oss:20b", "llama3.2:cloud"])

    def test_main_supports_model_override_for_prompt(self):
        fake_client = FakeClient(host=olliq.DEFAULT_LOCAL_OLLAMA_URL)

        with patch("olliq.cli.build_client", return_value=fake_client):
            with patch("builtins.print") as mock_print:
                exit_code = olliq.cli.main(["--model=gpt-oss:20b", "Hello"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(fake_client.chat_calls[0]["model"], "gpt-oss:20b")
        self.assertEqual(mock_print.call_args_list[-1].args[0], "hello back")

    def test_main_prompts_for_api_key_in_cloud_mode(self):
        fake_client = FakeClient(host=olliq.DEFAULT_CLOUD_OLLAMA_URL)

        with patch("olliq.cli.build_client", return_value=fake_client) as build_client_mock:
            with patch.dict(os.environ, ENV_KEYS, clear=True):
                with patch("sys.stdin.isatty", return_value=True):
                    with patch("getpass.getpass", return_value="prompt-secret"):
                        with patch("builtins.print"):
                            exit_code = olliq.cli.main(["--cloud", "--model=gpt-oss:20b", "Hello"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(build_client_mock.call_args.kwargs["api_key"], "prompt-secret")

    def test_main_supports_system_prompt_override(self):
        fake_client = FakeClient(host=olliq.DEFAULT_LOCAL_OLLAMA_URL)

        with patch("olliq.cli.build_client", return_value=fake_client):
            with patch("builtins.print"):
                exit_code = olliq.cli.main(
                    ["--model=gpt-oss:20b", "--system-prompt=Be concise.", "Hello"]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            fake_client.chat_calls[0]["messages"],
            [
                {"role": "system", "content": "Be concise."},
                {"role": "user", "content": "Hello"},
            ],
        )

    def test_generate_reports_model_not_found_with_hint(self):
        config = OllamaConfig(
            model="missing-model",
            url=olliq.DEFAULT_LOCAL_OLLAMA_URL,
            cloud=False,
        )

        with self.assertRaises(GenerationError) as exc:
            olliq.generate("Hello", config, client=FailingModelClient(host=config.url))

        self.assertIn("Use --list to inspect available models", str(exc.exception))

    def test_main_uses_stdin_when_no_prompt_argument_is_provided(self):
        fake_client = FakeClient(host=olliq.DEFAULT_LOCAL_OLLAMA_URL)

        with patch("olliq.cli.build_client", return_value=fake_client):
            with patch("sys.stdin", io.StringIO("Summarize this text")):
                with patch("builtins.print"):
                    exit_code = olliq.cli.main(["--model=qwen3:latest"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            fake_client.chat_calls[0]["messages"],
            [{"role": "user", "content": "Summarize this text"}],
        )

    def test_main_combines_prompt_argument_and_stdin(self):
        fake_client = FakeClient(host=olliq.DEFAULT_LOCAL_OLLAMA_URL)

        with patch("olliq.cli.build_client", return_value=fake_client):
            with patch("sys.stdin", io.StringIO("Line one\nLine two")):
                with patch("builtins.print"):
                    exit_code = olliq.cli.main(["--model=qwen3:latest", "summarize"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            fake_client.chat_calls[0]["messages"],
            [{"role": "user", "content": "summarize\n\nLine one\nLine two"}],
        )

    def test_main_help_uses_package_name(self):
        with patch("sys.stdout", new_callable=io.StringIO):
            with self.assertRaises(SystemExit) as exc:
                olliq.cli.main(["--help"])

        self.assertEqual(exc.exception.code, 0)

    def test_main_requires_config_path_when_default_config_is_missing(self):
        with patch("sys.stderr", new_callable=io.StringIO) as stderr:
            with patch("pathlib.Path.exists", return_value=False):
                with patch.dict(os.environ, ENV_KEYS, clear=True):
                    exit_code = olliq.cli.main(["Hello"])

        self.assertEqual(exit_code, 1)
        self.assertIn("Specify it with --config", stderr.getvalue())
        self.assertIn("environment variables", stderr.getvalue())

    def test_main_uses_environment_when_default_config_is_missing(self):
        fake_client = FakeClient(host=olliq.DEFAULT_LOCAL_OLLAMA_URL)

        with patch("olliq.cli.build_client", return_value=fake_client):
            with patch("pathlib.Path.exists", return_value=False):
                with patch.dict(
                    os.environ,
                    ENV_KEYS | {"OLLAMA_MODEL": "qwen3:latest", "OLLAMA_CLOUD": "false"},
                    clear=True,
                ):
                    with patch("builtins.print"):
                        exit_code = olliq.cli.main(["Hello"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(fake_client.chat_calls[0]["model"], "qwen3:latest")

    def test_main_supports_stream_output(self):
        fake_client = FakeStreamClient(host=olliq.DEFAULT_LOCAL_OLLAMA_URL)

        with patch("olliq.cli.build_client", return_value=fake_client):
            with patch("builtins.print") as mock_print:
                exit_code = olliq.cli.main(["--stream", "--model=qwen3:latest", "Hello"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(fake_client.chat_calls[0]["stream"], True)
        printed = ["".join(str(arg) for arg in call.args) for call in mock_print.call_args_list]
        self.assertEqual(printed, ["hello ", "stream", ""])

    def test_resolve_config_prefers_explicit_overrides(self):
        config_path = self.make_temp_config(
            """
            {
              "ollama": {
                "model": "json-model",
                "cloud": false,
                "url": "http://json-host:11434",
                "temperature": 0.2,
                "system_prompt": "From json."
              }
            }
            """
        )

        with patch.dict(
            os.environ,
            ENV_KEYS | {
                "OLLAMA_MODEL": "env-model",
                "OLLAMA_CLOUD": "false",
                "OLLAMA_URL": "http://env-host:11434",
                "OLLAMA_TEMPERATURE": "0.5",
                "OLLAMA_SYSTEM_PROMPT": "From env.",
            },
            clear=True,
        ):
            config = olliq.resolve_config(
                config_path,
                model="explicit-model",
                cloud=True,
                temperature=0.9,
                system_prompt="From explicit.",
            )

        self.assertEqual(config.model, "explicit-model")
        self.assertTrue(config.cloud)
        self.assertEqual(config.url, olliq.DEFAULT_CLOUD_OLLAMA_URL)
        self.assertEqual(config.temperature, 0.9)
        self.assertEqual(config.system_prompt, "From explicit.")


if __name__ == "__main__":
    unittest.main()
