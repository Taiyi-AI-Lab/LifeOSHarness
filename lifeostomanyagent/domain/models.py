from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class BehaviorProfile(BaseModel):
    speech_style: list[str] = Field(default_factory=list)
    forbidden_patterns: list[str] = Field(default_factory=list)
    emotion_rules: dict[str, Any] = Field(default_factory=dict)


class WorldRules(BaseModel):
    timezone: str = "Asia/Shanghai"
    work_hours: str = "09:00-18:00"
    locations: list[str] = Field(default_factory=list)
    custom_facts: list[str] = Field(default_factory=list)


class RuntimeModules(BaseModel):
    persona: bool = True
    emotion: bool = True
    memory: bool = True
    world_facts: bool = True
    proactive: bool = True


class AgentPackConfig(BaseModel):
    pack_id: str
    display_name: str
    base_system_prompt: str
    world_rules: WorldRules = Field(default_factory=WorldRules)
    behavior_profile: BehaviorProfile = Field(default_factory=BehaviorProfile)
    runtime_modules: RuntimeModules = Field(default_factory=RuntimeModules)
    is_preset: bool = False


class WorldOverrides(BaseModel):
    display_name: str | None = None
    base_system_prompt_append: str | None = None


class ContextRequest(BaseModel):
    world_id: str
    user_message: str
    connector_id: str = "generic"
    session_id: str | None = None
    merge_mode: Literal["prepend", "replace", "append"] = "prepend"
    extra_blocks: list[str] = Field(default_factory=list)


class ContextBlockTrace(BaseModel):
    id: str
    tag: str | None
    content_length: int


class ContextResponse(BaseModel):
    world_id: str
    connector_id: str
    system: str
    order: list[str]
    blocks: list[ContextBlockTrace]


class SessionEventRequest(BaseModel):
    world_id: str
    connector_id: str
    session_id: str
    meaningful: bool = True


class PackCreateRequest(BaseModel):
    pack_id: str
    display_name: str
    base_system_prompt: str
    world_rules: WorldRules | None = None
    behavior_profile: BehaviorProfile | None = None
    runtime_modules: RuntimeModules | None = None


class WorldCreateRequest(BaseModel):
    pack_id: str
    display_name: str
    overrides: WorldOverrides | None = None


class WorldResponse(BaseModel):
    world_id: str
    pack_id: str
    display_name: str
    overrides: WorldOverrides = Field(default_factory=WorldOverrides)


class PackResponse(BaseModel):
    pack_id: str
    display_name: str
    is_preset: bool
    config: AgentPackConfig
