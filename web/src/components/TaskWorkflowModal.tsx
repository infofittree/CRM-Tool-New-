import { useState, useEffect, useCallback, useRef } from "react";
import { createPortal } from "react-dom";
import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { cn, formatDate } from "@/lib/utils";
import api, { type Task, type ActivityWizardResponse } from "@/lib/api";
import ActivityWizard from "@/components/ActivityWizard";
import { getTaskTypeConfig, getTaskOrigin } from "@/lib/taskTypes";
import {
  X, CheckCircle2, Phone, MessageSquare, ArrowRight, ArrowLeft, AlertTriangle,
  User, Building2, Globe, Briefcase, Star,
} from "lucide-react";

type ModalView = "details" | "wizard" | "success" | "lead";

interface TaskWorkflowModalProps {
  task: Task;
  onClose: () => void;
}

export default function TaskWorkflowModal({ task, onClose }: TaskWorkflowModalProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [view, setView] = useState<ModalView>("details");
  const [wizardFollowupId, setWizardFollowupId] = useState<number | null>(null);
  const [creatingFollowup, setCreatingFollowup] = useState(false);
  const [taskError, setTaskError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [transitioning, setTransitioning] = useState(false);
  const detailsScrollRef = useRef<HTMLDivElement>(null);
  const wizardKey = useRef(0);

  // ESC key support
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (view === "wizard") return; // Let wizard handle its own ESC
        if (view === "lead") { setView("details"); return; }
        onClose();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose, view]);

  // Lock the actual scroll container (<main>) and preserve its scroll position
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

  const handleCompleteTask = useCallback(async () => {
    if (creatingFollowup) return;
    setTaskError("");
    if (task.followup_id) {
      setTransitioning(true);
      setTimeout(() => {
        setWizardFollowupId(task.followup_id);
        setView("wizard");
        wizardKey.current += 1;
        setTransitioning(false);
      }, 200);
      return;
    }
    setCreatingFollowup(true);
    try {
      const res = await api.post("/followups", {
        lead_id: task.lead_id,
        followup_date: new Date().toISOString().split("T")[0],
        next_followup: new Date(Date.now() + 2 * 86400000).toISOString().split("T")[0],
        discussion: task.discussion || "Follow-Up",
        next_action: task.next_action || "Call Again",
      });
      const newId = res.data.followup_id;
      setTransitioning(true);
      setTimeout(() => {
        setWizardFollowupId(newId);
        setView("wizard");
        wizardKey.current += 1;
        setTransitioning(false);
      }, 200);
    } catch (err: any) {
      setTaskError(err.response?.data?.detail || "Failed to prepare task. Please try again.");
    } finally {
      setCreatingFollowup(false);
    }
  }, [task, creatingFollowup]);

  const onWizardComplete = useCallback((result: ActivityWizardResponse) => {
    const msg = result.next_followup_id
      ? `Activity completed. ${result.next_action_type} created — due ${new Date(result.next_followup_date!).toLocaleDateString()}.`
      : "Activity completed. No follow-up scheduled.";
    setTransitioning(true);
    setWizardFollowupId(null);
    setTimeout(() => {
      setSuccessMessage(msg);
      setView("success");
      setTransitioning(false);
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    }, 200);
  }, [queryClient]);

  // Auto-close after success
  useEffect(() => {
    if (view === "success") {
      const timer = setTimeout(onClose, 1500);
      return () => clearTimeout(timer);
    }
  }, [view, onClose]);

  const typeConfig = getTaskTypeConfig(task.discussion, task.next_action);
  const isCompleted = task.bucket === "completed";

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
        {/* ── View: Details ── */}
        {view === "details" && (
          <>
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-border/40 shrink-0">
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-2 h-2 rounded-full bg-primary shrink-0" />
                <h2 className="font-bold text-[15px] truncate">{task.company_name}</h2>
                <span className="text-[11px] text-muted-foreground/50 font-medium">{task.standard_status}</span>
              </div>
              <button onClick={onClose} className="p-2 rounded-lg hover:bg-muted/60 transition-colors">
                <X className="w-4 h-4 text-muted-foreground/60" />
              </button>
            </div>

            {/* Content */}
            <div ref={detailsScrollRef} className="flex-1 overflow-y-auto px-6 py-5 space-y-4">
              {/* Task type card */}
              {!isCompleted && task.discussion && (
                <div className="rounded-[14px] bg-gradient-to-br from-primary/[0.04] to-primary/[0.02] border border-primary/20 p-4 space-y-2">
                  <span className={cn("text-xs font-bold px-2 py-0.5 rounded border inline-block", typeConfig.badgeColor)}>
                    {typeConfig.badge}
                  </span>
                  <p className="text-base font-bold text-foreground">{typeConfig.label}</p>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {getTaskOrigin(task.discussion, task.next_action, task.last_contact_date)}
                  </p>
                </div>
              )}

              {/* Info grid */}
              <div className="rounded-[14px] bg-muted/20 p-4">
                <p className="text-[11px] font-semibold text-muted-foreground/50 uppercase tracking-wider mb-3">Task Information</p>
                <div className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
                  <InfoRow label="Company" value={task.company_name} />
                  <InfoRow label="Status" value={task.standard_status} />
                  <InfoRow
                    label="Due"
                    value={`${task.due_label}${task.due_date ? ` · ${formatDate(task.due_date)}` : ""}`}
                    valueClass={task.days_to < 0 ? "text-red-600" : task.days_to === 0 ? "text-amber-600" : ""}
                  />
                  <InfoRow label="Assigned To" value={task.assigned_to || "—"} />
                  <InfoRow label="Country" value={task.country || "—"} />
                  <InfoRow label="Category" value={task.lead_category || "—"} />
                  {task.phone && (
                    <div className="flex items-center gap-2">
                      <Phone className="w-3.5 h-3.5 text-muted-foreground/50 shrink-0" />
                      <span className="font-medium">{task.phone}</span>
                    </div>
                  )}
                  {task.email && (
                    <div className="flex items-center gap-2">
                      <MessageSquare className="w-3.5 h-3.5 text-muted-foreground/50 shrink-0" />
                      <span className="font-medium truncate">{task.email}</span>
                    </div>
                  )}
                </div>
                {task.next_action_plan && !isCompleted && (
                  <div className="mt-3 pt-3 border-t border-border/40">
                    <p className="text-[11px] text-muted-foreground/60 mb-0.5">Action Plan</p>
                    <p className="text-sm font-medium text-primary">{task.next_action_plan}</p>
                  </div>
                )}
              </div>

              {/* Workflow preview */}
              {!isCompleted && task.discussion && (
                <div className="rounded-[14px] bg-blue-50/50 border border-blue-100 p-4 space-y-2">
                  <p className="text-[11px] font-semibold text-blue-700 uppercase tracking-wider">What happens next?</p>
                  <ul className="text-xs text-blue-700 space-y-1">
                    <li className="flex items-center gap-1.5"><ArrowRight className="w-3 h-3 shrink-0" />Guided wizard records your activity</li>
                    <li className="flex items-center gap-1.5"><ArrowRight className="w-3 h-3 shrink-0" />Next follow-up is auto-created</li>
                    <li className="flex items-center gap-1.5"><ArrowRight className="w-3 h-3 shrink-0" />Dashboard and analytics update</li>
                  </ul>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="shrink-0 px-6 py-4 border-t border-border/40">
              {taskError && (
                <div className="flex items-center gap-2 p-3 rounded-xl bg-destructive/8 border border-destructive/15 text-destructive text-sm mb-3">
                  <AlertTriangle className="w-4 h-4 shrink-0" />
                  <span>{taskError}</span>
                </div>
              )}
              <div className="flex items-center gap-3">
                {!isCompleted ? (
                  <>
                    <Button
                      size="lg"
                      className="flex-1 gap-2 bg-primary hover:bg-primary/90 rounded-[12px]"
                      onClick={handleCompleteTask}
                      disabled={creatingFollowup}
                    >
                      {creatingFollowup ? (
                        <><div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full" /> Preparing...</>
                      ) : (
                        <><CheckCircle2 className="w-4 h-4" />{typeConfig.ctaLabel}</>
                      )}
                    </Button>
                    <Button
                      variant="outline"
                      size="lg"
                      onClick={() => setView("lead")}
                      className="gap-2 rounded-[12px]"
                    >
                      <ArrowRight className="w-4 h-4" />Open Lead
                    </Button>
                  </>
                ) : (
                  <Button variant="outline" size="lg" className="flex-1 rounded-[12px]" onClick={onClose}>
                    Close
                  </Button>
                )}
              </div>
            </div>
          </>
        )}


        {/* ── View: Lead Brief ── */}
        {view === "lead" && (
          <>
            {/* Header */}
            <div className="flex items-center gap-3 px-6 py-4 border-b border-border/40 shrink-0">
              <button onClick={() => setView("details")} className="p-2 rounded-lg hover:bg-muted/60 transition-colors">
                <ArrowLeft className="w-4 h-4" />
              </button>
              <div className="flex items-center gap-2 min-w-0">
                <User className="w-4 h-4 text-primary shrink-0" />
                <h2 className="font-bold text-[15px] truncate">{task.company_name || "Lead Brief"}</h2>
                <span className="text-[11px] text-muted-foreground/50 font-medium">Lead {task.lead_id}</span>
              </div>
              <button onClick={onClose} className="ml-auto p-2 rounded-lg hover:bg-muted/60 transition-colors">
                <X className="w-4 h-4 text-muted-foreground/60" />
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto px-6 py-5 space-y-4">
              {/* Status and Score */}
              <div className="flex items-center gap-3 flex-wrap">
                <span className={cn(
                  "text-xs font-bold px-2.5 py-1 rounded-full border",
                  task.status === "Order Closed" ? "bg-green-50 text-green-700 border-green-200" :
                  task.status === "Lost" ? "bg-red-50 text-red-700 border-red-200" :
                  task.status === "Negotiation" ? "bg-amber-50 text-amber-700 border-amber-200" :
                  "bg-blue-50 text-blue-700 border-blue-200"
                )}>
                  {task.standard_status || task.status}
                </span>
                <span className={cn(
                  "text-xs font-bold px-2.5 py-1 rounded-full border",
                  task.band === "HOT" ? "bg-red-50 text-red-700 border-red-200" :
                  task.band === "WARM" ? "bg-amber-50 text-amber-700 border-amber-200" :
                  "bg-slate-50 text-slate-700 border-slate-200"
                )}>
                  <Star className="w-3 h-3 inline mr-1" />{task.band} · Score {task.score}
                </span>
                {task.lead_category && (
                  <span className="text-xs px-2.5 py-1 rounded-full bg-muted/40 text-muted-foreground border border-border/40">
                    {task.lead_category}
                  </span>
                )}
              </div>

              {/* Contact card */}
              <div className="rounded-[14px] bg-muted/20 p-4">
                <p className="text-[11px] font-semibold text-muted-foreground/50 uppercase tracking-wider mb-3">Contact Information</p>
                <div className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
                  <InfoRow label="Contact Person" value={task.contact_person || "—"} />
                  <InfoRow label="Company" value={task.company_name || "—"} />
                  {task.phone && (
                    <div className="flex items-center gap-2">
                      <Phone className="w-3.5 h-3.5 text-muted-foreground/50 shrink-0" />
                      <span className="font-medium">{task.phone}</span>
                    </div>
                  )}
                  {task.email && (
                    <div className="flex items-center gap-2">
                      <MessageSquare className="w-3.5 h-3.5 text-muted-foreground/50 shrink-0" />
                      <span className="font-medium truncate">{task.email}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Lead Details */}
              <div className="rounded-[14px] bg-muted/20 p-4">
                <p className="text-[11px] font-semibold text-muted-foreground/50 uppercase tracking-wider mb-3">Lead Details</p>
                <div className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
                  <div className="flex items-center gap-2">
                    <Globe className="w-3.5 h-3.5 text-muted-foreground/50 shrink-0" />
                    <span className="font-medium">{task.country || "No country"}</span>
                  </div>
                  <InfoRow label="Assigned To" value={task.assigned_to || "—"} />
                  <InfoRow label="Priority" value={task.band || "—"} />
                  <InfoRow label="Engagement" value={task.buyer_engagement_frequency || "—"} />
                </div>
              </div>

              {/* Requirements */}
              <div className="rounded-[14px] bg-muted/20 p-4">
                <p className="text-[11px] font-semibold text-muted-foreground/50 uppercase tracking-wider mb-3">Requirements</p>
                <div className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
                  <InfoRow label="Product Interest" value={task.product_interest || "—"} />
                  <InfoRow label="Interest Level" value={task.interest_level || "—"} />
                  <InfoRow label="Deal Value" value={task.potential_deal_value || "—"} />
                  <InfoRow label="Last Contact" value={task.last_contact_date ? formatDate(task.last_contact_date) : "—"} />
                </div>
                {task.customer_requirements && (
                  <div className="mt-3 pt-3 border-t border-border/40">
                    <p className="text-[11px] text-muted-foreground/60 mb-0.5">Customer Requirements</p>
                    <p className="text-sm font-medium text-foreground">{task.customer_requirements}</p>
                  </div>
                )}
                {task.next_action_plan && (
                  <div className="mt-3 pt-3 border-t border-border/40">
                    <p className="text-[11px] text-muted-foreground/60 mb-0.5">Action Plan</p>
                    <p className="text-sm font-medium text-primary">{task.next_action_plan}</p>
                  </div>
                )}
              </div>
            </div>

            {/* Footer */}
            <div className="shrink-0 px-6 py-4 border-t border-border/40">
              <div className="flex items-center gap-3">
                <Button
                  variant="outline"
                  size="lg"
                  className="gap-2 rounded-[12px]"
                  onClick={() => setView("details")}
                >
                  <ArrowLeft className="w-4 h-4" /> Back to Task
                </Button>
                <Button
                  variant="outline"
                  size="lg"
                  className="gap-2 flex-1 rounded-[12px]"
                  onClick={() => { navigate(`/leads/${task.lead_id}`); onClose(); }}
                >
                  <Briefcase className="w-4 h-4" /> Open Full Lead
                </Button>
              </div>
            </div>
          </>
        )}

        {/* ── View: Wizard (embedded ActivityWizard) ── */}
        {view === "wizard" && wizardFollowupId && (
          <ActivityWizard
            key={wizardKey.current}
            followupId={wizardFollowupId}
            leadStatus={task.status}
            assignedTo={task.assigned_to || ""}
            companyName={task.company_name}
            taskType={task.next_action || ""}
            taskDiscussion={task.discussion || ""}
            onClose={() => { setWizardFollowupId(null); setView("details"); }}
            onComplete={onWizardComplete}
            embedded
          />
        )}

        {/* ── View: Success ── */}
        {view === "success" && (
          <div className="flex flex-col items-center justify-center py-16 px-6 animate-fade-in">
            <CheckCircle2 className="w-12 h-12 text-emerald-500 mb-4" />
            <p className="text-lg font-semibold text-foreground">Activity Recorded</p>
            <p className="text-sm text-muted-foreground mt-2 text-center max-w-md">{successMessage}</p>
          </div>
        )}
      </div>
    </div>,
    document.body
  );
}

function InfoRow({ label, value, valueClass }: { label: string; value: string; valueClass?: string }) {
  return (
    <div>
      <p className="text-[11px] text-muted-foreground/60">{label}</p>
      <p className={cn("font-medium", valueClass)}>{value}</p>
    </div>
  );
}
