import { Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { EmptyState, ErrorState, LoadingState } from "../components/DataState";
import { JsonBlock } from "../components/JsonBlock";
import { StatusBadge } from "../components/StatusBadge";
import { listPacks } from "../lib/api";
import type { PackResponse } from "../types";

export function Packs({ apiKey }: { apiKey: string }) {
  const [packs, setPacks] = useState<PackResponse[]>([]);
  const [selected, setSelected] = useState<PackResponse | null>(null);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const next = await listPacks(apiKey);
      setPacks(next);
      setSelected((current) => current ?? next[0] ?? null);
    } catch (event) {
      setError(event instanceof Error ? event.message : "Unable to load packs.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, [apiKey]);

  const filtered = useMemo(() => {
    const term = query.trim().toLowerCase();
    if (!term) {
      return packs;
    }
    return packs.filter((pack) =>
      [pack.pack_id, pack.display_name, pack.config.identity?.agent_name || ""].some((value) =>
        value.toLowerCase().includes(term),
      ),
    );
  }, [packs, query]);

  if (loading) {
    return <LoadingState title="Loading packs" />;
  }

  if (error) {
    return <ErrorState title="Packs unavailable" detail={error} action={load} />;
  }

  return (
    <div className="page-stack">
      <section className="page-header">
        <div>
          <p className="eyebrow">Structured Templates</p>
          <h1>Agent Packs</h1>
        </div>
        <label className="search-field">
          <Search size={16} aria-hidden="true" />
          <span className="sr-only">Search packs</span>
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search" />
        </label>
      </section>

      {filtered.length === 0 ? (
        <EmptyState title="No packs found" />
      ) : (
        <section className="split-view">
          <div className="panel list-panel">
            {filtered.map((pack) => (
              <button
                key={pack.pack_id}
                className={`list-row ${selected?.pack_id === pack.pack_id ? "is-active" : ""}`}
                type="button"
                onClick={() => setSelected(pack)}
              >
                <span>
                  <strong>{pack.display_name}</strong>
                  <small>{pack.pack_id}</small>
                </span>
                <StatusBadge label={pack.is_preset ? "preset" : "custom"} tone={pack.is_preset ? "success" : "neutral"} />
              </button>
            ))}
          </div>
          <div className="page-stack">
            {selected ? (
              <>
                <section className="panel">
                  <div className="panel__header">
                    <h2>{selected.display_name}</h2>
                    <StatusBadge label={selected.config.identity?.agent_name || "legacy"} />
                  </div>
                  <dl className="kv-list">
                    <div>
                      <dt>Runtime modules</dt>
                      <dd>{Object.entries(selected.config.runtime_modules).filter(([, enabled]) => enabled).length}</dd>
                    </div>
                    <div>
                      <dt>Core values</dt>
                      <dd>{selected.config.identity?.core_values?.join(", ") || "none"}</dd>
                    </div>
                  </dl>
                </section>
                <JsonBlock title="AgentPackConfig" value={selected.config} />
              </>
            ) : null}
          </div>
        </section>
      )}
    </div>
  );
}
