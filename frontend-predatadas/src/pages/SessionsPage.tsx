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
        <p className="text-zinc-500">Cargando sesiones...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-zinc-900">Sesiones de conciliación</h1>
        <p className="text-sm text-zinc-500 mt-1">Historial de conciliaciones de predatadas</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">{sessions.length} sesiones</CardTitle>
        </CardHeader>
        <CardContent>
          {sessions.length === 0 ? (
            <div className="text-center py-12 text-zinc-500">
              <FileText className="h-12 w-12 mx-auto text-zinc-300 mb-3" />
              <p>Aún no hay sesiones de conciliación.</p>
              <Link to="/upload" className="text-[#fc7c34] hover:underline text-sm">Carga un fichero para empezar</Link>
            </div>
          ) : (
            <div className="rounded-lg border overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow className="bg-zinc-50">
                    <TableHead className="w-12">#</TableHead>
                    <TableHead>Fichero</TableHead>
                    <TableHead>Contrapartes</TableHead>
                    <TableHead>Tipo</TableHead>
                    <TableHead className="text-right">Operaciones</TableHead>
                    <TableHead className="text-right">Con discrepancias</TableHead>
                    <TableHead className="text-right">Total discrepancias</TableHead>
                    <TableHead className="text-right">Críticas</TableHead>
                    <TableHead className="text-right">Fecha</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sessions.map((s) => (
                    <TableRow key={s.id} className="cursor-pointer hover:bg-zinc-50">
                      <TableCell className="text-xs text-zinc-500">{s.id}</TableCell>
                      <TableCell>
                        <Link to={`/sessions/${s.id}`} className="text-[#fc7c34] hover:underline text-xs font-mono">
                          {s.filename || `Sesión #${s.id}`}
                        </Link>
                      </TableCell>
                      <TableCell className="text-xs text-zinc-600">{s.emisor_name} / {s.receptor_name}</TableCell>
                      <TableCell>
                        <Badge variant="outline" className="text-xs">{s.sft_type}/{s.action_type}</Badge>
                      </TableCell>
                      <TableCell className="text-right text-sm">{s.total_trades}</TableCell>
                      <TableCell className="text-right">
                        <span className={s.trades_with_unmatches > 0 ? "text-red-700 font-semibold text-sm" : "text-green-700 text-sm"}>
                          {s.trades_with_unmatches}
                        </span>
                      </TableCell>
                      <TableCell className="text-right">
                        <span className={s.total_unmatches > 0 ? "text-red-700 font-semibold text-sm" : "text-green-700 text-sm"}>
                          {s.total_unmatches}
                        </span>
                      </TableCell>
                      <TableCell className="text-right">
                        <span className={s.critical_count > 0 ? "text-red-700 font-semibold text-sm" : "text-zinc-400 text-sm"}>
                          {s.critical_count || "—"}
                        </span>
                      </TableCell>
                      <TableCell className="text-right text-xs text-zinc-500">
                        {new Date(s.created_at).toLocaleDateString("es-ES")}
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
