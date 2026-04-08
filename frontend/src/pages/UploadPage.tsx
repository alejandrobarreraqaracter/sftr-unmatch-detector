import { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { uploadFiles } from "@/lib/api";
import { toast } from "sonner";
import { Upload, FileText, ArrowRight } from "lucide-react";

export default function UploadPage() {
  const navigate = useNavigate();
  const [emisorFile, setEmisorFile] = useState<File | null>(null);
  const [receptorFile, setReceptorFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);

  const handleDrop = useCallback(
    (setter: (f: File) => void) => (e: React.DragEvent) => {
      e.preventDefault();
      const file = e.dataTransfer.files[0];
      if (file) setter(file);
    },
    []
  );

  const handleFileSelect = (setter: (f: File) => void) => (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) setter(file);
  };

  const handleUpload = async () => {
    if (!emisorFile || !receptorFile) {
      toast.error("Please select both files");
      return;
    }
    setUploading(true);
    try {
      const session = await uploadFiles(emisorFile, receptorFile);
      toast.success(`Comparison complete: ${session.total_unmatches} mismatches found`);
      navigate(`/sessions/${session.id}`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-zinc-900">Upload Reports</h1>
        <p className="text-sm text-zinc-500 mt-1">
          Upload two SFTR reports (CSV or XML) to compare field-by-field
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <FileText className="h-4 w-4 text-blue-600" />
              Emisor Report
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div
              className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                emisorFile ? "border-green-300 bg-green-50" : "border-zinc-300 hover:border-zinc-400"
              }`}
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDrop(setEmisorFile)}
            >
              {emisorFile ? (
                <div className="space-y-2">
                  <FileText className="h-8 w-8 text-green-600 mx-auto" />
                  <p className="text-sm font-medium text-green-700">{emisorFile.name}</p>
                  <p className="text-xs text-zinc-500">{(emisorFile.size / 1024).toFixed(1)} KB</p>
                  <Button variant="outline" size="sm" onClick={() => setEmisorFile(null)}>
                    Remove
                  </Button>
                </div>
              ) : (
                <div className="space-y-2">
                  <Upload className="h-8 w-8 text-zinc-400 mx-auto" />
                  <p className="text-sm text-zinc-600">Drop file here or click to browse</p>
                  <p className="text-xs text-zinc-400">CSV (semicolon-separated) or XML</p>
                  <label>
                    <input
                      type="file"
                      accept=".csv,.xml"
                      className="hidden"
                      onChange={handleFileSelect(setEmisorFile)}
                    />
                    <Button variant="outline" size="sm" asChild>
                      <span>Browse Files</span>
                    </Button>
                  </label>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <FileText className="h-4 w-4 text-purple-600" />
              Receptor Report
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div
              className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                receptorFile ? "border-green-300 bg-green-50" : "border-zinc-300 hover:border-zinc-400"
              }`}
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDrop(setReceptorFile)}
            >
              {receptorFile ? (
                <div className="space-y-2">
                  <FileText className="h-8 w-8 text-green-600 mx-auto" />
                  <p className="text-sm font-medium text-green-700">{receptorFile.name}</p>
                  <p className="text-xs text-zinc-500">{(receptorFile.size / 1024).toFixed(1)} KB</p>
                  <Button variant="outline" size="sm" onClick={() => setReceptorFile(null)}>
                    Remove
                  </Button>
                </div>
              ) : (
                <div className="space-y-2">
                  <Upload className="h-8 w-8 text-zinc-400 mx-auto" />
                  <p className="text-sm text-zinc-600">Drop file here or click to browse</p>
                  <p className="text-xs text-zinc-400">CSV (semicolon-separated) or XML</p>
                  <label>
                    <input
                      type="file"
                      accept=".csv,.xml"
                      className="hidden"
                      onChange={handleFileSelect(setReceptorFile)}
                    />
                    <Button variant="outline" size="sm" asChild>
                      <span>Browse Files</span>
                    </Button>
                  </label>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="flex justify-center">
        <Button
          size="lg"
          disabled={!emisorFile || !receptorFile || uploading}
          onClick={handleUpload}
          className="px-8"
        >
          {uploading ? (
            "Comparing..."
          ) : (
            <>
              Compare Reports <ArrowRight className="h-4 w-4 ml-2" />
            </>
          )}
        </Button>
      </div>

      <Card className="bg-zinc-50 border-zinc-200">
        <CardContent className="py-4">
          <p className="text-xs text-zinc-500">
            <strong>CSV format:</strong> Semicolon-separated with columns <code className="bg-white px-1 rounded">field_name;value</code>.
            Auto-detects SFT type and action type from the data.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
