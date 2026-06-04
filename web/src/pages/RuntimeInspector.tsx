import { Play, RotateCcw } from "lucide-react";
import { useEffect, useState } from "react";

import { EmptyState, ErrorState, LoadingState } from "../components/DataState";
import { JsonBlock } from "../components/JsonBlock";
import { StatusBadge } from "../components/StatusBadge";
import { buildContext, CONNECTORS, type ConnectorId, INTENTS, type InteractionIntent, listWorlds } from "../lib/api";
import { formatMillis } from "../lib/format";
import { loadContextRuns, saveContextRun } from "../lib/storage";
import type { ContextResponse, ContextRun, WorldResponse } from "../types";

export function RuntimeInspector({ apiKey }: { apiKey: string }) {
  const [worlds, setWorlds] = useState<WorldResponse[]>([]);
  const [worldId, setWorldId] = useState("");
  const [connectorId, setConnectorId] = useState<ConnectorId>("claude-code");
  const [intent, setIntent] = useState<InteractionIntent>("auto");
  const [message, setMessage] = useState("今天有点累，想聊一下。");
  const [runs, setRuns] = useState<ContextRun[]>(() => loadContextRuns());
  const [result, setResult] = useState<ContextResponse | null>(null);
  const [loadingWorlds, setLoadingWorlds] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoadingWorlds(true);
    setError(null);
    try {
      const nextWorlds = await listWorlds(apiKey);
      setWorlds(nextWorlds);
      setWorldId((current) => current || nextWorlds[0]?.world_id || "");
    } catch (event) {
      setError(event instanceof Error ? event.message : "Unable to load worlds.");
    } finally {
      setLoadingWorlds(false);
    }
  }

  useEffect(() => {
    void load();
  }, [apiKey]);

  async function runContext() {
    if (!worldId || !message.trim()) {
      setError("Choose a world and enter a message.");
      return;
    }
    setRunning(true);
    setError(null);
    try {
      const response = await buildContext(apiKey, {
        world_id: worldId,
        user_message: message,
        connector_id: connectorId,
        interaction_intent: intent,
      });
      setResult(response);
      const run: ContextRun = {
        id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
        createdAt: Date.now(),
        worldId,
        connectorId,
        message,
        injected: response.injected,
        resolvedIntent: response.resolved_intent,
        blockCount: response.blocks.length,
        systemLength: response.system.length,
        reason: response.intent_reason,
      };
      setRuns(saveContextRun(run));
    } catch (event) {
      setError(event instanceof Error ? event.message : "Unable to build context.");
    } finally {
      setRunning(false);
    }
  }

  if (loadingWorlds) {
    return <LoadingState title="Loading inspector" />;
  }

  return (
    <div className="page-stack">
      <section className="page-header">
        <div>
          <p className="eyebrow">Connector Context</p>
          <h1>Runtime Inspector</h1>
        </div>
        <button className="button button--secondary" type="button" onClick={() => setResult(null)}>
          <RotateCcw size={16} aria-hidden="true" />
          Clear
        </button>
      </section>

      {error ? <ErrorState title="Inspector error" detail={error} action={load} /> : null}
      {worlds.length === 0 ? <EmptyState title="No worlds available" /> : null}

      <section className="inspector-grid">
        <form className="panel form-panel" onSubmit={(event) => event.preventDefault()}>
          <label>
            <span>World</span>
            <select value={worldId} onChange={(event) => setWorldId(event.target.value)}>
              {worlds.map((world) => (
                <option value={world.world_id} key={world.world_id}>
                  {world.display_name}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Connector</span>
            <select value={connectorId} onChange={(event) => setConnectorId(event.target.value as ConnectorId)}>
              {CONNECTORS.map((connector) => (
                <option value={connector} key={connector}>
                  {connector}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Intent</span>
            <select value={intent} onChange={(event) => setIntent(event.target.value as InteractionIntent)}>
              {INTENTS.map((item) => (
                <option value={item} key={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>
          <label className="form-panel__message">
            <span>User message</span>
            <textarea value={message} onChange={(event) => setMessage(event.target.value)} rows={7} />
          </label>
          <button className="button" type="button" onClick={runContext} disabled={running}>
            <Play size={16} aria-hidden="true" />
            {running ? "Running" : "Run Context"}
          </button>
        </form>

        <section className="page-stack">
          <section className="panel">
            <div className="panel__header">
              <h2>Decision</h2>
              {result ? (
                <StatusBadge
                  label={result.injected ? "injected" : "skipped"}
                  tone={result.injected ? "success" : "warning"}
                />
              ) : null}
            </div>
            {result ? (
              <dl className="kv-list">
                <div>
                  <dt>Intent</dt>
                  <dd>{result.resolved_intent}</dd>
                </div>
                <div>
                  <dt>Classifier</dt>
                  <dd>{result.intent_classifier}</dd>
                </div>
                <div>
                  <dt>Reason</dt>
                  <dd>{result.intent_reason || "none"}</dd>
                </div>
              </dl>
            ) : (
              <EmptyState title="No run yet" />
            )}
          </section>
          {result ? (
            <>
              <section className="panel table-wrap">
                <div className="panel__header">
                  <h2>Blocks</h2>
                  <span>{result.blocks.length}</span>
                </div>
                <table>
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Tag</th>
                      <th>Length</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.blocks.map((block) => (
                      <tr key={block.id}>
                        <td>{block.id}</td>
                        <td>{block.tag || "none"}</td>
                        <td>{block.content_length}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </section>
              <JsonBlock title="Final system preview" value={result.system} />
            </>
          ) : null}
        </section>
      </section>

      <section className="panel">
        <div className="panel__header">
          <h2>Recent Local Runs</h2>
          <span>{runs.length}</span>
        </div>
        <div className="run-list">
          {runs.slice(0, 8).map((run) => (
            <article className="run-item" key={run.id}>
              <div>
                <strong>{run.connectorId}</strong>
                <p>{run.message}</p>
              </div>
              <div className="run-item__meta">
                <StatusBadge
                  label={run.injected ? "injected" : "skipped"}
                  tone={run.injected ? "success" : "warning"}
                />
                <span>{run.resolvedIntent}</span>
                <span>{formatMillis(run.createdAt)}</span>
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
