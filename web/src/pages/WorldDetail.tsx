import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { EmptyState, ErrorState, LoadingState } from "../components/DataState";
import { JsonBlock } from "../components/JsonBlock";
import { StatusBadge } from "../components/StatusBadge";
import { getInspectorState } from "../lib/api";
import { countByStatus, formatMillis } from "../lib/format";
import type { InspectorState } from "../types";

const tabs = ["Profile", "Persona", "Emotion", "Memory", "Dreams", "World Facts", "Context Preview"];

export function WorldDetail({ apiKey }: { apiKey: string }) {
  const { worldId } = useParams();
  const [state, setState] = useState<InspectorState | null>(null);
  const [activeTab, setActiveTab] = useState(tabs[0]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    if (!worldId) {
      setError("Missing world id.");
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setState(await getInspectorState(apiKey, worldId));
    } catch (event) {
      setError(event instanceof Error ? event.message : "Unable to load world state.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, [apiKey, worldId]);

  const factStatus = useMemo(
    () => countByStatus(state?.world_facts.all ?? []),
    [state?.world_facts.all],
  );

  if (loading) {
    return <LoadingState title="Loading world detail" />;
  }

  if (error) {
    return <ErrorState title="World unavailable" detail={error} action={load} />;
  }

  if (!state) {
    return <EmptyState title="No world state" />;
  }

  return (
    <div className="page-stack">
      <section className="page-header">
        <div>
          <p className="eyebrow">World Detail</p>
          <h1>{state.world.display_name}</h1>
        </div>
        <Link className="button button--secondary" to="/inspector">
          Test Context
        </Link>
      </section>

      <section className="metric-grid">
        <MiniMetric label="Memories" value={state.memories.length} />
        <MiniMetric label="Dreams" value={state.dreams.dreams.length} />
        <MiniMetric label="Facts" value={state.world_facts.all.length} />
        <MiniMetric label="Active facts" value={factStatus.active || 0} />
      </section>

      <nav className="tab-list" aria-label="World sections">
        {tabs.map((tab) => (
          <button
            key={tab}
            type="button"
            className={activeTab === tab ? "is-active" : ""}
            onClick={() => setActiveTab(tab)}
          >
            {tab}
          </button>
        ))}
      </nav>

      {activeTab === "Profile" ? (
        <section className="panel detail-grid">
          <div>
            <h2>World</h2>
            <dl className="kv-list">
              <div>
                <dt>World ID</dt>
                <dd className="mono">{state.world.world_id}</dd>
              </div>
              <div>
                <dt>Pack</dt>
                <dd>{state.world.pack_id}</dd>
              </div>
              <div>
                <dt>Agent</dt>
                <dd>{state.pack.config.identity?.agent_name || state.pack.display_name}</dd>
              </div>
            </dl>
          </div>
          <JsonBlock title="Pack config" value={state.pack.config} />
        </section>
      ) : null}

      {activeTab === "Persona" ? <JsonBlock title="Persona document" value={state.persona} /> : null}
      {activeTab === "Emotion" ? <JsonBlock title="Emotion document" value={state.emotion} /> : null}
      {activeTab === "Memory" ? <MemoryTable state={state} /> : null}
      {activeTab === "Dreams" ? <JsonBlock title="Dream state" value={state.dreams} /> : null}
      {activeTab === "World Facts" ? <FactsTable state={state} /> : null}
      {activeTab === "Context Preview" ? (
        <JsonBlock
          title="Context preview source data"
          value={{
            persona: state.persona,
            emotion: state.emotion,
            memories: state.memories.slice(0, 8),
            activeFacts: state.world_facts.active.slice(0, 8),
          }}
        />
      ) : null}
    </div>
  );
}

function MiniMetric({ label, value }: { label: string; value: number }) {
  return (
    <article className="metric-card metric-card--compact">
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

function MemoryTable({ state }: { state: InspectorState }) {
  if (!state.memories.length) {
    return <EmptyState title="No memories yet" />;
  }
  return (
    <section className="panel table-wrap">
      <table>
        <thead>
          <tr>
            <th>Type</th>
            <th>Content</th>
            <th>Status</th>
            <th>Activated</th>
            <th>Updated</th>
          </tr>
        </thead>
        <tbody>
          {state.memories.map((memory) => (
            <tr key={memory.id}>
              <td>{memory.type}</td>
              <td>{memory.content}</td>
              <td>
                <StatusBadge label={memory.status} tone={memory.status === "active" ? "success" : "neutral"} />
              </td>
              <td>{memory.activationCount}</td>
              <td>{formatMillis(memory.updatedAt)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function FactsTable({ state }: { state: InspectorState }) {
  if (!state.world_facts.all.length) {
    return <EmptyState title="No world facts yet" />;
  }
  return (
    <section className="panel table-wrap">
      <table>
        <thead>
          <tr>
            <th>Subject</th>
            <th>Category</th>
            <th>Status</th>
            <th>Condition</th>
            <th>Updated</th>
          </tr>
        </thead>
        <tbody>
          {state.world_facts.all.map((fact) => (
            <tr key={fact.id}>
              <td>{fact.subject}</td>
              <td>{fact.category}</td>
              <td>
                <StatusBadge label={fact.status} tone={fact.status === "active" ? "success" : "warning"} />
              </td>
              <td>{fact.condition}</td>
              <td>{formatMillis(fact.updatedAt)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
