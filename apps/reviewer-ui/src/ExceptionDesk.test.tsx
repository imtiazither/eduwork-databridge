import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { ExceptionDesk } from "./ExceptionDesk";
import { DraftGuardProvider } from "./DraftGuard";
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
  return render(<QueryClientProvider client={client}><DraftGuardProvider><ExceptionDesk /></DraftGuardProvider></QueryClientProvider>);
}
function setupApi({ saveStatus = 200, queueStatus = 200, count = 1 } = {}) {
  const records = Array.from({ length: count }, (_, index) => ({ ...issue, quarantine_id: `issue-${index + 1}` }));
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
      const current = records.find(row => row.quarantine_id === url.pathname.split("/").at(-2))!;
      const payload = JSON.parse(String(init?.body));
      const saved: Resolution = { id: `resolution-${history.length + 1}`, quarantine_id: current.quarantine_id, revision: current.revision + 1, status: payload.status, note: payload.note, reviewer_id: "reviewer-1", recorded_at: "2026-10-18T12:01:00Z", corrected_snapshot_id: null, imported: false };
      if (status === 200) { history.unshift(saved); Object.assign(current, { status: saved.status, revision: saved.revision }); }
      body = saved;
    } else if (url.pathname.endsWith("/history")) body = history.filter(row => row.quarantine_id === url.pathname.split("/").at(-2));
    else if (url.pathname.endsWith("/quarantine/page")) {
      status = queueStatus;
      const filtered = records.filter(row => (!url.searchParams.has("status") || row.status === url.searchParams.get("status")) && (url.searchParams.get("needs_attention") !== "true" || ["open", "acknowledged"].includes(row.status)));
      const limit = Number(url.searchParams.get("limit") ?? 20);
      const offset = Math.min(Number(url.searchParams.get("offset") ?? 0), Math.floor(Math.max(0, filtered.length - 1) / limit) * limit);
      body = { items: filtered.slice(offset, offset + limit), total: filtered.length, limit, offset };
    }
    else throw new Error(`Unhandled request ${url.pathname}`);
    return Promise.resolve({ ok: status === 200, status, json: async () => body } as Response);
  });
  vi.stubGlobal("fetch", fetch);
  return fetch;
}
afterEach(() => { cleanup(); clients.splice(0).forEach(client => client.clear()); vi.unstubAllGlobals(); vi.restoreAllMocks(); });

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
  const fetch = setupApi({ count: 21 }); renderDesk();
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
  await waitFor(() => expect(fetch.mock.calls.some(([url, init]) => String(url).includes("/quarantine/page?") && (init?.headers as Record<string, string>)["X-Organization-ID"] === "org-2")).toBe(true));
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

test.each(["record", "filter", "severity", "sort", "organization", "identity", "refresh", "page"])("protects an unfinished note before changing %s", async action => {
  setupApi({ count: 21 }); renderDesk();
  await screen.findByRole("heading", { name: "Missing employee ID" });
  const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
  fireEvent.change(screen.getByLabelText("Resolution note"), { target: { value: "Unfinished review" } });
  if (action === "record") fireEvent.click(screen.getAllByRole("button", { name: /HR-1/ })[1]);
  if (action === "filter") fireEvent.change(screen.getByLabelText("Exception filter"), { target: { value: "closed" } });
  if (action === "severity") fireEvent.change(screen.getByLabelText("Severity"), { target: { value: "blocking" } });
  if (action === "sort") fireEvent.change(screen.getByLabelText("Sort order"), { target: { value: "severity" } });
  if (action === "organization") fireEvent.change(screen.getByLabelText("Organization"), { target: { value: "org-2" } });
  if (action === "identity") fireEvent.change(screen.getByLabelText("Local demo identity"), { target: { value: "demo-viewer" } });
  if (action === "refresh") fireEvent.click(screen.getByRole("button", { name: "Refresh exceptions" }));
  if (action === "page") fireEvent.click(screen.getByRole("button", { name: "Next page" }));
  expect(confirm).toHaveBeenCalledWith("Discard unsaved resolution changes?");
  expect(screen.getByLabelText("Resolution note")).toHaveValue("Unfinished review");
  expect(screen.getByLabelText("Exception filter")).toHaveValue("needs_attention");
  expect(screen.getByLabelText("Local demo identity")).toHaveValue("demo-admin");
  expect(screen.getByLabelText("Organization")).toHaveValue("org-1");
});

test("requests the selected server-side sort from the first page", async () => {
  const fetch = setupApi({ count: 21 }); renderDesk();
  await screen.findByLabelText("Resolution note");
  fireEvent.click(screen.getByRole("button", { name: "Next page" }));
  await waitFor(() => expect(fetch.mock.calls.some(([url]) => String(url).includes("offset=20"))).toBe(true));
  fireEvent.change(screen.getByLabelText("Sort order"), { target: { value: "severity" } });
  await waitFor(() => expect(fetch.mock.calls.some(([url]) => String(url).includes("sort=severity") && String(url).includes("offset=0"))).toBe(true));
});

test("warns on browser unload only while a draft is unfinished", async () => {
  setupApi(); renderDesk();
  await screen.findByRole("heading", { name: "Missing employee ID" });
  const clean = new Event("beforeunload", { cancelable: true });
  window.dispatchEvent(clean);
  expect(clean.defaultPrevented).toBe(false);
  fireEvent.change(screen.getByLabelText("Resolution note"), { target: { value: "Draft" } });
  const dirty = new Event("beforeunload", { cancelable: true });
  window.dispatchEvent(dirty);
  expect(dirty.defaultPrevented).toBe(true);
  vi.spyOn(window, "confirm").mockReturnValue(true);
  fireEvent.change(screen.getByLabelText("Severity"), { target: { value: "warning" } });
  expect(await screen.findByLabelText("Resolution note")).toHaveValue("");
  const discarded = new Event("beforeunload", { cancelable: true });
  window.dispatchEvent(discarded);
  expect(discarded.defaultPrevented).toBe(false);
});

test("clears the unload warning after a successful save", async () => {
  setupApi(); renderDesk();
  await screen.findByLabelText("Resolution note");
  fireEvent.change(screen.getByLabelText("Resolution note"), { target: { value: "Completed review" } });
  fireEvent.click(screen.getByRole("button", { name: "Save resolution" }));
  await screen.findByText(/Resolution saved/);
  await waitFor(() => expect(screen.getByRole("button", { name: "Save resolution" })).toBeDisabled());
  await waitFor(() => {
    const event = new Event("beforeunload", { cancelable: true }); window.dispatchEvent(event);
    expect(event.defaultPrevented).toBe(false);
  });
});

test.each([0, 20])("has no extra page when the matching total is %s", async count => {
  setupApi({ count }); renderDesk();
  await screen.findByText(count ? "Showing 1-20 of 20 matching issues" : "Showing 0-0 of 0 matching issues");
  expect(screen.getByRole("button", { name: "Next page" })).toBeDisabled();
  expect(screen.getByText("Page 1 of 1")).toBeInTheDocument();
});

test("returns to the last valid page after closing its final matching issue", async () => {
  setupApi({ count: 21 }); renderDesk();
  await screen.findByText("Showing 1-20 of 21 matching issues");
  fireEvent.click(screen.getByRole("button", { name: "Next page" }));
  await screen.findByText("Showing 21-21 of 21 matching issues");
  fireEvent.change(screen.getByLabelText("Resolution status"), { target: { value: "closed" } });
  fireEvent.change(screen.getByLabelText("Resolution note"), { target: { value: "Checked the source" } });
  fireEvent.click(screen.getByRole("button", { name: "Save resolution" }));
  await screen.findByText("Showing 1-20 of 20 matching issues");
  expect(screen.getByText("Page 1 of 1")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Next page" })).toBeDisabled();
});
