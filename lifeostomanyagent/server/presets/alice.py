from __future__ import annotations

from pathlib import Path

from lifeostomanyagent.config import repo_root


def alice_system_prompt_path() -> Path:
    return (
        repo_root()
        / "003-life-os"
        / "bws_fuxian"
        / "alicetrace"
        / "system-prompt.md"
    )


def load_alice_system_prompt() -> str:
    path = alice_system_prompt_path()
    if not path.exists():
        raise FileNotFoundError(f"Alice system prompt not found: {path}")
    return path.read_text("utf-8").strip()


def build_alice_pack_config() -> dict:
    from lifeostomanyagent.domain.models import AgentPackConfig, WorldRules

    prompt = load_alice_system_prompt()
    config = AgentPackConfig(
        pack_id="alice",
        display_name="Alice",
        base_system_prompt=prompt,
        world_rules=WorldRules(
            timezone="Asia/Shanghai",
            work_hours="08:00-24:00",
            locations=["珠海横琴", "澳门氹仔"],
            custom_facts=["身份编号 #76ACAD", "远程协作助理"],
        ),
        is_preset=True,
    )
    return config.model_dump()
