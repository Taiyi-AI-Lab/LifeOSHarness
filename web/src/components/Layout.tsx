import {
  Activity,
  Boxes,
  Brain,
  Database,
  FlaskConical,
  Home,
  KeyRound,
  Menu,
  Package,
  X,
} from "lucide-react";
import { type ReactNode, useEffect, useState } from "react";
import { NavLink } from "react-router-dom";

import { getHealth } from "../lib/api";
import { saveApiKey } from "../lib/storage";
import { StatusBadge } from "./StatusBadge";

const navItems = [
  { to: "/", label: "Overview", icon: Home },
  { to: "/worlds", label: "Worlds", icon: Boxes },
  { to: "/packs", label: "Agent Packs", icon: Package },
  { to: "/inspector", label: "Runtime Inspector", icon: FlaskConical },
];

type LayoutProps = {
  children: ReactNode;
  apiKey: string;
  onApiKeyChange: (value: string) => void;
};

export function Layout({ children, apiKey, onApiKeyChange }: LayoutProps) {
  const [open, setOpen] = useState(false);
  const [draftKey, setDraftKey] = useState(apiKey);
  const [health, setHealth] = useState<"ok" | "down" | "checking">("checking");

  useEffect(() => {
    setDraftKey(apiKey);
  }, [apiKey]);

  useEffect(() => {
    let cancelled = false;
    getHealth()
      .then((result) => {
        if (!cancelled) {
          setHealth(result.status === "ok" ? "ok" : "down");
        }
      })
      .catch(() => {
        if (!cancelled) {
          setHealth("down");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  function persistKey() {
    const trimmed = draftKey.trim();
    saveApiKey(trimmed);
    onApiKeyChange(trimmed);
  }

  return (
    <div className="app-shell">
      <aside className={`sidebar ${open ? "sidebar--open" : ""}`}>
        <div className="brand">
          <span className="brand__mark">
            <Brain size={20} aria-hidden="true" />
          </span>
          <div>
            <strong>LifeOS</strong>
            <span>Web Console</span>
          </div>
        </div>
        <nav className="sidebar__nav" aria-label="Primary">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                onClick={() => setOpen(false)}
              >
                <Icon size={18} aria-hidden="true" />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>
      </aside>

      <div className="workspace">
        <header className="topbar">
          <button
            className="icon-button topbar__menu"
            type="button"
            onClick={() => setOpen(true)}
            aria-label="Open navigation"
          >
            <Menu size={20} aria-hidden="true" />
          </button>
          <div className="topbar__status">
            <Activity size={16} aria-hidden="true" />
            <StatusBadge
              label={health === "checking" ? "Checking" : health === "ok" ? "Server ok" : "Server down"}
              tone={health === "ok" ? "success" : health === "down" ? "danger" : "neutral"}
            />
          </div>
          <div className="api-key-control">
            <KeyRound size={16} aria-hidden="true" />
            <label htmlFor="api-key">API key</label>
            <input
              id="api-key"
              type="password"
              value={draftKey}
              onChange={(event) => setDraftKey(event.target.value)}
            />
            <button className="button button--secondary" type="button" onClick={persistKey}>
              Save
            </button>
          </div>
          <div className="topbar__db">
            <Database size={16} aria-hidden="true" />
            <span>FastAPI :8000</span>
          </div>
        </header>
        <main className="content" id="main-content">
          {children}
        </main>
      </div>

      {open ? (
        <button
          className="sidebar-backdrop"
          type="button"
          onClick={() => setOpen(false)}
          aria-label="Close navigation"
        >
          <X size={24} aria-hidden="true" />
        </button>
      ) : null}
    </div>
  );
}
