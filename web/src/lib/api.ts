import type { ContextResponse, InspectorState, PackResponse, WorldResponse } from "../types";

export const CONNECTORS = ["generic", "claude-code", "codex", "pi", "hermes", "openclaw"] as const;
export const INTENTS = ["auto", "chitchat", "task"] as const;

export type ConnectorId = (typeof CONNECTORS)[number];
export type InteractionIntent = (typeof INTENTS)[number];

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(
  path: string,
  apiKey: string,
  init: RequestInit = {},
  requireKey = true,
): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  if (apiKey) {
    headers.set("X-API-Key", apiKey);
  }
  const response = await fetch(`/api${path}`, { ...init, headers });
  if (!response.ok) {
    if (response.status === 401) {
      throw new ApiError(401, "Invalid or missing API key.");
    }
    const body = await response.json().catch(() => null);
    throw new ApiError(response.status, body?.detail || response.statusText);
  }
  if (!requireKey && response.headers.get("content-type")?.includes("application/json")) {
    return response.json() as Promise<T>;
  }
  return response.json() as Promise<T>;
}

export function getHealth(): Promise<{ status: string }> {
  return request<{ status: string }>("/health", "", {}, false);
}

export function listWorlds(apiKey: string): Promise<WorldResponse[]> {
  return request<WorldResponse[]>("/worlds", apiKey);
}

export function listPacks(apiKey: string): Promise<PackResponse[]> {
  return request<PackResponse[]>("/packs", apiKey);
}

export function getInspectorState(apiKey: string, worldId: string): Promise<InspectorState> {
  return request<InspectorState>(`/inspector/worlds/${worldId}/state`, apiKey);
}

export function buildContext(
  apiKey: string,
  payload: {
    world_id: string;
    user_message: string;
    connector_id: ConnectorId;
    interaction_intent: InteractionIntent;
    session_id?: string;
  },
): Promise<ContextResponse> {
  return request<ContextResponse>("/runtime/context", apiKey, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
