import { useQuery } from "@tanstack/react-query";

interface VersionResponse {
  version: string;
  maturity: string;
  completed_phases: number[];
}

async function fetchVersion(): Promise<VersionResponse> {
  const response = await fetch(`${import.meta.env.VITE_API_BASE_URL ?? ""}/api/v1/version`);
  if (!response.ok) throw new Error("Version endpoint is unavailable");
  return response.json() as Promise<VersionResponse>;
}

export function App() {
  const version = useQuery({ queryKey: ["version"], queryFn: fetchVersion, retry: false });

  return (
    <main>
      <header>
        <p className="eyebrow">Governance-ready data foundation</p>
        <h1>EduWork DataBridge</h1>
        <p className="lede">
          An industry-neutral framework for documented, validated, traceable learning and workforce data.
        </p>
      </header>
      <section aria-labelledby="maturity-heading" className="panel">
        <h2 id="maturity-heading">Current prototype boundary</h2>
        <p>Blueprint Phases 0–14 are implemented as a documented, benchmarked, security-reviewed release candidate with reproducible evidence and explicit pre-production limits.</p>
        <div className="status" role="status">
          {version.isLoading && "Checking API…"}
          {version.isError && "API not connected; the static shell remains available."}
          {version.data && `Version ${version.data.version} · ${version.data.maturity} · phases ${version.data.completed_phases.join(", ")}`}
        </div>
      </section>
      <section className="grid" aria-label="Foundation capabilities">
        <article><h2>Canonical model</h2><p>Industry-neutral people, organizations, programs, offerings, participation, assessments, competencies, and credentials.</p></article>
        <article><h2>Control plane</h2><p>Versioned source, contract, mapping, rule, review, lineage, export, audit, and access metadata.</p></article>
        <article><h2>Claim discipline</h2><p>No production pipeline, partner deployment, certification, or outcome is implied by the Phase 2 foundation.</p></article>
      </section>
    </main>
  );
}
