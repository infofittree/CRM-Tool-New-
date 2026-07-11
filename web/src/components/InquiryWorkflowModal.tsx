import { useState, useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth";
import {
  fetchInquiries, updateInquiry, commitInquiry,
  type Inquiry, COMMITMENT_LABELS,
  DISPLAY_STATUS_LABELS, DISPLAY_STATUS_COLORS,
  fetchInquiryRevisions, requestRevision, respondToRevision,
  type InquiryRevision, REVISION_REASONS, REVISION_STATUS_LABELS,
} from "@/lib/inquiries";
import {
  X, CheckCircle2, Clock, Calendar, Timer, AlertTriangle,
  User, ArrowRight, Building2, Check, MessageSquare,
} from "lucide-react";

type ModalView = "details" | "action" | "revision" | "success";

interface InquiryWorkflowModalProps {
  inquiry: Inquiry;
  onClose: () => void;
}

export default function InquiryWorkflowModal({ inquiry: initialInquiry, onClose }: InquiryWorkflowModalProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const isProc = user?.role === "Admin" || user?.role === "Manager" || user?.role === "Procurement";

  const [inquiry, setInquiry] = useState(initialInquiry);
  const [view, setView] = useState<ModalView>("details");
  const [transitioning, setTransitioning] = useState(false);
  const [error, setError] = useState("");

  // Action form state
  const [commitType, setCommitType] = useState<string>("");
  const [commitResponse, setCommitResponse] = useState("");
  const [commitDate, setCommitDate] = useState("");
  const [respondText, setRespondText] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // Revision state
  const [revisions, setRevisions] = useState<InquiryRevision[]>([]);
  const [revisionReason, setRevisionReason] = useState("");
  const [revisionFeedback, setRevisionFeedback] = useState("");
  const [revisionTargetPrice, setRevisionTargetPrice] = useState("");
  const [revisionQuantity, setRevisionQuantity] = useState("");
  const [revisionPackaging, setRevisionPackaging] = useState("");
  const [revisionDelivery, setRevisionDelivery] = useState("");
  const [revisionPayment, setRevisionPayment] = useState("");
  const [revisionAdditional, setRevisionAdditional] = useState("");

  const contentRef = useRef<HTMLDivElement>(null);

  // Lock scroll on main
  useEffect(() => {
    const mainEl = document.querySelector("main");
    if (mainEl) {
      const saved = mainEl.scrollTop;
      mainEl.style.overflow = "hidden";
      return () => { mainEl.style.overflow = ""; mainEl.scrollTop = saved; };
    }
  }, []);

  // ESC key
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && view !== "action") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose, view]);

  // Lock <main> scroll (same pattern as TaskWorkflowModal)
  useEffect(() => {
    const mainEl = document.querySelector("main");
    if (mainEl) {
      const savedScrollTop = mainEl.scrollTop;
      mainEl.style.overflow = "hidden";
      return () => {
        mainEl.style.overflow = "";
        mainEl.scrollTop = savedScrollTop;
      };
    }
  }, []);

  // Scroll to top on view change
  useEffect(() => {
    if (contentRef.current) contentRef.current.scrollTop = 0;
  }, [view]);

  const transition = (to: ModalView) => {
    setTransitioning(true);
    setTimeout(() => { setView(to); setTransitioning(false); }, 200);
  };

  const refresh = async () => {
    try {
      const updated = await fetchInquiries({ lead_id: inquiry.lead_id });
      const found = updated.find((i) => i.id === inquiry.id);
      if (found) setInquiry(found);
    } catch { /* ignore */ }
  };

  const loadRevisions = async () => {
    try {
      const revs = await fetchInquiryRevisions(inquiry.id);
      setRevisions(revs);
    } catch { /* ignore */ }
  };

  // Load revisions when opening revision view
  useEffect(() => {
    if (view === "revision") loadRevisions();
  }, [view]);

  const handleRequestRevision = async () => {
    setSubmitting(true);
    setError("");
    try {
      await requestRevision(inquiry.id, {
        reason: revisionReason,
        customer_feedback: revisionFeedback.trim() || undefined,
        target_price: revisionTargetPrice.trim() || undefined,
        quantity: revisionQuantity.trim() || undefined,
        packaging: revisionPackaging.trim() || undefined,
        delivery_timeline: revisionDelivery.trim() || undefined,
        payment_terms: revisionPayment.trim() || undefined,
        additional_requirements: revisionAdditional.trim() || undefined,
      });
      await refresh();
      queryClient.invalidateQueries({ queryKey: ["inquiries"] });
      transition("success");
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to submit revision request");
    } finally {
      setSubmitting(false);
    }
  };

  // ── Handlers ──
  const handleCommit = async () => {
    setSubmitting(true);
    setError("");
    try {
      await commitInquiry(inquiry.id, {
        commitment_type: commitType,
        expected_response_date: commitType === "WILL_TAKE_TIME" && commitDate ? new Date(commitDate).toISOString() : undefined,
        response: commitType === "ANSWER_NOW" ? commitResponse : undefined,
      });
      await refresh();
      queryClient.invalidateQueries({ queryKey: ["inquiries"] });
      transition("success");
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to commit. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleRespond = async () => {
    if (!respondText.trim()) return;
    setSubmitting(true);
    setError("");
    try {
      await updateInquiry(inquiry.id, { response: respondText });
      await refresh();
      queryClient.invalidateQueries({ queryKey: ["inquiries"] });
      transition("success");
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to respond. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleClose = async () => {
    setSubmitting(true);
    try {
      await updateInquiry(inquiry.id, { status: "CLOSED" });
      setInquiry({ ...inquiry, status: "CLOSED" });
      queryClient.invalidateQueries({ queryKey: ["inquiries"] });
    } catch { /* ignore */ }
    setSubmitting(false);
  };

  // Auto-close on success
  useEffect(() => {
    if (view === "success") {
      const t = setTimeout(onClose, 1500);
      return () => clearTimeout(t);
    }
  }, [view, onClose]);

  const displayStatus = isProc ? inquiry.status.replace(/_/g, " ") : (DISPLAY_STATUS_LABELS[inquiry.status] || inquiry.status);

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/25 backdrop-blur-[2px]" onClick={onClose}>
      <div
        className={cn(
          "bg-white rounded-2xl shadow-[var(--shadow-modal)] w-full mx-4 max-h-[85vh] overflow-hidden flex flex-col",
          "max-w-[520px] sm:max-w-[600px] md:max-w-[700px] lg:max-w-[780px]",
          "transition-opacity duration-200",
          transitioning ? "opacity-0" : "opacity-100"
        )}
        onClick={(e) => e.stopPropagation()}
      >
        {/* ── Header ── */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border/40 shrink-0 rounded-t-2xl">
          <div className="flex items-center gap-3 min-w-0">
            <span className={cn("text-[11px] font-semibold px-2 py-0.5 rounded-full border shrink-0", DISPLAY_STATUS_COLORS[inquiry.status] || "")}>
              {displayStatus}
            </span>
            <h2 className="font-bold text-[15px] truncate">{inquiry.title}</h2>
          </div>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-muted/60 transition-colors">
            <X className="w-4 h-4 text-muted-foreground/60" />
          </button>
        </div>

        {/* ── View: Details ── */}
        {view === "details" && (
          <>
            <div ref={contentRef} className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
              {isProc ? <ProcurementDetails inquiry={inquiry} onAction={() => transition("action")} onClose={onClose} onCloseInquiry={handleClose} submitting={submitting} /> : <SalesDetails inquiry={inquiry} onClose={onClose} />}
            </div>
            <div className="shrink-0 px-6 py-4 border-t border-border/40 rounded-b-2xl">
              <div className="flex items-center gap-3">
                {!isProc && !inquiry.response && inquiry.status !== "CLOSED" && (
                  <Button size="lg" className="flex-1 gap-2 bg-primary hover:bg-primary/90 rounded-[12px]" onClick={() => transition("action")}>
                    <MessageSquare className="w-4 h-4" />Reply
                  </Button>
                )}
                {!isProc && inquiry.response && inquiry.status !== "CLOSED" && inquiry.status !== "REVISION_REQUESTED" && (
                  <Button size="lg" className="flex-1 gap-2 bg-amber-600 hover:bg-amber-700 text-white rounded-[12px]" onClick={() => transition("revision")}>
                    <MessageSquare className="w-4 h-4" />Request Revision
                  </Button>
                )}
                {isProc && !inquiry.response && inquiry.status !== "CLOSED" && (
                  <Button size="lg" className="flex-1 gap-2 bg-primary hover:bg-primary/90 rounded-[12px]" onClick={() => transition("action")}>
                    <CheckCircle2 className="w-4 h-4" />Respond
                  </Button>
                )}
                <Button variant="outline" size="lg" onClick={() => { navigate(`/leads/${inquiry.lead_id}`); onClose(); }} className="gap-2 rounded-[12px]">
                  <ArrowRight className="w-4 h-4" />Open Lead
                </Button>
              </div>
            </div>
          </>
        )}

        {/* ── View: Action ── */}
        {view === "action" && (
          <>
            <div ref={contentRef} className="flex-1 overflow-y-auto px-6 py-5">
              {isProc ? (
                <ProcurementAction inquiry={inquiry} commitType={commitType} setCommitType={setCommitType} commitResponse={commitResponse} setCommitResponse={setCommitResponse} commitDate={commitDate} setCommitDate={setCommitDate} onCommit={handleCommit} submitting={submitting} error={error} onBack={() => transition("details")} />
              ) : (
                <SalesReply respondText={respondText} setRespondText={setRespondText} onRespond={handleRespond} submitting={submitting} error={error} onBack={() => transition("details")} />
              )}
            </div>
          </>
        )}

        {/* ── View: Revision ── */}
        {view === "revision" && (
          <>
            <div ref={contentRef} className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
              <button onClick={() => transition("details")} className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors">
                <ArrowRight className="w-4 h-4 rotate-180" />Back to inquiry
              </button>

              {/* Current response summary */}
              {inquiry.response && (
                <div className="rounded-[14px] bg-emerald-50/50 border border-emerald-200 p-4">
                  <p className="text-[11px] font-semibold text-emerald-600 uppercase tracking-wider mb-1">Current Procurement Response</p>
                  <p className="text-sm leading-relaxed whitespace-pre-wrap">{inquiry.response}</p>
                </div>
              )}

              {/* Negotiation history */}
              {revisions.length > 0 && (
                <div>
                  <p className="text-[11px] font-semibold text-muted-foreground/50 uppercase tracking-wider mb-2">Negotiation History ({revisions.length} rounds)</p>
                  <div className="space-y-2">
                    {revisions.map((rev) => (
                      <div key={rev.id} className={cn("rounded-lg border p-3 text-sm", rev.status === "PENDING" ? "border-amber-200 bg-amber-50/30" : "border-border/40")}>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-semibold text-xs">Revision #{rev.revision_number}</span>
                          <span className={cn("text-[10px] font-semibold px-1.5 py-0.5 rounded-full", rev.status === "PENDING" ? "bg-amber-100 text-amber-700" : "bg-emerald-100 text-emerald-700")}>{REVISION_STATUS_LABELS[rev.status] || rev.status}</span>
                          <span className="text-[11px] text-muted-foreground/50 ml-auto">{rev.created_by} · {new Date(rev.created_at).toLocaleDateString()}</span>
                        </div>
                        <p className="text-[12px] text-muted-foreground/70">{rev.reason.replace(/_/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase())}</p>
                        {rev.customer_feedback && <p className="text-[12px] mt-1">{rev.customer_feedback}</p>}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Revision form */}
              <div className="space-y-4">
                <div>
                  <label className="text-xs font-medium text-muted-foreground/70 mb-1.5 block">What did the customer say? *</label>
                  <textarea value={revisionFeedback} onChange={(e) => setRevisionFeedback(e.target.value)} rows={4}
                    placeholder="Customer feedback, concerns, or requests..." className="w-full rounded-lg border border-input bg-background px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 resize-none" />
                </div>
                <div>
                  <label className="text-xs font-medium text-muted-foreground/70 mb-1.5 block">What do you need from procurement? *</label>
                  <textarea value={revisionAdditional} onChange={(e) => setRevisionAdditional(e.target.value)} rows={4}
                    placeholder="What changes or information does procurement need to provide?" className="w-full rounded-lg border border-input bg-background px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 resize-none" />
                </div>
              </div>

              {error && <p className="text-sm text-destructive">{error}</p>}
            </div>

            {/* Revision Footer */}
            <div className="shrink-0 px-6 py-4 border-t border-border/40 rounded-b-2xl">
              <div className="flex items-center gap-3">
                <Button onClick={handleRequestRevision} disabled={submitting || !revisionFeedback.trim() || !revisionAdditional.trim()} className="flex-1 gap-2 bg-amber-600 hover:bg-amber-700 text-white rounded-[12px]">
                  {submitting ? "Sending..." : <><MessageSquare className="w-4 h-4" />Send Revision Request</>}
                </Button>
                <Button variant="outline" onClick={() => transition("details")} className="rounded-[12px]">Cancel</Button>
              </div>
            </div>
          </>
        )}

        {/* ── View: Success ── */}
        {view === "success" && (
          <div className="flex-1 flex flex-col items-center justify-center py-16 px-6 animate-fade-in">
            <CheckCircle2 className="w-12 h-12 text-emerald-500 mb-4" />
            <p className="text-lg font-semibold text-foreground">Inquiry Updated</p>
            <p className="text-sm text-muted-foreground mt-2">Changes saved successfully</p>
          </div>
        )}
      </div>
    </div>,
    document.body
  );
}

/* ── Sales Details View ── */
function SalesDetails({ inquiry, onClose }: { inquiry: Inquiry; onClose: () => void }) {
  return (
    <div className="space-y-5">
      {inquiry.response ? (
        <div className="rounded-[14px] bg-gradient-to-br from-emerald-50 to-white border border-emerald-200 p-5 space-y-3">
          <div className="flex items-center gap-2 text-emerald-700"><CheckCircle2 className="w-5 h-5" /><span className="font-bold text-base">Procurement Response</span></div>
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{inquiry.response}</p>
          <div className="flex items-center gap-4 text-[12px] text-muted-foreground/60 pt-1 border-t border-emerald-100">
            {inquiry.assigned_to && <span className="flex items-center gap-1"><User className="w-3.5 h-3.5" />{inquiry.assigned_to}</span>}
            {inquiry.responded_at && <span className="flex items-center gap-1"><Calendar className="w-3.5 h-3.5" />{new Date(inquiry.responded_at).toLocaleDateString()}</span>}
          </div>
        </div>
      ) : (
        <div className={cn("rounded-[14px] border p-4 flex items-start gap-3", inquiry.status === "OVERDUE" ? "bg-red-50 border-red-200" : "bg-amber-50 border-amber-200")}>
          <div className={cn("p-2 rounded-full shrink-0", inquiry.status === "OVERDUE" ? "bg-red-100" : "bg-amber-100")}>
            {inquiry.status === "OVERDUE" ? <AlertTriangle className="w-5 h-5 text-red-600" /> : inquiry.status === "EOD_COMMITTED" ? <Clock className="w-5 h-5 text-orange-600" /> : <Timer className="w-5 h-5 text-amber-600" />}
          </div>
          <div>
            <p className={cn("font-semibold text-sm", inquiry.status === "OVERDUE" ? "text-red-800" : "text-amber-800")}>
              {inquiry.status === "EOD_COMMITTED" ? "Procurement will respond by end of day" : inquiry.status === "OVERDUE" ? "Response is overdue" : inquiry.status === "PENDING_RESPONSE" ? (inquiry.expected_response_date ? `Procurement expects to respond by ${new Date(inquiry.expected_response_date).toLocaleDateString()}` : "Procurement is reviewing this inquiry") : "Awaiting procurement review"}
            </p>
            <p className="text-[12px] text-muted-foreground/70 mt-1">{inquiry.assigned_to ? `Contact: ${inquiry.assigned_to}` : "Assigning to procurement..."}</p>
          </div>
        </div>
      )}

      <SalesTimeline inquiry={inquiry} />

      <div className="grid grid-cols-2 gap-4 text-sm">
        <div><p className="text-[11px] font-semibold text-muted-foreground/50 uppercase tracking-wider">Created By</p><p className="font-medium">{inquiry.created_by}</p></div>
        <div><p className="text-[11px] font-semibold text-muted-foreground/50 uppercase tracking-wider">Procurement Contact</p><p className="font-medium">{inquiry.assigned_to}</p></div>
        <div><p className="text-[11px] font-semibold text-muted-foreground/50 uppercase tracking-wider">Created</p><p className="font-medium">{new Date(inquiry.created_at).toLocaleDateString()}</p></div>
        <div><p className="text-[11px] font-semibold text-muted-foreground/50 uppercase tracking-wider">Last Updated</p><p className="font-medium">{timeAgo(inquiry.updated_at)}</p></div>
      </div>

      <div>
        <p className="text-[11px] font-semibold text-muted-foreground/50 uppercase tracking-wider mb-1">Lead</p>
        <div className="flex items-center gap-1.5 text-sm text-primary"><Building2 className="w-3.5 h-3.5" />{inquiry.company_name || inquiry.lead_id} <span className="text-muted-foreground/50 font-mono">#{inquiry.lead_id}</span></div>
      </div>

      {inquiry.description && (
        <div><p className="text-[11px] font-semibold text-muted-foreground/50 uppercase tracking-wider mb-1.5">Original Inquiry</p><div className="bg-muted/30 rounded-lg p-3.5 text-sm leading-relaxed whitespace-pre-wrap">{inquiry.description}</div></div>
      )}
    </div>
  );
}

function SalesTimeline({ inquiry }: { inquiry: Inquiry }) {
  return (
    <div>
      <p className="text-[11px] font-semibold text-muted-foreground/50 uppercase tracking-wider mb-3">Timeline</p>
      <div className="pl-1">
        <TimelineStep done label="Inquiry Created" sub={new Date(inquiry.created_at).toLocaleString()} />
        <TimelineStep done={!!inquiry.assigned_to} label="Assigned to Procurement" sub={inquiry.assigned_to || undefined} />
        <TimelineStep done={inquiry.status === "EOD_COMMITTED" || inquiry.status === "PENDING_RESPONSE" || inquiry.status === "RESPONDED" || inquiry.status === "OVERDUE" || inquiry.status === "CLOSED"} label="Response Commitment" sub={inquiry.commitment_type ? (COMMITMENT_LABELS[inquiry.commitment_type] || inquiry.commitment_type) : undefined} />
        <TimelineStep isLast done={!!inquiry.response} label="Response Submitted" sub={inquiry.responded_at ? new Date(inquiry.responded_at).toLocaleString() : undefined} />
      </div>
    </div>
  );
}

/* ── Procurement Details View ── */
function ProcurementDetails({ inquiry, onAction, onCloseInquiry, submitting }: { inquiry: Inquiry; onAction: () => void; onCloseInquiry: () => void; onClose: () => void; submitting: boolean }) {
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-4 text-sm">
        <div><p className="text-[11px] font-semibold text-muted-foreground/50 uppercase tracking-wider">Requested By</p><p className="font-medium">{inquiry.created_by}</p></div>
        <div><p className="text-[11px] font-semibold text-muted-foreground/50 uppercase tracking-wider">Assigned To</p><p className="font-medium">{inquiry.assigned_to}</p></div>
        <div><p className="text-[11px] font-semibold text-muted-foreground/50 uppercase tracking-wider">Type</p><p className="font-medium">{inquiry.type}</p></div>
        <div><p className="text-[11px] font-semibold text-muted-foreground/50 uppercase tracking-wider">Priority</p>
          <span className={cn("text-[10px] font-semibold px-1.5 py-0.5 rounded", PRIORITY_COLORS[inquiry.priority] || "")}>{inquiry.priority}</span>
        </div>
        <div><p className="text-[11px] font-semibold text-muted-foreground/50 uppercase tracking-wider">Created</p><p className="font-medium">{new Date(inquiry.created_at).toLocaleString()}</p></div>
        <div><p className="text-[11px] font-semibold text-muted-foreground/50 uppercase tracking-wider">Age</p><p className="font-medium">{timeAgo(inquiry.created_at)}</p></div>
      </div>

      <div>
        <p className="text-[11px] font-semibold text-muted-foreground/50 uppercase tracking-wider mb-1">Lead</p>
        <div className="flex items-center gap-1.5 text-sm text-primary"><Building2 className="w-3.5 h-3.5" />{inquiry.company_name || inquiry.lead_id} <span className="text-muted-foreground/50 font-mono">#{inquiry.lead_id}</span></div>
      </div>

      {inquiry.description && (
        <div><p className="text-[11px] font-semibold text-muted-foreground/50 uppercase tracking-wider mb-1.5">Inquiry Details</p><div className="bg-muted/30 rounded-lg p-3.5 text-sm leading-relaxed whitespace-pre-wrap">{inquiry.description}</div></div>
      )}

      {inquiry.response ? (
        <div>
          <p className="text-[11px] font-semibold text-emerald-600 uppercase tracking-wider mb-1.5">Your Response · {inquiry.responded_at ? new Date(inquiry.responded_at).toLocaleDateString() : ""}</p>
          <div className="bg-emerald-50/50 rounded-lg p-3.5 text-sm leading-relaxed whitespace-pre-wrap">{inquiry.response}</div>
          <div className="flex items-center gap-2 mt-3">
            <Button size="sm" variant="outline" className="gap-1.5" onClick={onCloseInquiry} disabled={submitting}>
              <CheckCircle2 className="w-3.5 h-3.5" />Close Inquiry
            </Button>
          </div>
        </div>
      ) : (
        <div className="rounded-[14px] border border-primary/20 bg-primary/[0.02] p-4">
          <p className="text-[11px] font-semibold text-primary uppercase tracking-wider mb-1">No response yet</p>
          <p className="text-sm text-muted-foreground mb-3">Click Respond to provide your answer.</p>
        </div>
      )}

      {inquiry.commitment_type && inquiry.status !== "RESPONDED" && inquiry.status !== "CLOSED" && (
        <div className="rounded-lg bg-muted/30 p-3.5 space-y-1.5 text-sm">
          <p className="text-[11px] font-semibold text-muted-foreground/50 uppercase tracking-wider">Current Commitment</p>
          <p><span className="text-muted-foreground/60">Type:</span> {COMMITMENT_LABELS[inquiry.commitment_type] || inquiry.commitment_type}</p>
          {inquiry.expected_response_date && <p><span className="text-muted-foreground/60">Due:</span> {new Date(inquiry.expected_response_date).toLocaleDateString()}</p>}
          {inquiry.committed_at && <p><span className="text-muted-foreground/60">Committed:</span> {new Date(inquiry.committed_at).toLocaleString()}</p>}
        </div>
      )}
    </div>
  );
}

/* ── Procurement Action View ── */
function ProcurementAction({ inquiry, commitType, setCommitType, commitResponse, setCommitResponse, commitDate, setCommitDate, onCommit, submitting, error, onBack }: {
  inquiry: Inquiry; commitType: string; setCommitType: (v: string) => void;
  commitResponse: string; setCommitResponse: (v: string) => void;
  commitDate: string; setCommitDate: (v: string) => void;
  onCommit: () => void; submitting: boolean; error: string; onBack: () => void;
}) {
  return (
    <div className="space-y-5">
      <button onClick={onBack} className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors">
        <ArrowRight className="w-4 h-4 rotate-180" />Back to inquiry
      </button>

      <div>
        <p className="text-[11px] font-semibold text-muted-foreground/50 uppercase tracking-wider mb-3">How will you respond?</p>
        <div className="space-y-2.5">
          <button onClick={() => setCommitType("ANSWER_NOW")} className={cn("w-full text-left flex items-center gap-4 p-4 rounded-xl border-2 transition-all", commitType === "ANSWER_NOW" ? "border-emerald-400 bg-emerald-50/50" : "border-emerald-200 hover:border-emerald-300")}>
            <div className={cn("w-10 h-10 rounded-lg flex items-center justify-center", commitType === "ANSWER_NOW" ? "bg-emerald-200" : "bg-emerald-100")}><CheckCircle2 className="w-5 h-5 text-emerald-600" /></div>
            <div className="flex-1"><p className="font-semibold text-sm">Answer Now</p><p className="text-[12px] text-muted-foreground/60">Respond immediately</p></div>
          </button>
          <button onClick={() => setCommitType("BY_EOD")} className={cn("w-full text-left flex items-center gap-4 p-4 rounded-xl border-2 transition-all", commitType === "BY_EOD" ? "border-orange-400 bg-orange-50/50" : "border-orange-200 hover:border-orange-300")}>
            <div className={cn("w-10 h-10 rounded-lg flex items-center justify-center", commitType === "BY_EOD" ? "bg-orange-200" : "bg-orange-100")}><Clock className="w-5 h-5 text-orange-600" /></div>
            <div className="flex-1"><p className="font-semibold text-sm">By End Of Day</p><p className="text-[12px] text-muted-foreground/60">Respond before EOD</p></div>
          </button>
          <button onClick={() => setCommitType("WILL_TAKE_TIME")} className={cn("w-full text-left flex items-center gap-4 p-4 rounded-xl border-2 transition-all", commitType === "WILL_TAKE_TIME" ? "border-blue-400 bg-blue-50/50" : "border-blue-200 hover:border-blue-300")}>
            <div className={cn("w-10 h-10 rounded-lg flex items-center justify-center", commitType === "WILL_TAKE_TIME" ? "bg-blue-200" : "bg-blue-100")}><Calendar className="w-5 h-5 text-blue-600" /></div>
            <div className="flex-1"><p className="font-semibold text-sm">Will Take Time</p><p className="text-[12px] text-muted-foreground/60">Set a future response date</p></div>
          </button>
        </div>
      </div>

      {commitType === "ANSWER_NOW" && (
        <div className="space-y-3">
          <label className="text-xs font-medium text-muted-foreground/70 block">Your Response *</label>
          <textarea value={commitResponse} onChange={(e) => setCommitResponse(e.target.value)} placeholder="Pricing, MOQ, lead time, or any relevant information..." rows={5}
            className="w-full rounded-lg border border-input bg-background px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 resize-none" />
        </div>
      )}
      {commitType === "BY_EOD" && (
        <div className="bg-orange-50 rounded-lg p-4 text-[13px] text-orange-800 space-y-1">
          <p className="font-semibold">One-click commitment</p>
          <p className="text-orange-600/70">Sales will see: <strong>Expected Today</strong></p>
        </div>
      )}
      {commitType === "WILL_TAKE_TIME" && (
        <div>
          <label className="text-xs font-medium text-muted-foreground/70 mb-1.5 block">Expected Response Date *</label>
          <input type="date" value={commitDate} onChange={(e) => setCommitDate(e.target.value)}
            className="w-full rounded-lg border border-input bg-background px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20" />
        </div>
      )}

      {error && <p className="text-sm text-destructive">{error}</p>}

      {commitType && (
        <div className="flex items-center gap-3 pt-2">
          <Button onClick={onCommit} disabled={submitting || (commitType === "ANSWER_NOW" && !commitResponse.trim()) || (commitType === "WILL_TAKE_TIME" && !commitDate)} className="px-6 rounded-[12px]">
            {submitting ? "Submitting..." : commitType === "ANSWER_NOW" ? "Submit Response" : commitType === "BY_EOD" ? "Confirm EOD Commitment" : "Set Date"}
          </Button>
          <Button variant="outline" onClick={onBack} className="rounded-[12px]">Cancel</Button>
        </div>
      )}
    </div>
  );
}

/* ── Sales Reply View ── */
function SalesReply({ respondText, setRespondText, onRespond, submitting, error, onBack }: {
  respondText: string; setRespondText: (v: string) => void; onRespond: () => void;
  submitting: boolean; error: string; onBack: () => void;
}) {
  return (
    <div className="space-y-5">
      <button onClick={onBack} className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors">
        <ArrowRight className="w-4 h-4 rotate-180" />Back to inquiry
      </button>
      <div className="space-y-3">
        <label className="text-xs font-medium text-muted-foreground/70 block">Your Reply *</label>
        <textarea value={respondText} onChange={(e) => setRespondText(e.target.value)} placeholder="Type your reply to this inquiry..." rows={5}
          className="w-full rounded-lg border border-input bg-background px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 resize-none" />
      </div>
      {error && <p className="text-sm text-destructive">{error}</p>}
      <div className="flex items-center gap-3 pt-2">
        <Button onClick={onRespond} disabled={submitting || !respondText.trim()} className="px-6 rounded-[12px]">
          {submitting ? "Sending..." : "Send Reply"}
        </Button>
        <Button variant="outline" onClick={onBack} className="rounded-[12px]">Cancel</Button>
      </div>
    </div>
  );
}

/* ── Shared components ── */
const PRIORITY_COLORS: Record<string, string> = {
  LOW: "bg-slate-50 text-slate-500", MEDIUM: "bg-blue-50 text-blue-700",
  HIGH: "bg-orange-50 text-orange-700", URGENT: "bg-red-50 text-red-700",
};

function TimelineStep({ done, label, sub, isLast }: { done: boolean; label: string; sub?: string; isLast?: boolean }) {
  return (
    <div className="flex gap-3">
      <div className="flex flex-col items-center">
        <div className={cn("w-3 h-3 rounded-full border-2 shrink-0 mt-0.5", done ? "bg-emerald-500 border-emerald-500" : "bg-white border-muted-foreground/30")} />
        {!isLast && <div className={cn("w-px flex-1 my-0.5", done ? "bg-emerald-200" : "bg-muted-foreground/15")} />}
      </div>
      <div className={cn("pb-4 text-sm", done ? "text-foreground/80" : "text-muted-foreground/50")}>
        <p className="font-medium">{label}</p>
        {sub && <p className="text-[12px] text-muted-foreground/60">{sub}</p>}
      </div>
    </div>
  );
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}
