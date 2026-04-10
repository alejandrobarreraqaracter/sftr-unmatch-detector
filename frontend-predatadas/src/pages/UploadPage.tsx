import { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { uploadFile } from "@/lib/api";
import { toast } from "sonner";
import { Upload, FileText, CheckCircle2, Info } from "lucide-react";

type UploadBatchItem = {
  name: string;
  status: "pending" | "uploading" | "done" | "error";
  detail?: string;
  sessionId?: number;
};

export default function UploadPage() {
  const navigate = useNavigate();
  const fileRef = useRef<HTMLInputElement>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [emisorName, setEmisorName] = useState("CP1");
  const [receptorName, setReceptorName] = useState("CP2");
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [uploadItems, setUploadItems] = useState<UploadBatchItem[]>([]);

  const syncUploadItems = (acceptedFiles: File[]) => {
    setUploadItems(
      acceptedFiles.map((file) => ({
        name: file.name,
        status: "pending",
      }))
    );
  };

  const handleFiles = (incoming: FileList | File[]) => {
    const acceptedFiles = Array.from(incoming).filter((f) => f.name.toLowerCase().endsWith(".csv"));
    const rejectedCount = Array.from(incoming).length - acceptedFiles.length;
    if (rejectedCount > 0) {
      toast.error("Solo se admiten ficheros CSV");
    }
    if (acceptedFiles.length === 0) return;
    setFiles(acceptedFiles);
    syncUploadItems(acceptedFiles);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files?.length) handleFiles(e.dataTransfer.files);
  };

  const handleSubmit = async () => {
    if (files.length === 0) return;
    setUploading(true);
    let successCount = 0;
    let failureCount = 0;
    let lastSessionId: number | null = null;

    try {
      for (const file of files) {
        setUploadItems((current) =>
          current.map((item) =>
            item.name === file.name ? { ...item, status: "uploading", detail: "Procesando..." } : item
          )
        );

        try {
          const session = await uploadFile(file, emisorName, receptorName, "predatadas");
          successCount += 1;
          lastSessionId = session.id;
          setUploadItems((current) =>
            current.map((item) =>
              item.name === file.name
                ? {
                    ...item,
                    status: "done",
                    sessionId: session.id,
                    detail: `${session.total_trades} operaciones · ${session.total_unmatches} discrepancias`,
                  }
                : item
            )
          );
        } catch (err) {
          failureCount += 1;
          setUploadItems((current) =>
            current.map((item) =>
              item.name === file.name
                ? {
                    ...item,
                    status: "error",
                    detail: err instanceof Error ? err.message : "Error de carga",
                  }
                : item
            )
          );
        }
      }

      if (successCount > 0 && failureCount === 0) {
        toast.success(`${successCount} ficheros cargados correctamente`);
      } else if (successCount > 0 && failureCount > 0) {
        toast.warning(`${successCount} ficheros cargados, ${failureCount} con error`);
      } else {
        toast.error("No se pudo cargar ningún fichero");
      }

      if (lastSessionId) {
        navigate("/sessions");
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error en la carga por lotes");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-zinc-900">Cargar fichero predatadas</h1>
        <p className="text-sm text-zinc-500 mt-1">
          Carga un CSV tabular con CP1 y CP2 para los 7 campos clave de predatadas
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Etiquetas de contraparte</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-4">
          <div className="space-y-1">
            <Label htmlFor="emisor">Nombre CP1</Label>
            <Input
              id="emisor"
              value={emisorName}
              onChange={(e) => setEmisorName(e.target.value)}
              placeholder="Ej. Santander"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="receptor">Nombre CP2</Label>
            <Input
              id="receptor"
              value={receptorName}
              onChange={(e) => setReceptorName(e.target.value)}
              placeholder="Ej. Contraparte"
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Ficheros predatadas</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div
            className={`border-2 border-dashed rounded-lg p-10 text-center transition-colors cursor-pointer ${
              dragOver
                ? "border-[#fc7c34] bg-orange-50"
                : files.length > 0
                ? "border-green-400 bg-green-50"
                : "border-zinc-300 hover:border-zinc-400"
            }`}
            onDrop={handleDrop}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onClick={() => fileRef.current?.click()}
          >
            {files.length > 0 ? (
              <div className="flex flex-col items-center gap-2">
                <CheckCircle2 className="h-10 w-10 text-green-500" />
                <p className="font-medium text-green-700">{files.length} fichero(s) seleccionados</p>
                <p className="text-xs text-green-600">Carga múltiple preparada — haz clic para cambiar</p>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-2">
                <Upload className="h-10 w-10 text-zinc-400" />
                <p className="font-medium text-zinc-600">Suelta aquí uno o varios CSV o haz clic para buscarlos</p>
                <p className="text-xs text-zinc-400">Separados por punto y coma, UTF-8</p>
              </div>
            )}
          </div>
          <input
            ref={fileRef}
            type="file"
            accept=".csv"
            multiple
            className="hidden"
            onChange={(e) => e.target.files && handleFiles(e.target.files)}
          />

          {uploadItems.length > 0 && (
            <div className="rounded-lg border border-zinc-200 overflow-hidden">
              <div className="bg-zinc-50 px-3 py-2 text-xs font-medium text-zinc-600">
                Lote de carga ({uploadItems.length} ficheros)
              </div>
              <div className="divide-y divide-zinc-200">
                {uploadItems.map((item) => (
                  <div key={item.name} className="flex items-start justify-between gap-3 px-3 py-2 text-sm">
                    <div className="min-w-0">
                      <p className="truncate font-medium text-zinc-900">{item.name}</p>
                      {item.detail && <p className="mt-0.5 text-xs text-zinc-500">{item.detail}</p>}
                    </div>
                    <span
                      className={
                        item.status === "done"
                          ? "rounded-full border border-green-200 bg-green-50 px-2 py-0.5 text-xs font-medium text-green-700"
                          : item.status === "error"
                            ? "rounded-full border border-red-200 bg-red-50 px-2 py-0.5 text-xs font-medium text-red-700"
                            : item.status === "uploading"
                              ? "rounded-full border border-orange-200 bg-orange-50 px-2 py-0.5 text-xs font-medium text-orange-700"
                              : "rounded-full border border-zinc-200 bg-zinc-50 px-2 py-0.5 text-xs font-medium text-zinc-600"
                      }
                    >
                      {item.status === "done"
                        ? "Cargado"
                        : item.status === "error"
                          ? "Error"
                          : item.status === "uploading"
                            ? "Procesando"
                            : "Pendiente"}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <Button
            className="w-full"
            disabled={files.length === 0 || uploading}
            onClick={handleSubmit}
          >
            {uploading ? (
              "Procesando lote..."
            ) : (
              <>
                <FileText className="h-4 w-4 mr-2" />
                Ejecutar conciliación en lote
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      <Card className="border-zinc-200 bg-zinc-50">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2 text-zinc-600">
            <Info className="h-4 w-4" />
            Expected CSV Format
          </CardTitle>
        </CardHeader>
        <CardContent className="text-xs text-zinc-600 space-y-2">
          <p>Semicolon-separated CSV with a header row. One row per trade. Required columns:</p>
          <ul className="list-disc list-inside space-y-1 ml-2">
            <li><code className="bg-zinc-100 px-1 rounded">uti</code> — Unique Trade Identifier</li>
            <li><code className="bg-zinc-100 px-1 rounded">sft_type</code> — Repo, BSB, SL, ML</li>
            <li><code className="bg-zinc-100 px-1 rounded">action_type</code> — NEWT, MODI, EROR, etc.</li>
            <li>
              Per field:{" "}
              <code className="bg-zinc-100 px-1 rounded">{"{field_name}_cp1"}</code> and{" "}
              <code className="bg-zinc-100 px-1 rounded">{"{field_name}_cp2"}</code>
            </li>
          </ul>
          <p className="text-zinc-500">
            Sample file: <code className="bg-zinc-100 px-1 rounded">backend/sample_data/sftr_reconciliation_sample.csv</code>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
