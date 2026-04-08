const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, options);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${body}`);
  }
  return res.json();
}

// ─── Types ────────────────────────────────────────────────────────────────────

export interface Session {
  id: number;
  created_at: string;
  sft_type: string;
  action_type: string;
  emisor_name: string;
  receptor_name: string;
  filename: string | null;
  total_trades: number;
  total_fields: number;
  total_unmatches: number;
  critical_count: number;
  warning_count: number;
  trades_with_unmatches: number;
}

export interface TradeRecord {
  id: number;
  session_id: number;
  row_number: number;
  uti: string | null;
  sft_type: string | null;
  action_type: string | null;
  emisor_lei: string | null;
  receptor_lei: string | null;
  total_fields: number;
  total_unmatches: number;
  critical_count: number;
  warning_count: number;
  has_unmatches: boolean;
}

export interface FieldComparison {
  id: number;
  trade_id: number;
  session_id: number;
  table_number: number;
  field_number: number;
  field_name: string;
  obligation: string | null;
  emisor_value: string | null;
  receptor_value: string | null;
  result: "MATCH" | "UNMATCH" | "MIRROR" | "NA";
  severity: "CRITICAL" | "WARNING" | "INFO" | "NONE";
  root_cause: string | null;
  status: "PENDING" | "IN_NEGOTIATION" | "RESOLVED" | "EXCLUDED";
  assignee: string | null;
  notes: string | null;
  validated: boolean;
  updated_at: string | null;
}

export interface SessionDetail extends Session {
  trades: TradeRecord[];
}

export interface TradeDetail extends TradeRecord {
  field_comparisons: FieldComparison[];
}

export interface SessionSummary {
  total_trades: number;
  trades_with_unmatches: number;
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
  trade_id: number | null;
  field_comparison_id: number | null;
  action: string;
  user: string | null;
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

// ─── API calls ────────────────────────────────────────────────────────────────

export async function uploadFile(
  file: File,
  emisorName: string,
  receptorName: string,
): Promise<Session> {
  const form = new FormData();
  form.append("file", file);
  form.append("emisor_name", emisorName);
  form.append("receptor_name", receptorName);
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

export async function getTrade(tradeId: number): Promise<TradeDetail> {
  return request<TradeDetail>(`/api/trades/${tradeId}`);
}

export async function updateFieldComparison(
  fcId: number,
  data: { status?: string; assignee?: string; notes?: string; validated?: boolean }
): Promise<FieldComparison> {
  return request<FieldComparison>(`/api/field-comparisons/${fcId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function bulkUpdate(
  sessionId: number,
  data: { action: string; assignee?: string; trade_id?: number }
): Promise<{ updated: number }> {
  return request<{ updated: number }>(`/api/sessions/${sessionId}/bulk-update`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export function exportUrl(sessionId: number, unmatches_only = false): string {
  return `${API_URL}/api/sessions/${sessionId}/export${unmatches_only ? "?only_unmatches=true" : ""}`;
}

// ─── AI ───────────────────────────────────────────────────────────────────────

export interface AIStatus {
  provider: string;
  model: string;
  available: boolean;
}

export interface FieldAnalysis {
  field_id: number;
  field_name: string;
  explanation: string;
  resolution_steps: string[];
  regulatory_risk: string;
}

export interface TradeAnalysis {
  trade_id: number;
  uti: string | null;
  summary: string;
  priority_field: string | null;
  main_risk: string | null;
  recommended_action: string | null;
}

export interface SessionNarrative {
  session_id: number;
  provider: string;
  model: string;
  narrative: string;
}

export async function getAIStatus(): Promise<AIStatus> {
  return request<AIStatus>("/api/ai/status");
}

export async function analyzeField(fcId: number): Promise<FieldAnalysis> {
  return request<FieldAnalysis>(`/api/ai/field-comparisons/${fcId}/analyze`, { method: "POST" });
}

export async function analyzeTrade(tradeId: number): Promise<TradeAnalysis> {
  return request<TradeAnalysis>(`/api/ai/trades/${tradeId}/analyze`, { method: "POST" });
}

export async function generateNarrative(sessionId: number): Promise<SessionNarrative> {
  return request<SessionNarrative>(`/api/ai/sessions/${sessionId}/narrative`, { method: "POST" });
}

export async function getTopFields(limit = 10): Promise<TopFieldItem[]> {
  return request<TopFieldItem[]>(`/api/analytics/top-fields?limit=${limit}`);
}

export async function getTrend(days = 30): Promise<TrendItem[]> {
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
