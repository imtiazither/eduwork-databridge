import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { ReviewDesk } from "./ReviewDesk";
import type { MatchCandidate, MatchDecision } from "./reviewApi";

const candidate: MatchCandidate = {
  candidate_id: "candidate-1", left_record_key: "HR-1", right_record_key: "LMS-1",
  status: "review", score: .82, evidence: { rule_id: "exact_email", fingerprints: ["masked"] },
  revision: 0, decision_count: 0, latest_decision: null, created_at: "2026-10-07T12:00:00Z",
};
const clients: QueryClient[] = [];

function renderDesk() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  clients.push(client);
  return render(<QueryClientProvider client={client}><ReviewDesk /></QueryClientProvider>);
}

function setupApi({ saveStatus = 200, total = 1, empty = false, queueStatus = 200 } = {}) {
  let current = { ...candidate };
  const decisions: MatchDecision[] = [];
  const fetch = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input), "http://test");
    let body: unknown;
    let status = 200;
    const user = (init?.headers as Record<string, string>)?.["X-Demo-User"];
    if (url.pathname.endsWith("/organizations")) body = [{ id: "org-1", name: "Northstar" }, { id: "org-2", name: "Other organization" }];
    else if (url.pathname.endsWith("/me")) body = { display_name: user === "demo-viewer" ? "Demo Viewer" : "Demo Administrator", permissions: user === "demo-viewer" ? ["sources:read"] : ["matching:write"] };
    else if (url.pathname.endsWith("/summary")) body = { total_candidates: empty ? 0 : total, unreviewed_candidates: decisions.length ? total - 1 : total, needs_review_candidates: decisions.length ? 0 : total, by_status: { [current.status]: total } };
    else if (url.pathname.endsWith("/review-queue")) {
      status = queueStatus;
      body = empty ? [] : Array.from({ length: total }, (_, index) => ({ ...current, candidate_id: `candidate-${index + 1}` }));
    } else if (url.pathname.endsWith("/decisions") && init?.method === "POST") {
      status = saveStatus;
      const payload = JSON.parse(String(init.body));
      const saved: MatchDecision = { id: "decision-1", candidate_id: current.candidate_id, decision: payload.decision, revision: 1, reason: payload.reason, reviewer_id: "reviewer-1", decided_at: "2026-10-07T12:01:00Z", supersedes_decision_id: null };
      body = saved;
      if (status === 200) {
        decisions.unshift(saved);
        current = { ...current, revision: 1, decision_count: 1, latest_decision: saved, status: payload.decision };
      }
    } else if (url.pathname.endsWith("/decisions")) body = decisions;
    else if (url.pathname.endsWith("/synthetic")) body = { candidate_count: 1 };
    else throw new Error(`Unhandled test request ${url.pathname}`);
    return Promise.resolve({ ok: status === 200, status, json: async () => body } as Response);
  });
  vi.stubGlobal("fetch", fetch);
  return fetch;
}

afterEach(() => {
  cleanup();
  clients.splice(0).forEach((client) => client.clear());
  vi.unstubAllGlobals();
});

test("shows scoped evidence and saves a reason with the observed revision", async () => {
  const fetch = setupApi();
  renderDesk();
  await screen.findByRole("heading", { name: "HR-1 ↔ LMS-1" });
  const save = screen.getByRole("button", { name: "Save decision" });
  expect(save).toBeDisabled();
  fireEvent.change(screen.getByLabelText("Reason for this decision"), { target: { value: "   " } });
  expect(save).toBeDisabled();
  fireEvent.change(screen.getByLabelText("Decision"), { target: { value: "no_match" } });
  fireEvent.change(screen.getByLabelText("Reason for this decision"), { target: { value: " Source owner confirmed two people. " } });
  fireEvent.click(save);
  expect(await screen.findByText(/Decision saved/)).toBeInTheDocument();
  const post = fetch.mock.calls.find(([, init]) => init?.method === "POST");
  expect(JSON.parse(String(post?.[1]?.body))).toEqual({ decision: "no_match", reason: "Source owner confirmed two people.", expected_revision: 0 });
  expect(post?.[1]?.headers).toMatchObject({ "X-Organization-ID": "org-1", "X-Demo-User": "demo-admin" });
  expect(await screen.findByText(/Latest decision: Keep separate/)).toBeInTheDocument();
  expect(screen.getByText(/Keep separate · revision 1/)).toBeInTheDocument();
});

test("requires refresh after a conflicting reviewer save and never claims success", async () => {
  setupApi({ saveStatus: 409 });
  renderDesk();
  await screen.findByRole("heading", { name: "HR-1 ↔ LMS-1" });
  fireEvent.change(screen.getByLabelText("Reason for this decision"), { target: { value: "Needs review" } });
  fireEvent.click(screen.getByRole("button", { name: "Save decision" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(/Another reviewer changed/);
  expect(screen.getByRole("button", { name: "Save decision" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Refresh candidate" })).toBeInTheDocument();
  expect(screen.queryByText(/Decision saved/)).not.toBeInTheDocument();
});

test.each([403, 500])("shows save failure %s without pretending to persist it", async (saveStatus) => {
  setupApi({ saveStatus });
  renderDesk();
  await screen.findByRole("heading", { name: "HR-1 ↔ LMS-1" });
  fireEvent.change(screen.getByLabelText("Reason for this decision"), { target: { value: "Needs review" } });
  fireEvent.click(screen.getByRole("button", { name: "Save decision" }));
  await screen.findByRole("alert");
  expect(screen.queryByText(/Decision saved/)).not.toBeInTheDocument();
});

test("filters, searches, and pages through the queue", async () => {
  const fetch = setupApi({ total: 20 });
  renderDesk();
  await screen.findByRole("heading", { name: "HR-1 ↔ LMS-1" });
  fireEvent.click(screen.getByRole("button", { name: "Next page" }));
  await waitFor(() => expect(fetch.mock.calls.some(([url]) => String(url).includes("offset=20"))).toBe(true));
  fireEvent.change(screen.getByLabelText("Queue filter"), { target: { value: "defer" } });
  await waitFor(() => expect(fetch.mock.calls.some(([url]) => String(url).includes("status=defer") && String(url).includes("offset=0"))).toBe(true));
  fireEvent.change(screen.getByLabelText("Search record keys"), { target: { value: "HR-1" } });
  fireEvent.click(screen.getByRole("button", { name: "Search" }));
  await waitFor(() => expect(fetch.mock.calls.some(([url]) => String(url).includes("q=HR-1"))).toBe(true));
});

test("isolates organization and viewer sessions", async () => {
  const fetch = setupApi();
  renderDesk();
  await screen.findByRole("heading", { name: "HR-1 ↔ LMS-1" });
  fireEvent.change(screen.getByLabelText("Organization"), { target: { value: "org-2" } });
  await waitFor(() => expect(fetch.mock.calls.some(([url, init]) => String(url).includes("review-queue") && (init?.headers as Record<string, string>)["X-Organization-ID"] === "org-2")).toBe(true));
  fireEvent.change(screen.getByLabelText("Local demo identity"), { target: { value: "demo-viewer" } });
  expect(await screen.findByText(/cannot review identity candidates/)).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Save decision" })).not.toBeInTheDocument();
  expect(fetch.mock.calls.some(([url, init]) => String(url).includes("review-queue") && (init?.headers as Record<string, string>)["X-Demo-User"] === "demo-viewer")).toBe(false);
});

test("offers an explicit synthetic run for an empty local queue", async () => {
  const fetch = setupApi({ empty: true });
  renderDesk();
  fireEvent.click(await screen.findByRole("button", { name: "Generate synthetic candidates" }));
  expect(await screen.findByText(/Synthetic candidates created/)).toBeInTheDocument();
  const post = fetch.mock.calls.find(([, init]) => init?.method === "POST");
  expect(JSON.parse(String(post?.[1]?.body))).toEqual({ match_config_id: "person_probabilistic_v1", dataset_preset: "small" });
});

test("keeps a queue failure visible without using preview decisions", async () => {
  setupApi({ queueStatus: 403 });
  renderDesk();
  expect(await screen.findByRole("alert")).toHaveTextContent(/does not have permission/);
  expect(screen.queryByRole("button", { name: "Save decision" })).not.toBeInTheDocument();
});
