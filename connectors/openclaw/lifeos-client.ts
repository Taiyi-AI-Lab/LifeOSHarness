/**
 * LifeOS API client for OpenClaw plugin (fetch + ~/.lifeos/config.json).
 */

import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

export const CONNECTOR_ID = "openclaw";

export interface LifeOSConfig {
	serverUrl: string;
	apiKey: string;
	worldId: string;
	mergeMode: "prepend" | "append";
}

export interface ContextResponse {
	system: string;
	injected?: boolean;
}

export function loadConfig(): LifeOSConfig | null {
	const enabled = (process.env.LIFEOS_ENABLED ?? "true").toLowerCase() !== "false";
	if (!enabled) {
		return null;
	}

	let fileConfig: Partial<{
		server_url: string;
		api_key: string;
		default_world_id: string;
		merge_mode: string;
	}> = {};
	try {
		const raw = readFileSync(join(homedir(), ".lifeos", "config.json"), "utf8");
		fileConfig = JSON.parse(raw) as typeof fileConfig;
	} catch {
		// optional file
	}

	const serverUrl = (process.env.LIFEOS_SERVER_URL ?? fileConfig.server_url ?? "http://127.0.0.1:8000").replace(
		/\/$/,
		"",
	);
	const apiKey = process.env.LIFEOS_API_KEY ?? fileConfig.api_key ?? "";
	const worldId = process.env.LIFEOS_WORLD_ID ?? fileConfig.default_world_id ?? "";
	const mergeMode = (process.env.LIFEOS_MERGE_MODE ?? fileConfig.merge_mode ?? "prepend") as "prepend" | "append";

	if (!apiKey || !worldId) {
		return null;
	}

	return { serverUrl, apiKey, worldId, mergeMode };
}

export async function lifeosPost<T>(
	config: LifeOSConfig,
	path: string,
	body: Record<string, unknown>,
): Promise<T | null> {
	try {
		const response = await fetch(`${config.serverUrl}${path}`, {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
				"X-API-Key": config.apiKey,
			},
			body: JSON.stringify({ ...body, world_id: config.worldId }),
		});
		if (!response.ok) {
			return null;
		}
		return (await response.json()) as T;
	} catch {
		return null;
	}
}

export function mergeSystemPrompt(base: string, lifeosBlock: string, mode: "prepend" | "append"): string {
	if (mode === "append") {
		return `${base}\n\n${lifeosBlock}`;
	}
	return `${lifeosBlock}\n\n---\n\n${base}`;
}

export async function fetchContext(
	config: LifeOSConfig,
	sessionId: string,
	userMessage: string,
): Promise<string | null> {
	const result = await lifeosPost<ContextResponse>(config, "/runtime/context", {
		connector_id: CONNECTOR_ID,
		session_id: sessionId,
		user_message: userMessage,
	});
	if (!result?.injected || !result.system) {
		return null;
	}
	return result.system;
}

export function resolveSessionId(ctx: { sessionId?: string; sessionKey?: string }): string {
	return ctx.sessionId ?? ctx.sessionKey ?? "unknown";
}
