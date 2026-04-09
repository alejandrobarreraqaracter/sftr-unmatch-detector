import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { SeverityBadge } from "@/components/SeverityBadge";
import { getSession, getSessionSummary, bulkUpdate, exportUrl, generateNarrative, reprocessSession, type SessionDetail, type TradeRecord, type SessionSummary } from "@/lib/api";
import { toast } from "sonner";
import { Download, RefreshCcw, Search, AlertTriangle, CheckCircle2, ChevronRight, Sparkles, X } from "lucide-react";
import ReactMarkdown from "react-markdown";

type PairingFilter = "ALL" | "UNPAIR" | "UNMATCH" | "CLEAN";

export default function SessionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [session, setSession] = useState<SessionDetail | null>(null);
  const [summary, setSummary] = useState<SessionSummary | null>(null);
  const [search, setSearch] = useState("");
  const [pairingFilter, setPairingFilter] = useState<PairingFilter>("ALL");
  const [loading, setLoading] = useState(true);
  const [narrative, setNarrative] = useState<string | null>(null);
  const [generatingNarrative, setGeneratingNarrative] = useState(false);
  const [reprocessing, setReprocessing] = useState(false);

  const sessionId = Number(id);

  useEffect(() => {
    if (!id) return;
    Promise.all([getSession(sessionId), getSessionSummary(sessionId)])
      .then(([s, sum]) => { setSession(s); setSummary(sum); })
      .catch(() => toast.error("Error al cargar la sesión"))
      .finally(() => setLoading(false));
  }, [id, sessionId]);

  const filteredTrades = session?.trades.filter((t) => {
    if (pairingFilter === "UNPAIR" && t.pairing_status !== "UNPAIR") return false;
    if (pairingFilter === "UNMATCH" && t.pairing_status !== "UNMATCH") return false;
    if (pairingFilter === "CLEAN" && t.has_unmatches) return false;
    if (!search) return true;
    return (t.uti || "").toLowerCase().includes(search.toLowerCase());
  }) ?? [];

  const unpairCount = session?.trades.filter((t) => t.pairing_status === "UNPAIR").length ?? 0;
  const unmatchOnlyCount = session?.trades.filter((t) => t.pairing_status === "UNMATCH").length ?? 0;
  const cleanCount = session ? session.trades.length - (unpairCount + unmatchOnlyCount) : 0;

  const handleGenerateNarrative = async () => {
    if (!session) return;
    setGeneratingNarrative(true);
    try {
      const result = await generateNarrative(session.id);
      setNarrative(result.narrative);
    } catch {
      toast.error("Error al generar el resumen — verifica el proveedor IA");
    } finally {
      setGeneratingNarrative(false);
    }
  };

  const handleBulkResolve = async () => {
    try {
      const result = await bulkUpdate(sessionId, { action: "resolve_all" });
      toast.success(`${result.updated} campos resueltos`);
      const [s, sum] = await Promise.all([getSession(sessionId), getSessionSummary(sessionId)]);
      setSession(s);
      setSummary(sum);
    } catch {
      toast.error("Error en la actualización masiva");
    }
  };

  const handleReprocess = async () => {
    setReprocessing(true);
    try {
      const result = await reprocessSession(sessionId);
      const [s, sum] = await Promise.all([getSession(sessionId), getSessionSummary(sessionId)]);
      setSession(s);
      setSummary(sum);
      toast.success(
        `Sesión reprocesada: ${result.fields_reprocessed} campos revisados, ${result.total_unmatches} discrepancias`
      );
    } catch {
      toast.error("Error al reprocesar la sesión");
    } finally {
      setReprocessing(false);
    }
  };

  if (loading) return <div className="flex items-center justify-center h-64"><p className="text-zinc-500">Cargando sesión...</p></div>;
  if (!session) return <div className="flex items-center justify-center h-64"><p className="text-zinc-500">Sesión no encontrada</p></div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-900">Sesión #{session.id}</h1>
          <p className="text-sm text-zinc-500 mt-1">
            {session.filename} · {session.sft_type}/{session.action_type} · {session.emisor_name} vs {session.receptor_name} · {new Date(session.created_at).toLocaleString("es-ES")}
          </p>
        </div>
        <div className="flex gap-2">
          <a href={exportUrl(sessionId)} download>
            <Button variant="outline" size="sm"><Download className="h-4 w-4 mr-1" /> Exportar todo</Button>
          </a>
          <a href={exportUrl(sessionId, true)} download>
            <Button variant="outline" size="sm"><Download className="h-4 w-4 mr-1" /> Exportar discrepancias</Button>
          </a>
          <Button variant="outline" size="sm" onClick={handleReprocess} disabled={reprocessing}>
            <RefreshCcw className="h-4 w-4 mr-1" />
            {reprocessing ? "Reprocesando..." : "Reprocesar sesión"}
          </Button>
          <Button
            variant="outline" size="sm"
            onClick={handleGenerateNarrative}
            disabled={generatingNarrative}
            className="border-[#fc7c34] text-[#fc7c34] hover:bg-orange-50"
          >
            <Sparkles className="h-4 w-4 mr-1" />
            {generatingNarrative ? "Generando..." : "Resumen IA"}
          </Button>
          <Button variant="outline" size="sm" onClick={handleBulkResolve}>
            <CheckCircle2 className="h-4 w-4 mr-1" /> Resolver todo
          </Button>
        </div>
      </div>

      {generatingNarrative && (
        <Card className="border-orange-200 bg-orange-50">
          <CardContent className="py-4">
            <p className="text-sm text-orange-600 animate-pulse flex items-center gap-2">
              <Sparkles className="h-4 w-4" /> Generando resumen ejecutivo con IA...
            </p>
          </CardContent>
        </Card>
      )}

      {narrative && (
        <Card className="border-orange-200 bg-orange-50">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm flex items-center gap-2 text-orange-800">
                <Sparkles className="h-4 w-4" /> Resumen Ejecutivo IA
              </CardTitle>
              <button onClick={() => setNarrative(null)} className="text-orange-400 hover:text-orange-600">
                <X className="h-4 w-4" />
              </button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="prose prose-sm max-w-none text-zinc-700 leading-relaxed">
              <ReactMarkdown
                components={{
                  h1: ({children}) => <h1 className="text-base font-bold text-zinc-900 mt-3 mb-1">{children}</h1>,
                  h2: ({children}) => <h2 className="text-sm font-bold text-zinc-900 mt-3 mb-1">{children}</h2>,
                  h3: ({children}) => <h3 className="text-sm font-semibold text-zinc-800 mt-2 mb-1">{children}</h3>,
                  strong: ({children}) => <strong className="font-semibold text-zinc-900">{children}</strong>,
                  p: ({children}) => <p className="text-sm text-zinc-700 mb-2">{children}</p>,
                  ul: ({children}) => <ul className="list-disc list-inside text-sm text-zinc-700 mb-2 space-y-1">{children}</ul>,
                  ol: ({children}) => <ol className="list-decimal list-inside text-sm text-zinc-700 mb-2 space-y-1">{children}</ol>,
                  li: ({children}) => <li className="text-sm text-zinc-700">{children}</li>,
                }}
              >
                {narrative}
              </ReactMarkdown>
            </div>
          </CardContent>
        </Card>
      )}

      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
          <MetricCard label="Total operaciones" value={summary.total_trades} />
          <MetricCard label="Con discrepancias" value={summary.trades_with_unmatches} color="red" />
          <MetricCard label="Unpair" value={unpairCount} color="purple" />
          <MetricCard label="Total discrepancias" value={summary.total_unmatches} color="red" />
          <MetricCard label="Críticas" value={summary.critical_count} color="red" icon={<AlertTriangle className="h-3 w-3" />} />
          <MetricCard label="Advertencias" value={summary.warning_count} color="amber" />
          <MetricCard label="Resueltas" value={summary.resolved_count} color="green" icon={<CheckCircle2 className="h-3 w-3" />} />
        </div>
      )}

      <Card>
        <CardHeader>
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <CardTitle className="text-base">
              Operaciones ({filteredTrades.length} de {session.trades.length})
            </CardTitle>
            <div className="flex flex-wrap items-center gap-2">
              <Select value={pairingFilter} onValueChange={(value) => setPairingFilter(value as PairingFilter)}>
                <SelectTrigger className="h-9 w-40 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">Todos</SelectItem>
                  <SelectItem value="UNPAIR">Solo Unpair</SelectItem>
                  <SelectItem value="UNMATCH">Solo Unmatch</SelectItem>
                  <SelectItem value="CLEAN">Solo limpias</SelectItem>
                </SelectContent>
              </Select>
              <div className="relative">
                <Search className="h-4 w-4 absolute left-2 top-2.5 text-zinc-400" />
                <Input
                  placeholder="Buscar por UTI..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-8 w-52 h-9"
                />
              </div>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="inline-flex rounded-full border border-purple-200 bg-purple-50 px-2 py-1 font-medium text-purple-700">
              Unpair: {unpairCount}
            </span>
            <span className="inline-flex rounded-full border border-red-200 bg-red-50 px-2 py-1 font-medium text-red-700">
              Unmatch: {unmatchOnlyCount}
            </span>
            <span className="inline-flex rounded-full border border-zinc-200 bg-zinc-50 px-2 py-1 font-medium text-zinc-600">
              Limpias: {cleanCount}
            </span>
          </div>
        </CardHeader>
        <CardContent>
          <div className="rounded-lg border overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow className="bg-zinc-50">
                  <TableHead className="w-8">#</TableHead>
                  <TableHead>UTI</TableHead>
                  <TableHead>Tipo</TableHead>
                  <TableHead className="text-right">Campos</TableHead>
                  <TableHead className="text-right">Discrepancias</TableHead>
                  <TableHead>Tipo</TableHead>
                  <TableHead className="text-right">Críticas</TableHead>
                  <TableHead className="text-right">Advertencias</TableHead>
                  <TableHead className="w-8"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredTrades.map((trade) => (
                  <TradeRow key={trade.id} trade={trade} sessionId={sessionId} />
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function TradeRow({ trade, sessionId }: { trade: TradeRecord; sessionId: number }) {
  const rowBg = trade.pairing_status === "UNPAIR"
    ? "bg-purple-100/60 hover:bg-purple-100"
    : trade.has_unmatches
      ? trade.critical_count > 0
        ? "bg-red-50/40 hover:bg-red-50"
        : "bg-amber-50/40 hover:bg-amber-50"
      : "hover:bg-zinc-50";

  return (
    <TableRow className={`cursor-pointer ${rowBg}`}>
      <TableCell className="text-xs text-zinc-500">{trade.row_number}</TableCell>
      <TableCell className="font-mono text-xs">
        <Link to={`/sessions/${sessionId}/trades/${trade.id}`} className="hover:text-[#fc7c34] hover:underline">
          {trade.uti || `Operación #${trade.row_number}`}
        </Link>
      </TableCell>
      <TableCell className="text-xs">{trade.sft_type}/{trade.action_type}</TableCell>
      <TableCell className="text-right text-xs text-zinc-500">{trade.total_fields}</TableCell>
      <TableCell className="text-right">
        {trade.total_unmatches > 0
          ? <span className="text-xs font-semibold text-red-700">{trade.total_unmatches}</span>
          : <span className="text-xs text-green-600">0</span>}
      </TableCell>
      <TableCell>
        {trade.pairing_status === "UNPAIR" ? (
          <div className="flex flex-col gap-1">
            <span className="inline-flex w-fit rounded-full border border-purple-200 bg-purple-50 px-2 py-0.5 text-[11px] font-semibold text-purple-700">
              Unpair
            </span>
            <span className="text-[11px] text-zinc-500">
              {trade.pairing_reason || "UTI / Other counterparty"}
            </span>
          </div>
        ) : trade.pairing_status === "UNMATCH" ? (
          <span className="inline-flex w-fit rounded-full border border-red-200 bg-red-50 px-2 py-0.5 text-[11px] font-semibold text-red-700">
            Unmatch
          </span>
        ) : (
          <span className="text-xs text-zinc-400">—</span>
        )}
      </TableCell>
      <TableCell className="text-right">
        {trade.critical_count > 0
          ? <span className="inline-flex items-center gap-1"><SeverityBadge severity="CRITICAL" /><span className="text-xs font-semibold text-red-700">{trade.critical_count}</span></span>
          : <span className="text-xs text-zinc-400">—</span>}
      </TableCell>
      <TableCell className="text-right">
        {trade.warning_count > 0
          ? <span className="text-xs font-semibold text-amber-700">{trade.warning_count}</span>
          : <span className="text-xs text-zinc-400">—</span>}
      </TableCell>
      <TableCell>
        <Link to={`/sessions/${sessionId}/trades/${trade.id}`}>
          <ChevronRight className="h-4 w-4 text-zinc-400" />
        </Link>
      </TableCell>
    </TableRow>
  );
}

function MetricCard({ label, value, color, icon }: { label: string; value: number; color?: string; icon?: React.ReactNode }) {
  const colorMap: Record<string, string> = {
    red: "text-red-700", amber: "text-amber-700", blue: "text-blue-700",
    green: "text-green-700", purple: "text-purple-700",
  };
  return (
    <div className="rounded-lg border border-zinc-200 p-3">
      <p className="text-xs text-zinc-500 flex items-center gap-1">{icon}{label}</p>
      <p className={`text-xl font-bold ${color ? colorMap[color] || "" : "text-zinc-900"}`}>{value}</p>
    </div>
  );
}
