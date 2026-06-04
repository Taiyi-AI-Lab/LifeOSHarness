import { ArrowRight, Boxes, FlaskConical, Package } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { ErrorState, LoadingState } from "../components/DataState";
import { StatusBadge } from "../components/StatusBadge";
import { listPacks, listWorlds } from "../lib/api";
import { compactId, formatMillis, pluralize } from "../lib/format";
import { loadContextRuns } from "../lib/storage";
import type { ContextRun, PackResponse, WorldResponse } from "../types";

type OverviewProps = {
  apiKey: string;
};

export function Overview({ apiKey }: OverviewProps) {
  const [worlds, setWorlds] = useState<WorldResponse[]>([]);
  const [packs, setPacks] = useState<PackResponse[]>([]);
  const [runs, setRuns] = useState<ContextRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [nextWorlds, nextPacks] = await Promise.all([listWorlds(apiKey), listPacks(apiKey)]);
      setWorlds(nextWorlds);
      setPacks(nextPacks);
      setRuns(loadContextRuns());
    } catch (event) {
      setError(event instanceof Error ? event.message : "Unable to load overview.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, [apiKey]);

  if (loading) {
    return <LoadingState title="Loading overview" />;
  }

  if (error) {
    return <ErrorState title="Overview unavailable" detail={error} action={load} />;
  }

  const injectedRuns = runs.filter((run) => run.injected).length;

  return (
    <div className="page-stack">
      <section className="page-header">
        <div>
          <p className="eyebrow">Agent World Runtime</p>
          <h1>Overview</h1>
        </div>
        <Link className="button" to="/inspector">
          Run Inspector
          <ArrowRight size={16} aria-hidden="true" />
        </Link>
      </section>

      <section className="metric-grid" aria-label="Runtime metrics">
        <MetricCard icon={<Boxes size={20} />} label="Worlds" value={worlds.length.toString()} />
        <MetricCard icon={<Package size={20} />} label="Agent Packs" value={packs.length.toString()} />
        <MetricCard
          icon={<FlaskConical size={20} />}
          label="Local context runs"
          value={runs.length.toString()}
        />
        <MetricCard label="Injected locally" value={`${injectedRuns}/${runs.length || 0}`} />
      </section>

      <section className="panel">
        <div className="panel__header">
          <h2>Active Worlds</h2>
          <Link to="/worlds">View all</Link>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>World ID</th>
                <th>Pack</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {worlds.slice(0, 8).map((world) => (
                <tr key={world.world_id}>
                  <td>
                    <Link to={`/worlds/${world.world_id}`}>{world.display_name}</Link>
                  </td>
                  <td className="mono">{compactId(world.world_id)}</td>
                  <td>{world.pack_id}</td>
                  <td>
                    <StatusBadge label="available" tone="success" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel">
        <div className="panel__header">
          <h2>Recent Context Runs</h2>
          <span>{pluralize(runs.length, "run")}</span>
        </div>
        <div className="run-list">
          {runs.slice(0, 6).map((run) => (
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
                <span>{run.blockCount} blocks</span>
                <span>{formatMillis(run.createdAt)}</span>
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}

function MetricCard({
  icon,
  label,
  value,
}: {
  icon?: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <article className="metric-card">
      <div className="metric-card__icon" aria-hidden="true">
        {icon}
      </div>
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}
