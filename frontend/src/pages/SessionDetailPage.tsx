import { useEffect, useState, useMemo, useCallback } from "react";
import { useParams } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { SeverityBadge, ResultBadge, StatusBadge } from "@/components/SeverityBadge";
import FieldDetailPanel from "@/components/FieldDetailPanel";
import { getSession, getSessionSummary, bulkUpdate, exportUrl, type SessionDetail, type FieldResult, type SessionSummary } from "@/lib/api";
import { toast } from "sonner";
import { Download, Search, AlertTriangle, CheckCircle2, Info, ArrowUpDown } from "lucide-react";

type SeverityFilter = "ALL" | "CRITICAL" | "WARNING" | "INFO";
type ResultFilter = "ALL" | "UNMATCH" | "MATCH" | "MIRROR" | "NA";
type StatusFilter = "ALL" | "PENDING" | "IN_NEGOTIATION" | "RESOLVED" | "EXCLUDED";

export default function SessionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [session, setSession] = useState<SessionDetail | null>(null);
  const [summary, setSummary] = useState<SessionSummary | null>(null);
  const [selectedField, setSelectedField] = useState<FieldResult | null>(null);
  const [search, setSearch] = useState("");
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>("ALL");
  const [resultFilter, setResultFilter] = useState<ResultFilter>("ALL");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("ALL");
  const [tableFilter, setTableFilter] = useState<string>("ALL");
  const [loading, setLoading] = useState(true);

  const sessionId = Number(id);

  useEffect(() => {
    if (!id) return;
    Promise.all([getSession(sessionId), getSessionSummary(sessionId)])
      .then(([s, sum]) => {
        setSession(s);
        setSummary(sum);
      })
      .catch(() => toast.error("Failed to load session"))
      .finally(() => setLoading(false));
  }, [id, sessionId]);

  const filteredFields = useMemo(() => {
    if (!session) return [];
    return session.field_results.filter((f) => {
      if (severityFilter !== "ALL" && f.severity !== severityFilter) return false;
      if (resultFilter !== "ALL" && f.result !== resultFilter) return false;
      if (statusFilter !== "ALL" && f.status !== statusFilter) return false;
      if (tableFilter !== "ALL" && f.table_number !== Number(tableFilter)) return false;
      if (search && !f.field_name.toLowerCase().includes(search.toLowerCase())) return false;
      return true;
    });
  }, [session, severityFilter, resultFilter, statusFilter, tableFilter, search]);

  const handleFieldUpdated = useCallback((updated: FieldResult) => {
    setSession((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        field_results: prev.field_results.map((f) => (f.id === updated.id ? updated : f)),
      };
    });
  }, []);

  const handleBulkResolve = async () => {
    try {
      const result = await bulkUpdate(sessionId, { action: "resolve_all" });
      toast.success(`${result.updated} fields resolved`);
      const s = await getSession(sessionId);
      setSession(s);
    } catch {
      toast.error("Bulk update failed");
    }
  };

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      if (e.key === "r" || e.key === "R") {
        if (selectedField) {
          setSelectedField({ ...selectedField, status: "RESOLVED" });
        }
      }
      if (e.key === "n" || e.key === "N") {
        if (selectedField) {
          setSelectedField(selectedField);
        }
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [selectedField]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-zinc-500">Loading session...</p>
      </div>
    );
  }

  if (!session) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-zinc-500">Session not found</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-900">Session #{session.id}</h1>
          <p className="text-sm text-zinc-500 mt-1">
            {session.sft_type}/{session.action_type} · UTI: {session.uti} · {new Date(session.created_at).toLocaleString()}
          </p>
        </div>
        <div className="flex gap-2">
          <a href={exportUrl(sessionId)} download>
            <Button variant="outline" size="sm">
              <Download className="h-4 w-4 mr-1" /> Export All
            </Button>
          </a>
          <a href={exportUrl(sessionId, true)} download>
            <Button variant="outline" size="sm">
              <Download className="h-4 w-4 mr-1" /> Export Unmatches
            </Button>
          </a>
          <Button variant="outline" size="sm" onClick={handleBulkResolve}>
            <CheckCircle2 className="h-4 w-4 mr-1" /> Resolve All
          </Button>
        </div>
      </div>

      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3">
          <MetricCard label="Total" value={summary.total_fields} />
          <MetricCard label="Match" value={summary.match_count} color="green" />
          <MetricCard label="Mirror" value={summary.mirror_count} color="purple" />
          <MetricCard label="Unmatch" value={summary.total_unmatches} color="red" />
          <MetricCard label="Critical" value={summary.critical_count} color="red" icon={<AlertTriangle className="h-3 w-3" />} />
          <MetricCard label="Warning" value={summary.warning_count} color="amber" />
          <MetricCard label="Info" value={summary.info_count} color="blue" icon={<Info className="h-3 w-3" />} />
          <MetricCard label="Resolved" value={summary.resolved_count} color="green" icon={<CheckCircle2 className="h-3 w-3" />} />
        </div>
      )}

      <Card>
        <CardHeader>
          <div className="flex flex-col md:flex-row gap-4 items-start md:items-center justify-between">
            <CardTitle className="text-base">
              Field Comparison ({filteredFields.length} of {session.field_results.length})
            </CardTitle>
            <div className="flex flex-wrap gap-2 items-center">
              <div className="relative">
                <Search className="h-4 w-4 absolute left-2 top-2.5 text-zinc-400" />
                <Input
                  placeholder="Search fields..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-8 w-48 h-9"
                />
              </div>
            </div>
          </div>

          <div className="flex flex-wrap gap-2 mt-3">
            <Tabs value={severityFilter} onValueChange={(v) => setSeverityFilter(v as SeverityFilter)}>
              <TabsList className="h-8">
                <TabsTrigger value="ALL" className="text-xs h-7 px-2">All</TabsTrigger>
                <TabsTrigger value="CRITICAL" className="text-xs h-7 px-2">Critical</TabsTrigger>
                <TabsTrigger value="WARNING" className="text-xs h-7 px-2">Warning</TabsTrigger>
                <TabsTrigger value="INFO" className="text-xs h-7 px-2">Info</TabsTrigger>
              </TabsList>
            </Tabs>

            <Select value={resultFilter} onValueChange={(v) => setResultFilter(v as ResultFilter)}>
              <SelectTrigger className="w-32 h-8 text-xs">
                <ArrowUpDown className="h-3 w-3 mr-1" />
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">All Results</SelectItem>
                <SelectItem value="UNMATCH">Unmatch</SelectItem>
                <SelectItem value="MATCH">Match</SelectItem>
                <SelectItem value="MIRROR">Mirror</SelectItem>
                <SelectItem value="NA">N/A</SelectItem>
              </SelectContent>
            </Select>

            <Select value={statusFilter} onValueChange={(v) => setStatusFilter(v as StatusFilter)}>
              <SelectTrigger className="w-36 h-8 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">All Status</SelectItem>
                <SelectItem value="PENDING">Pending</SelectItem>
                <SelectItem value="IN_NEGOTIATION">In Negotiation</SelectItem>
                <SelectItem value="RESOLVED">Resolved</SelectItem>
                <SelectItem value="EXCLUDED">Excluded</SelectItem>
              </SelectContent>
            </Select>

            <Select value={tableFilter} onValueChange={setTableFilter}>
              <SelectTrigger className="w-32 h-8 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">All Tables</SelectItem>
                <SelectItem value="1">Table 1</SelectItem>
                <SelectItem value="2">Table 2</SelectItem>
                <SelectItem value="3">Table 3</SelectItem>
                <SelectItem value="4">Table 4</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          <div className="rounded-lg border overflow-hidden">
            <div className="max-h-screen overflow-y-auto">
              <Table>
                <TableHeader>
                  <TableRow className="bg-zinc-50 sticky top-0">
                    <TableHead className="w-10">Tbl</TableHead>
                    <TableHead className="w-10">#</TableHead>
                    <TableHead>Field Name</TableHead>
                    <TableHead className="w-10">Obl</TableHead>
                    <TableHead>Emisor Value</TableHead>
                    <TableHead>Receptor Value</TableHead>
                    <TableHead>Result</TableHead>
                    <TableHead>Severity</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Assignee</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredFields.map((field) => (
                    <TableRow
                      key={field.id}
                      className={`cursor-pointer hover:bg-zinc-50 ${
                        field.result === "UNMATCH"
                          ? field.severity === "CRITICAL"
                            ? "bg-red-50/50"
                            : field.severity === "WARNING"
                            ? "bg-amber-50/50"
                            : "bg-blue-50/50"
                          : field.result === "MIRROR"
                          ? "bg-purple-50/50"
                          : ""
                      }`}
                      onClick={() => setSelectedField(field)}
                    >
                      <TableCell className="text-xs text-zinc-500">{field.table_number}</TableCell>
                      <TableCell className="text-xs text-zinc-500">{field.field_number}</TableCell>
                      <TableCell className="font-medium text-sm">{field.field_name}</TableCell>
                      <TableCell className="text-xs font-semibold text-center">{field.obligation}</TableCell>
                      <TableCell className="text-xs font-mono max-w-36 truncate">{field.emisor_value || "—"}</TableCell>
                      <TableCell className="text-xs font-mono max-w-36 truncate">{field.receptor_value || "—"}</TableCell>
                      <TableCell><ResultBadge result={field.result} /></TableCell>
                      <TableCell><SeverityBadge severity={field.severity} /></TableCell>
                      <TableCell><StatusBadge status={field.status} /></TableCell>
                      <TableCell className="text-xs text-zinc-500">{field.assignee || "—"}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>
        </CardContent>
      </Card>

      <FieldDetailPanel
        field={selectedField}
        open={selectedField !== null}
        onClose={() => setSelectedField(null)}
        onUpdated={handleFieldUpdated}
      />
    </div>
  );
}

function MetricCard({
  label,
  value,
  color,
  icon,
}: {
  label: string;
  value: number;
  color?: string;
  icon?: React.ReactNode;
}) {
  const colorMap: Record<string, string> = {
    red: "text-red-700",
    amber: "text-amber-700",
    blue: "text-blue-700",
    green: "text-green-700",
    purple: "text-purple-700",
  };
  return (
    <div className="rounded-lg border border-zinc-200 p-3">
      <p className="text-xs text-zinc-500 flex items-center gap-1">
        {icon}
        {label}
      </p>
      <p className={`text-xl font-bold ${color ? colorMap[color] || "" : "text-zinc-900"}`}>{value}</p>
    </div>
  );
}
