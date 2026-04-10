import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { SeverityBadge } from "@/components/SeverityBadge";
import { getSessions, type Session } from "@/lib/api";
import { AlertTriangle, Upload, FileWarning, ArrowRight, ChevronRight } from "lucide-react";

export default function DashboardPage() {
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
        <p className="text-zinc-500">Cargando...</p>
      </div>
    );
  }

  if (sessions.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-96 gap-4">
        <FileWarning className="h-16 w-16 text-zinc-300" />
        <h2 className="text-xl font-semibold text-zinc-700">Sin sesiones todavía</h2>
        <p className="text-zinc-500">Carga un fichero de predatadas para comenzar.</p>
        <Link to="/upload">
          <Button>
            <Upload className="h-4 w-4 mr-2" />
            Cargar informe
          </Button>
        </Link>
      </div>
    );
  }

  const latest = sessions[0];
  const totalSessions = sessions.length;
  const totalUnmatches = sessions.reduce((s, x) => s + x.total_unmatches, 0);
  const totalCritical = sessions.reduce((s, x) => s + x.critical_count, 0);
  const totalTrades = sessions.reduce((s, x) => s + x.total_trades, 0);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-900">Inicio</h1>
          <p className="text-sm text-zinc-500 mt-1">Resumen de todas las sesiones de predatadas</p>
        </div>
        <Link to="/upload">
          <Button>
            <Upload className="h-4 w-4 mr-2" />
            Nueva comparación
          </Button>
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-zinc-500">Total sesiones</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-zinc-900">{totalSessions}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-zinc-500">Total operaciones</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-zinc-900">{totalTrades.toLocaleString()}</p>
          </CardContent>
        </Card>
        <Card className="border-red-200 bg-red-50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-red-600 flex items-center gap-1">
              <AlertTriangle className="h-4 w-4" /> Total discrepancias
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-red-800">{totalUnmatches.toLocaleString()}</p>
          </CardContent>
        </Card>
        <Card className="border-red-200 bg-red-50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-red-600 flex items-center gap-1">
              <AlertTriangle className="h-4 w-4" /> Críticas
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-red-800">{totalCritical.toLocaleString()}</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-base">Última sesión — #{latest.id}</CardTitle>
            <p className="text-xs text-zinc-500 mt-1">
              {latest.filename} · {latest.emisor_name} vs {latest.receptor_name} · {new Date(latest.created_at).toLocaleString("es-ES")}
            </p>
          </div>
          <Link to={`/sessions/${latest.id}`}>
            <Button variant="outline" size="sm">
              Ver operaciones <ArrowRight className="h-3 w-3 ml-1" />
            </Button>
          </Link>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
            <Metric label="Operaciones" value={latest.total_trades} />
            <Metric label="Con discrepancias" value={latest.trades_with_unmatches} color="red" />
            <Metric label="Discrepancias" value={latest.total_unmatches} color="red" />
            <Metric label="Críticas" value={latest.critical_count} color="red" />
            <Metric label="Advertencias" value={latest.warning_count} color="amber" />
            <Metric label="Campos" value={latest.total_fields} />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base">Sesiones recientes</CardTitle>
          <Link to="/sessions">
            <Button variant="outline" size="sm">
              Ver todas <ArrowRight className="h-3 w-3 ml-1" />
            </Button>
          </Link>
        </CardHeader>
        <CardContent>
          <div className="rounded-lg border overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow className="bg-zinc-50">
                  <TableHead className="w-12">#</TableHead>
                  <TableHead>Fichero</TableHead>
                  <TableHead>Contrapartes</TableHead>
                  <TableHead className="text-right">Operaciones</TableHead>
                  <TableHead className="text-right">Discrepancias</TableHead>
                  <TableHead className="text-right">Críticas</TableHead>
                  <TableHead className="text-right">Fecha</TableHead>
                  <TableHead className="w-8"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sessions.slice(0, 10).map((s) => (
                  <TableRow key={s.id} className="cursor-pointer hover:bg-zinc-50">
                    <TableCell className="text-xs text-zinc-500">{s.id}</TableCell>
                    <TableCell className="text-xs font-mono text-zinc-700 max-w-36 truncate">{s.filename || "—"}</TableCell>
                    <TableCell className="text-xs text-zinc-600">{s.emisor_name} / {s.receptor_name}</TableCell>
                    <TableCell className="text-right text-xs">{s.total_trades}</TableCell>
                    <TableCell className="text-right">
                      {s.total_unmatches > 0
                        ? <span className="text-xs font-semibold text-red-700">{s.total_unmatches}</span>
                        : <span className="text-xs text-green-600">0</span>}
                    </TableCell>
                    <TableCell className="text-right">
                      {s.critical_count > 0
                        ? <span className="inline-flex items-center gap-1"><SeverityBadge severity="CRITICAL" /><span className="text-xs font-semibold text-red-700">{s.critical_count}</span></span>
                        : <span className="text-xs text-zinc-400">—</span>}
                    </TableCell>
                    <TableCell className="text-right text-xs text-zinc-500">
                      {new Date(s.created_at).toLocaleDateString("es-ES")}
                    </TableCell>
                    <TableCell>
                      <Link to={`/sessions/${s.id}`}>
                        <ChevronRight className="h-4 w-4 text-zinc-400" />
                      </Link>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function Metric({ label, value, color }: { label: string; value: number; color?: string }) {
  const colorMap: Record<string, string> = { red: "text-red-700", amber: "text-amber-700" };
  return (
    <div className="rounded-lg border border-zinc-200 p-3">
      <p className="text-xs text-zinc-500">{label}</p>
      <p className={`text-xl font-bold ${color ? colorMap[color] || "" : "text-zinc-900"}`}>{value.toLocaleString()}</p>
    </div>
  );
}
