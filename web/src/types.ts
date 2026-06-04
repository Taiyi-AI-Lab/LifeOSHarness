export type RuntimeModules = {
  persona: boolean;
  emotion: boolean;
  memory: boolean;
  world_facts: boolean;
  proactive: boolean;
  dreams: boolean;
};

export type AgentPackConfig = {
  pack_id: string;
  display_name: string;
  identity?: {
    agent_name: string;
    codename?: string | null;
    identity_code?: string | null;
    backstory: string;
    relationship_stance: string;
    core_values: string[];
  } | null;
  behavior_profile: Record<string, unknown>;
  behavior_trajectory: Record<string, unknown>;
  world_rules: Record<string, unknown>;
  runtime_modules: RuntimeModules;
  is_preset: boolean;
  base_system_prompt?: string | null;
};

export type PackResponse = {
  pack_id: string;
  display_name: string;
  is_preset: boolean;
  config: AgentPackConfig;
};

export type WorldResponse = {
  world_id: string;
  pack_id: string;
  display_name: string;
  overrides: Record<string, unknown>;
};

export type ContextBlockTrace = {
  id: string;
  tag: string | null;
  content_length: number;
};

export type ContextResponse = {
  world_id: string;
  connector_id: string;
  system: string;
  order: string[];
  blocks: ContextBlockTrace[];
  resolved_intent: "chitchat" | "task";
  injected: boolean;
  intent_classifier: string;
  intent_reason: string;
};

export type MemoryEntry = {
  id: string;
  type: string;
  content: string;
  status: string;
  createdAt: number;
  updatedAt: number;
  lastActivatedAt: number | null;
  activationCount: number;
  metadata: Record<string, unknown>;
};

export type WorldFact = {
  id: number;
  category: string;
  subject: string;
  description: string;
  status: string;
  condition: string;
  acquiredAt: number | null;
  acquiredVia: string | null;
  relatedMomentId: string | null;
  realWorldPrice: number | null;
  paidPrice: number | null;
  deliveryAt: number | null;
  expiresAt: number | null;
  metadata: Record<string, unknown>;
  createdAt: number;
  updatedAt: number;
};

export type FactEvent = {
  id: number;
  factId: number | null;
  eventType: string;
  subject: string;
  createdAt: number;
  metadata: Record<string, unknown>;
};

export type InspectorState = {
  world: WorldResponse;
  pack: PackResponse;
  persona: Record<string, unknown> | null;
  emotion: Record<string, unknown> | null;
  memories: MemoryEntry[];
  dreams: {
    seeds: Array<Record<string, unknown>>;
    dreams: Array<Record<string, unknown>>;
  };
  world_facts: {
    active: WorldFact[];
    all: WorldFact[];
    fact_events: FactEvent[];
    clock_events: Array<Record<string, unknown>>;
    venue_visits: Array<Record<string, unknown>>;
  };
};

export type ContextRun = {
  id: string;
  createdAt: number;
  worldId: string;
  connectorId: string;
  message: string;
  injected: boolean;
  resolvedIntent: string;
  blockCount: number;
  systemLength: number;
  reason: string;
};
