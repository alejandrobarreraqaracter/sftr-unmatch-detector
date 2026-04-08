import { useEffect, useState, useMemo, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { SeverityBadge, StatusBadge } from "@/components/SeverityBadge";
import FieldDetailPanel from "@/components/FieldDetailPanel";
import { getTrade, bulkUpdate, analyzeTrade, type TradeDetail, type FieldComparison, type TradeAnalysis } from "@/lib/api";
import { toast } from "sonner";
import { Search, AlertTriangle, CheckCircle2, ArrowLeft, ArrowUpDown, Sparkles, X } from "lucide-react";

type SeverityFilter = "ALL" | "CRITICAL" | "WARNING" | "INFO";
type ResultFilter = "ALL" | "UNMATCH" | "MATCH" | "MIRROR" | "NA";
type StatusFilter = "ALL" | "PENDING" | "IN_NEGOTIATION" | "RESOLVED" | "EXCLUDED";

const ROOT_CAUSE_SHORT: Record<string, string> = {
  MATCH: "Coincide",
  BOTH_EMPTY: "Ambos vacíos",
  MISSING_EMISOR: "Falta CP1",
  MISSING_RECEPTOR: "Falta CP2",
  MIRROR_MATCH: "Espejo",
  NUMERIC_DELTA: "Diferencia numérica",
  NUMERIC_WITHIN_TOLERANCE: "Dentro tolerancia",
  DATE_MISMATCH: "Diferencia fecha",
  FORMAT_DIFFERENCE: "Formato",
  VALUE_MISMATCH: "Valor distinto",
  NOT_APPLICABLE: "N/A",
};

export default function TradeDetailPage() {
  const { id: sessionId, tradeId } = useParams<{ id: string; tradeId: string }>();
  const [trade, setTrade] = useState<TradeDetail | null>(null);
  const [selectedField, setSelectedField] = useState<FieldComparison | null>(null);
  const [search, setSearch] = useState("");
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>("ALL");
  const [resultFilter, setResultFilter] = useState<ResultFilter>("ALL");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("ALL");
  const [tableFilter, setTableFilter] = useState("ALL");
  const [loading, setLoading] = useState(true);
  const [tradeAnalysis, setTradeAnalysis] = useState<TradeAnalysis | null>(null);
  const [analyzingTrade, setAnalyzingTrade] = useState(false);

  useEffect(() => {
    if (!tradeId) return;
    getTrade(Number(tradeId))
      .then(setTrade)
      .catch(() => toast.error("Error al cargar la operación"))
      .finally(() => setLoading(false));
  }, [tradeId]);

  const filteredFields = useMemo(() => {
    if (!trade) return [];
    return trade.field_comparisons.filter((f) => {
      if (severityFilter !== "ALL" && f.severity !== severityFilter) return false;
      if (resultFilter !== "ALL" && f.result !== resultFilter) return false;
      if (statusFilter !== "ALL" && f.status !== statusFilter) return false;
      if (tableFilter !== "ALL" && f.table_number !== Number(tableFilter)) return false;
      if (search && !f.field_name.toLowerCase().includes(search.toLowerCase())) return false;
      return true;
    });
  }, [trade, severityFilter, resultFilter, statusFilter, tableFilter, search]);

  const handleFieldUpdated = useCallback((updated: FieldComparison) => {
    setTrade((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        field_comparisons: prev.field_comparisons.map((f) => (f.id === updated.id ? updated : f)),
      };
    });
    setSelectedField(updated);
  }, []);

  const handleBulkResolve = async () => {
    if (!trade) return;
    try {
      const result = await bulkUpdate(trade.session_id, { action: "resolve_all", trade_id: trade.id });
      toast.success(`${result.updated} campos resueltos`);
      const updated = await getTrade(trade.id);
      setTrade(updated);
    } catch {
      toast.error("Error en la actualización masiva");
    }
  };

  const handleAnalyzeTrade = async () => {
    if (!trade) return;
    setAnalyzingTrade(true);
    setTradeAnalysis(null);
    try {
      const result = await analyzeTrade(trade.id);
      setTradeAnalysis(result);
    } catch {
      toast.error("Error en el análisis IA — verifica el proveedor");
    } finally {
      setAnalyzingTrade(false);
    }
  };

  if (loading) return <div className="flex items-center justify-center h-64"><p className="text-zinc-500">Cargando operación...</p></div>;
  if (!trade) return <div className="flex items-center justify-center h-64"><p className="text-zinc-500">Operación no encontrada</p></div>;

  const unmatches = trade.field_comparisons.filter((f) => f.result === "UNMATCH").length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <Link to={`/sessions/${sessionId}`} className="flex items-center gap-1 text-sm text-zinc-500 hover:text-[#fc7c34] mb-1">
            <ArrowLeft className="h-3 w-3" /> Volver a la sesión
          </Link>
          <h1 className="text-2xl font-semibold text-zinc-900 font-mono">
            {trade.uti || `Operación #${trade.row_number}`}
          </h1>
          <p className="text-sm text-zinc-500 mt-1">
            {trade.sft_type}/{trade.action_type}
            {trade.emisor_lei && ` · CP1: ${trade.emisor_lei}`}
            {trade.receptor_lei && ` · CP2: ${trade.receptor_lei}`}
          </p>
        </div>
        <div className="flex gap-2">
          {trade.has_unmatches && (
            <Button
              variant="outline" size="sm"
              onClick={handleAnalyzeTrade}
              disabled={analyzingTrade}
              className="border-[#fc7c34] text-[#fc7c34] hover:bg-orange-50"
            >
              <Sparkles className="h-4 w-4 mr-1" />
              {analyzingTrade ? "Analizando..." : "Analizar con IA"}
            </Button>
          )}
          <Button variant="outline" size="sm" onClick={handleBulkResolve}>
            <CheckCircle2 className="h-4 w-4 mr-1" /> Resolver todo
          </Button>
        </div>
      </div>

      {analyzingTrade && (
        <Card className="border-orange-200 bg-orange-50">
          <CardContent className="py-4">
            <p className="text-sm text-orange-600 animate-pulse flex items-center gap-2">
              <Sparkles className="h-4 w-4" /> Analizando discrepancias con IA...
            </p>
          </CardContent>
        </Card>
      )}

      {tradeAnalysis && (
        <Card className="border-orange-200 bg-orange-50">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm flex items-center gap-2 text-orange-800">
                <Sparkles className="h-4 w-4" /> Análisis IA de la operación
              </CardTitle>
              <button onClick={() => setTradeAnalysis(null)} className="text-orange-400 hover:text-orange-600">
                <X className="h-4 w-4" />
              </button>
            </div>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {tradeAnalysis.summary && (
              <div>
                <p className="text-xs font-semibold text-zinc-500 uppercase mb-1">Resumen</p>
                <p className="text-zinc-700">{tradeAnalysis.summary}</p>
              </div>
            )}
            {tradeAnalysis.priority_field && (
              <div>
                <p className="text-xs font-semibold text-zinc-500 uppercase mb-1">Campo prioritario</p>
                <p className="text-zinc-700 font-medium">{tradeAnalysis.priority_field}</p>
              </div>
            )}
            {tradeAnalysis.main_risk && (
              <div>
                <p className="text-xs font-semibold text-red-500 uppercase mb-1">Riesgo principal</p>
                <p className="text-red-700">{tradeAnalysis.main_risk}</p>
              </div>
            )}
            {tradeAnalysis.recommended_action && (
              <div>
                <p className="text-xs font-semibold text-zinc-500 uppercase mb-1">Acción recomendada</p>
                <p className="text-zinc-700">{tradeAnalysis.recommended_action}</p>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricCard label="Total campos" value={trade.total_fields} />
        <MetricCard label="Discrepancias" value={unmatches} color="red" icon={<AlertTriangle className="h-3 w-3" />} />
        <MetricCard label="Críticas" value={trade.critical_count} color="red" />
        <MetricCard label="Advertencias" value={trade.warning_count} color="amber" />
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col md:flex-row gap-4 items-start md:items-center justify-between">
            <CardTitle className="text-base">
              Comparación de campos ({filteredFields.length} de {trade.field_comparisons.length})
            </CardTitle>
            <div className="relative">
              <Search className="h-4 w-4 absolute left-2 top-2.5 text-zinc-400" />
              <Input
                placeholder="Buscar campo..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-8 w-48 h-9"
              />
            </div>
          </div>

          <div className="flex flex-wrap gap-2 mt-3">
            <Tabs value={severityFilter} onValueChange={(v) => setSeverityFilter(v as SeverityFilter)}>
              <TabsList className="h-8">
                <TabsTrigger value="ALL" className="text-xs h-7 px-2">Todos</TabsTrigger>
                <TabsTrigger value="CRITICAL" className="text-xs h-7 px-2">Crítico</TabsTrigger>
                <TabsTrigger value="WARNING" className="text-xs h-7 px-2">Advertencia</TabsTrigger>
                <TabsTrigger value="INFO" className="text-xs h-7 px-2">Informativo</TabsTrigger>
              </TabsList>
            </Tabs>

            <Select value={resultFilter} onValueChange={(v) => setResultFilter(v as ResultFilter)}>
              <SelectTrigger className="w-36 h-8 text-xs">
                <ArrowUpDown className="h-3 w-3 mr-1" />
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">Todos los resultados</SelectItem>
                <SelectItem value="UNMATCH">Discrepancia</SelectItem>
                <SelectItem value="MATCH">Coincide</SelectItem>
                <SelectItem value="MIRROR">Espejo</SelectItem>
                <SelectItem value="NA">N/A</SelectItem>
              </SelectContent>
            </Select>

            <Select value={statusFilter} onValueChange={(v) => setStatusFilter(v as StatusFilter)}>
              <SelectTrigger className="w-40 h-8 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">Todos los estados</SelectItem>
                <SelectItem value="PENDING">Pendiente</SelectItem>
                <SelectItem value="IN_NEGOTIATION">En negociación</SelectItem>
                <SelectItem value="RESOLVED">Resuelto</SelectItem>
                <SelectItem value="EXCLUDED">Excluido</SelectItem>
              </SelectContent>
            </Select>

            <Select value={tableFilter} onValueChange={setTableFilter}>
              <SelectTrigger className="w-36 h-8 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">Todas las tablas</SelectItem>
                <SelectItem value="1">Tabla 1</SelectItem>
                <SelectItem value="2">Tabla 2</SelectItem>
                <SelectItem value="3">Tabla 3</SelectItem>
                <SelectItem value="4">Tabla 4</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          <div className="rounded-lg border overflow-hidden">
            <div className="max-h-[65vh] overflow-y-auto">
              <Table>
                <TableHeader>
                  <TableRow className="bg-zinc-50 sticky top-0">
                    <TableHead className="w-10">Tabla</TableHead>
                    <TableHead className="w-10">#</TableHead>
                    <TableHead>Campo</TableHead>
                    <TableHead className="w-10">Obl.</TableHead>
                    <TableHead>Valor CP1</TableHead>
                    <TableHead>Valor CP2</TableHead>
                    <TableHead>Causa raíz</TableHead>
                    <TableHead>Severidad</TableHead>
                    <TableHead>Estado</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredFields.map((field) => (
                    <TableRow
                      key={field.id}
                      className={`cursor-pointer ${
                        field.result === "UNMATCH"
                          ? field.severity === "CRITICAL"
                            ? "bg-red-50/50 hover:bg-red-50"
                            : field.severity === "WARNING"
                            ? "bg-amber-50/50 hover:bg-amber-50"
                            : "bg-blue-50/50 hover:bg-blue-50"
                          : field.result === "MIRROR"
                          ? "bg-purple-50/50 hover:bg-purple-50"
                          : "hover:bg-zinc-50"
                      }`}
                      onClick={() => setSelectedField(field)}
                    >
                      <TableCell className="text-xs text-zinc-500">{field.table_number}</TableCell>
                      <TableCell className="text-xs text-zinc-500">{field.field_number}</TableCell>
                      <TableCell className="font-medium text-sm">{field.field_name}</TableCell>
                      <TableCell className="text-xs font-semibold text-center">{field.obligation}</TableCell>
                      <TableCell className="text-xs font-mono max-w-36 truncate">{field.emisor_value || "—"}</TableCell>
                      <TableCell className="text-xs font-mono max-w-36 truncate">{field.receptor_value || "—"}</TableCell>
                      <TableCell className="text-xs text-zinc-500">{field.root_cause ? (ROOT_CAUSE_SHORT[field.root_cause] || field.root_cause) : "—"}</TableCell>
                      <TableCell><SeverityBadge severity={field.severity} /></TableCell>
                      <TableCell><StatusBadge status={field.status} /></TableCell>
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
