import { exceptionSorts, exceptionStatuses } from "./exceptionApi";

export interface ExceptionPreferences { filter: string; severity: string; sort: string; }
export const defaultExceptionPreferences: ExceptionPreferences = {
  filter: "needs_attention", severity: "all", sort: "oldest",
};
const filters = new Set(["all", "needs_attention", ...Object.keys(exceptionStatuses)]);
const severities = new Set(["all", "blocking", "error", "warning"]);
const sorts = new Set(Object.keys(exceptionSorts));
const key = (user: string, organization: string) => `eduwork-exception-filters:v1:${encodeURIComponent(user)}:${encodeURIComponent(organization)}`;

export function readExceptionPreferences(user: string, organization: string): ExceptionPreferences {
  try {
    const saved: unknown = JSON.parse(window.sessionStorage.getItem(key(user, organization)) ?? "null");
    if (!saved || typeof saved !== "object" || Array.isArray(saved)) return { ...defaultExceptionPreferences };
    const values = saved as Record<string, unknown>;
    return {
      filter: typeof values.filter === "string" && filters.has(values.filter) ? values.filter : "needs_attention",
      severity: typeof values.severity === "string" && severities.has(values.severity) ? values.severity : "all",
      sort: typeof values.sort === "string" && sorts.has(values.sort) ? values.sort : "oldest",
    };
  } catch {
    return { ...defaultExceptionPreferences };
  }
}

export function writeExceptionPreferences(user: string, organization: string, preferences: ExceptionPreferences) {
  try {
    const { filter, severity, sort } = preferences;
    window.sessionStorage.setItem(key(user, organization), JSON.stringify({ filter, severity, sort }));
  } catch {
    // Reviews still work when browser storage is unavailable.
  }
}
