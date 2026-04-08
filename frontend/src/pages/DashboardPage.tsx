import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { SeverityBadge, StatusBadge } from "@/components/SeverityBadge";
import FieldDetailPanel from "@/components/FieldDetailPanel";
import { getSessions, getSession, type Session, type FieldResult, type SessionDetail } from "@/lib/api";
import { AlertTriangle, CheckCircle2, Upload, FileWarning, ArrowRight } from "lucide-react";

export default function DashboardPage() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [latestDetail, setLatestDetail] = useState<SessionDetail | null>(null);
  const [selectedField, setSelectedField] = useState<FieldResult | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const list = await getSessions();
        setSessions(list);
        if (list.length > 0) {
          const detail = await getSession(list[0].id);
          setLatestDetail(detail);
        }
      } catch {
        // no sessions yet
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const latest = sessions[0];
  const unmatches = latestDetail?.field_results.filter((f) => f.result === "UNMATCH") || [];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-zinc-500">Loading...</p>
      </div>
    );
  }

  if (!latest) {
    return (
      <div className="flex flex-col items-center justify-center h-96 gap-4">
        <FileWarning className="h-16 w-16 text-zinc-300" />
        <h2 className="text-xl font-semibold text-zinc-700">No sessions yet</h2>
        <p className="text-zinc-500">Upload two SFTR reports to get started.</p>
        <Link to="/upload">
          <Button>
            <Upload className="h-4 w-4 mr-2" />
            Upload Reports
          </Button>
        </Link>
      </div>
    );
  }

  const criticalCount = unmatches.filter((f) => f.severity === "CRITICAL").length;
  const warningCount = unmatches.filter((f) => f.severity === "WARNING").length;
  const resolvedCount = unmatches.filter((f) => f.status === "RESOLVED").length;

  const handleFieldUpdated = (updated: FieldResult) => {
    if (!latestDetail) return;
    setLatestDetail({
      ...latestDetail,
      field_results: latestDetail.field_results.map((f) => (f.id === updated.id ? updated : f)),
    });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-900">Dashboard</h1>
          <p className="text-sm text-zinc-500 mt-1">Latest comparison session overview</p>
        </div>
        <Link to="/upload">
          <Button>
            <Upload className="h-4 w-4 mr-2" />
            New Comparison
          </Button>
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-zinc-500">Total Fields</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-zinc-900">{latest.total_fields}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-zinc-500">Unmatches</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-red-700">{latest.total_unmatches}</p>
          </CardContent>
        </Card>
        <Card className="border-red-200 bg-red-50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-red-600 flex items-center gap-1">
              <AlertTriangle className="h-4 w-4" />
              Critical
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-red-800">{criticalCount}</p>
          </CardContent>
        </Card>
        <Card className="border-green-200 bg-green-50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-green-600 flex items-center gap-1">
              <CheckCircle2 className="h-4 w-4" />
              Resolved
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-green-800">{resolvedCount}</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-base">
              Mismatches — {latest.emisor_name?.slice(0, 10)}… vs {latest.receptor_name?.slice(0, 10)}…
            </CardTitle>
            <p className="text-xs text-zinc-500 mt-1">
              UTI: {latest.uti} · {latest.sft_type}/{latest.action_type} · {new Date(latest.created_at).toLocaleString()}
            </p>
          </div>
          <Link to={`/sessions/${latest.id}`}>
            <Button variant="outline" size="sm">
              View All <ArrowRight className="h-3 w-3 ml-1" />
            </Button>
          </Link>
        </CardHeader>
        <CardContent>
          <div className="rounded-lg border overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow className="bg-zinc-50">
                  <TableHead className="w-12">Tbl</TableHead>
                  <TableHead>Field</TableHead>
                  <TableHead>Obl</TableHead>
                  <TableHead>Emisor</TableHead>
                  <TableHead>Receptor</TableHead>
                  <TableHead>Severity</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {unmatches.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-8 text-zinc-500">
                      No mismatches found — all fields match!
                    </TableCell>
                  </TableRow>
                ) : (
                  unmatches.slice(0, 20).map((field) => (
                    <TableRow
                      key={field.id}
                      className="cursor-pointer hover:bg-zinc-50"
                      onClick={() => setSelectedField(field)}
                    >
                      <TableCell className="text-xs text-zinc-500">{field.table_number}</TableCell>
                      <TableCell className="font-medium text-sm">{field.field_name}</TableCell>
                      <TableCell className="text-xs font-semibold">{field.obligation}</TableCell>
                      <TableCell className="text-xs font-mono max-w-32 truncate">{field.emisor_value || "—"}</TableCell>
                      <TableCell className="text-xs font-mono max-w-32 truncate">{field.receptor_value || "—"}</TableCell>
                      <TableCell><SeverityBadge severity={field.severity} /></TableCell>
                      <TableCell><StatusBadge status={field.status} /></TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
          {unmatches.length > 20 && (
            <p className="text-xs text-zinc-500 mt-2 text-center">
              Showing 20 of {unmatches.length} mismatches.{" "}
              <Link to={`/sessions/${latest.id}`} className="text-blue-600 hover:underline">View all</Link>
            </p>
          )}
          {warningCount > 0 && (
            <p className="text-xs text-amber-600 mt-2">{warningCount} conditional field warnings</p>
          )}
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
