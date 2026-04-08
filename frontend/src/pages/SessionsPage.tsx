import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { getSessions, type Session } from "@/lib/api";
import { FileText } from "lucide-react";

export default function SessionsPage() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getSessions()
      .then(setSessions)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-zinc-500">Loading sessions...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-zinc-900">Comparison Sessions</h1>
        <p className="text-sm text-zinc-500 mt-1">History of all SFTR report comparisons</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">{sessions.length} Sessions</CardTitle>
        </CardHeader>
        <CardContent>
          {sessions.length === 0 ? (
            <div className="text-center py-12 text-zinc-500">
              <FileText className="h-12 w-12 mx-auto text-zinc-300 mb-3" />
              <p>No comparison sessions yet.</p>
              <Link to="/upload" className="text-blue-600 hover:underline text-sm">Upload reports to get started</Link>
            </div>
          ) : (
            <div className="rounded-lg border overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow className="bg-zinc-50">
                    <TableHead>Date</TableHead>
                    <TableHead>Emisor</TableHead>
                    <TableHead>Receptor</TableHead>
                    <TableHead>UTI</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead className="text-right">Fields</TableHead>
                    <TableHead className="text-right">Unmatches</TableHead>
                    <TableHead className="text-right">Critical</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sessions.map((s) => (
                    <TableRow key={s.id} className="cursor-pointer hover:bg-zinc-50">
                      <TableCell>
                        <Link to={`/sessions/${s.id}`} className="text-blue-600 hover:underline text-sm">
                          {new Date(s.created_at).toLocaleDateString()}
                        </Link>
                      </TableCell>
                      <TableCell className="text-sm font-mono max-w-32 truncate">{s.emisor_name}</TableCell>
                      <TableCell className="text-sm font-mono max-w-32 truncate">{s.receptor_name}</TableCell>
                      <TableCell className="text-xs font-mono max-w-40 truncate">{s.uti}</TableCell>
                      <TableCell>
                        <Badge variant="outline" className="text-xs">{s.sft_type}/{s.action_type}</Badge>
                      </TableCell>
                      <TableCell className="text-right text-sm">{s.total_fields}</TableCell>
                      <TableCell className="text-right">
                        <span className={s.total_unmatches > 0 ? "text-red-700 font-semibold" : "text-green-700"}>
                          {s.total_unmatches}
                        </span>
                      </TableCell>
                      <TableCell className="text-right">
                        <span className={s.critical_count > 0 ? "text-red-700 font-semibold" : "text-zinc-400"}>
                          {s.critical_count}
                        </span>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
