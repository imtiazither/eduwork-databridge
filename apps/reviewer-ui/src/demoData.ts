export interface VersionResponse {
  version: string;
  maturity: string;
  completed_phases: number[];
}

export interface DemoSummaryResponse {
  preset: string;
  seed: number;
  generated_at: string;
  synthetic: boolean;
  privacy_notice: string;
  counts: Record<string, number>;
  defect_summary: Record<string, number>;
  defect_catalog: Record<string, string>;
}

export type ViewKey = "overview" | "sources" | "exceptions" | "identity" | "evidence";
export type IssueCategory = "Data quality" | "Timing" | "Identity";

export interface IssueDefinition {
  key: string;
  label: string;
  category: IssueCategory;
  tone: "attention" | "review" | "blocked";
  example: string;
  nextStep: string;
}

export const fallbackSummary: DemoSummaryResponse = {
  preset: "small",
  seed: 20260719,
  generated_at: "2026-07-19T00:00:00+00:00",
  synthetic: true,
  privacy_notice:
    "All records are deterministic synthetic fixtures. They do not describe real people or organizations.",
  counts: {
    assessment_results: 120,
    credential_awards: 25,
    hris_people: 120,
    identity_truth_rows: 120,
    lms_courses: 6,
    lms_participations: 366,
  },
  defect_summary: {
    completion_before_assignment: 5,
    conflicting_department: 3,
    credential_before_assessment: 1,
    duplicate_lms_account: 6,
    formula_like_text: 1,
    invalid_completion_status: 7,
    late_event: 2,
    missing_employee_id: 9,
    name_variant: 9,
  },
  defect_catalog: {
    completion_before_assignment: "Completion timestamp precedes assignment timestamp.",
    conflicting_department: "HRIS and LMS department codes disagree.",
    credential_before_assessment: "Credential award precedes the qualifying assessment.",
    duplicate_lms_account: "One synthetic person has two LMS accounts.",
    formula_like_text: "A harmless synthetic text value begins with a spreadsheet formula character.",
    invalid_completion_status: "LMS status contains a value outside the approved code set.",
    late_event: "A learning event arrives after the expected reporting window.",
    missing_employee_id: "HRIS employee identifier is blank while related systems retain an ID.",
    name_variant: "LMS name contains spacing, punctuation, or nickname variation.",
  },
};

export const issueDefinitions: IssueDefinition[] = [
  {
    key: "missing_employee_id",
    label: "Missing employee ID",
    category: "Identity",
    tone: "blocked",
    example: "Carlos Hassan · HRIS row 22",
    nextStep: "Hold the row until an approved identifier is supplied.",
  },
  {
    key: "name_variant",
    label: "Name needs normalization",
    category: "Identity",
    tone: "review",
    example: "Samira Williams · double-spaced uppercase LMS name",
    nextStep: "Compare trusted IDs before accepting a name-based candidate.",
  },
  {
    key: "invalid_completion_status",
    label: "Unknown completion status",
    category: "Data quality",
    tone: "attention",
    example: 'Hiro Johnson · status "done-ish"',
    nextStep: "Map an approved source value or quarantine the record.",
  },
  {
    key: "duplicate_lms_account",
    label: "Duplicate LMS account",
    category: "Identity",
    tone: "review",
    example: "Elena Ibrahim · LMS-0000005 and LMS-DUP-0000005",
    nextStep: "Review the two accounts as one candidate set; do not merge silently.",
  },
  {
    key: "completion_before_assignment",
    label: "Completion predates assignment",
    category: "Timing",
    tone: "blocked",
    example: "Olivia Taylor · completed two days before assignment",
    nextStep: "Confirm the dates with the source owner before publication.",
  },
  {
    key: "conflicting_department",
    label: "Department conflict",
    category: "Data quality",
    tone: "review",
    example: "HRIS and LMS disagree for three synthetic records",
    nextStep: "Apply the named source-of-record rule and retain both source values.",
  },
  {
    key: "late_event",
    label: "Late learning event",
    category: "Timing",
    tone: "attention",
    example: "Two LMS events missed the expected reporting window",
    nextStep: "Flag the report as incomplete until the late-arrival window closes.",
  },
  {
    key: "credential_before_assessment",
    label: "Credential predates assessment",
    category: "Timing",
    tone: "blocked",
    example: "One award appears before its qualifying assessment",
    nextStep: "Quarantine the award and request source confirmation.",
  },
  {
    key: "formula_like_text",
    label: "Formula-like export value",
    category: "Data quality",
    tone: "attention",
    example: "One harmless test string begins with an equals sign",
    nextStep: "Escape the value before a spreadsheet export is opened.",
  },
];

export const pipelineStages = [
  {
    key: "collect",
    number: "01",
    label: "Collect",
    title: "Keep the original evidence",
    body: "Read approved files without changing them. Save a checksum, source name, timestamp, and run ID so the starting point can be proved later.",
    evidence: "Six source files · checksums in the public manifest",
  },
  {
    key: "check",
    number: "02",
    label: "Check",
    title: "Find the awkward records early",
    body: "Profile structure and test business rules before the data reaches a report. A bad row is explained and held, not quietly dropped.",
    evidence: "Nine planted issue types · 43 planted occurrences",
  },
  {
    key: "connect",
    number: "03",
    label: "Connect",
    title: "Link people with restraint",
    body: "Use organization-scoped trusted IDs first. Conflicts and gray-zone matches stay visible for a person to review.",
    evidence: "Identity truth set · reversible review decisions",
  },
  {
    key: "publish",
    number: "04",
    label: "Publish",
    title: "Release only governed outputs",
    body: "Create a documented mart or masked export only after checks pass and permissions are confirmed.",
    evidence: "CSV and Parquet outputs · dictionary and retention metadata",
  },
  {
    key: "trace",
    number: "05",
    label: "Trace",
    title: "Answer: where did this number come from?",
    body: "Follow a report field back through the export, mart, rule, and raw snapshot. The explanation travels with the result.",
    evidence: "Run and field lineage · audit events",
  },
] as const;

