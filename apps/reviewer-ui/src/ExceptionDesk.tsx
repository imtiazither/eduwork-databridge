import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { exceptionStatuses, type ExceptionRecord, type ExceptionSummary, type Resolution } from "./exceptionApi";
import { reviewRequest, ReviewApiError, type Actor, type Organization } from "./reviewApi";

const pageSize = 20;

function ErrorNotice({ error }: { error: Error | null }) {
  return error ? <p className="review-notice error" role="alert">{error.message}</p> : null;
}

function ExceptionDetail({ issue, user, organizationId, refresh, saved }: {
  issue: ExceptionRecord; user: string; organizationId: string;
  refresh: () => Promise<void>; saved: () => Promise<void>;
}) {
  const [status, setStatus] = useState("acknowledged");
  const [note, setNote] = useState("");
  const [snapshot, setSnapshot] = useState("");
  const [offset, setOffset] = useState(0);
  const history = useQuery({
    queryKey: ["exception-history", user, organizationId, issue.quarantine_id, offset],
    queryFn: () => reviewRequest<Resolution[]>(`/quarantine/${issue.quarantine_id}/history?limit=${pageSize}&offset=${offset}`, user, organizationId),
    retry: false,
  });
  const save = useMutation({
    mutationFn: () => reviewRequest<Resolution>(`/quarantine/${issue.quarantine_id}/resolve`, user, organizationId, {
      status, note: note.trim(), expected_revision: issue.revision,
      corrected_snapshot_id: snapshot.trim() || null,
    }),
    onSuccess: saved, retry: false,
  });
  const conflict = save.error instanceof ReviewApiError && save.error.status === 409;
  function submit(event: FormEvent) {
    event.preventDefault();
    if (note.trim() && !save.isPending && !conflict) save.mutate();
  }

  return <article className="exception-inspector" aria-labelledby="exception-title">
    <p className="section-kicker">{issue.severity} · revision {issue.revision}</p>
    <h3 id="exception-title">{issue.rule_title}</h3>
    <p className="exception-record-key">Record <code>{issue.source_record_key}</code> · {exceptionStatuses[issue.status]}</p>
    <dl className="exception-evidence">
      <div><dt>Rule</dt><dd><code>{issue.rule_key}</code></dd></div>
      <div><dt>Field</dt><dd>{issue.field_name || "Record"}</dd></div>
      <div><dt>Source snapshot</dt><dd><code>{issue.raw_snapshot_id}</code></dd></div>
      <div><dt>Masked evidence</dt><dd>{issue.evidence_masked || "No field value retained"}</dd></div>
      <div><dt>Why it was held</dt><dd>{issue.explanation}</dd></div>
      {issue.remediation && <div><dt>Suggested next step</dt><dd>{issue.remediation}</dd></div>}
      {issue.supersedes_quarantine_id && <div><dt>Previous issue</dt><dd><code>{issue.supersedes_quarantine_id}</code></dd></div>}
    </dl>
    <form className="review-form" onSubmit={submit}>
      <label htmlFor="exception-status">Resolution status</label>
      <select id="exception-status" value={status} disabled={save.isPending} onChange={event => setStatus(event.target.value)}>
        {Object.entries(exceptionStatuses).map(([value, label]) => <option key={value} value={value}>{value === "open" ? "Reopen" : label}</option>)}
      </select>
      <label htmlFor="exception-note">Resolution note</label>
      <textarea id="exception-note" rows={3} required maxLength={2000} disabled={save.isPending}
        value={note} onChange={event => setNote(event.target.value)} />
      <label htmlFor="corrected-snapshot">Corrected snapshot ID (optional)</label>
      <input id="corrected-snapshot" value={snapshot} disabled={save.isPending} onChange={event => setSnapshot(event.target.value)}
        pattern="[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}" />
      <p className="review-help">A status records the review outcome. Source corrections still need validation before publication.</p>
      <ErrorNotice error={save.error} />
      {conflict && <button type="button" className="review-button quiet" onClick={() => void refresh()}>Refresh exception</button>}
      <button type="submit" className="review-button" disabled={!note.trim() || save.isPending || conflict}>
        {save.isPending ? "Saving resolution…" : "Save resolution"}
      </button>
    </form>
    <section className="review-history" aria-label="Resolution history">
      <h4>Resolution history</h4>
      <ErrorNotice error={history.error} />
      {history.isPending && <p role="status">Loading resolution history…</p>}
      {history.data?.length === 0 && <p>No resolutions on this page.</p>}
      <ol>{history.data?.map(item => <li key={item.id}>
        <strong>{exceptionStatuses[item.status]} · revision {item.revision}</strong>
        <p>{item.note}</p>
        <small><time dateTime={item.recorded_at}>{new Date(item.recorded_at).toLocaleString()}</time> · reviewer <code>{item.reviewer_id || "Not recorded"}</code></small>
        {item.imported && <p className="review-help">Imported latest resolution from an earlier version.</p>}
        {item.corrected_snapshot_id && <p>Corrected snapshot: <code>{item.corrected_snapshot_id}</code></p>}
      </li>)}</ol>
      {(issue.revision > pageSize || offset > 0) && <div className="review-pagination">
        <button type="button" disabled={offset === 0 || history.isFetching} onClick={() => setOffset(offset - pageSize)}>Newer resolutions</button>
        <button type="button" disabled={!history.data || history.data.length < pageSize || history.isFetching} onClick={() => setOffset(offset + pageSize)}>Older resolutions</button>
      </div>}
    </section>
  </article>;
}

function ExceptionQueue({ user, organizationId }: { user: string; organizationId: string }) {
  const client = useQueryClient();
  const [filter, setFilter] = useState("needs_attention");
  const [severity, setSeverity] = useState("all");
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [offset, setOffset] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [notice, setNotice] = useState("");
  const params = new URLSearchParams({ limit: String(pageSize), offset: String(offset) });
  if (filter === "needs_attention") params.set("needs_attention", "true");
  else if (filter !== "all") params.set("status", filter);
  if (severity !== "all") params.set("severity", severity);
  if (query) params.set("q", query);
  const summary = useQuery({
    queryKey: ["exception-summary", user, organizationId],
    queryFn: () => reviewRequest<ExceptionSummary>("/quarantine/summary", user, organizationId), retry: false,
  });
  const queue = useQuery({
    queryKey: ["exception-queue", user, organizationId, filter, severity, query, offset],
    queryFn: () => reviewRequest<ExceptionRecord[]>(`/quarantine?${params}`, user, organizationId), retry: false,
  });
  const selected = queue.data?.find(item => item.quarantine_id === selectedId) ?? queue.data?.[0];
  async function refresh() {
    await Promise.all([
      client.invalidateQueries({ queryKey: ["exception-queue", user, organizationId] }),
      client.invalidateQueries({ queryKey: ["exception-summary", user, organizationId] }),
      client.invalidateQueries({ queryKey: ["exception-history", user, organizationId] }),
    ]);
  }
  function resetSelection() { setOffset(0); setSelectedId(null); setNotice(""); }
  return <>
    <div className="review-workload" aria-label="Exception workload">
      <div><strong>{summary.data?.needs_attention ?? "—"}</strong><span>Need attention</span></div>
      <div><strong>{summary.data ? summary.data.by_severity.blocking ?? 0 : "—"}</strong><span>Blocking issues · all statuses</span></div>
      <div><strong>{summary.data?.total ?? "—"}</strong><span>Total issues</span></div>
      <button type="button" className="review-button quiet" disabled={queue.isFetching} onClick={() => void refresh()}>Refresh exceptions</button>
    </div>
    <ErrorNotice error={summary.error} />
    <div className="review-toolbar exception-toolbar">
      <label>Exception filter<select value={filter} onChange={event => { setFilter(event.target.value); resetSelection(); }}>
        <option value="needs_attention">Needs attention</option><option value="all">All statuses</option>
        {Object.entries(exceptionStatuses).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
      </select></label>
      <label>Severity<select value={severity} onChange={event => { setSeverity(event.target.value); resetSelection(); }}>
        <option value="all">All severities</option><option value="blocking">Blocking</option><option value="error">Error</option><option value="warning">Warning</option>
      </select></label>
      <form onSubmit={event => { event.preventDefault(); setQuery(search.trim()); resetSelection(); }}>
        <label htmlFor="exception-search">Search record or rule</label>
        <div><input id="exception-search" maxLength={100} value={search} onChange={event => setSearch(event.target.value)} /><button type="submit">Search</button></div>
      </form>
    </div>
    {notice && <p className="review-notice" role="status">{notice}</p>}
    <ErrorNotice error={queue.error} />
    {queue.isPending && <p role="status">Loading exceptions…</p>}
    {queue.data?.length === 0 && !queue.error && <div className="review-empty">
      <h3>No exceptions in this view.</h3><p>{summary.data?.total === 0 ? "Run a validation to create issues for this organization." : "Change the filters or search to find other issues."}</p>
    </div>}
    {queue.data && !queue.error && queue.data.length > 0 && <div className="review-layout">
      <ul className="candidate-list exception-queue" aria-label="Exceptions">
        {queue.data.map(issue => <li key={issue.quarantine_id}><button type="button"
          aria-pressed={selected?.quarantine_id === issue.quarantine_id} onClick={() => { setSelectedId(issue.quarantine_id); setNotice(""); }}>
          <strong>{issue.source_record_key}</strong><span>{issue.rule_title}</span>
          <small>{issue.severity} · {exceptionStatuses[issue.status]}</small>
        </button></li>)}
      </ul>
      {selected && <ExceptionDetail key={`${selected.quarantine_id}:${selected.revision}`} issue={selected} user={user}
        organizationId={organizationId} refresh={refresh} saved={async () => { setNotice("Resolution saved. The note and reviewer are recorded in history."); await refresh(); }} />}
    </div>}
    <div className="review-pagination" aria-label="Exception pagination">
      <button type="button" disabled={offset === 0 || queue.isFetching} onClick={() => { setOffset(offset - pageSize); setSelectedId(null); }}>Previous page</button>
      <span>Page {Math.floor(offset / pageSize) + 1}</span>
      <button type="button" disabled={!queue.data || queue.data.length < pageSize || queue.isFetching || queue.isError} onClick={() => { setOffset(offset + pageSize); setSelectedId(null); }}>Next page</button>
    </div>
  </>;
}

export function ExceptionDesk() {
  const [user, setUser] = useState("demo-admin");
  const [organizationId, setOrganizationId] = useState("");
  const organizations = useQuery({ queryKey: ["review-organizations", user], queryFn: () => reviewRequest<Organization[]>("/organizations", user), retry: false });
  const actor = useQuery({ queryKey: ["review-actor", user], queryFn: () => reviewRequest<Actor>("/me", user), retry: false });
  const activeOrganization = organizations.data?.find(item => item.id === organizationId) ?? organizations.data?.[0];
  const canReview = actor.data?.permissions.includes("validation:write");
  return <section className="view live-review live-exceptions" aria-labelledby="exceptions-title">
    <div className="view-heading"><div><p className="section-kicker">Data quality</p><h2 id="exceptions-title">Exception desk</h2></div><p className="view-intro">Review held records and record the next step.</p></div>
    <div className="review-session">
      <label>Local demo identity<select value={user} onChange={event => { setUser(event.target.value); setOrganizationId(""); }}>
        <option value="demo-admin">Demo administrator</option><option value="demo-viewer">Demo viewer</option>
      </select></label>
      <label>Organization<select value={activeOrganization?.id ?? ""} disabled={!organizations.data?.length} onChange={event => setOrganizationId(event.target.value)}>
        {!organizations.data?.length && <option value="">No organization available</option>}
        {organizations.data?.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}
      </select></label>
      {actor.data && <span>Signed in: {actor.data.display_name}</span>}
    </div>
    <ErrorNotice error={organizations.error ?? actor.error} />
    {(organizations.isPending || actor.isPending) && <p role="status">Connecting exception desk…</p>}
    {organizations.data?.length === 0 && <p className="review-notice">No accessible organizations.</p>}
    {actor.data && !canReview && <p className="review-notice">Your account cannot review exceptions.</p>}
    {activeOrganization && canReview && !organizations.error && !actor.error && <ExceptionQueue key={`${user}:${activeOrganization.id}`} user={user} organizationId={activeOrganization.id} />}
  </section>;
}
