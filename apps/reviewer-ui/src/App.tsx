import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import {
  fallbackSummary,
  issueDefinitions,
  pipelineStages,
  type DemoSummaryResponse,
  type IssueCategory,
  type VersionResponse,
  type ViewKey,
} from "./demoData";

const apiBase = import.meta.env.VITE_API_BASE_URL ?? "";
const staticDemo = import.meta.env.VITE_STATIC_DEMO === "true";
const siteBase = import.meta.env.BASE_URL;
const docsHref = `${siteBase}docs/`;
const fieldGuideHref = `${docsHref}EduWork_DataBridge_Field_Guide.pdf`;
const themeStorageKey = "eduwork-databridge-theme";

type Theme = "light" | "dark";

function getInitialTheme(): Theme {
  if (typeof window === "undefined") return "light";

  try {
    const savedTheme = window.localStorage.getItem(themeStorageKey);
    if (savedTheme === "light" || savedTheme === "dark") return savedTheme;
  } catch {
    // A private browsing policy may make storage unavailable. The system preference still works.
  }

  return typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

async function fetchJson<Response>(path: string): Promise<Response> {
  const response = await fetch(`${apiBase}${path}`);
  if (!response.ok) throw new Error(`Request failed with status ${response.status}`);
  return response.json() as Promise<Response>;
}

const navigation: { key: ViewKey; label: string }[] = [
  { key: "overview", label: "Case overview" },
  { key: "sources", label: "Source checks" },
  { key: "exceptions", label: "Exceptions" },
  { key: "identity", label: "Identity review" },
  { key: "evidence", label: "Evidence trail" },
];

function formatNumber(value: number | undefined) {
  return new Intl.NumberFormat("en-US").format(value ?? 0);
}

function Overview({ issueTotal }: { issueTotal: number }) {
  const [selectedStage, setSelectedStage] = useState(0);
  const stage = pipelineStages[selectedStage];

  return (
    <section className="view" aria-labelledby="overview-title">
      <div className="view-heading">
        <div>
          <p className="section-kicker">A five-stop evidence path</p>
          <h2 id="overview-title">Follow the answer, not the architecture diagram.</h2>
        </div>
        <p className="view-intro">
          The small fixture contains {issueTotal} deliberately planted problems. Pick a stop to see
          what a reviewer should be able to learn there.
        </p>
      </div>
      <ol className="stage-list">
        {pipelineStages.map((item, index) => (
          <li key={item.key}>
            <button
              className={index === selectedStage ? "stage-button active" : "stage-button"}
              aria-pressed={index === selectedStage}
              onClick={() => setSelectedStage(index)}
            >
              <span>{item.number}</span>
              {item.label}
            </button>
          </li>
        ))}
      </ol>
      <div className="stage-detail" aria-live="polite">
        <p className="detail-number">STOP {stage.number}</p>
        <div>
          <h3>{stage.title}</h3>
          <p>{stage.body}</p>
        </div>
        <p className="evidence-note">Evidence here: {stage.evidence}</p>
      </div>
      <div className="overview-grid">
        <article className="question-card">
          <p className="section-kicker">The working question</p>
          <h3>Who finished cybersecurity training, passed the assessment, and has a valid credential?</h3>
          <p>
            The answer crosses four source systems. DataBridge keeps each join, exception, and rule
            visible so a reviewer can defend the final list.
          </p>
        </article>
        <article className="principle-card">
          <p className="section-kicker">The operating principle</p>
          <blockquote>When the evidence is uncertain, the software should say so.</blockquote>
          <p>Ambiguous identity matches and material data errors belong in a review queue.</p>
        </article>
      </div>
    </section>
  );
}

function Sources({ summary }: { summary: DemoSummaryResponse }) {
  const sources = [
    { system: "HRIS", file: "employees.csv", detail: "People", count: summary.counts.hris_people },
    { system: "LMS", file: "participation.json", detail: "Learning events", count: summary.counts.lms_participations },
    { system: "Assessment", file: "assessment_results.xlsx", detail: "Results", count: summary.counts.assessment_results },
    { system: "Credential", file: "credential_awards.parquet", detail: "Awards", count: summary.counts.credential_awards },
  ];

  return (
    <section className="view" aria-labelledby="sources-title">
      <div className="view-heading">
        <div>
          <p className="section-kicker">Source checks</p>
          <h2 id="sources-title">Four systems. Four versions of the story.</h2>
        </div>
        <p className="view-intro">Every file below is synthetic, deterministic, and checksummed in the fixture manifest.</p>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr><th>System</th><th>Public fixture</th><th>What it contributes</th><th>Rows</th><th>Evidence</th></tr>
          </thead>
          <tbody>
            {sources.map((source) => (
              <tr key={source.system}>
                <td><strong>{source.system}</strong></td>
                <td><code>{source.file}</code></td>
                <td>{source.detail}</td>
                <td>{formatNumber(source.count)}</td>
                <td><span className="status-pill good"><span />Checksummed</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="manifest-note">
        <span className="manifest-mark">S</span>
        <div><strong>Synthetic by design</strong><p>{summary.privacy_notice}</p></div>
        <code>seed {summary.seed}</code>
      </div>
    </section>
  );
}

function Exceptions({ summary }: { summary: DemoSummaryResponse }) {
  const filters: ("All" | IssueCategory)[] = ["All", "Data quality", "Timing", "Identity"];
  const [filter, setFilter] = useState<(typeof filters)[number]>("All");
  const [selectedKey, setSelectedKey] = useState("missing_employee_id");
  const visibleIssues = issueDefinitions.filter((issue) => filter === "All" || issue.category === filter);
  const selected = issueDefinitions.find((issue) => issue.key === selectedKey) ?? issueDefinitions[0];

  return (
    <section className="view" aria-labelledby="exceptions-title">
      <div className="view-heading">
        <div>
          <p className="section-kicker">Exception desk</p>
          <h2 id="exceptions-title">A short queue with reasons, not a mystery error log.</h2>
        </div>
        <p className="view-intro">Counts are planted conditions in the small public fixture. A person can inspect the rule before deciding what happens next.</p>
      </div>
      <div className="filter-row" aria-label="Filter exception types">
        {filters.map((item) => (
          <button key={item} aria-pressed={filter === item} onClick={() => setFilter(item)}>{item}</button>
        ))}
      </div>
      <div className="exception-layout">
        <ul className="exception-list" aria-label="Synthetic exception types">
          {visibleIssues.map((issue) => (
            <li key={issue.key}>
              <button
                className={selected.key === issue.key ? "exception-row active" : "exception-row"}
                onClick={() => setSelectedKey(issue.key)}
              >
                <span className={`issue-dot ${issue.tone}`} />
                <span><strong>{issue.label}</strong><small>{issue.category}</small></span>
                <b>{summary.defect_summary[issue.key] ?? 0}</b>
              </button>
            </li>
          ))}
        </ul>
        <article className="exception-detail" aria-live="polite">
          <span className={`tone-label ${selected.tone}`}>{selected.tone === "blocked" ? "Hold" : "Review"}</span>
          <p className="section-kicker">Example from the fixture</p>
          <h3>{selected.example}</h3>
          <p>{summary.defect_catalog[selected.key]}</p>
          <div className="next-step"><span>Next step</span><p>{selected.nextStep}</p></div>
        </article>
      </div>
    </section>
  );
}

function IdentityReview() {
  const [decision, setDecision] = useState("Pending review");

  return (
    <section className="view" aria-labelledby="identity-title">
      <div className="view-heading">
        <div>
          <p className="section-kicker">Identity review</p>
          <h2 id="identity-title">A likely match still deserves a reason.</h2>
        </div>
        <p className="view-intro">This interaction is a UI preview. It does not write a decision to the API, and it resets on refresh.</p>
      </div>
      <div className="identity-layout">
        <article className="record-card">
          <div className="record-source"><span>HR</span><strong>HRIS record</strong></div>
          <h3>Elena Ibrahim</h3>
          <dl><div><dt>Employee ID</dt><dd>EMP-0000005</dd></div><div><dt>Department</dt><dd>People</dd></div><div><dt>Status</dt><dd>Active</dd></div></dl>
        </article>
        <div className="match-score"><span>Trusted ID agrees</span><strong>Review</strong><small>Duplicate account detected</small></div>
        <article className="record-card">
          <div className="record-source"><span>LM</span><strong>LMS records</strong></div>
          <h3>Elena Ibrahim</h3>
          <dl><div><dt>Primary account</dt><dd>LMS-0000005</dd></div><div><dt>Second account</dt><dd>LMS-DUP-0000005</dd></div><div><dt>Evidence</dt><dd>2 source rows</dd></div></dl>
        </article>
      </div>
      <div className="decision-bar">
        <div><p className="section-kicker">Current preview decision</p><strong aria-live="polite">{decision}</strong></div>
        <div className="decision-actions">
          <button onClick={() => setDecision("Link accounts")}>Link accounts</button>
          <button onClick={() => setDecision("Keep separate")}>Keep separate</button>
          <button className="quiet" onClick={() => setDecision("Deferred")}>Defer</button>
        </div>
      </div>
    </section>
  );
}

function Evidence() {
  return (
    <section className="view" aria-labelledby="evidence-title">
      <div className="view-heading">
        <div>
          <p className="section-kicker">Evidence trail</p>
          <h2 id="evidence-title">The report row comes with a route home.</h2>
        </div>
        <p className="view-intro">A reviewer can trace a field backward without relying on the person who built the pipeline.</p>
      </div>
      <div className="lineage" aria-label="Example lineage path">
        <div><span>01</span><small>Raw snapshot</small><strong>HRIS employees</strong><code>sha256: 66dcf6…</code></div>
        <i aria-hidden="true">→</i>
        <div><span>02</span><small>Mapping rule</small><strong>hris_person_v1</strong><code>version 1</code></div>
        <i aria-hidden="true">→</i>
        <div><span>03</span><small>Governed mart</small><strong>Training status</strong><code>field documented</code></div>
        <i aria-hidden="true">→</i>
        <div className="lineage-output"><span>04</span><small>Masked export</small><strong>CSV / Parquet</strong><code>permission gated</code></div>
      </div>
      <div className="boundary-grid">
        <article><p className="section-kicker">What this build demonstrates</p><ul><li>Repeatable synthetic processing</li><li>Visible validation and match evidence</li><li>Documented, permission-aware outputs</li></ul></article>
        <article><p className="section-kicker">What still needs a real pilot</p><ul><li>Partner-specific mappings and ownership</li><li>Production identity and infrastructure checks</li><li>Measured time, cost, and quality outcomes</li></ul></article>
      </div>
    </section>
  );
}

export function App() {
  const [view, setView] = useState<ViewKey>("overview");
  const [theme, setTheme] = useState<Theme>(getInitialTheme);
  const version = useQuery({
    queryKey: ["version"],
    queryFn: () => fetchJson<VersionResponse>("/api/v1/version"),
    retry: false,
    enabled: !staticDemo,
  });
  const summaryQuery = useQuery({
    queryKey: ["demo-summary"],
    queryFn: () => fetchJson<DemoSummaryResponse>("/api/v1/demo/summary"),
    retry: false,
    enabled: !staticDemo,
  });
  const summary = summaryQuery.data ?? fallbackSummary;
  const issueTotal = useMemo(
    () => Object.values(summary.defect_summary).reduce((total, count) => total + count, 0),
    [summary],
  );

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.colorScheme = theme;
    document
      .querySelector('meta[name="theme-color"]')
      ?.setAttribute("content", theme === "dark" ? "#110e06" : "#16373a");

    try {
      window.localStorage.setItem(themeStorageKey, theme);
    } catch {
      // Theme switching should remain usable even when storage is blocked.
    }
  }, [theme]);

  const currentView = {
    overview: <Overview issueTotal={issueTotal} />,
    sources: <Sources summary={summary} />,
    exceptions: <Exceptions summary={summary} />,
    identity: <IdentityReview />,
    evidence: <Evidence />,
  }[view];

  return (
    <>
      <a className="skip-link" href="#workspace">Skip to review workspace</a>
      <header className="site-header">
        <a className="wordmark" href="#top" aria-label="EduWork DataBridge home">
          <i className="bridge-mark" aria-hidden="true"><span /><span /></i>
          <span><small>EDUWORK</small><b>DataBridge</b></span>
        </a>
        <nav className="site-nav" aria-label="Product navigation">
          <a href="#story">Why it exists</a>
          <a href="#workspace">Reviewer desk</a>
          <a href="#contribution">Contribution</a>
          <a href={docsHref}>Documentation</a>
        </nav>
        <div className="header-actions">
          <div className="api-state" role="status">
            <span className={staticDemo ? "static" : version.data ? "live" : version.isLoading ? "checking" : "offline"} />
            {staticDemo
              ? "Synthetic demo"
              : version.data
                ? `API ${version.data.version}`
                : version.isLoading
                  ? "Checking local API"
                  : "Preview data"}
          </div>
          <button
            className="theme-toggle"
            type="button"
            aria-pressed={theme === "dark"}
            aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
            onClick={() => setTheme((current) => (current === "dark" ? "light" : "dark"))}
          >
            <span className="theme-toggle-track" aria-hidden="true">
              <span className="theme-toggle-stars"><i /><i /><i /></span>
              <span className="theme-toggle-cloud" />
              <span className="theme-toggle-thumb" />
            </span>
            <span className="theme-toggle-label">{theme === "dark" ? "Light" : "Dark"}</span>
          </button>
          <a className="header-cta" href="#workspace">Open the case</a>
        </div>
      </header>

      <main id="top">
        <section className="hero" aria-labelledby="page-title">
          <div className="hero-copy">
            <p className="hero-kicker"><span>Open-source reference</span> Learning + workforce data</p>
            <h1 id="page-title"><em>Can we trust</em> the training report?</h1>
            <p className="hero-lede">The employee list lives in HR. Completions live in the LMS. Scores and credentials arrive in two more files. DataBridge turns that hand-built reconciliation into a trail people can inspect.</p>
            <div className="hero-actions">
              <a className="button primary" href="#workspace">Walk the evidence path <span aria-hidden="true">↘</span></a>
              <a className="button text" href="#story">Read the Monday story <span aria-hidden="true">→</span></a>
            </div>
            <div className="hero-footnote">
              <span>Public reference build · v0.15.0</span>
              <p>No customer records. No hidden matches. No outcome claims.</p>
            </div>
          </div>
          <aside className="evidence-board" aria-label="Synthetic case evidence path">
            <div className="board-topline">
              <span>CASE 07–26</span>
              <b>Northstar Learning Labs</b>
              <i>Synthetic</i>
            </div>
            <blockquote>“Who finished the training, passed, and received the credential?”</blockquote>
            <div className="source-map" aria-label="Four source systems converge on one reviewed answer">
              <div className="source-stack">
                <span><b>HR</b><small>120 people</small></span>
                <span><b>LMS</b><small>366 events</small></span>
                <span><b>TEST</b><small>120 results</small></span>
                <span><b>AWARD</b><small>25 records</small></span>
              </div>
              <div className="route-lines" aria-hidden="true"><i /><i /><i /><i /></div>
              <div className="review-node">
                <small>REVIEW FIRST</small>
                <strong>{issueTotal}</strong>
                <span>planted problems</span>
              </div>
            </div>
            <div className="board-result"><span>?</span><p><b>The report is not the evidence.</b><small>The route to the answer is.</small></p></div>
          </aside>
        </section>

        <section className="story-section" id="story" aria-labelledby="story-title">
          <div className="story-heading">
            <p className="section-kicker">Monday · 9:07 a.m.</p>
            <h2 id="story-title">A familiar request. An answer spread across four systems.</h2>
          </div>
          <div className="story-steps">
            <article>
              <span>01</span>
              <p className="story-time">The request</p>
              <h3>Leadership needs one defensible training list.</h3>
              <p>The question sounds simple until HR, learning, assessment, and credential records disagree.</p>
            </article>
            <article>
              <span>02</span>
              <p className="story-time">The awkward middle</p>
              <h3>Names drift. IDs disappear. Dates arrive out of order.</h3>
              <p>Those records should not vanish into spreadsheet formulas or a silent fuzzy match.</p>
            </article>
            <article>
              <span>03</span>
              <p className="story-time">Before publishing</p>
              <h3>Keep the source, show the rule, and surface uncertainty.</h3>
              <p>DataBridge makes the reconciliation reviewable before anyone treats it as fact.</p>
            </article>
          </div>
        </section>

        <section className="metric-strip" aria-label="Synthetic fixture summary">
          <div><strong>{formatNumber(summary.counts.hris_people)}</strong><span>people in HRIS</span></div>
          <div><strong>{formatNumber(summary.counts.lms_participations)}</strong><span>learning events</span></div>
          <div><strong>{formatNumber(summary.counts.assessment_results)}</strong><span>assessment results</span></div>
          <div><strong>{formatNumber(summary.counts.credential_awards)}</strong><span>credential awards</span></div>
          <p><b>SYNTHETIC</b> Safe to inspect. Not a customer outcome.</p>
        </section>

        <div className="workspace-intro">
          <div>
            <p className="section-kicker">Interactive case file</p>
            <h2>Follow one answer from raw source to governed output.</h2>
          </div>
          <p>Move through the five review stops. The examples are small enough to understand and concrete enough to challenge.</p>
        </div>

        <div className="workspace-shell" id="workspace">
          <nav className="workspace-nav" aria-label="Reviewer console sections">
            <p>REVIEW DESK</p>
            {navigation.map((item, index) => (
              <button key={item.key} className={view === item.key ? "active" : ""} aria-current={view === item.key ? "page" : undefined} onClick={() => setView(item.key)}>
                <span>0{index + 1}</span>{item.label}
                {item.key === "exceptions" && <b>{issueTotal}</b>}
              </button>
            ))}
            <div className="nav-footnote"><span>Reference build</span><p>Phases 0–14 complete. Production checks and partner validation remain.</p></div>
          </nav>
          <div className="workspace-content">{currentView}</div>
        </div>

        <section className="contribution" id="contribution" aria-labelledby="contribution-title">
          <div className="contribution-heading">
            <p className="section-kicker">The contribution</p>
            <h2 id="contribution-title">Data integration is easy to hide. DataBridge makes it inspectable.</h2>
            <p>Not another dashboard—a reusable way to preserve evidence while records are cleaned, linked, checked, and released.</p>
          </div>
          <div className="principle-grid">
            <article><span>01</span><h3>Evidence travels</h3><p>Checksums, source context, rules, and lineage stay attached to the answer.</p></article>
            <article><span>02</span><h3>Bad rows have a path</h3><p>Material problems are explained and held for review instead of quietly disappearing.</p></article>
            <article><span>03</span><h3>Identity stays conservative</h3><p>A likely match can be suggested. A trusted-ID conflict cannot be wished away.</p></article>
          </div>
        </section>

        <section className="resource-cta" aria-labelledby="resource-title">
          <div>
            <p className="section-kicker">Inspect the work</p>
            <h2 id="resource-title">Start with the story. Stay for the evidence.</h2>
            <p>Read the five-page field guide, explore the technical documentation, or inspect the source and synthetic fixtures.</p>
          </div>
          <div className="resource-links">
            <a className="button light" href={fieldGuideHref}>Open the field guide <span aria-hidden="true">↗</span></a>
            <a className="button outline" href={docsHref}>Browse documentation <span aria-hidden="true">→</span></a>
            <a className="quiet-link" href="https://github.com/imtiazither/eduwork-databridge">View the repository</a>
          </div>
        </section>
      </main>

      <footer>
        <a className="footer-mark" href="#top"><i className="bridge-mark" aria-hidden="true"><span /><span /></i><span>EduWork DataBridge</span></a>
        <p>Open-source reference implementation · Apache-2.0 · public examples use synthetic data only</p>
        <div><a href={docsHref}>Docs</a><a href={fieldGuideHref}>Field guide</a><a href="https://github.com/imtiazither/eduwork-databridge">GitHub</a></div>
      </footer>
    </>
  );
}
