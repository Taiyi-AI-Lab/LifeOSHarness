from __future__ import annotations

import pytest
import typer

from lifeostomanyagent.client.cli import _select_world
from lifeostomanyagent.domain.models import WorldResponse


def _world(world_id: str, pack_id: str, display_name: str) -> WorldResponse:
    return WorldResponse(world_id=world_id, pack_id=pack_id, display_name=display_name)


def test_select_world_by_id():
    worlds = [
        _world("chenyuan-world", "chenyuan", "我的陈远"),
        _world("musheng-world", "musheng", "木生"),
    ]

    selected = _select_world(worlds, world_id="musheng-world", pack_id=None, display_name=None)

    assert selected.world_id == "musheng-world"


def test_select_world_by_unique_pack():
    worlds = [
        _world("chenyuan-world", "chenyuan", "我的陈远"),
        _world("musheng-world", "musheng", "木生"),
    ]

    selected = _select_world(worlds, world_id=None, pack_id="musheng", display_name=None)

    assert selected.world_id == "musheng-world"


def test_select_world_by_pack_and_name():
    worlds = [
        _world("chenyuan-1", "chenyuan", "我的陈远"),
        _world("chenyuan-2", "chenyuan", "测试陈远"),
    ]

    selected = _select_world(worlds, world_id=None, pack_id="chenyuan", display_name="测试陈远")

    assert selected.world_id == "chenyuan-2"


def test_select_world_rejects_ambiguous_pack():
    worlds = [
        _world("chenyuan-1", "chenyuan", "我的陈远"),
        _world("chenyuan-2", "chenyuan", "测试陈远"),
    ]

    with pytest.raises(typer.BadParameter, match="matched 2 worlds"):
        _select_world(worlds, world_id=None, pack_id="chenyuan", display_name=None)


def test_select_world_requires_filter():
    with pytest.raises(typer.BadParameter, match="pass --world-id"):
        _select_world([], world_id=None, pack_id=None, display_name=None)


def test_select_world_for_dream_commands_by_pack():
    worlds = [
        _world("chenyuan-world", "chenyuan", "我的陈远"),
        _world("musheng-world", "musheng", "木生"),
    ]

    selected = _select_world(worlds, world_id=None, pack_id="musheng", display_name=None)

    assert selected.world_id == "musheng-world"


def test_select_world_for_dream_commands_by_world_id():
    worlds = [
        _world("chenyuan-world", "chenyuan", "我的陈远"),
        _world("musheng-world", "musheng", "木生"),
    ]

    selected = _select_world(worlds, world_id="chenyuan-world", pack_id=None, display_name=None)

    assert selected.pack_id == "chenyuan"
