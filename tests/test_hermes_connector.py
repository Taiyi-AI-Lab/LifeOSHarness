from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

from lifeostomanyagent.connectors.hermes import (
    HERMES_PLUGIN_SOURCE,
    install_hermes_plugin,
)


def _load_lifeos_client():
    module_path = HERMES_PLUGIN_SOURCE / "lifeos_client.py"
    spec = importlib.util.spec_from_file_location("hermes_lifeos_client", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_register(*, client_module=None):
    plugin_dir = HERMES_PLUGIN_SOURCE
    pkg_name = "lifeos_hermes_plugin"
    client = client_module or _load_lifeos_client()
    sys.modules[f"{pkg_name}.lifeos_client"] = client
    sys.modules.pop(pkg_name, None)
    init_path = plugin_dir / "__init__.py"
    spec = importlib.util.spec_from_file_location(
        pkg_name,
        init_path,
        submodule_search_locations=[str(plugin_dir)],
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[pkg_name] = module
    spec.loader.exec_module(module)
    return module


def test_hermes_plugin_source_has_required_files():
    assert (HERMES_PLUGIN_SOURCE / "plugin.yaml").exists()
    assert (HERMES_PLUGIN_SOURCE / "__init__.py").exists()
    assert (HERMES_PLUGIN_SOURCE / "lifeos_client.py").exists()
    manifest = (HERMES_PLUGIN_SOURCE / "plugin.yaml").read_text("utf-8")
    assert "pre_llm_call" in manifest
    assert "on_session_start" in manifest


def test_install_hermes_plugin_copies_files(tmp_path: Path):
    plugins_dir = tmp_path / "plugins"
    result = install_hermes_plugin(plugins_dir=plugins_dir, symlink=False)
    assert result.plugin_dir == plugins_dir / "lifeos"
    assert (result.plugin_dir / "plugin.yaml").exists()
    assert (result.plugin_dir / "__init__.py").exists()
    assert (result.plugin_dir / "lifeos_client.py").exists()


def test_install_hermes_plugin_symlink(tmp_path: Path):
    plugins_dir = tmp_path / "plugins"
    result = install_hermes_plugin(plugins_dir=plugins_dir, symlink=True)
    assert result.plugin_dir.is_symlink()
    assert result.plugin_dir.resolve() == HERMES_PLUGIN_SOURCE.resolve()


def test_register_wires_all_hooks():
    plugin = _load_register()
    ctx = MagicMock()
    plugin.register(ctx)
    events = [call.args[0] for call in ctx.register_hook.call_args_list]
    assert events == [
        "pre_llm_call",
        "on_session_start",
        "post_llm_call",
        "on_session_end",
    ]


def test_pre_llm_call_returns_context(tmp_path: Path, monkeypatch):
    client = _load_lifeos_client()
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "server_url": "http://127.0.0.1:8000",
                "api_key": "test-key",
                "default_world_id": "world-1",
            }
        ),
        "utf-8",
    )
    monkeypatch.setattr(client, "CONFIG_PATH", config_path)

    calls: list[tuple[str, dict]] = []

    def fake_api_post(config, path, body):
        calls.append((path, body))
        if path == "/runtime/context":
            return {"system": "陈远 context block", "injected": True}
        return {}

    monkeypatch.setattr(client, "api_post", fake_api_post)

    plugin = _load_register(client_module=client)
    result = plugin._pre_llm_call("sess-1", "你好", model="test")
    assert result == {"context": "陈远 context block"}
    assert calls[0][0] == "/runtime/context"
    assert calls[0][1]["user_message"] == "你好"
    assert calls[0][1]["connector_id"] == "hermes"
    assert calls[1][0] == "/runtime/turn/begin"


def test_pre_llm_call_does_not_begin_turn_when_context_not_injected(tmp_path: Path, monkeypatch):
    client = _load_lifeos_client()
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "server_url": "http://127.0.0.1:8000",
                "api_key": "test-key",
                "default_world_id": "world-1",
            }
        ),
        "utf-8",
    )
    monkeypatch.setattr(client, "CONFIG_PATH", config_path)

    calls: list[tuple[str, dict]] = []

    def fake_api_post(config, path, body):
        calls.append((path, body))
        if path == "/runtime/context":
            return {"system": "", "injected": False}
        return {}

    monkeypatch.setattr(client, "api_post", fake_api_post)

    plugin = _load_register(client_module=client)
    result = plugin._pre_llm_call("sess-1", "帮我修 pytest", model="test")
    plugin._post_llm_call("sess-1")

    assert result is None
    assert [call[0] for call in calls] == ["/runtime/context"]


def test_pre_llm_call_without_config_returns_none(tmp_path: Path, monkeypatch):
    client = _load_lifeos_client()
    config_path = tmp_path / "config.json"
    config_path.write_text("{}", "utf-8")
    monkeypatch.setattr(client, "CONFIG_PATH", config_path)

    plugin = _load_register(client_module=client)
    assert plugin._pre_llm_call("sess-1", "hello") is None
