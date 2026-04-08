import { useState } from "react";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { SeverityBadge, ResultBadge, StatusBadge } from "./SeverityBadge";
import { updateField, type FieldResult } from "@/lib/api";
import { toast } from "sonner";

interface Props {
  field: FieldResult | null;
  open: boolean;
  onClose: () => void;
  onUpdated: (updated: FieldResult) => void;
}

export default function FieldDetailPanel({ field, open, onClose, onUpdated }: Props) {
  const [status, setStatus] = useState("");
  const [assignee, setAssignee] = useState("");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);

  const resetForm = (f: FieldResult) => {
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
      const updated = await updateField(field.id, {
        status,
        assignee: assignee || undefined,
        notes: notes || undefined,
      });
      onUpdated(updated);
      toast.success("Field updated successfully");
      onClose();
    } catch {
      toast.error("Failed to update field");
    } finally {
      setSaving(false);
    }
  };

  const handleOpenChange = (isOpen: boolean) => {
    if (!isOpen) {
      setStatus("");
      setAssignee("");
      setNotes("");
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
                <span className="text-sm text-zinc-500">Table {field.table_number} · Field {field.field_number}</span>
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
                  <p className="text-xs font-medium text-zinc-500">Obligation</p>
                  <p className="text-sm font-semibold">{field.obligation}</p>
                </div>
                <div className="space-y-1">
                  <p className="text-xs font-medium text-zinc-500">Validated</p>
                  <p className="text-sm font-semibold">{field.validated ? "Yes" : "No"}</p>
                </div>
              </div>

              <div className="space-y-3 rounded-lg border border-zinc-200 p-4">
                <h4 className="text-xs font-semibold text-zinc-500 uppercase tracking-wide">Values</h4>
                <div className="space-y-2">
                  <div>
                    <p className="text-xs text-zinc-500">Emisor</p>
                    <p className="text-sm font-mono bg-zinc-50 rounded px-2 py-1 break-all">
                      {field.emisor_value || "—"}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-zinc-500">Receptor</p>
                    <p className="text-sm font-mono bg-zinc-50 rounded px-2 py-1 break-all">
                      {field.receptor_value || "—"}
                    </p>
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                <h4 className="text-xs font-semibold text-zinc-500 uppercase tracking-wide">Resolution</h4>
                <div className="space-y-2">
                  <Label htmlFor="status">Status</Label>
                  <Select value={status} onValueChange={setStatus}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select status" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="PENDING">Pending</SelectItem>
                      <SelectItem value="IN_NEGOTIATION">In Negotiation</SelectItem>
                      <SelectItem value="RESOLVED">Resolved</SelectItem>
                      <SelectItem value="EXCLUDED">Excluded</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="assignee">Assignee</Label>
                  <Input
                    id="assignee"
                    value={assignee}
                    onChange={(e) => setAssignee(e.target.value)}
                    placeholder="Team member name"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="notes">Notes</Label>
                  <Textarea
                    id="notes"
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="Resolution notes..."
                    rows={3}
                  />
                </div>
              </div>

              <div className="flex gap-2">
                <Button onClick={handleSave} disabled={saving} className="flex-1">
                  {saving ? "Saving..." : "Save Changes"}
                </Button>
                <Button variant="outline" onClick={onClose}>
                  Cancel
                </Button>
              </div>
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}
