import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import {
  reviewRequest, ReviewApiError, statusLabels,
  type Actor, type Decision, type MatchCandidate, type MatchDecision,
  type Organization, type QueueSummary,
} from "./reviewApi";

const pageSize = 20;

function ErrorNotice({ error }: { error: Error | null }) {
  return error ? <p className="review-notice error" role="alert">{error.message}</p> : null;
}

function CandidateDetail({ candidate, user, organizationId, onSaved, onRefresh }: {
  candidate: MatchCandidate;
  user: string;
  organizationId: string;
  onSaved: () => Promise<void>;
  onRefresh: () => void;
}) {
  const [decision, setDecision] = useState<Decision>("defer");
  const [reason, setReason] = useState("");
  const [historyOffset, setHistoryOffset] = useState(0);
  const history = useQuery({
    queryKey: ["review-history", user, organizationId, candidate.candidate_id, historyOffset],
    queryFn: () => reviewRequest<MatchDecision[]>(
      `/matches/${candidate.candidate_id}/decisions?limit=${pageSize}&offset=${historyOffset}`,
      user, organizationId,
    ),
    retry: false,
  });
  const save = useMutation({
    mutationFn: () => reviewRequest<MatchDecision>(
      `/matches/${candidate.candidate_id}/decisions`, user, organizationId,
      { decision, reason: reason.trim(), expected_revision: candidate.revision },
    ),
    onSuccess: onSaved,
    retry: false,
  });
  const conflict = save.error instanceof ReviewApiError && save.error.status === 409;
  function submit(event: FormEvent) {
    event.preventDefault();
    if (reason.trim() && !save.isPending && !conflict) save.mutate();
  }

  return (
    <article className="candidate-detail" aria-labelledby="candidate-title">
      <p className="section-kicker">Candidate evidence · revision {candidate.revision}</p>
      <h3 id="candidate-title">{candidate.left_record_key} ↔ {candidate.right_record_key}</h3>
      <div className="candidate-facts">
        <span>{statusLabels[candidate.status] ?? candidate.status}</span>
        <span>{candidate.score === null ? "Deterministic rule" : `Score ${(candidate.score * 100).toFixed(1)}%`}</span>
        <span>{candidate.decision_count} recorded decisions</span>
      </div>
      <p className="review-help">Scores suggest candidates. Review the rule, fingerprints, and conflicts before recording a decision. A decision does not merge source records.</p>
      <details open className="review-evidence">
        <summary>Comparison evidence</summary>
        <pre>{JSON.stringify(candidate.evidence, null, 2)}</pre>
      </details>
      {candidate.latest_decision && (
        <div className="latest-decision">
          <strong>Latest decision: {statusLabels[candidate.latest_decision.decision]}</strong>
          <p>{candidate.latest_decision.reason}</p>
        </div>
      )}
      <form className="review-form" onSubmit={submit}>
        <label htmlFor="review-decision">Decision</label>
        <select id="review-decision" value={decision} disabled={save.isPending} onChange={(event) => setDecision(event.target.value as Decision)}>
          <option value="defer">Defer for more evidence</option>
          <option value="match">Confirm match</option>
          <option value="no_match">Keep separate</option>
          <option value="escalate">Escalate to source owner</option>
        </select>
        <label htmlFor="review-reason">Reason for this decision</label>
        <textarea id="review-reason" value={reason} required maxLength={2000} rows={4}
          disabled={save.isPending} onChange={(event) => setReason(event.target.value)}
          placeholder="Describe the evidence and the next step." />
        <p className="review-help">The API records your identity, reason, and revision in the decision history and audit trail.</p>
        <ErrorNotice error={save.error} />
        {conflict && <button type="button" className="review-button quiet" onClick={onRefresh}>Refresh candidate</button>}
        <button type="submit" className="review-button" disabled={!reason.trim() || save.isPending || conflict}>
          {save.isPending ? "Saving decision…" : "Save decision"}
        </button>
      </form>
      <section className="review-history" aria-label="Decision history">
        <h4>Decision history</h4>
        <ErrorNotice error={history.error} />
        {history.isPending && <p role="status">Loading history…</p>}
        {history.data?.length === 0 && <p>No decisions on this page.</p>}
        <ol>
          {history.data?.map((item) => (
            <li key={item.id}>
              <strong>{statusLabels[item.decision]} · revision {item.revision}</strong>
              <p>{item.reason}</p>
              <small><time dateTime={item.decided_at}>{new Date(item.decided_at).toLocaleString()}</time> · reviewer <code>{item.reviewer_id}</code></small>
            </li>
          ))}
        </ol>
        {(candidate.decision_count > pageSize || historyOffset > 0) && <div className="review-pagination">
          <button type="button" disabled={historyOffset === 0 || history.isFetching || save.isPending} onClick={() => setHistoryOffset(historyOffset - pageSize)}>Newer decisions</button>
          <button type="button" disabled={!history.data || history.data.length < pageSize || history.isFetching || save.isPending} onClick={() => setHistoryOffset(historyOffset + pageSize)}>Older decisions</button>
        </div>}
      </section>
    </article>
  );
}

function OrganizationQueue({ user, organizationId }: { user: string; organizationId: string }) {
  const client = useQueryClient();
  const [filter, setFilter] = useState("needs_review");
  const [offset, setOffset] = useState(0);
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [notice, setNotice] = useState("");
  const params = new URLSearchParams({ limit: String(pageSize), offset: String(offset) });
  if (filter === "needs_review") params.set("needs_review", "true");
  else if (filter === "unreviewed") params.set("unreviewed", "true");
  else if (filter !== "all") params.set("status", filter);
  if (query) params.set("q", query);
  const summary = useQuery({
    queryKey: ["review-summary", user, organizationId],
    queryFn: () => reviewRequest<QueueSummary>("/matches/review-queue/summary", user, organizationId),
    retry: false,
  });
  const queue = useQuery({
    queryKey: ["review-queue", user, organizationId, filter, offset, query],
    queryFn: () => reviewRequest<MatchCandidate[]>(`/matches/review-queue?${params}`, user, organizationId),
    retry: false,
  });
  const selected = queue.data?.find((item) => item.candidate_id === selectedId) ?? queue.data?.[0];
  async function refresh() {
    await Promise.all([
      client.invalidateQueries({ queryKey: ["review-queue", user, organizationId] }),
      client.invalidateQueries({ queryKey: ["review-summary", user, organizationId] }),
      client.invalidateQueries({ queryKey: ["review-history", user, organizationId] }),
    ]);
  }
  const generate = useMutation({
    mutationFn: () => reviewRequest("/matches/probabilistic/synthetic", user, organizationId, {
      match_config_id: "person_probabilistic_v1", dataset_preset: "small",
    }),
    onSuccess: async () => {
      setNotice("Synthetic candidates created. Review their evidence below.");
      await refresh();
    },
    retry: false,
  });

  return (
    <>
      <div className="review-workload" aria-label="Review workload">
        <div><strong>{summary.data?.needs_review_candidates ?? "—"}</strong><span>Need attention</span></div>
        <div><strong>{summary.data?.unreviewed_candidates ?? "—"}</strong><span>Never reviewed</span></div>
        <div><strong>{summary.data?.total_candidates ?? "—"}</strong><span>Total candidates</span></div>
        <button type="button" className="review-button quiet" disabled={queue.isFetching || generate.isPending} onClick={() => void refresh()}>Refresh queue</button>
      </div>
      <ErrorNotice error={summary.error} />
      <div className="review-toolbar">
        <label>Queue filter
          <select value={filter} onChange={(event) => { setFilter(event.target.value); setOffset(0); setSelectedId(null); }}>
            <option value="needs_review">Needs attention</option>
            <option value="unreviewed">Never reviewed</option>
            <option value="all">All candidates</option>
            {Object.entries(statusLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </label>
        <form onSubmit={(event) => { event.preventDefault(); setQuery(search.trim()); setOffset(0); setSelectedId(null); }}>
          <label htmlFor="candidate-search">Search record keys</label>
          <div><input id="candidate-search" value={search} maxLength={100} onChange={(event) => setSearch(event.target.value)} /><button type="submit">Search</button></div>
        </form>
      </div>
      {notice && <p className="review-notice" role="status">{notice}</p>}
      <ErrorNotice error={queue.error} />
      {queue.isPending && <p role="status">Loading review queue…</p>}
      {queue.data?.length === 0 && !queue.error && <div className="review-empty">
        <h3>No candidates in this view.</h3>
        <p>Change the filter or search to find other candidates.</p>
        {summary.data?.total_candidates === 0 && <>
          <p>Create a small synthetic run to try this review workflow. It adds fictional candidates to this organization's local queue.</p>
          <button type="button" className="review-button" disabled={generate.isPending} onClick={() => generate.mutate()}>{generate.isPending ? "Creating candidates…" : "Generate synthetic candidates"}</button>
          <ErrorNotice error={generate.error} />
        </>}
      </div>}
      {queue.data && !queue.error && queue.data.length > 0 && <div className="review-layout">
        <ul className="candidate-list" aria-label="Match candidates">
          {queue.data.map((item) => <li key={item.candidate_id}>
            <button type="button" aria-pressed={selected?.candidate_id === item.candidate_id}
              onClick={() => { setSelectedId(item.candidate_id); setNotice(""); }}>
              <strong>{item.left_record_key}</strong><span>↔ {item.right_record_key}</span>
              <small>{statusLabels[item.status] ?? item.status} · {item.decision_count} decisions</small>
            </button>
          </li>)}
        </ul>
        {selected && <CandidateDetail key={`${selected.candidate_id}:${selected.revision}`} candidate={selected} user={user}
          organizationId={organizationId} onRefresh={() => void refresh()} onSaved={async () => {
            setNotice("Decision saved. Its reason and reviewer are recorded in the audit trail.");
            await refresh();
          }} />}
      </div>}
      <div className="review-pagination" aria-label="Queue pagination">
        <button type="button" disabled={offset === 0 || queue.isFetching} onClick={() => { setOffset(offset - pageSize); setSelectedId(null); }}>Previous page</button>
        <span>Page {Math.floor(offset / pageSize) + 1}</span>
        <button type="button" disabled={!queue.data || queue.data.length < pageSize || queue.isFetching || queue.isError} onClick={() => { setOffset(offset + pageSize); setSelectedId(null); }}>Next page</button>
      </div>
    </>
  );
}

export function ReviewDesk() {
  const [user, setUser] = useState("demo-admin");
  const [organizationId, setOrganizationId] = useState("");
  const organizations = useQuery({
    queryKey: ["review-organizations", user],
    queryFn: () => reviewRequest<Organization[]>("/organizations", user), retry: false,
  });
  const actor = useQuery({
    queryKey: ["review-actor", user],
    queryFn: () => reviewRequest<Actor>("/me", user), retry: false,
  });
  const activeOrganization = organizations.data?.find((item) => item.id === organizationId) ?? organizations.data?.[0];
  const canReview = actor.data?.permissions.includes("matching:write");

  return (
    <section className="view live-review" aria-labelledby="identity-title">
      <div className="view-heading">
        <div><p className="section-kicker">Live identity review</p><h2 id="identity-title">Evidence, a reason, and a recorded decision.</h2></div>
        <p className="view-intro">Decisions in this desk persist in the connected API. The local demo uses fictional records and explicit demo identities.</p>
      </div>
      <div className="review-session">
        <label>Local demo identity<select value={user} onChange={(event) => { setUser(event.target.value); setOrganizationId(""); }}>
          <option value="demo-admin">Demo administrator</option><option value="demo-viewer">Demo viewer</option>
        </select></label>
        <label>Organization<select value={activeOrganization?.id ?? ""} disabled={!organizations.data?.length} onChange={(event) => setOrganizationId(event.target.value)}>
          {!organizations.data?.length && <option value="">No organization available</option>}
          {organizations.data?.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
        </select></label>
        {actor.data && <span>Signed in: {actor.data.display_name}</span>}
      </div>
      <ErrorNotice error={organizations.error ?? actor.error} />
      {(organizations.isPending || actor.isPending) && <p role="status">Connecting review session…</p>}
      {organizations.data?.length === 0 && <p className="review-notice">No accessible organizations. Run migrations and seed the local demo first.</p>}
      {actor.data && !canReview && <p className="review-notice">Your account can view source metadata but cannot review identity candidates.</p>}
      {activeOrganization && canReview && !organizations.error && !actor.error && <OrganizationQueue key={`${user}:${activeOrganization.id}`} user={user} organizationId={activeOrganization.id} />}
    </section>
  );
}
