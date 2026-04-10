import { Badge } from "@/components/ui/badge";

const severityStyles: Record<string, string> = {
  CRITICAL: "bg-red-100 text-red-800 border-red-200",
  WARNING: "bg-amber-100 text-amber-800 border-amber-200",
  INFO: "bg-blue-100 text-blue-800 border-blue-200",
  NONE: "bg-green-100 text-green-800 border-green-200",
};

const resultStyles: Record<string, string> = {
  MATCH: "bg-green-100 text-green-800 border-green-200",
  UNMATCH: "bg-red-100 text-red-800 border-red-200",
  MIRROR: "bg-purple-100 text-purple-800 border-purple-200",
  NA: "bg-zinc-100 text-zinc-500 border-zinc-200",
};

const statusStyles: Record<string, string> = {
  PENDING: "bg-amber-100 text-amber-800 border-amber-200",
  IN_NEGOTIATION: "bg-blue-100 text-blue-800 border-blue-200",
  RESOLVED: "bg-green-100 text-green-800 border-green-200",
  EXCLUDED: "bg-zinc-100 text-zinc-500 border-zinc-200",
};

const severityLabels: Record<string, string> = {
  CRITICAL: "Crítico",
  WARNING: "Advertencia",
  INFO: "Informativo",
  NONE: "Correcto",
};

const resultLabels: Record<string, string> = {
  MATCH: "Coincide",
  UNMATCH: "Discrepancia",
  MIRROR: "Espejo",
  NA: "N/A",
};

const statusLabels: Record<string, string> = {
  PENDING: "Pendiente",
  IN_NEGOTIATION: "En negociación",
  RESOLVED: "Resuelto",
  EXCLUDED: "Excluido",
};

export function SeverityBadge({ severity }: { severity: string }) {
  return (
    <Badge variant="outline" className={`text-xs font-medium ${severityStyles[severity] || ""}`}>
      {severityLabels[severity] || severity}
    </Badge>
  );
}

export function ResultBadge({ result }: { result: string }) {
  return (
    <Badge variant="outline" className={`text-xs font-medium ${resultStyles[result] || ""}`}>
      {resultLabels[result] || result}
    </Badge>
  );
}

export function StatusBadge({ status }: { status: string }) {
  return (
    <Badge variant="outline" className={`text-xs font-medium ${statusStyles[status] || ""}`}>
      {statusLabels[status] || status}
    </Badge>
  );
}
