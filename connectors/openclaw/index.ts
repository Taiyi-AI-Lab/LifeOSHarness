/**
 * LifeOS OpenClaw plugin — inject Agent World context via before_prompt_build.
 *
 * Config: ~/.lifeos/config.json (lifeos login / world-create)
 * Env: LIFEOS_ENABLED, LIFEOS_SERVER_URL, LIFEOS_API_KEY, LIFEOS_WORLD_ID, LIFEOS_MERGE_MODE
 */

import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";

import {
	CONNECTOR_ID,
	fetchContext,
	lifeosPost,
	loadConfig,
	mergeSystemPrompt,
	resolveSessionId,
} from "./lifeos-client";

const startedSessions = new Set<string>();
const activeTurnSessions = new Set<string>();

export default definePluginEntry({
	id: "lifeos",
	name: "LifeOS",
	description:
		"Inject LifeOS Agent World context (persona, emotion, memory, world state) before each agent turn",
	register(api) {
		api.on("session_start", async (event, ctx) => {
			const config = loadConfig();
			if (!config) {
				return;
			}
			if (event.reason !== "new") {
				return;
			}
			const sessionId = resolveSessionId(ctx);
			if (startedSessions.has(sessionId)) {
				return;
			}
			await lifeosPost(config, "/runtime/session/start", {
				connector_id: CONNECTOR_ID,
				session_id: sessionId,
			});
			startedSessions.add(sessionId);
		});

		api.on(
			"before_prompt_build",
			async (event, ctx) => {
				const config = loadConfig();
				if (!config) {
					return;
				}

				const sessionId = resolveSessionId(ctx);
				if (!startedSessions.has(sessionId)) {
					await lifeosPost(config, "/runtime/session/start", {
						connector_id: CONNECTOR_ID,
						session_id: sessionId,
					});
					startedSessions.add(sessionId);
				}

				const block = await fetchContext(config, sessionId, event.prompt ?? "");
				if (!block) {
					return;
				}

				await lifeosPost(config, "/runtime/turn/begin", {
					connector_id: CONNECTOR_ID,
					session_id: sessionId,
				});
				activeTurnSessions.add(sessionId);

				const base = event.systemPrompt ?? "";
				return {
					systemPrompt: mergeSystemPrompt(base, block, config.mergeMode),
				};
			},
			{ priority: 10, timeoutMs: 30_000 },
		);

		api.on("agent_end", async (_event, ctx) => {
			const config = loadConfig();
			if (!config) {
				return;
			}
			const sessionId = resolveSessionId(ctx);
			if (!activeTurnSessions.has(sessionId)) {
				return;
			}
			await lifeosPost(config, "/runtime/turn/finish", {
				connector_id: CONNECTOR_ID,
				session_id: sessionId,
				meaningful: true,
			});
			activeTurnSessions.delete(sessionId);
		});

		api.on("session_end", async (_event, ctx) => {
			const config = loadConfig();
			if (!config) {
				return;
			}
			const sessionId = resolveSessionId(ctx);
			activeTurnSessions.delete(sessionId);
			await lifeosPost(config, "/runtime/session/end", {
				connector_id: CONNECTOR_ID,
				session_id: sessionId,
				meaningful: true,
			});
			startedSessions.delete(sessionId);
		});
	},
});
