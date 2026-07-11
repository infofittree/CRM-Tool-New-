import { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth";
import { type LeadHandover, acceptHandover, declineHandover } from "@/lib/api";
import { X, CheckCircle2, XCircle, ArrowRightLeft, User, Building2, AlertTriangle, Clock } from "lucide-react";

const REASON_LABELS: Record<string, string> = {
  product_expertise: "Product Expertise",
  language: "Language Match",
  region: "Region / Territory",
  customer_request: "Customer Request",
  workload: "Workload Balance",
  leave: "Leave / Availability",
  manager_decision: "Manager Decision",
  other: "Other",
};

interface HandoverResponseModalProps {
  handover: LeadHandover;
  onClose: () => void;
}

export default function HandoverResponseModal({ handover, onClose }: HandoverResponseModalProps) {
  const queryClient = useQueryClient();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<"accepted" | "declined" | null>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  useEffect(() => {
    if (result) {
      const t = setTimeout(onClose, 1500);
      return () => clearTimeout(t);
    }
  }, [result, onClose]);

  const handleAccept = async () => {
    setSubmitting(true);
    setError("");
    try {
      await acceptHandover(handover.id);
      queryClient.invalidateQueries({ queryKey: ["leads"] });
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      setResult("accepted");
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to accept transfer");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDecline = async () => {
    setSubmitting(true);
    setError("");
    try {
      await declineHandover(handover.id);
      queryClient.invalidateQueries({ queryKey: ["leads"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      setResult("declined");
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to decline transfer");
    } finally {
      setSubmitting(false);
    }
  };

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/25 backdrop-blur-[2px]" onClick={onClose}>
      <div
        className="bg-white rounded-2xl shadow-[var(--shadow-modal)] w-full max-w-[520px] mx-4 max-h-[85vh] overflow-hidden flex flex-col animate-scale-in"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border/40 shrink-0 rounded-t-2xl">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-amber-100 flex items-center justify-center">
              <ArrowRightLeft className="w-4 h-4 text-amber-600" />
            </div>
            <div>
              <h2 className="font-bold text-[15px]">Lead Transfer Request</h2>
              <p className="text-[11px] text-muted-foreground/50">Review and respond</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-muted/60 transition-colors">
            <X className="w-4 h-4 text-muted-foreground/60" />
          </button>
        </div>

        {/* Result Screen */}
        {result ? (
          <div className="flex-1 flex flex-col items-center justify-center py-16 px-6">
            {result === "accepted" ? (
              <><CheckCircle2 className="w-12 h-12 text-emerald-500 mb-4" /><p className="text-lg font-semibold">Transfer Accepted</p><p className="text-sm text-muted-foreground mt-1">Lead ownership has been transferred</p></>
            ) : (
              <><XCircle className="w-12 h-12 text-muted-foreground/50 mb-4" /><p className="text-lg font-semibold">Transfer Declined</p><p className="text-sm text-muted-foreground mt-1">The sender has been notified</p></>
            )}
          </div>
        ) : (
          <>
            {/* Body */}
            <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
              {/* Transfer Info */}
              <div className="rounded-[14px] bg-amber-50/50 border border-amber-200 p-4">
                <div className="flex items-center gap-3 mb-3">
                  <User className="w-4 h-4 text-amber-600 shrink-0" />
                  <p className="text-sm"><span className="font-semibold">{handover.from_user}</span> wants to transfer a lead to you</p>
                </div>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div><p className="text-[11px] text-muted-foreground/60">Lead</p><p className="font-medium">{handover.company_name || handover.lead_id}</p></div>
                  <div><p className="text-[11px] text-muted-foreground/60">Reason</p><p className="font-medium">{REASON_LABELS[handover.reason] || handover.reason}</p></div>
                  <div><p className="text-[11px] text-muted-foreground/60">Requested</p><p className="font-medium">{new Date(handover.requested_at).toLocaleString()}</p></div>
                </div>
              </div>

              {handover.notes && (
                <div>
                  <p className="text-[11px] font-semibold text-muted-foreground/50 uppercase tracking-wider mb-1">Notes</p>
                  <p className="text-sm bg-muted/30 rounded-lg p-3.5 whitespace-pre-wrap">{handover.notes}</p>
                </div>
              )}

              {error && <p className="text-sm text-destructive">{error}</p>}
            </div>

            {/* Footer */}
            <div className="flex items-center gap-3 px-6 py-4 border-t border-border/40 shrink-0 rounded-b-2xl">
              <Button onClick={handleAccept} disabled={submitting} className="flex-1 gap-2 bg-emerald-600 hover:bg-emerald-700 rounded-[12px]">
                <CheckCircle2 className="w-4 h-4" />{submitting ? "Processing..." : "Accept Transfer"}
              </Button>
              <Button variant="outline" onClick={handleDecline} disabled={submitting} className="rounded-[12px] gap-2">
                <XCircle className="w-4 h-4" />Decline
              </Button>
            </div>
          </>
        )}
      </div>
    </div>,
    document.body
  );
}
