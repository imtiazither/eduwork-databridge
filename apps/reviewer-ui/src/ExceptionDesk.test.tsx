import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { ExceptionDesk } from "./ExceptionDesk";
import type { ExceptionRecord, Resolution } from "./exceptionApi";

const issue: ExceptionRecord = {
  quarantine_id: "issue-1", source_record_key: "HR-1", field_name: "employee_id", evidence_masked: "[masked]",
  explanation: "An identifier is required.", rule_key: "required_id", rule_title: "Missing employee ID",
  severity: "blocking", status: "open", revision: 0, created_at: "2026-10-18T12:00:00Z",
  raw_snapshot_id: "snapshot-1", supersedes_quarantine_id: null, remediation: "Contact the source owner.",
};
const clients: QueryClient[] = [];
function renderDesk() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  clients.push(client);
  return render(<QueryClientProvider client={client}><ExceptionDesk /></QueryClientProvider>);
}
function setupApi({ saveStatus = 200, queueStatus = 200, count = 1 } = {}) {
  let current = { ...issue };
  const history: Resolution[] = [];
  const fetch = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input), "http://test");
    const user = (init?.headers as Record<string, string>)["X-Demo-User"];
    let body: unknown; let status = 200;
    if (url.pathname.endsWith("/organizations")) body = [{ id: "org-1", name: "Northstar" }, { id: "org-2", name: "Other" }];
    else if (url.pathname.endsWith("/me")) body = { display_name: user, permissions: user === "demo-viewer" ? [] : ["validation:write"] };
    else if (url.pathname.endsWith("/summary")) body = { total: count, needs_attention: count, by_status: { open: count }, by_severity: { blocking: count } };
    else if (url.pathname.endsWith("/resolve")) {
      status = saveStatus;
      const payload = JSON.parse(String(init?.body));
      const saved: Resolution = { id: "resolution-1", quarantine_id: current.quarantine_id, revision: 1, status: payload.status, note: payload.note, reviewer_id: "reviewer-1", recorded_at: "2026-10-18T12:01:00Z", corrected_snapshot_id: null, imported: false };
      if (status === 200) { history.unshift(saved); current = { ...current, status: saved.status, revision: 1 }; }
      body = saved;
    } else if (url.pathname.endsWith("/history")) body = history;
    else if (url.pathname.endsWith("/quarantine")) { status = queueStatus; body = Array.from({ length: count }, (_, index) => ({ ...current, quarantine_id: `issue-${index + 1}` })); }
    else throw new Error(`Unhandled request ${url.pathname}`);
    return Promise.resolve({ ok: status === 200, status, json: async () => body } as Response);
  });
  vi.stubGlobal("fetch", fetch);
  return fetch;
}
afterEach(() => { cleanup(); clients.splice(0).forEach(client => client.clear()); vi.unstubAllGlobals(); });

test("records a reasoned resolution and reads its saved history after remount", async () => {
  const fetch = setupApi();
  const view = renderDesk();
  await screen.findByRole("heading", { name: "Missing employee ID" });
  expect(screen.getByRole("button", { name: "Save resolution" })).toBeDisabled();
  fireEvent.change(screen.getByLabelText("Resolution note"), { target: { value: "Contacted source owner" } });
  fireEvent.click(screen.getByRole("button", { name: "Save resolution" }));
  await screen.findByText(/Resolution saved/);
  expect(JSON.parse(String(fetch.mock.calls.find(([, init]) => init?.method === "POST")?.[1]?.body))).toEqual({ status: "acknowledged", note: "Contacted source owner", expected_revision: 0, corrected_snapshot_id: null });
  view.unmount(); renderDesk();
  expect(await screen.findByText("Contacted source owner")).toBeInTheDocument();
});

test.each([409, 403, 500])("keeps save error %s visible without confirming a save", async saveStatus => {
  setupApi({ saveStatus }); renderDesk();
  await screen.findByRole("heading", { name: "Missing employee ID" });
  fireEvent.change(screen.getByLabelText("Resolution note"), { target: { value: "Review" } });
  fireEvent.click(screen.getByRole("button", { name: "Save resolution" }));
  await screen.findByRole("alert");
  expect(screen.queryByText(/Resolution saved/)).not.toBeInTheDocument();
  if (saveStatus === 409) { expect(screen.getByRole("button", { name: "Save resolution" })).toBeDisabled(); expect(screen.getByRole("button", { name: "Refresh exception" })).toBeInTheDocument(); }
});

test("filters, searches, and pages the persisted queue", async () => {
  const fetch = setupApi({ count: 20 }); renderDesk();
  await screen.findByRole("heading", { name: "Missing employee ID" });
  fireEvent.click(screen.getByRole("button", { name: "Next page" }));
  await waitFor(() => expect(fetch.mock.calls.some(([url]) => String(url).includes("offset=20"))).toBe(true));
  fireEvent.change(screen.getByLabelText("Severity"), { target: { value: "blocking" } });
  fireEvent.change(screen.getByLabelText("Exception filter"), { target: { value: "closed" } });
  fireEvent.change(screen.getByLabelText("Search record or rule"), { target: { value: "HR-1" } });
  fireEvent.click(screen.getByRole("button", { name: "Search" }));
  await waitFor(() => expect(fetch.mock.calls.some(([url]) => String(url).includes("severity=blocking") && String(url).includes("status=closed") && String(url).includes("q=HR-1") && String(url).includes("offset=0"))).toBe(true));
});

test("separates organization caches and denies viewer controls", async () => {
  const fetch = setupApi(); renderDesk();
  await screen.findByRole("heading", { name: "Missing employee ID" });
  fireEvent.change(screen.getByLabelText("Organization"), { target: { value: "org-2" } });
  await waitFor(() => expect(fetch.mock.calls.some(([url, init]) => String(url).includes("/quarantine?") && (init?.headers as Record<string, string>)["X-Organization-ID"] === "org-2")).toBe(true));
  fireEvent.change(screen.getByLabelText("Local demo identity"), { target: { value: "demo-viewer" } });
  await screen.findByText(/cannot review exceptions/);
  expect(screen.queryByRole("button", { name: "Save resolution" })).not.toBeInTheDocument();
  expect(fetch.mock.calls.some(([url, init]) => String(url).includes("/quarantine") && (init?.headers as Record<string, string>)["X-Demo-User"] === "demo-viewer")).toBe(false);
});

test("shows empty and unavailable queues without fixture substitution", async () => {
  setupApi({ count: 0 }); const view = renderDesk();
  await screen.findByText("No exceptions in this view."); view.unmount();
  setupApi({ queueStatus: 403 }); renderDesk();
  expect(await screen.findByRole("alert")).toHaveTextContent(/permission/);
  expect(screen.queryByRole("button", { name: "Save resolution" })).not.toBeInTheDocument();
});
