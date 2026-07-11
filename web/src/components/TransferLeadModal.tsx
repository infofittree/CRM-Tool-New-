import { useState, useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth";
import api, { type Lead, type LeadHandover, createHandover } from "@/lib/api";
import { X, ArrowRightLeft, Search, User } from "lucide-react";

const HANDOVER_REASONS = [
  { value: "product_expertise", label: "Product Expertise" },
  { value: "language", label: "Language Match" },
  { value: "region", label: "Region / Territory" },
  { value: "customer_request", label: "Customer Request" },
  { value: "workload", label: "Workload Balance" },
  { value: "leave", label: "Leave / Availability" },
  { value: "manager_decision", label: "Manager Decision" },
  { value: "other", label: "Other" },
];

interface TransferLeadModalProps {
  lead: Lead;
  onClose: () => void;
}

export default function TransferLeadModal({ lead, onClose }: TransferLeadModalProps) {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [teammates, setTeammates] = useState<{ full_name: string; role: string }[]>([]);
  const [recipientSearch, setRecipientSearch] = useState("");
  const [selectedRecipient, setSelectedRecipient] = useState("");
  const [reason, setReason] = useState("");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const searchRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api.get("/users/transfer-recipients").then((r) => {
      const me = user?.full_name?.toLowerCase();
      setTeammates(r.data.filter((u: any) => u.full_name.toLowerCase() !== me));
    }).catch(() => {});
  }, [user]);

  useEffect(() => {
    if (searchRef.current) searchRef.current.focus();
  }, []);

  const filtered = teammates.filter((t) =>
    !recipientSearch || t.full_name.toLowerCase().includes(recipientSearch.toLowerCase())
  );

  const handleSubmit = async () => {
    if (!selectedRecipient || !reason) return;
    setSubmitting(true);
    setError("");
    try {
      await createHandover(lead.lead_id, {
        to_user: selectedRecipient,
        reason,
        notes: notes.trim() || undefined,
      });
      queryClient.invalidateQueries({ queryKey: ["leads"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to create transfer request");
    } finally {
      setSubmitting(false);
    }
  };

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/25 backdrop-blur-[2px]" onClick={onClose}>
      <div
        className="bg-white rounded-2xl shadow-[var(--shadow-modal)] w-full max-w-[520px] sm:max-w-[600px] md:max-w-[700px] mx-4 max-h-[85vh] overflow-hidden flex flex-col animate-scale-in"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border/40 shrink-0 rounded-t-2xl">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
              <ArrowRightLeft className="w-4 h-4 text-primary" />
            </div>
            <div>
              <h2 className="font-bold text-[15px]">Transfer Lead</h2>
              <p className="text-[11px] text-muted-foreground/50">Reassign ownership to another team member</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-muted/60 transition-colors">
            <X className="w-4 h-4 text-muted-foreground/60" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
          {/* Current Owner + Lead Info */}
          <div className="grid grid-cols-2 gap-4">
            <div className="rounded-[14px] bg-muted/20 p-4">
              <p className="text-[11px] font-semibold text-muted-foreground/50 uppercase tracking-wider mb-1">Current Owner</p>
              <p className="text-sm font-medium">{lead.assigned_to || "Unassigned"}</p>
            </div>
            <div className="rounded-[14px] bg-muted/20 p-4">
              <p className="text-[11px] font-semibold text-muted-foreground/50 uppercase tracking-wider mb-1">Lead</p>
              <p className="text-sm font-medium truncate">{lead.company_name || lead.lead_id}</p>
              <p className="text-[11px] text-muted-foreground/50 font-mono">{lead.lead_id}</p>
            </div>
          </div>

          {/* Recipient */}
          <div>
            <label className="text-sm font-medium text-foreground block mb-1.5">Recipient *</label>
            {selectedRecipient ? (
              <div className="flex items-center gap-2 p-3 rounded-lg border border-primary/30 bg-primary/[0.03]">
                <div className="w-7 h-7 rounded-full bg-primary/10 flex items-center justify-center">
                  <User className="w-3.5 h-3.5 text-primary" />
                </div>
                <span className="text-sm font-medium flex-1">{selectedRecipient}</span>
                <button onClick={() => setSelectedRecipient("")} className="p-1 rounded hover:bg-muted"><X className="w-3.5 h-3.5" /></button>
              </div>
            ) : (
              <div className="space-y-2">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground/40" />
                  <input ref={searchRef} type="text" value={recipientSearch} onChange={(e) => setRecipientSearch(e.target.value)}
                    placeholder="Search team member..."
                    className="w-full pl-9 pr-4 py-2.5 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20" />
                </div>
                <div className="max-h-[160px] overflow-y-auto border rounded-lg divide-y divide-border/40">
                  {filtered.length === 0 ? (
                    <p className="p-3 text-sm text-muted-foreground text-center">No team members found</p>
                  ) : filtered.map((t) => (
                    <button key={t.full_name} onClick={() => { setSelectedRecipient(t.full_name); setRecipientSearch(""); }}
                      className="w-full text-left px-3 py-2.5 text-sm hover:bg-muted/40 transition-colors flex items-center gap-2">
                      <User className="w-4 h-4 text-muted-foreground/50 shrink-0" />
                      <span className="font-medium">{t.full_name}</span>
                      <span className="text-[11px] text-muted-foreground/40 ml-auto">{t.role}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Reason */}
          <div>
            <label className="text-sm font-medium text-foreground block mb-1.5">Reason *</label>
            <select value={reason} onChange={(e) => setReason(e.target.value)}
              className="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20">
              <option value="">Select a reason...</option>
              {HANDOVER_REASONS.map((r) => (<option key={r.value} value={r.value}>{r.label}</option>))}
            </select>
          </div>

          {/* Notes */}
          <div>
            <label className="text-sm font-medium text-foreground block mb-1.5">Notes <span className="text-muted-foreground/50 font-normal">(optional)</span></label>
            <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={3}
              placeholder="Any context for the recipient..."
              className="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 resize-none" />
          </div>

          {error && <p className="text-sm text-destructive">{error}</p>}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-border/40 shrink-0 rounded-b-2xl">
          <Button variant="outline" onClick={onClose} className="rounded-[12px]">Cancel</Button>
          <Button onClick={handleSubmit} disabled={submitting || !selectedRecipient || !reason} className="rounded-[12px] gap-2">
            {submitting ? "Sending..." : <><ArrowRightLeft className="w-4 h-4" />Transfer Lead</>}
          </Button>
        </div>
      </div>
    </div>,
    document.body
  );
}
