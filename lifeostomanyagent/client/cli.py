from __future__ import annotations

import json
import uuid
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from lifeostomanyagent.client.sdk import ClientConfig, ConfigStore, LifeOSClient
from lifeostomanyagent.domain.models import WorldResponse

app = typer.Typer(no_args_is_help=True, help="LifeOS client CLI")
connector_app = typer.Typer(no_args_is_help=True, help="Install LifeOS connectors")
app.add_typer(connector_app, name="connector")
console = Console()


def _client() -> LifeOSClient:
    config = ConfigStore().load()
    return LifeOSClient(config)


def _world_id(explicit: str | None) -> str:
    config = ConfigStore().load()
    world_id = explicit or config.default_world_id
    if not world_id:
        raise typer.BadParameter("missing world id; pass --world or run `lifeos world create` and `lifeos login --world-id ...`")
    return world_id


def _select_world(
    worlds: list[WorldResponse],
    *,
    world_id: str | None,
    pack_id: str | None,
    display_name: str | None,
) -> WorldResponse:
    if not any([world_id, pack_id, display_name]):
        raise typer.BadParameter("pass --world-id, --pack, or --name")

    matches = worlds
    if world_id:
        matches = [world for world in matches if world.world_id == world_id]
    if pack_id:
        matches = [world for world in matches if world.pack_id == pack_id]
    if display_name:
        matches = [world for world in matches if world.display_name == display_name]

    if not matches:
        raise typer.BadParameter("matched 0 worlds; run `lifeos world-list` to inspect available worlds")
    if len(matches) > 1:
        rendered = ", ".join(f"{world.display_name}({world.pack_id}:{world.world_id})" for world in matches)
        raise typer.BadParameter(f"matched {len(matches)} worlds; add --world-id or --name. matches: {rendered}")
    return matches[0]


def _resolve_world_for_command(
    client: LifeOSClient,
    config: ClientConfig,
    *,
    world_id: str | None,
    pack_id: str | None,
    display_name: str | None,
) -> str:
    if pack_id or display_name:
        worlds = client.list_worlds()
        return _select_world(worlds, world_id=world_id, pack_id=pack_id, display_name=display_name).world_id
    return world_id or _world_id(None)


@app.command("login")
def login(
    server: str = typer.Option("http://127.0.0.1:8000", "--server"),
    api_key: str = typer.Option("dev-lifeos-key-change-me", "--api-key"),
    world_id: str | None = typer.Option(None, "--world-id"),
) -> None:
    store = ConfigStore()
    config = ClientConfig(server_url=server, api_key=api_key, default_world_id=world_id)
    store.save(config)
    with LifeOSClient(config) as client:
        health = client.health()
    console.print(f"[green]已连接[/green] {server} status={health['status']}")


@app.command("world-create")
def world_create(
    pack_id: str = typer.Option("alice", "--pack"),
    name: str = typer.Option("我的 Alice", "--name"),
    set_default: bool = typer.Option(True, "--set-default/--no-set-default"),
) -> None:
    with _client() as client:
        client.install_alice_preset()
        world = client.create_world(pack_id, name)
    if set_default:
        store = ConfigStore()
        config = store.load()
        config.default_world_id = world.world_id
        store.save(config)
    console.print(json.dumps(world.model_dump(), ensure_ascii=False, indent=2))


@app.command("world-list")
def world_list() -> None:
    config = ConfigStore().load()
    with LifeOSClient(config) as client:
        worlds = client.list_worlds()

    if not worlds:
        console.print("[yellow]暂无 world[/yellow]")
        return

    default_world_id = config.default_world_id
    for world in worlds:
        marker = "*" if world.world_id == default_world_id else " "
        console.print(f"{marker} {world.world_id}  pack={world.pack_id}  name={world.display_name}")


@app.command("world-use")
def world_use(
    world_id: str | None = typer.Option(None, "--world-id", help="Exact world_id to set as default"),
    pack_id: str | None = typer.Option(None, "--pack", help="Select the only world for this pack_id"),
    name: str | None = typer.Option(None, "--name", help="Select by world display_name"),
) -> None:
    store = ConfigStore()
    config = store.load()
    with LifeOSClient(config) as client:
        worlds = client.list_worlds()

    world = _select_world(worlds, world_id=world_id, pack_id=pack_id, display_name=name)
    previous_world_id = config.default_world_id
    config.default_world_id = world.world_id
    store.save(config)

    console.print(
        json.dumps(
            {
                "previous_world_id": previous_world_id,
                "default_world_id": world.world_id,
                "pack_id": world.pack_id,
                "display_name": world.display_name,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


@app.command("context")
def context_pull(
    message: str = typer.Argument(...),
    world: str | None = typer.Option(None, "--world"),
    connector: str = typer.Option("generic", "--connector"),
    session_id: str | None = typer.Option(None, "--session-id"),
    output_format: str = typer.Option("text", "--format", help="text|json|blocks"),
) -> None:
    world_id = _world_id(world)
    with _client() as client:
        result = client.pull_context(
            world_id=world_id,
            message=message,
            connector_id=connector,
            session_id=session_id,
        )
    if output_format == "json":
        console.print_json(result.model_dump_json())
        return
    if output_format == "blocks":
        console.print(f"[bold]world_id[/bold]: {result.world_id}")
        console.print(f"[bold]connector[/bold]: {result.connector_id}")
        console.print(f"[bold]总长度[/bold]: {len(result.system)} 字符\n")
        for i, (block_id, block) in enumerate(zip(result.order, result.blocks), 1):
            tag = block.tag or "-"
            console.print(f"  {i}. {block_id:22s} tag={tag:18s} len={block.content_length}")
        console.print()
        console.print(Panel(result.system, title=f"LifeOS context ({connector})", border_style="cyan"))
        return
    console.print(Panel(result.system, title=f"LifeOS context ({connector})", border_style="cyan"))


@app.command("session-start")
def session_start(
    connector: str = typer.Option(..., "--connector"),
    session_id: str | None = typer.Option(None, "--session-id"),
    world: str | None = typer.Option(None, "--world"),
) -> None:
    world_id = _world_id(world)
    sid = session_id or str(uuid.uuid4())
    with _client() as client:
        result = client.session_start(world_id=world_id, connector_id=connector, session_id=sid)
    console.print(json.dumps({"session_id": sid, **result}, ensure_ascii=False))


@app.command("session-end")
def session_end(
    connector: str = typer.Option(..., "--connector"),
    session_id: str = typer.Option(..., "--session-id"),
    world: str | None = typer.Option(None, "--world"),
    meaningful: bool = typer.Option(True, "--meaningful/--not-meaningful"),
) -> None:
    world_id = _world_id(world)
    with _client() as client:
        result = client.session_end(
            world_id=world_id,
            connector_id=connector,
            session_id=session_id,
            meaningful=meaningful,
        )
    console.print(json.dumps(result, ensure_ascii=False))


@app.command("dream-run")
def dream_run(
    world: str | None = typer.Option(None, "--world", "--world-id", help="Exact world_id to generate dreams for"),
    pack_id: str | None = typer.Option(None, "--pack", help="Select the only world for this pack_id"),
    name: str | None = typer.Option(None, "--name", help="Select by world display_name"),
    dream_date: str | None = typer.Option(None, "--date", help="Generate this local date, e.g. 2026-06-02"),
    force: bool = typer.Option(False, "--force", help="Regenerate even if the dream already exists"),
) -> None:
    config = ConfigStore().load()
    with LifeOSClient(config) as client:
        world_id = _resolve_world_for_command(client, config, world_id=world, pack_id=pack_id, display_name=name)
        result = client.dream_run(world_id=world_id, dream_date=dream_date, force=force)
    console.print(json.dumps(result, ensure_ascii=False, indent=2))


@app.command("dream-show")
def dream_show(
    world: str | None = typer.Option(None, "--world", "--world-id", help="Exact world_id to inspect"),
    pack_id: str | None = typer.Option(None, "--pack", help="Select the only world for this pack_id"),
    name: str | None = typer.Option(None, "--name", help="Select by world display_name"),
) -> None:
    config = ConfigStore().load()
    with LifeOSClient(config) as client:
        world_id = _resolve_world_for_command(client, config, world_id=world, pack_id=pack_id, display_name=name)
        result = client.dream_latest(world_id=world_id)
    console.print(json.dumps(result, ensure_ascii=False, indent=2))


@connector_app.command("install")
def connector_install(
    name: str = typer.Argument(..., help="pi | claude-code | codex | hermes | openclaw"),
    symlink: bool = typer.Option(False, "--symlink", help="Symlink hook/extension instead of copy (dev)"),
    extensions_dir: str | None = typer.Option(None, "--extensions-dir"),
    claude_settings: str | None = typer.Option(None, "--claude-settings", help="Claude Code settings.json path"),
    codex_home: str | None = typer.Option(None, "--codex-home", help="Codex home (default ~/.codex)"),
    hermes_plugins_dir: str | None = typer.Option(None, "--hermes-plugins-dir", help="Hermes plugins dir (default ~/.hermes/plugins)"),
    openclaw_extensions_dir: str | None = typer.Option(
        None, "--openclaw-extensions-dir", help="OpenClaw extensions dir (default ~/.openclaw/extensions)"
    ),
) -> None:
    if name in {"pi"}:
        from lifeostomanyagent.connectors.pi import install_pi_extension

        target = Path(extensions_dir) if extensions_dir else None
        dest = install_pi_extension(target_dir=target, symlink=symlink)
        console.print(f"[green]已安装 pi Extension[/green] → {dest}")
        console.print("下一步：lifeos login && lifeos world-create，然后直接运行 pi")
        return

    if name in {"claude-code", "claude_code", "claude"}:
        from lifeostomanyagent.connectors.claude_code import install_claude_code_hooks

        settings = Path(claude_settings) if claude_settings else None
        result = install_claude_code_hooks(settings_path=settings, symlink=symlink)
        console.print(f"[green]已安装 Claude Code hooks[/green]")
        console.print(f"  settings: {result.settings_path}")
        console.print(f"  hook:     {result.hook_script}")
        console.print("下一步：lifeos login && lifeos world-create，然后启动 claude")
        return

    if name == "codex":
        from lifeostomanyagent.connectors.codex import install_codex_hooks

        home = Path(codex_home) if codex_home else None
        result = install_codex_hooks(codex_home=home, symlink=symlink)
        console.print(f"[green]已安装 Codex hooks[/green]")
        console.print(f"  hooks.json:  {result.hooks_path}")
        console.print(f"  config.toml: {result.config_path}")
        console.print(f"  hook:        {result.hook_script}")
        console.print("下一步：lifeos login && lifeos world-create，然后启动 codex")
        return

    if name == "hermes":
        from lifeostomanyagent.connectors.hermes import install_hermes_plugin

        plugins_dir = Path(hermes_plugins_dir) if hermes_plugins_dir else None
        result = install_hermes_plugin(plugins_dir=plugins_dir, symlink=symlink)
        console.print(f"[green]已安装 Hermes plugin[/green]")
        console.print(f"  plugin: {result.plugin_dir}")
        console.print("下一步：lifeos login && lifeos world-create，然后启动 hermes")
        return

    if name == "openclaw":
        from lifeostomanyagent.connectors.openclaw import install_openclaw_plugin

        ext_dir = Path(openclaw_extensions_dir) if openclaw_extensions_dir else None
        result = install_openclaw_plugin(extensions_dir=ext_dir, symlink=symlink)
        console.print(f"[green]已安装 OpenClaw plugin[/green]")
        console.print(f"  plugin: {result.plugin_dir}")
        console.print("下一步：lifeos login && lifeos world-create")
        console.print("        openclaw plugins enable lifeos")
        console.print("        openclaw gateway restart   # 或重启 Gateway")
        return

    raise typer.BadParameter(f"unsupported connector: {name} (try: pi, claude-code, codex, hermes, openclaw)")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
