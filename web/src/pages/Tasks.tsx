import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTaskQueue } from "@/hooks/useDashboard";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn, formatDate } from "@/lib/utils";
import { useAuth } from "@/lib/auth";
import api, { completeFollowup, type Task, type ActivityWizardResponse } from "@/lib/api";
import ActivityWizard from "@/components/ActivityWizard";
import { getTaskTypeConfig, getTaskOrigin, getWorkflowDebug } from "@/lib/taskTypes";
import {
  ListTodo, Clock, AlertTriangle, Calendar, Phone, X, CheckCircle2, User, ArrowRight, MessageSquare, ChevronDown, ChevronRight, Bug, Filter, Building2,
} from "lucide-react";

const LEAD_STATUSES = ["Prospect", "Requirement Qualified", "Technical Discussion", "Quotation Sent", "Sample Sent", "Negotiation", "Trial Order", "Order Closed", "Nurturing", "Lost"];
const INTEREST_LEVELS = ["LOW", "MEDIUM", "HIGH", "VERY_HIGH"];
const NEXT_ACTION_OPTIONS = ["No Follow-Up Required", "Call Again", "Send Quotation", "Await Customer Response", "Schedule Meeting", "Send Samples", "Request Procurement Information", "Other"];
const NEXT_ACTION_TEMPLATES: Record<string, string> = { "Call Again": "Follow-Up Call", "Send Quotation": "Send Quotation", "Await Customer Response": "Check Customer Response", "Schedule Meeting": "Conduct Meeting", "Send Samples": "Follow Up On Samples", "Request Procurement Information": "Review Procurement Response", "Other": "Follow-Up" };
const STATUS_SUGGESTED_ACTIONS: Record<string, string> = { "Prospect": "Call Again", "Requirement Qualified": "Send Quotation", "Technical Discussion": "Call Again", "Quotation Sent": "Await Customer Response", "Sample Sent": "Call Again", "Negotiation": "Call Again", "Trial Order": "Call Again", "Nurturing": "Call Again" };
type TabKey = "all" | "calls" | "responses" | "procurement" | "meetings" | "quotations";
const QUICK_FILTERS: { key: TabKey; label: string }[] = [
  { key: "all", label: "All Tasks" }, { key: "calls", label: "Call Back" }, { key: "responses", label: "Responses" },
  { key: "procurement", label: "Procurement" }, { key: "meetings", label: "Meetings" }, { key: "quotations", label: "Quotations" },
];

export default function Tasks() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [selectedTab, setSelectedTab] = useState<TabKey>("all");
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [showActivityWizard, setShowActivityWizard] = useState(false);
  const [wizardFollowupId, setWizardFollowupId] = useState<number | null>(null);
  const [wizardSuccess, setWizardSuccess] = useState("");
  const [creatingFollowup, setCreatingFollowup] = useState(false);
  const [taskError, setTaskError] = useState("");
  const [expandedSection, setExpandedSection] = useState<string | null>(null);
  const [leadStatus, setLeadStatus] = useState("");
  const [interestLevel, setInterestLevel] = useState("");
  const [dealValue, setDealValue] = useState("");
  const [discussionSummary, setDiscussionSummary] = useState("");
  const [customerRequirements, setCustomerRequirements] = useState("");
  const [nextActionType, setNextActionType] = useState("");
  const [nextFollowupDate, setNextFollowupDate] = useState("");
  const [showAbandonWarning, setShowAbandonWarning] = useState(false);

  const { data, isLoading } = useTaskQueue();
  const { data: leadsData } = useQuery({
    queryKey: ["tasks", "my-leads", user?.full_name],
    queryFn: () => api.get("/leads", { params: { assigned_to: user?.full_name, page_size: 1 } }).then((r) => r.data.total || 0),
    enabled: !!user, staleTime: 60000, refetchOnWindowFocus: false,
  });

  useEffect(() => {
    if (selectedTask) document.body.style.overflow = "hidden";
    else document.body.style.overflow = "";
    return () => { document.body.style.overflow = ""; };
  }, [selectedTask]);

  const drawerContentRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (selectedTask && drawerContentRef.current) drawerContentRef.current.scrollTop = 0;
  }, [selectedTask]);

  const summaryCards = [
    { label: "Due Today", value: data?.today_capped?.length ?? 0, icon: Clock, color: "text-amber-600", bg: "bg-amber-50/80", border: "border-amber-100" },
    { label: "Overdue", value: data?.overdue?.length ?? 0, icon: AlertTriangle, color: "text-red-500", bg: "bg-red-50/80", border: "border-red-100" },
    { label: "Upcoming", value: data?.upcoming?.length ?? 0, icon: Calendar, color: "text-teal-600", bg: "bg-teal-50/60", border: "border-teal-100" },
    { label: "My Leads", value: leadsData ?? 0, icon: Building2, color: "text-emerald-600", bg: "bg-emerald-50/60", border: "border-emerald-100" },
  ];

  const filterTasksByType = (tasks: any[]) => {
    if (selectedTab === "all") return tasks;
    return tasks.filter((t: any) => {
      const cfg = getTaskTypeConfig(t.discussion, t.next_action);
      const label = cfg.badge.toLowerCase();
      if (selectedTab === "calls") return label.includes("call");
      if (selectedTab === "responses") return label.includes("response");
      if (selectedTab === "procurement") return label.includes("procurement");
      if (selectedTab === "meetings") return label.includes("meeting");
      if (selectedTab === "quotations") return label.includes("quotation");
      return true;
    });
  };

  const allPending = filterTasksByType([...(data?.overdue ?? []), ...(data?.today_capped ?? []), ...(data?.upcoming ?? [])]);
  const allDone = filterTasksByType(data?.completed ?? []);

  const getDayGroup = (task: any): string => {
    const d = task.days_to;
    if (d < 0) return "overdue";
    if (d === 0) return "today";
    if (d === 1) return "tomorrow";
    if (d <= 7) return "this-week";
    return "later";
  };

  const DAY_GROUPS = [
    { key: "overdue", label: "Overdue", color: "text-destructive", icon: AlertTriangle },
    { key: "today", label: "Today", color: "text-amber-600", icon: Clock },
    { key: "tomorrow", label: "Tomorrow", color: "text-blue-600", icon: Calendar },
    { key: "this-week", label: "This Week", color: "text-primary", icon: Calendar },
    { key: "later", label: "Later", color: "text-muted-foreground", icon: Calendar },
  ];

  const groupedPending = DAY_GROUPS.map((g) => ({ ...g, tasks: allPending.filter((t) => getDayGroup(t) === g.key) })).filter((g) => g.tasks.length > 0);
  const groupedDone = allDone.length > 0 ? [{ key: "done", label: "Completed", tasks: allDone }] : [];

  const handleOpenTask = (task: Task) => {
    setSelectedTask(task);
    setExpandedSection(null);
    setLeadStatus(task.status || "");
    setInterestLevel(task.interest_level || "");
    setDealValue(task.potential_deal_value || "");
    setDiscussionSummary("");
    setCustomerRequirements(task.customer_requirements || "");
    setNextActionType(STATUS_SUGGESTED_ACTIONS[task.standard_status] || "");
    setNextFollowupDate("");
    setShowAbandonWarning(false);
    setTaskError("");
  };

  const onWizardComplete = (result: ActivityWizardResponse) => {
    setShowActivityWizard(false);
    setWizardFollowupId(null);
    setWizardSuccess(result.next_followup_id ? `Task completed. ${result.next_action_type} created — due ${new Date(result.next_followup_date!).toLocaleDateString()}.` : "Task completed. No follow-up scheduled.");
    queryClient.invalidateQueries({ queryKey: ["tasks"] });
    queryClient.invalidateQueries({ queryKey: ["dashboard"] });
  };

  const handleCompleteTask = async () => {
    if (!selectedTask || creatingFollowup) return;
    setTaskError("");
    if (selectedTask.followup_id) {
      setWizardFollowupId(selectedTask.followup_id);
      setShowActivityWizard(true);
      return;
    }
    setCreatingFollowup(true);
    try {
      const res = await api.post("/followups", {
        lead_id: selectedTask.lead_id,
        followup_date: new Date().toISOString().split("T")[0],
        next_followup: new Date(Date.now() + 2 * 86400000).toISOString().split("T")[0],
        discussion: selectedTask.discussion || "Follow-Up",
        next_action: selectedTask.next_action || "Call Again",
      });
      const newId = res.data.followup_id;
      setSelectedTask({ ...selectedTask, followup_id: newId });
      setWizardFollowupId(newId);
      setShowActivityWizard(true);
    } catch (err: any) {
      setTaskError(err.response?.data?.detail || "Failed to prepare task. Please try again.");
    } finally {
      setCreatingFollowup(false);
    }
  };

  return (
    <div className="p-5 lg:p-7 space-y-5 max-w-[1400px] mx-auto">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {summaryCards.map((s) => (
          <div key={s.label} className={cn("rounded-2xl border p-5 transition-all duration-200 hover-lift", s.bg, s.border)}>
            <div className="flex items-center justify-between mb-3">
              <s.icon className={cn("w-4 h-4", s.color)} />
              <span className={cn("text-2xl font-bold tabular-nums tracking-tight", s.color)}>{s.value}</span>
            </div>
            <p className="text-[13px] font-medium text-foreground/70">{s.label}</p>
          </div>
        ))}
      </div>

      <div className="flex gap-1.5 flex-wrap">
        {QUICK_FILTERS.map((f) => {
          const count = selectedTab === f.key ? allPending.length + allDone.length : 0;
          return (
            <button key={f.key} onClick={() => setSelectedTab(f.key)} className={cn("flex items-center gap-2 px-3.5 py-2 rounded-[12px] text-sm font-medium transition-all duration-150 border", selectedTab === f.key ? "bg-primary/[0.06] text-primary border-primary/30 shadow-sm" : "bg-card text-muted-foreground border-border/50 hover:text-foreground hover:border-border")}>
              <span className="text-[13px]">{f.label}</span>
              {selectedTab === f.key && count > 0 && <span className="text-[11px] bg-primary/10 text-primary px-1.5 py-0.5 rounded-full font-semibold">{count}</span>}
            </button>
          );
        })}
      </div>

      <div className="space-y-6">
        {isLoading ? (
          <div className="space-y-4">
            {Array.from({ length: 3 }).map((_, i) => (<div key={i}><div className="skeleton h-5 w-32 mb-3" /><div className="space-y-2">{Array.from({ length: 2 }).map((_, j) => (<div key={j} className="rounded-2xl border border-border/50 p-4"><div className="skeleton h-4 w-48" /><div className="skeleton h-3 w-32 mt-2" /></div>))}</div></div>))}
          </div>
        ) : allPending.length === 0 && allDone.length === 0 ? (
          <Card className="border-border/40 rounded-2xl"><CardContent className="py-16 text-center"><CheckCircle2 className="w-10 h-10 text-emerald-300/50 mx-auto mb-3" /><p className="text-muted-foreground font-medium">No tasks here</p></CardContent></Card>
        ) : (
          <>
            {groupedPending.map((group) => (
              <div key={group.key}>
                <div className="flex items-center gap-2 mb-3"><group.icon className={cn("w-4 h-4", group.color)} /><h3 className={cn("text-[15px] font-semibold", group.color)}>{group.label}</h3><span className="text-xs font-medium text-muted-foreground bg-muted px-2 py-0.5 rounded-full">{group.tasks.length}</span></div>
                <div className="space-y-2">{group.tasks.map((task: any) => (<TaskCard key={`${task.lead_id}-${task.followup_id || "no-fu"}`} task={task} onClick={() => handleOpenTask(task)} />))}</div>
              </div>
            ))}
            {groupedDone.map((group) => (
              <div key={group.key}>
                <div className="flex items-center gap-2 mb-3"><CheckCircle2 className="w-4 h-4 text-emerald-500" /><h3 className="text-[15px] font-semibold text-emerald-600">{group.label}</h3><span className="text-xs font-medium text-muted-foreground bg-muted px-2 py-0.5 rounded-full">{group.tasks.length}</span></div>
                <div className="space-y-2">{group.tasks.map((task: any) => (<TaskCard key={`${task.lead_id}-${task.followup_id || "no-fu"}-done`} task={task} onClick={() => handleOpenTask(task)} />))}</div>
              </div>
            ))}
          </>
        )}
      </div>

      {selectedTask && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/25 backdrop-blur-[2px] animate-fade-in" onClick={() => { setSelectedTask(null); }}>
          <div className="bg-white rounded-2xl shadow-[var(--shadow-modal)] w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto animate-scale-in" onClick={(e) => e.stopPropagation()}>
            <div className="sticky top-0 bg-white/95 backdrop-blur-sm border-b border-border/40 z-10 px-6 py-4 flex items-center justify-between shrink-0 rounded-t-2xl">
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-2 h-2 rounded-full bg-primary shrink-0" />
                <h2 className="font-bold text-[15px] truncate">{selectedTask.company_name}</h2>
                <span className="text-[11px] text-muted-foreground/50 font-medium">{selectedTask.standard_status}</span>
              </div>
              <button onClick={() => { setSelectedTask(null); }} className="p-2 rounded-lg hover:bg-muted/60 transition-colors"><X className="w-4 h-4 text-muted-foreground/60" /></button>
            </div>
            <div ref={drawerContentRef} className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
              {selectedTask.bucket !== "completed" && selectedTask.discussion && (
                <div className="rounded-[14px] bg-gradient-to-br from-primary/[0.04] to-primary/[0.02] border border-primary/20 p-4 space-y-2">
                  <span className={cn("text-xs font-bold px-2 py-0.5 rounded border inline-block", getTaskTypeConfig(selectedTask.discussion, selectedTask.next_action).badgeColor)}>{getTaskTypeConfig(selectedTask.discussion, selectedTask.next_action).badge}</span>
                  <p className="text-base font-bold text-foreground">{getTaskTypeConfig(selectedTask.discussion, selectedTask.next_action).label}</p>
                  <p className="text-sm text-muted-foreground leading-relaxed">{getTaskOrigin(selectedTask.discussion, selectedTask.next_action, selectedTask.last_contact_date)}</p>
                </div>
              )}
              <div className="rounded-[14px] bg-muted/20 p-4 space-y-3">
                <p className="text-[11px] font-semibold text-muted-foreground/50 uppercase tracking-wider">Task Information</p>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div><p className="text-[11px] text-muted-foreground/60">Lead</p><p className="font-medium truncate">{selectedTask.company_name}</p></div>
                  <div><p className="text-[11px] text-muted-foreground/60">Status</p><p className="font-medium">{selectedTask.standard_status}</p></div>
                  <div><p className="text-[11px] text-muted-foreground/60">Due</p><p className={cn("font-medium", selectedTask.days_to < 0 ? "text-red-600" : selectedTask.days_to === 0 ? "text-amber-600" : "")}>{selectedTask.due_label}{selectedTask.due_date ? ` · ${formatDate(selectedTask.due_date)}` : ""}</p></div>
                  <div><p className="text-[11px] text-muted-foreground/60">Assigned To</p><p className="font-medium">{selectedTask.assigned_to || "—"}</p></div>
                </div>
                {selectedTask.next_action_plan && selectedTask.bucket !== "completed" && (<div className="pt-1 border-t border-border/40"><p className="text-[11px] text-muted-foreground/60 mb-0.5">Action Plan</p><p className="text-sm font-medium text-primary">{selectedTask.next_action_plan}</p></div>)}
                {selectedTask.phone && <div className="flex items-center gap-2 text-sm"><Phone className="w-3.5 h-3.5 text-muted-foreground/50" /><span>{selectedTask.phone}</span></div>}
                {selectedTask.email && <div className="flex items-center gap-2 text-sm"><MessageSquare className="w-3.5 h-3.5 text-muted-foreground/50" /><span>{selectedTask.email}</span></div>}
              </div>
              {selectedTask.bucket !== "completed" && (
                <div className="rounded-[14px] bg-primary/[0.02] border border-primary/20 overflow-hidden">
                  <div className="px-4 py-3 border-b border-primary/10"><p className="text-[11px] font-semibold text-primary uppercase tracking-wider">Next Action</p></div>
                  <div className="px-4 pb-4 space-y-4 pt-4">
                    <div><label className="text-[11px] font-medium text-muted-foreground/60 mb-1 block">Action *</label><select value={nextActionType} onChange={(e) => setNextActionType(e.target.value)} className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"><option value="">— Select next action —</option>{NEXT_ACTION_OPTIONS.map((a) => <option key={a} value={a}>{a}</option>)}</select></div>
                    {nextActionType && nextActionType !== "No Follow-Up Required" && (<div><label className="text-[11px] font-medium text-muted-foreground/60 mb-1 block">Follow-Up Date *</label><input type="date" value={nextFollowupDate} onChange={(e) => setNextFollowupDate(e.target.value)} className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20" /></div>)}
                  </div>
                </div>
              )}
              {wizardSuccess && (<div className="rounded-[14px] bg-emerald-50 border border-emerald-200 p-4 text-center"><CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto mb-2" /><p className="text-sm font-semibold text-emerald-800">Activity Recorded</p><p className="text-xs text-emerald-600 mt-1">{wizardSuccess}</p></div>)}
            </div>
            <div className="sticky bottom-0 bg-white/95 backdrop-blur-sm border-t border-border/40 px-6 py-4 -mx-6 -mb-5">
              {taskError && (<div className="flex items-center gap-2 p-3 rounded-xl bg-destructive/8 border border-destructive/15 text-destructive text-sm mb-3"><AlertTriangle className="w-4 h-4 shrink-0" /><span>{taskError}</span></div>)}
              <div className="flex items-center gap-3">
                {selectedTask.bucket !== "completed" && !wizardSuccess ? (
                  <>
                    <Button size="lg" className="flex-1 gap-2 bg-primary hover:bg-primary/90 rounded-[12px]" onClick={handleCompleteTask} disabled={creatingFollowup}>
                      {creatingFollowup ? (<><div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full" /> Preparing...</>) : (<><CheckCircle2 className="w-4 h-4" />{getTaskTypeConfig(selectedTask.discussion, selectedTask.next_action).ctaLabel}</>)}
                    </Button>
                    <Button variant="outline" size="lg" onClick={() => { navigate(`/leads/${selectedTask.lead_id}`); setSelectedTask(null); }} className="gap-2 rounded-[12px]"><ArrowRight className="w-4 h-4" />Open Lead</Button>
                  </>
                ) : wizardSuccess ? (
                  <Button size="lg" className="flex-1 rounded-[12px]" onClick={() => { setSelectedTask(null); setWizardSuccess(""); }}>Close</Button>
                ) : (
                  <Button variant="outline" size="lg" className="flex-1 rounded-[12px]" onClick={() => { navigate(`/leads/${selectedTask.lead_id}`); setSelectedTask(null); }}><ArrowRight className="w-4 h-4 mr-2" />Open Lead</Button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {showActivityWizard && selectedTask && wizardFollowupId && (
        <ActivityWizard followupId={wizardFollowupId} leadStatus={selectedTask.status} assignedTo={selectedTask.assigned_to || ""} companyName={selectedTask.company_name} taskType={selectedTask.next_action || ""} taskDiscussion={selectedTask.discussion || ""} onClose={() => { setShowActivityWizard(false); setWizardFollowupId(null); }} onComplete={onWizardComplete} />
      )}
    </div>
  );
}

function TaskCard({ task, onClick }: { task: any; onClick: () => void }) {
  const isLate = task.days_to < 0;
  const isToday = task.days_to === 0;
  const isCompleted = task.bucket === "completed";
  const typeConfig = getTaskTypeConfig(task.discussion, task.next_action);
  const dueLabel = isCompleted ? "Done" : isLate ? `${Math.abs(task.days_to)}d late` : isToday ? "Today" : task.days_to === 1 ? "Tomorrow" : `${task.days_to}d`;
  return (
    <div onClick={onClick} className={cn("flex items-center gap-3.5 px-4 py-3.5 rounded-2xl border bg-card cursor-pointer transition-all duration-180 hover:shadow-[var(--shadow-card-hover)]", isLate ? "border-red-200/50 hover:border-red-300/60" : "border-border/50 hover:border-primary/15", isCompleted && "opacity-55")}>
      <div className={cn("w-2.5 h-2.5 rounded-full shrink-0", isCompleted ? "bg-emerald-400" : isLate ? "bg-destructive" : isToday ? "bg-accent" : "bg-primary/40")} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-semibold text-[14px] truncate">{task.company_name}</span>
          <span className={cn("badge-premium px-1.5 py-0.5 rounded-md border", typeConfig.badgeColor)}>{typeConfig.badge}</span>
          {!isCompleted && <span className="badge-premium px-1.5 py-0.5 rounded-md bg-muted/60 text-muted-foreground/50 border-0">{task.standard_status}</span>}
          {isCompleted && task.outcome_notes && <span className="text-[11px] text-muted-foreground/35 line-clamp-1 italic">"{task.outcome_notes.slice(0, 60)}{task.outcome_notes.length > 60 ? '...' : ''}"</span>}
        </div>
      </div>
      <div className="flex items-center gap-2.5 shrink-0">
        <span className={cn("badge-premium px-2 py-0.5 rounded-lg", isCompleted ? "bg-emerald-50 text-emerald-600" : isLate ? "bg-red-50 text-red-600" : isToday ? "bg-amber-50 text-amber-600" : "bg-muted text-muted-foreground/50")}>{dueLabel}</span>
        <ArrowRight className="w-3.5 h-3.5 text-muted-foreground/15" />
      </div>
    </div>
  );
}
