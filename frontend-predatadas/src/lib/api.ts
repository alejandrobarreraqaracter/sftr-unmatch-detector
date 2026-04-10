const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
export type ProductType = "sftr" | "predatadas";
const DEFAULT_PRODUCT_TYPE: ProductType = "predatadas";

export type DemoUser = {
  username: string;
  display_name: string;
};

const DEMO_USER_STORAGE_KEY = "predatadas-demo-user";

export function getStoredDemoUser(): DemoUser | null {
  const raw = window.localStorage.getItem(DEMO_USER_STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as DemoUser;
  } catch {
    window.localStorage.removeItem(DEMO_USER_STORAGE_KEY);
    return null;
  }
}

export function setStoredDemoUser(user: DemoUser | null) {
  if (!user) {
    window.localStorage.removeItem(DEMO_USER_STORAGE_KEY);
    return;
  }
  window.localStorage.setItem(DEMO_USER_STORAGE_KEY, JSON.stringify(user));
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const headers = new Headers(options?.headers);
  const demoUser = getStoredDemoUser();
  if (demoUser?.username) {
    headers.set("X-Demo-User", demoUser.username);
  }
  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
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
  product_type: "sftr" | "predatadas";
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
  pairing_status: "UNPAIR" | "UNMATCH" | null;
  pairing_reason: string | null;
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
  difference_value: number | null;
  difference_unit: string | null;
  difference_display: string | null;
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

export interface AnalyticsOverview {
  date_from: string | null;
  date_to: string | null;
  sessions: number;
  total_trades: number;
  trades_with_unmatches: number;
  total_unmatches: number;
  critical_count: number;
  warning_count: number;
  unpair_trades: number;
  unmatch_trades: number;
  clean_trades: number;
  pending_fields: number;
  resolved_fields: number;
  in_negotiation_fields: number;
  excluded_fields: number;
  quality_rate: number;
  resolution_rate: number;
}

export interface AnalyticsDailyItem {
  date: string;
  sessions: number;
  total_trades: number;
  trades_with_unmatches: number;
  total_unmatches: number;
  critical_count: number;
  warning_count: number;
  unpair_trades: number;
  unmatch_trades: number;
  clean_trades: number;
  resolved_fields: number;
  pending_fields: number;
}

export interface AnalyticsDelta {
  a: number;
  b: number;
  abs: number;
  pct: number | null;
}

export interface AnalyticsFieldComparisonItem {
  field_name: string;
  table_number: number;
  count_a: number;
  count_b: number;
  delta: number;
}

export interface AnalyticsComparison {
  period_a: AnalyticsOverview;
  period_b: AnalyticsOverview;
  deltas: Record<string, AnalyticsDelta>;
  top_fields_comparison: AnalyticsFieldComparisonItem[];
}

export interface AnalyticsDaySession {
  id: number;
  created_at: string;
  business_date: string;
  filename: string | null;
  emisor_name: string | null;
  receptor_name: string | null;
  sft_type: string | null;
  action_type: string | null;
  total_trades: number;
  trades_with_unmatches: number;
  total_unmatches: number;
  critical_count: number;
  warning_count: number;
}

export interface RegulatoryTopFieldItem {
  field_name: string;
  table_number: number;
  count: number;
  critical_count: number;
  warning_count: number;
}

export interface RegulatoryOpenItem {
  business_date: string;
  session_id: number;
  trade_id: number;
  row_number: number;
  uti: string | null;
  field_name: string;
  table_number: number;
  field_number: number;
  severity: string;
  status: string;
  assignee: string | null;
  root_cause: string | null;
  notes: string | null;
  updated_at: string | null;
}

export interface RegulatoryCounterpartyItem {
  emisor_name: string;
  receptor_name: string;
  sessions: number;
  total_trades: number;
  total_unmatches: number;
  critical_count: number;
}

export interface RegulatoryDaySummary {
  date: string;
  sessions: number;
  total_trades: number;
  trades_with_unmatches: number;
  unpair_trades: number;
  total_unmatches: number;
  critical_count: number;
  warning_count: number;
  resolved_fields: number;
  pending_fields: number;
}

export interface RegulatoryReportPreview {
  date_from: string | null;
  date_to: string | null;
  product_type?: ProductType;
  generated_at: string;
  sessions: number;
  filenames: string[];
  overview: AnalyticsOverview;
  daily_summary: RegulatoryDaySummary[];
  top_fields: RegulatoryTopFieldItem[];
  top_counterparties: RegulatoryCounterpartyItem[];
  open_items_count: number;
  critical_open_items_count: number;
  open_items: RegulatoryOpenItem[];
  comparison_to_previous_period: {
    previous_date_from: string;
    previous_date_to: string;
    deltas: Record<string, AnalyticsDelta>;
  } | null;
  risk_residual: {
    level: string;
    open_items: number;
    critical_open_items: number;
    unresolved_unpair_trades: number;
    top_field_concentration_pct: number;
    summary: string;
  } | null;
}

export interface RegulatorySnapshot {
  id: number;
  report_type: string;
  date_from: string | null;
  date_to: string | null;
  created_at: string;
  created_by: string | null;
  source_sessions_count: number;
  source_trades_count: number;
  source_field_comparisons_count: number;
  report_version: string;
  narrative_markdown: string | null;
  narrative_provider: string | null;
  narrative_model: string | null;
  payload: RegulatoryReportPreview;
}

export interface RegulatorySnapshotArtifactsResponse {
  snapshot_id: number;
  artifacts: {
    format: string;
    cached: boolean;
    size_bytes: number;
    path: string;
    mtime?: number;
  }[];
}

// ─── API calls ────────────────────────────────────────────────────────────────

export async function uploadFile(
  file: File,
  emisorName: string,
  receptorName: string,
  productType: ProductType = DEFAULT_PRODUCT_TYPE,
): Promise<Session> {
  const form = new FormData();
  form.append("file", file);
  form.append("emisor_name", emisorName);
  form.append("receptor_name", receptorName);
  form.append("product_type", productType);
  return request<Session>("/api/sessions/upload", { method: "POST", body: form });
}

export async function getSessions(productType: ProductType = DEFAULT_PRODUCT_TYPE): Promise<Session[]> {
  const suffix = productType ? `?product_type=${productType}` : "";
  return request<Session[]>(`/api/sessions${suffix}`);
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
  label?: string;
  profile_key?: string;
  available: boolean;
}

export interface LLMProfile {
  id: number;
  profile_key: string;
  label: string;
  provider: string;
  model: string;
  base_url: string | null;
  input_cost_per_million: number | null;
  output_cost_per_million: number | null;
  enabled: boolean;
  is_active: boolean;
  sort_order: number;
}

export interface LLMUsageOverview {
  total_requests: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_cached_input_tokens: number;
  total_cost: number;
  date_from: string | null;
  date_to: string | null;
}

export interface LLMUsageDailyItem {
  date: string;
  requests: number;
  input_tokens: number;
  output_tokens: number;
  total_cost: number;
}

export interface LLMUsageByUserItem {
  username: string;
  display_name: string;
  requests: number;
  input_tokens: number;
  output_tokens: number;
  total_cost: number;
}

export interface LLMUsageByModelItem {
  provider: string;
  model: string;
  requests: number;
  input_tokens: number;
  output_tokens: number;
  total_cost: number;
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

export interface ReprocessSessionResult {
  session_id: number;
  trades_reprocessed: number;
  fields_reprocessed: number;
  total_unmatches: number;
  critical_count: number;
  warning_count: number;
}

export interface AnalyticsNarrative {
  provider: string;
  model: string;
  date_from: string | null;
  date_to: string | null;
  narrative: string;
}

export interface AnalyticsChatResponse {
  provider: string;
  model: string;
  date_from: string | null;
  date_to: string | null;
  product_type?: ProductType | null;
  question: string;
  answer: string;
  suggested_visual: "none" | "daily_trend" | "top_fields" | "counterparties" | "day_sessions" | "comparison";
  selected_day?: string | null;
  guardrail_triggered?: boolean;
}

export async function loginDemoUser(username: string, password: string): Promise<DemoUser> {
  return request<DemoUser>("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
}

export async function getDemoUsers(): Promise<DemoUser[]> {
  return request<DemoUser[]>("/api/auth/users");
}

export async function getMe(): Promise<DemoUser> {
  return request<DemoUser>("/api/auth/me");
}

export async function getAIStatus(): Promise<AIStatus> {
  return request<AIStatus>("/api/ai/status");
}

export async function getAIProfiles(): Promise<LLMProfile[]> {
  return request<LLMProfile[]>("/api/ai/profiles");
}

export async function activateAIProfile(profileKey: string): Promise<LLMProfile> {
  return request<LLMProfile>("/api/ai/profiles/activate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ profile_key: profileKey }),
  });
}

export async function getLLMUsageOverview(dateFrom?: string, dateTo?: string): Promise<LLMUsageOverview> {
  return request<LLMUsageOverview>(withDateRange("/api/ai/usage/overview", dateFrom, dateTo));
}

export async function getLLMUsageDaily(dateFrom?: string, dateTo?: string): Promise<LLMUsageDailyItem[]> {
  return request<LLMUsageDailyItem[]>(withDateRange("/api/ai/usage/daily", dateFrom, dateTo));
}

export async function getLLMUsageByUser(dateFrom?: string, dateTo?: string): Promise<LLMUsageByUserItem[]> {
  return request<LLMUsageByUserItem[]>(withDateRange("/api/ai/usage/by-user", dateFrom, dateTo));
}

export async function getLLMUsageByModel(dateFrom?: string, dateTo?: string): Promise<LLMUsageByModelItem[]> {
  return request<LLMUsageByModelItem[]>(withDateRange("/api/ai/usage/by-model", dateFrom, dateTo));
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

export async function reprocessSession(sessionId: number): Promise<ReprocessSessionResult> {
  return request<ReprocessSessionResult>(`/api/sessions/${sessionId}/reprocess`, { method: "POST" });
}

function withDateRange(path: string, dateFrom?: string, dateTo?: string): string {
  const params = new URLSearchParams();
  if (dateFrom) params.set("date_from", dateFrom);
  if (dateTo) params.set("date_to", dateTo);
  const query = params.toString();
  return query ? `${path}${path.includes("?") ? "&" : "?"}${query}` : path;
}

function withProductType(path: string, productType?: ProductType): string {
  if (!productType) return path;
  return `${path}${path.includes("?") ? "&" : "?"}product_type=${productType}`;
}

export async function getAnalyticsOverview(dateFrom?: string, dateTo?: string, productType: ProductType = DEFAULT_PRODUCT_TYPE): Promise<AnalyticsOverview> {
  return request<AnalyticsOverview>(withProductType(withDateRange("/api/analytics/overview", dateFrom, dateTo), productType));
}

export async function getAnalyticsDaily(dateFrom?: string, dateTo?: string, productType: ProductType = DEFAULT_PRODUCT_TYPE): Promise<AnalyticsDailyItem[]> {
  return request<AnalyticsDailyItem[]>(withProductType(withDateRange("/api/analytics/daily", dateFrom, dateTo), productType));
}

export async function getTopFields(limit = 10, dateFrom?: string, dateTo?: string, productType: ProductType = DEFAULT_PRODUCT_TYPE): Promise<TopFieldItem[]> {
  return request<TopFieldItem[]>(withProductType(withDateRange(`/api/analytics/top-fields?limit=${limit}`, dateFrom, dateTo), productType));
}

export async function getByCounterparty(dateFrom?: string, dateTo?: string, productType: ProductType = DEFAULT_PRODUCT_TYPE): Promise<
  { emisor_name: string; receptor_name: string; sessions: number; total_unmatches: number; critical_count: number; total_trades: number }[]
> {
  return request(withProductType(withDateRange("/api/analytics/by-counterparty", dateFrom, dateTo), productType));
}

export async function getBySftType(dateFrom?: string, dateTo?: string, productType: ProductType = DEFAULT_PRODUCT_TYPE): Promise<
  { sft_type: string; sessions: number; total_unmatches: number; critical_count: number; total_trades: number }[]
> {
  return request(withProductType(withDateRange("/api/analytics/by-sft-type", dateFrom, dateTo), productType));
}

export async function generateAnalyticsReport(dateFrom?: string, dateTo?: string): Promise<AnalyticsNarrative> {
  return request<AnalyticsNarrative>(withProductType(withDateRange("/api/ai/analytics/report", dateFrom, dateTo), DEFAULT_PRODUCT_TYPE), { method: "POST" });
}

export async function downloadAnalyticsReport(
  format: "pdf" | "doc",
  narrative: AnalyticsNarrative
): Promise<void> {
  const res = await fetch(`${API_URL}/api/ai/analytics/report/export`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      format,
      narrative: narrative.narrative,
      date_from: narrative.date_from,
      date_to: narrative.date_to,
      provider: narrative.provider,
      model: narrative.model,
      product_type: DEFAULT_PRODUCT_TYPE,
    }),
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${body}`);
  }

  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  const filenameDate = narrative.date_from || new Date().toISOString().slice(0, 10);
  anchor.href = url;
  anchor.download = `predatadas_analytics_report_${filenameDate}.${format}`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(url);
}

export async function getAnalyticsComparison(
  fromA: string,
  toA: string,
  fromB: string,
  toB: string,
  productType: ProductType = DEFAULT_PRODUCT_TYPE,
): Promise<AnalyticsComparison> {
  const params = new URLSearchParams({
    from_a: fromA,
    to_a: toA,
    from_b: fromB,
    to_b: toB,
  });
  return request<AnalyticsComparison>(withProductType(`/api/analytics/compare?${params.toString()}`, productType));
}

export async function generateAnalyticsComparisonReport(
  fromA: string,
  toA: string,
  fromB: string,
  toB: string
): Promise<AnalyticsNarrative> {
  const params = new URLSearchParams({
    from_a: fromA,
    to_a: toA,
    from_b: fromB,
    to_b: toB,
    product_type: DEFAULT_PRODUCT_TYPE,
  });
  return request<AnalyticsNarrative>(`/api/ai/analytics/compare-report?${params.toString()}`, { method: "POST" });
}

export async function analyticsChat(
  question: string,
  dateFrom?: string,
  dateTo?: string,
  selectedDay?: string,
  comparison?: {
    fromA: string;
    toA: string;
    fromB: string;
    toB: string;
  }
): Promise<AnalyticsChatResponse> {
  return request<AnalyticsChatResponse>("/api/ai/analytics/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question,
      date_from: dateFrom,
      date_to: dateTo,
      product_type: DEFAULT_PRODUCT_TYPE,
      selected_day: selectedDay,
      compare_from_a: comparison?.fromA,
      compare_to_a: comparison?.toA,
      compare_from_b: comparison?.fromB,
      compare_to_b: comparison?.toB,
    }),
  });
}

export async function getAnalyticsSessionsByDay(day: string, productType: ProductType = DEFAULT_PRODUCT_TYPE): Promise<AnalyticsDaySession[]> {
  const params = new URLSearchParams({ day });
  return request<AnalyticsDaySession[]>(withProductType(`/api/analytics/sessions-by-day?${params.toString()}`, productType));
}

export async function getRegulatoryReportPreview(dateFrom?: string, dateTo?: string): Promise<RegulatoryReportPreview> {
  return request<RegulatoryReportPreview>(withProductType(withDateRange("/api/reporting/regulatory/preview", dateFrom, dateTo), DEFAULT_PRODUCT_TYPE));
}

export function regulatoryReportExportUrl(dateFrom?: string, dateTo?: string): string {
  return `${API_URL}${withProductType(withDateRange("/api/reporting/regulatory/export.xlsx", dateFrom, dateTo), DEFAULT_PRODUCT_TYPE)}`;
}

export async function generateRegulatorySnapshot(
  dateFrom?: string,
  dateTo?: string,
  includeAiNarrative = false,
  createdBy?: string
): Promise<RegulatorySnapshot> {
  return request<RegulatorySnapshot>("/api/reporting/regulatory/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      date_from: dateFrom,
      date_to: dateTo,
      product_type: DEFAULT_PRODUCT_TYPE,
      include_ai_narrative: includeAiNarrative,
      created_by: createdBy,
    }),
  });
}

export function regulatorySnapshotExportUrl(snapshotId: number, format: "xlsx" | "pdf" | "doc"): string {
  return `${API_URL}/api/reporting/regulatory/snapshots/${snapshotId}/export.${format}`;
}

export async function getRegulatorySnapshots(): Promise<RegulatorySnapshot[]> {
  const snapshots = await request<RegulatorySnapshot[]>("/api/reporting/regulatory/snapshots");
  return snapshots.filter((snapshot) => snapshot.payload?.product_type === DEFAULT_PRODUCT_TYPE);
}

export async function getRegulatorySnapshotArtifacts(snapshotId: number): Promise<RegulatorySnapshotArtifactsResponse> {
  return request<RegulatorySnapshotArtifactsResponse>(`/api/reporting/regulatory/snapshots/${snapshotId}/artifacts`);
}

export async function warmRegulatorySnapshot(snapshotId: number): Promise<{ snapshot_id: number; status: string }> {
  return request<{ snapshot_id: number; status: string }>(`/api/reporting/regulatory/snapshots/${snapshotId}/warm-cache`, {
    method: "POST",
  });
}
