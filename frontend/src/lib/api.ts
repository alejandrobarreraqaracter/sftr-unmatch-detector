const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, options);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${body}`);
  }
  return res.json();
}

export interface Session {
  id: number;
  created_at: string;
  sft_type: string;
  action_type: string;
  level: string;
  emisor_name: string;
  emisor_lei: string;
  receptor_name: string;
  receptor_lei: string;
  uti: string;
  total_fields: number;
  total_unmatches: number;
  critical_count: number;
}

export interface FieldResult {
  id: number;
  session_id: number;
  table_number: number;
  field_number: number;
  field_name: string;
  obligation: string;
  emisor_value: string | null;
  receptor_value: string | null;
  result: "MATCH" | "UNMATCH" | "MIRROR" | "NA";
  severity: "CRITICAL" | "WARNING" | "INFO" | "NONE";
  status: "PENDING" | "IN_NEGOTIATION" | "RESOLVED" | "EXCLUDED";
  assignee: string | null;
  notes: string | null;
  validated: boolean;
  updated_at: string | null;
}

export interface SessionDetail extends Session {
  field_results: FieldResult[];
}

export interface SessionSummary {
  total_fields: number;
  total_unmatches: number;
  critical_count: number;
  warning_count: number;
  info_count: number;
  match_count: number;
  mirror_count: number;
  na_count: number;
  resolved_count: number;
  pending_count: number;
}

export interface ActivityLog {
  id: number;
  session_id: number;
  field_result_id: number | null;
  action: string;
  user: string;
  timestamp: string;
  detail: string | null;
}

export interface TopFieldItem {
  field_name: string;
  table_number: number;
  count: number;
}

export interface TrendItem {
  date: string;
  total_unmatches: number;
  critical_count: number;
  sessions: number;
}

export async function uploadFiles(emisorFile: File, receptorFile: File): Promise<Session> {
  const form = new FormData();
  form.append("emisor_file", emisorFile);
  form.append("receptor_file", receptorFile);
  return request<Session>("/api/sessions/upload", { method: "POST", body: form });
}

export async function getSessions(): Promise<Session[]> {
  return request<Session[]>("/api/sessions");
}

export async function getSession(id: number): Promise<SessionDetail> {
  return request<SessionDetail>(`/api/sessions/${id}`);
}

export async function getSessionSummary(id: number): Promise<SessionSummary> {
  return request<SessionSummary>(`/api/sessions/${id}/summary`);
}

export async function getActivity(id: number): Promise<ActivityLog[]> {
  return request<ActivityLog[]>(`/api/sessions/${id}/activity`);
}

export async function updateField(
  fieldId: number,
  data: { status?: string; assignee?: string; notes?: string; validated?: boolean }
): Promise<FieldResult> {
  return request<FieldResult>(`/api/fields/${fieldId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function bulkUpdate(
  sessionId: number,
  data: { action: string; assignee?: string }
): Promise<{ updated: number }> {
  return request<{ updated: number }>(`/api/sessions/${sessionId}/bulk-update`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export function exportUrl(sessionId: number, unmatches_only: boolean = false): string {
  return `${API_URL}/api/sessions/${sessionId}/export${unmatches_only ? "?unmatches_only=true" : ""}`;
}

export async function getTopFields(limit: number = 10): Promise<TopFieldItem[]> {
  return request<TopFieldItem[]>(`/api/analytics/top-fields?limit=${limit}`);
}

export async function getTrend(days: number = 30): Promise<TrendItem[]> {
  return request<TrendItem[]>(`/api/analytics/trend?days=${days}`);
}

export async function getByCounterparty(): Promise<
  { emisor_name: string; receptor_name: string; sessions: number; total_unmatches: number; critical_count: number }[]
> {
  return request(`/api/analytics/by-counterparty`);
}

export async function getBySftType(): Promise<
  { sft_type: string; sessions: number; total_unmatches: number; critical_count: number }[]
> {
  return request(`/api/analytics/by-sft-type`);
}
