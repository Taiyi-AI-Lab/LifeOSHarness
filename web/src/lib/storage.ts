import type { ContextRun } from "../types";

const API_KEY_STORAGE = "lifeos.console.apiKey";
const RUNS_STORAGE = "lifeos.console.contextRuns";
const MAX_RUNS = 20;

export function loadApiKey(): string {
  return localStorage.getItem(API_KEY_STORAGE) || "dev-lifeos-key-change-me";
}

export function saveApiKey(value: string): void {
  localStorage.setItem(API_KEY_STORAGE, value);
}

export function loadContextRuns(): ContextRun[] {
  const raw = localStorage.getItem(RUNS_STORAGE);
  if (!raw) {
    return [];
  }
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function saveContextRun(run: ContextRun): ContextRun[] {
  const next = [run, ...loadContextRuns()].slice(0, MAX_RUNS);
  localStorage.setItem(RUNS_STORAGE, JSON.stringify(next));
  return next;
}
