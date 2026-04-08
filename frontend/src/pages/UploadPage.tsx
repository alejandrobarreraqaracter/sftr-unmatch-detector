import { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { uploadFile } from "@/lib/api";
import { toast } from "sonner";
import { Upload, FileText, CheckCircle2, Info } from "lucide-react";

export default function UploadPage() {
  const navigate = useNavigate();
  const fileRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [emisorName, setEmisorName] = useState("CP1");
  const [receptorName, setReceptorName] = useState("CP2");
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  const handleFile = (f: File) => {
    if (!f.name.endsWith(".csv")) {
      toast.error("Only CSV files are supported");
      return;
    }
    setFile(f);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  };

  const handleSubmit = async () => {
    if (!file) return;
    setUploading(true);
    try {
      const session = await uploadFile(file, emisorName, receptorName);
      toast.success(`${session.total_trades} trades processed — ${session.total_unmatches} unmatches found`);
      navigate(`/sessions/${session.id}`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-zinc-900">Upload Reconciliation File</h1>
        <p className="text-sm text-zinc-500 mt-1">
          Upload a tabular CSV with both counterparty values per trade
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Counterparty Labels</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-4">
          <div className="space-y-1">
            <Label htmlFor="emisor">CP1 Name (Emisor)</Label>
            <Input
              id="emisor"
              value={emisorName}
              onChange={(e) => setEmisorName(e.target.value)}
              placeholder="e.g. Santander"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="receptor">CP2 Name (Receptor)</Label>
            <Input
              id="receptor"
              value={receptorName}
              onChange={(e) => setReceptorName(e.target.value)}
              placeholder="e.g. Counterparty"
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Reconciliation File</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div
            className={`border-2 border-dashed rounded-lg p-10 text-center transition-colors cursor-pointer ${
              dragOver
                ? "border-[#fc7c34] bg-orange-50"
                : file
                ? "border-green-400 bg-green-50"
                : "border-zinc-300 hover:border-zinc-400"
            }`}
            onDrop={handleDrop}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onClick={() => fileRef.current?.click()}
          >
            {file ? (
              <div className="flex flex-col items-center gap-2">
                <CheckCircle2 className="h-10 w-10 text-green-500" />
                <p className="font-medium text-green-700">{file.name}</p>
                <p className="text-xs text-green-600">{(file.size / 1024).toFixed(1)} KB — click to change</p>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-2">
                <Upload className="h-10 w-10 text-zinc-400" />
                <p className="font-medium text-zinc-600">Drop CSV file here or click to browse</p>
                <p className="text-xs text-zinc-400">Semicolon-separated, UTF-8</p>
              </div>
            )}
          </div>
          <input
            ref={fileRef}
            type="file"
            accept=".csv"
            className="hidden"
            onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
          />

          <Button
            className="w-full"
            disabled={!file || uploading}
            onClick={handleSubmit}
          >
            {uploading ? (
              "Processing..."
            ) : (
              <>
                <FileText className="h-4 w-4 mr-2" />
                Run Reconciliation
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
