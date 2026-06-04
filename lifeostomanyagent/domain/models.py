from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class AgentIdentity(BaseModel):
    agent_name: str
    codename: str | None = None
    identity_code: str | None = None
    backstory: str = ""
    relationship_stance: str = ""
    core_values: list[str] = Field(default_factory=list)


class BehaviorProfile(BaseModel):
    speech_style: list[str] = Field(default_factory=list)
    forbidden_patterns: list[str] = Field(default_factory=list)
    emotion_rules: dict[str, Any] = Field(default_factory=dict)
    work_habits: list[str] = Field(default_factory=list)
    addressing_rules: list[str] = Field(default_factory=list)
    inner_voice_prompt: str | None = None


class BehaviorTrajectory(BaseModel):
    milestones: list[str] = Field(default_factory=list)
    proactive_style: str | None = None
    reaction_patterns: list[str] = Field(default_factory=list)


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
    dreams: bool = False


class AgentPackConfig(BaseModel):
    pack_id: str
    display_name: str
    identity: AgentIdentity | None = None
    behavior_profile: BehaviorProfile = Field(default_factory=BehaviorProfile)
    behavior_trajectory: BehaviorTrajectory = Field(default_factory=BehaviorTrajectory)
    world_rules: WorldRules = Field(default_factory=WorldRules)
    runtime_modules: RuntimeModules = Field(default_factory=RuntimeModules)
    is_preset: bool = False
    base_system_prompt: str | None = None  # legacy fallback during migration

    @model_validator(mode="after")
    def _require_identity_or_legacy_prompt(self) -> "AgentPackConfig":
        if self.identity is None and not (self.base_system_prompt or "").strip():
            raise ValueError("pack requires identity or base_system_prompt")
        return self


class WorldOverrides(BaseModel):
    display_name: str | None = None
    base_system_prompt_append: str | None = None


class ContextRequest(BaseModel):
    world_id: str
    user_message: str
    connector_id: str = "generic"
    session_id: str | None = None
    merge_mode: Literal["prepend", "replace", "append"] = "prepend"
    interaction_intent: Literal["auto", "chitchat", "task"] = "auto"
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
    resolved_intent: Literal["chitchat", "task"] = "chitchat"
    injected: bool = True
    intent_classifier: str = "rules"
    intent_reason: str = ""


class SessionEventRequest(BaseModel):
    world_id: str
    connector_id: str
    session_id: str
    meaningful: bool = True


class DreamRunRequest(BaseModel):
    world_id: str
    dream_date: str | None = None
    force: bool = False


class DreamRunResponse(BaseModel):
    world_id: str
    created: bool
    dream: dict[str, Any]


class DreamLatestResponse(BaseModel):
    world_id: str
    dream: dict[str, Any] | None = None


class PackCreateRequest(BaseModel):
    pack_id: str
    display_name: str
    identity: AgentIdentity | None = None
    behavior_profile: BehaviorProfile | None = None
    behavior_trajectory: BehaviorTrajectory | None = None
    world_rules: WorldRules | None = None
    runtime_modules: RuntimeModules | None = None
    base_system_prompt: str | None = None  # legacy

    @model_validator(mode="after")
    def _require_identity_or_legacy_prompt(self) -> "PackCreateRequest":
        if self.identity is None and not (self.base_system_prompt or "").strip():
            raise ValueError("pack requires identity or base_system_prompt")
        return self


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
