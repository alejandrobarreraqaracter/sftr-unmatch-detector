import { useEffect, useState } from "react";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { SeverityBadge, ResultBadge, StatusBadge } from "./SeverityBadge";
import { updateFieldComparison, analyzeField, getDemoUsers, type DemoUser, type FieldComparison, type FieldAnalysis } from "@/lib/api";
import { toast } from "sonner";
import { Sparkles } from "lucide-react";

const ROOT_CAUSE_LABELS: Record<string, string> = {
  MATCH: "Valores coinciden",
  BOTH_EMPTY: "Ambos valores vacíos",
  MISSING_EMISOR: "Valor CP1 ausente",
  MISSING_RECEPTOR: "Valor CP2 ausente",
  MIRROR_MATCH: "Valor espejo válido (ej. GIVE/TAKE)",
  NUMERIC_DELTA: "Diferencia numérica",
  NUMERIC_WITHIN_TOLERANCE: "Diferencia dentro de tolerancia",
  DATE_MISMATCH: "Diferencia en fecha",
  FORMAT_DIFFERENCE: "Mismo valor, formato distinto",
  VALUE_MISMATCH: "Valores distintos",
  NOT_APPLICABLE: "Campo no aplicable",
};

interface Props {
  field: FieldComparison | null;
  open: boolean;
  onClose: () => void;
  onUpdated: (updated: FieldComparison) => void;
}

export default function FieldDetailPanel({ field, open, onClose, onUpdated }: Props) {
  const [status, setStatus] = useState("");
  const [assignee, setAssignee] = useState("");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [analysis, setAnalysis] = useState<FieldAnalysis | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [users, setUsers] = useState<DemoUser[]>([]);

  useEffect(() => {
    getDemoUsers().then(setUsers).catch(() => {});
  }, []);

  const resetForm = (f: FieldComparison) => {
    setStatus(f.status);
    setAssignee(f.assignee || "");
    setNotes(f.notes || "");
  };

  if (field && status === "") {
    resetForm(field);
  }

  const handleSave = async () => {
    if (!field) return;
    setSaving(true);
    try {
      const updated = await updateFieldComparison(field.id, {
        status,
        assignee: assignee || undefined,
        notes: notes || undefined,
      });
      onUpdated(updated);
      toast.success("Campo actualizado correctamente");
      onClose();
    } catch {
      toast.error("Error al actualizar el campo");
    } finally {
      setSaving(false);
    }
  };

  const handleAnalyze = async () => {
    if (!field) return;
    setAnalyzing(true);
    setAnalysis(null);
    try {
      const result = await analyzeField(field.id);
      setAnalysis(result);
    } catch {
      toast.error("Error en el análisis IA — verifica la disponibilidad del proveedor");
    } finally {
      setAnalyzing(false);
    }
  };

  const handleOpenChange = (isOpen: boolean) => {
    if (!isOpen) {
      setStatus("");
      setAssignee("");
      setNotes("");
      setAnalysis(null);
      onClose();
    }
  };

  return (
    <Sheet open={open} onOpenChange={handleOpenChange}>
      <SheetContent className="w-full sm:max-w-lg overflow-y-auto">
        {field && (
          <>
            <SheetHeader>
              <SheetTitle className="text-left">
                <span className="text-sm text-zinc-500">Tabla {field.table_number} · Campo {field.field_number}</span>
                <br />
                {field.field_name}
              </SheetTitle>
            </SheetHeader>

            <div className="mt-6 space-y-6">
              <div className="flex gap-2 flex-wrap">
                <SeverityBadge severity={field.severity} />
                <ResultBadge result={field.result} />
                <StatusBadge status={field.status} />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <p className="text-xs font-medium text-zinc-500">Obligación</p>
                  <p className="text-sm font-semibold">{field.obligation || "—"}</p>
                </div>
                <div className="space-y-1">
                  <p className="text-xs font-medium text-zinc-500">Causa raíz</p>
                  <p className="text-sm font-semibold text-zinc-700">
                    {field.root_cause ? (ROOT_CAUSE_LABELS[field.root_cause] || field.root_cause) : "—"}
                  </p>
                </div>
              </div>

              <div className="space-y-3 rounded-lg border border-zinc-200 p-4 bg-zinc-50">
                <h4 className="text-xs font-semibold text-zinc-500 uppercase tracking-wide">Valores</h4>
                <div className="space-y-2">
                  <div>
                    <p className="text-xs text-zinc-500">CP1 (Emisor)</p>
                    <p className="text-sm font-mono bg-white border border-zinc-200 rounded px-2 py-1 break-all">
                      {field.emisor_value || "—"}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-zinc-500">CP2 (Receptor)</p>
                    <p className="text-sm font-mono bg-white border border-zinc-200 rounded px-2 py-1 break-all">
                      {field.receptor_value || "—"}
                    </p>
                  </div>
                </div>
              </div>

              {field.result === "UNMATCH" && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-semibold text-zinc-500 uppercase tracking-wide">Análisis IA</h4>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={handleAnalyze}
                      disabled={analyzing}
                      className="h-7 text-xs border-[#fc7c34] text-[#fc7c34] hover:bg-orange-50"
                    >
                      <Sparkles className="h-3 w-3 mr-1" />
                      {analyzing ? "Analizando..." : "Analizar"}
                    </Button>
                  </div>
                  {analyzing && (
                    <div className="rounded-lg border border-orange-200 bg-orange-50 p-3">
                      <p className="text-xs text-orange-600 animate-pulse">Consultando agente IA...</p>
                    </div>
                  )}
                  {analysis && (
                    <div className="rounded-lg border border-orange-200 bg-orange-50 p-3 space-y-2 text-xs">
                      {analysis.explanation && (
                        <div>
                          <p className="font-semibold text-zinc-700 mb-1">Explicación</p>
                          <p className="text-zinc-600">{analysis.explanation}</p>
                        </div>
                      )}
                      {analysis.resolution_steps?.length > 0 && (
                        <div>
                          <p className="font-semibold text-zinc-700 mb-1">Pasos de resolución</p>
                          <ul className="space-y-1 list-disc list-inside text-zinc-600">
                            {analysis.resolution_steps.map((s, i) => <li key={i}>{s}</li>)}
                          </ul>
                        </div>
                      )}
                      {analysis.regulatory_risk && (
                        <div>
                          <p className="font-semibold text-red-600 mb-1">Riesgo regulatorio</p>
                          <p className="text-red-700">{analysis.regulatory_risk}</p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              <div className="space-y-4">
                <h4 className="text-xs font-semibold text-zinc-500 uppercase tracking-wide">Resolución</h4>
                <div className="space-y-2">
                  <Label>Estado</Label>
                  <Select value={status} onValueChange={setStatus}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="PENDING">Pendiente</SelectItem>
                      <SelectItem value="IN_NEGOTIATION">En negociación</SelectItem>
                      <SelectItem value="RESOLVED">Resuelto</SelectItem>
                      <SelectItem value="EXCLUDED">Excluido</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Responsable</Label>
                  <Select value={assignee || "__none__"} onValueChange={(value) => setAssignee(value === "__none__" ? "" : value)}>
                    <SelectTrigger><SelectValue placeholder="Seleccionar responsable" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="__none__">Sin asignar</SelectItem>
                      {users.map((user) => (
                        <SelectItem key={user.username} value={user.display_name}>
                          {user.display_name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Notas</Label>
                  <Textarea
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="Notas de resolución..."
                    rows={3}
                  />
                </div>
              </div>

              <div className="flex gap-2">
                <Button onClick={handleSave} disabled={saving} className="flex-1">
                  {saving ? "Guardando..." : "Guardar cambios"}
                </Button>
                <Button variant="outline" onClick={onClose}>Cancelar</Button>
              </div>
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}
