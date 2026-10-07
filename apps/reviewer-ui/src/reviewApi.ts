const apiBase = import.meta.env.VITE_API_BASE_URL ?? "";

export interface Organization {
  id: string;
  name: string;
}

export interface Actor {
  display_name: string;
  permissions: string[];
  authentication_method: string;
}

export type Decision = "match" | "no_match" | "defer" | "escalate";

export interface MatchDecision {
  id: string;
  candidate_id: string;
  decision: Decision;
  revision: number;
  reason: string;
  reviewer_id: string;
  decided_at: string;
  supersedes_decision_id: string | null;
}

export interface MatchCandidate {
  candidate_id: string;
  left_record_key: string;
  right_record_key: string;
  score: number | null;
  evidence: Record<string, unknown>;
  status: string;
  revision: number;
  created_at: string;
  decision_count: number;
  latest_decision: MatchDecision | null;
}

export interface QueueSummary {
  total_candidates: number;
  unreviewed_candidates: number;
  needs_review_candidates: number;
  by_status: Record<string, number>;
}

export class ReviewApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export async function reviewRequest<T>(
  path: string,
  user: string,
  organizationId?: string,
  payload?: unknown,
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${apiBase}/api/v1${path}`, {
      method: payload === undefined ? "GET" : "POST",
      headers: {
        "X-Demo-User": user,
        ...(organizationId ? { "X-Organization-ID": organizationId } : {}),
        ...(payload === undefined ? {} : { "Content-Type": "application/json" }),
      },
      ...(payload === undefined ? {} : { body: JSON.stringify(payload) }),
    });
  } catch {
    throw new ReviewApiError(0, "The API is unavailable. Reconnect before reviewing or saving.");
  }
  if (!response.ok) {
    const messages: Record<number, string> = {
      401: "Authentication is required. Check the local demo identity configuration.",
      403: "Your account does not have permission to review this organization.",
      404: "This review record is unavailable. Refresh the queue.",
      409: "Another reviewer changed this candidate. Refresh and inspect the latest decision before saving.",
      422: "The review request is invalid. Check the decision and reason.",
      429: "Too many requests. Wait a moment before trying again.",
    };
    throw new ReviewApiError(response.status, messages[response.status] ?? "The request failed. No save was confirmed.");
  }
  return response.json() as Promise<T>;
}

export const statusLabels: Record<string, string> = {
  pending: "Pending",
  review: "Needs review",
  trusted_id_conflict: "Trusted ID conflict",
  auto_match: "Suggested match",
  match: "Match confirmed",
  no_match: "Keep separate",
  defer: "Deferred",
  escalate: "Escalated",
};
