import { ArrowRight, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { EmptyState, ErrorState, LoadingState } from "../components/DataState";
import { StatusBadge } from "../components/StatusBadge";
import { listWorlds } from "../lib/api";
import { compactId } from "../lib/format";
import type { WorldResponse } from "../types";

export function Worlds({ apiKey }: { apiKey: string }) {
  const [worlds, setWorlds] = useState<WorldResponse[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setWorlds(await listWorlds(apiKey));
    } catch (event) {
      setError(event instanceof Error ? event.message : "Unable to load worlds.");
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
      return worlds;
    }
    return worlds.filter((world) =>
      [world.display_name, world.world_id, world.pack_id].some((value) =>
        value.toLowerCase().includes(term),
      ),
    );
  }, [query, worlds]);

  if (loading) {
    return <LoadingState title="Loading worlds" />;
  }

  if (error) {
    return <ErrorState title="Worlds unavailable" detail={error} action={load} />;
  }

  return (
    <div className="page-stack">
      <section className="page-header">
        <div>
          <p className="eyebrow">World Instances</p>
          <h1>Worlds</h1>
        </div>
        <label className="search-field">
          <Search size={16} aria-hidden="true" />
          <span className="sr-only">Search worlds</span>
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search" />
        </label>
      </section>

      {filtered.length === 0 ? (
        <EmptyState title="No worlds found" detail="Create a world with the CLI or API first." />
      ) : (
        <section className="world-grid">
          {filtered.map((world) => (
            <article className="entity-card" key={world.world_id}>
              <div>
                <StatusBadge label="world" />
                <h2>{world.display_name}</h2>
                <p className="mono">{compactId(world.world_id, 12)}</p>
              </div>
              <dl>
                <div>
                  <dt>Pack</dt>
                  <dd>{world.pack_id}</dd>
                </div>
                <div>
                  <dt>Overrides</dt>
                  <dd>{Object.keys(world.overrides || {}).length}</dd>
                </div>
              </dl>
              <Link className="button button--secondary" to={`/worlds/${world.world_id}`}>
                Inspect
                <ArrowRight size={16} aria-hidden="true" />
              </Link>
            </article>
          ))}
        </section>
      )}
    </div>
  );
}
