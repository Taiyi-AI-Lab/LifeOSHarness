/**
 * LifeOS pi Extension
 *
 * Injects LifeOS world context (persona / emotion / memory / world rules) before each
 * agent turn via before_agent_start, calling the LifeOS server /runtime/context API.
 *
 * Config: ~/.lifeos/config.json (same as `lifeos login` / `lifeos world-create`)
 *   { "server_url", "api_key", "default_world_id" }
 *
 * Env overrides: LIFEOS_SERVER_URL, LIFEOS_API_KEY, LIFEOS_WORLD_ID, LIFEOS_ENABLED
 */

import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const CONNECTOR_ID = "pi";

interface LifeOSConfig {
	serverUrl: string;
	apiKey: string;
	worldId: string;
	enabled: boolean;
	mergeMode: "prepend" | "append";
}

interface ContextResponse {
	system: string;
}

function loadConfig(): LifeOSConfig | null {
	const enabled = (process.env.LIFEOS_ENABLED ?? "true").toLowerCase() !== "false";
	if (!enabled) {
		return null;
	}

	let fileConfig: Partial<{ server_url: string; api_key: string; default_world_id: string; merge_mode: string }> =
		{};
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
	const apiKey = process.env.LIFEOS_API_KEY ?? fileConfig.api_key ?? "dev-lifeos-key-change-me";
	const worldId = process.env.LIFEOS_WORLD_ID ?? fileConfig.default_world_id ?? "";
	const mergeMode = (process.env.LIFEOS_MERGE_MODE ?? fileConfig.merge_mode ?? "prepend") as "prepend" | "append";

	if (!worldId) {
		return null;
	}

	return { serverUrl, apiKey, worldId, enabled: true, mergeMode };
}

async function lifeosPost<T>(config: LifeOSConfig, path: string, body: Record<string, unknown>): Promise<T | null> {
	try {
		const response = await fetch(`${config.serverUrl}${path}`, {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
				"X-API-Key": config.apiKey,
			},
			body: JSON.stringify(body),
		});
		if (!response.ok) {
			return null;
		}
		return (await response.json()) as T;
	} catch {
		return null;
	}
}

function mergePrompt(base: string, lifeosBlock: string, mode: "prepend" | "append"): string {
	if (mode === "append") {
		return `${base}\n\n${lifeosBlock}`;
	}
	return `${lifeosBlock}\n\n---\n\n${base}`;
}

export default function lifeosExtension(pi: ExtensionAPI) {
	const startedSessions = new Set<string>();

	pi.registerCommand("lifeos", {
		description: "Show LifeOS connector status (/lifeos)",
		handler: async (_args, ctx) => {
			const config = loadConfig();
			if (!config) {
				ctx.ui.notify(
					"LifeOS 未配置：运行 lifeos login && lifeos world-create，或设置 LIFEOS_WORLD_ID",
					"warning",
				);
				return;
			}
			const health = await fetch(`${config.serverUrl}/health`);
			const ok = health.ok;
			ctx.ui.notify(
				ok
					? `LifeOS 已连接 world=${config.worldId.slice(0, 8)}… merge=${config.mergeMode}`
					: `LifeOS 服务不可达: ${config.serverUrl}`,
				ok ? "info" : "error",
			);
		},
	});

	pi.on("before_agent_start", async (event, ctx) => {
		const config = loadConfig();
		if (!config) {
			return undefined;
		}

		const sessionId = ctx.sessionManager.getSessionId();
		if (!startedSessions.has(sessionId)) {
			await lifeosPost(config, "/runtime/session/start", {
				world_id: config.worldId,
				connector_id: CONNECTOR_ID,
				session_id: sessionId,
			});
			startedSessions.add(sessionId);
		}

		await lifeosPost(config, "/runtime/turn/begin", {
			world_id: config.worldId,
			connector_id: CONNECTOR_ID,
			session_id: sessionId,
		});

		const context = await lifeosPost<ContextResponse>(config, "/runtime/context", {
			world_id: config.worldId,
			user_message: event.prompt,
			connector_id: CONNECTOR_ID,
			session_id: sessionId,
		});

		if (!context?.system) {
			if (ctx.hasUI) {
				ctx.ui.notify("LifeOS context 拉取失败，使用 pi 默认 system prompt", "warning");
			}
			return undefined;
		}

		return {
			systemPrompt: mergePrompt(event.systemPrompt, context.system, config.mergeMode),
		};
	});

	pi.on("agent_end", async (_event, ctx) => {
		const config = loadConfig();
		if (!config) {
			return;
		}
		const sessionId = ctx.sessionManager.getSessionId();
		await lifeosPost(config, "/runtime/turn/finish", {
			world_id: config.worldId,
			connector_id: CONNECTOR_ID,
			session_id: sessionId,
			meaningful: true,
		});
	});

	pi.on("session_shutdown", async (_event, ctx) => {
		const config = loadConfig();
		if (!config) {
			return;
		}
		const sessionId = ctx.sessionManager.getSessionId();
		await lifeosPost(config, "/runtime/session/end", {
			world_id: config.worldId,
			connector_id: CONNECTOR_ID,
			session_id: sessionId,
			meaningful: true,
		});
		startedSessions.delete(sessionId);
	});
}
