export const exceptionStatuses: Record<string, string> = {
  open: "Open", acknowledged: "Acknowledged", corrected_upstream: "Corrected at source",
  corrected_mapping: "Mapping corrected", waived: "Waived", closed: "Closed",
};

export interface ExceptionRecord {
  quarantine_id: string;
  source_record_key: string;
  field_name: string | null;
  evidence_masked: string | null;
  explanation: string;
  status: string;
  revision: number;
  created_at: string;
  raw_snapshot_id: string;
  supersedes_quarantine_id: string | null;
  rule_key: string;
  rule_title: string;
  severity: string;
  remediation: string | null;
}

export interface Resolution {
  id: string;
  quarantine_id: string;
  revision: number;
  status: string;
  note: string;
  reviewer_id: string | null;
  recorded_at: string;
  corrected_snapshot_id: string | null;
  imported: boolean;
}

export interface ExceptionSummary {
  total: number;
  needs_attention: number;
  by_status: Record<string, number>;
  by_severity: Record<string, number>;
}
