import { useState } from "react";
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

const LEAD_STATUSES = [
  "Prospect", "Requirement Qualified", "Technical Discussion", "Quotation Sent",
  "Sample Sent", "Negotiation", "Trial Order", "Order Closed", "Nurturing", "Lost",
];

const INTEREST_LEVELS = ["LOW", "MEDIUM", "HIGH", "VERY_HIGH"];

const NEXT_ACTION_OPTIONS = [
  "No Follow-Up Required", "Call Again", "Send Quotation", "Await Customer Response",
  "Schedule Meeting", "Send Samples", "Request Procurement Information", "Other",
];

const NEXT_ACTION_TEMPLATES: Record<string, string> = {
  "Call Again": "Follow-Up Call",
  "Send Quotation": "Send Quotation",
  "Await Customer Response": "Check Customer Response",
  "Schedule Meeting": "Conduct Meeting",
  "Send Samples": "Follow Up On Samples",
  "Request Procurement Information": "Review Procurement Response",
  "Other": "Follow-Up",
};

const STATUS_SUGGESTED_ACTIONS: Record<string, string> = {
  "Prospect": "Call Again", "Requirement Qualified": "Send Quotation",
  "Technical Discussion": "Call Again", "Quotation Sent": "Await Customer Response",
  "Sample Sent": "Call Again", "Negotiation": "Call Again",
  "Trial Order": "Call Again", "Nurturing": "Call Again",
};

type TabKey = "all" | "calls" | "responses" | "procurement" | "meetings" | "quotations";
type BucketKey = "today" | "overdue" | "upcoming" | "completed";

const QUICK_FILTERS: { key: TabKey; label: string; icon: string }[] = [
  { key: "all", label: "All Tasks", icon: "ListTodo" },
  { key: "calls", label: "Call Back", icon: "Phone" },
  { key: "responses", label: "Responses", icon: "MessageSquare" },
  { key: "procurement", label: "Procurement", icon: "AlertTriangle" },
  { key: "meetings", label: "Meetings", icon: "Calendar" },
  { key: "quotations", label: "Quotations", icon: "ArrowRight" },
];

export default function Tasks() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [selectedTab, setSelectedTab] = useState<TabKey>("all");
  const [bucket, setBucket] = useState<BucketKey>("today");
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [outcomeNotes, setOutcomeNotes] = useState("");
  const [completing, setCompleting] = useState(false);
  const [expandedSection, setExpandedSection] = useState<string | null>(null);
  const [leadStatus, setLeadStatus] = useState("");
  const [interestLevel, setInterestLevel] = useState("");
  const [dealValue, setDealValue] = useState("");
  const [discussionSummary, setDiscussionSummary] = useState("");
  const [customerRequirements, setCustomerRequirements] = useState("");
  const [nextActionType, setNextActionType] = useState("");
  const [nextFollowupDate, setNextFollowupDate] = useState("");
  const [showAbandonWarning, setShowAbandonWarning] = useState(false);
  const [showActivityWizard, setShowActivityWizard] = useState(false);
  const [wizardSuccess, setWizardSuccess] = useState("");

  const { data, isLoading } = useTaskQueue();
  const { data: leadsData } = useQuery({
    queryKey: ["tasks", "my-leads", user?.full_name],
    queryFn: () => api.get("/leads", { params: { assigned_to: user?.full_name, page_size: 1 } }).then((r) => r.data.total || 0),
    enabled: !!user,
    staleTime: 60_000,
    refetchOnWindowFocus: false,
  });

  const summaryCards = [
    { label: "Due Today", value: data?.today_capped?.length ?? 0, icon: Clock, color: "text-amber-600", bg: "bg-amber-50/80", border: "border-amber-100" },
    { label: "Overdue", value: data?.overdue?.length ?? 0, icon: AlertTriangle, color: "text-red-500", bg: "bg-red-50/80", border: "border-red-100" },
    { label: "Upcoming", value: data?.upcoming?.length ?? 0, icon: Calendar, color: "text-teal-600", bg: "bg-teal-50/60", border: "border-teal-100" },
    { label: "My Leads", value: leadsData ?? 0, icon: Building2, color: "text-emerald-600", bg: "bg-emerald-50/60", border: "border-emerald-100" },
  ];

  const bucketCounts = {
    today: data?.today_capped?.length ?? 0,
    overdue: data?.overdue?.length ?? 0,
    upcoming: data?.upcoming?.length ?? 0,
    completed: data?.completed?.length ?? 0,
  };

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

  const rawItems = bucket === "today" ? data?.today_capped ?? []
    : bucket === "overdue" ? data?.overdue ?? []
    : bucket === "upcoming" ? data?.upcoming ?? []
    : data?.completed ?? [];
  const items = filterTasksByType(rawItems);

  const isTerminal = selectedTask?.status === "Order Closed" || selectedTask?.status === "Lost";

  const handleOpenTask = (task: Task) => {
    setSelectedTask(task);
    setOutcomeNotes("");
    setCompleting(false);
    setExpandedSection(null);
    setLeadStatus(task.status || "");
    setInterestLevel(task.interest_level || "");
    setDealValue(task.potential_deal_value || "");
    setDiscussionSummary("");
    setCustomerRequirements(task.customer_requirements || "");
    setShowAbandonWarning(false);
    const suggested = STATUS_SUGGESTED_ACTIONS[task.standard_status] || "";
    setNextActionType(suggested);
    setNextFollowupDate("");
  };

  const onWizardComplete = (result: ActivityWizardResponse) => {
    setShowActivityWizard(false);
    setWizardSuccess(
      result.next_followup_id
        ? `Task completed. ${result.next_action_type} created — due ${new Date(result.next_followup_date!).toLocaleDateString()}.`
        : "Task completed. No follow-up scheduled."
    );
    queryClient.invalidateQueries({ queryKey: ["tasks"] });
    queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    queryClient.invalidateQueries({ queryKey: ["lead"] });
  };

  return (
    <div className="p-5 lg:p-7 space-y-5 max-w-[1400px] mx-auto">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {summaryCards.map((s) => (
          <div key={s.label} className={cn("rounded-2xl border p-4 transition-all", s.bg, s.border)}>
            <div className="flex items-center justify-between mb-2">
              <s.icon className={cn("w-4 h-4", s.color)} />
              <span className={cn("text-2xl font-bold tabular-nums", s.color)}>{s.value}</span>
            </div>
            <p className="text-sm font-medium text-foreground/80">{s.label}</p>
          </div>
        ))}
      </div>

      {/* Quick Filters */}
      <div className="flex gap-1.5 flex-wrap">
        {QUICK_FILTERS.map((f) => {
          const count = selectedTab === f.key ? items.length : 0;
          return (
            <button
              key={f.key}
              onClick={() => setSelectedTab(f.key)}
              className={cn(
                "flex items-center gap-2 px-3.5 py-2 rounded-[12px] text-sm font-medium transition-all duration-150 border",
                selectedTab === f.key
                  ? "bg-primary/[0.06] text-primary border-primary/30 shadow-sm"
                  : "bg-card text-muted-foreground border-border/50 hover:text-foreground hover:border-border",
              )}
            >
              <span className="text-[13px]">{f.label}</span>
              {selectedTab === f.key && count > 0 && (
                <span className="text-[11px] bg-primary/10 text-primary px-1.5 py-0.5 rounded-full font-semibold">
                  {count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Bucket tabs */}
      <div className="flex gap-1 p-1 rounded-xl bg-muted w-fit border border-border/30">
        {[
          { key: "today" as BucketKey, label: "Today" },
          { key: "overdue" as BucketKey, label: "Overdue" },
          { key: "upcoming" as BucketKey, label: "Upcoming" },
          { key: "completed" as BucketKey, label: "Done" },
        ].map((b) => (
          <button
            key={b.key}
            onClick={() => setBucket(b.key)}
            className={cn(
              "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all",
              bucket === b.key
                ? "bg-background text-foreground shadow-sm border border-border/50"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            {b.label}
            <span className={cn(
              "text-xs px-1.5 py-0.5 rounded-full",
              bucket === b.key ? "bg-muted text-muted-foreground" : "bg-background/50",
              b.key === "overdue" && bucketCounts.overdue > 0 ? "text-red-600 font-semibold" : "",
              b.key === "completed" && bucketCounts.completed > 0 ? "text-emerald-600 font-semibold" : "",
            )}>
              {bucketCounts[b.key]}
            </span>
          </button>
        ))}
      </div>

      {/* Compact Task Cards */}
      <div className="space-y-2">
        {isLoading ? (
          <div className="space-y-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="rounded-[14px] border border-border/60 p-4 space-y-2">
                <div className="skeleton h-4 w-48" />
                <div className="skeleton h-3 w-32" />
              </div>
            ))}
          </div>
        ) : items.length === 0 ? (
          <Card className="border-border/60 rounded-[14px]">
            <CardContent className="py-16 text-center">
              <CheckCircle2 className="w-10 h-10 text-emerald-300/50 mx-auto mb-3" />
              <p className="text-muted-foreground font-medium">No tasks here</p>
              <p className="text-xs text-muted-foreground/50 mt-1">
                {selectedTab !== "all" ? "Try a different filter" : bucket === "today" ? "All caught up!" : "Nothing to show"}
              </p>
            </CardContent>
          </Card>
        ) : (
          items.map((task: any) => {
            const isLate = task.days_to < 0;
            const isToday = task.days_to === 0;
            const isCompleted = task.bucket === "completed";
            const typeConfig = getTaskTypeConfig(task.discussion, task.next_action);
            const dueLabel = isCompleted ? "Done" : isLate ? `${Math.abs(task.days_to)}d late` : isToday ? "Today" : `${task.days_to}d`;
            return (
              <div
                key={task.lead_id + (isCompleted ? "_done" : "")}
                className={cn(
                  "flex items-center gap-3 px-4 py-3 rounded-[14px] border bg-card cursor-pointer",
                  "transition-all duration-150 hover:shadow-sm",
                  isLate ? "border-red-200/60 hover:border-red-300/60" : "border-border/60 hover:border-primary/20",
                  isCompleted && "opacity-75",
                )}
                onClick={() => handleOpenTask(task)}
              >
                <div className={cn(
                  "w-2.5 h-2.5 rounded-full shrink-0",
                  isCompleted ? "bg-emerald-400" : isLate ? "bg-destructive" : isToday ? "bg-accent" : "bg-primary/40",
                )} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-semibold text-[14px] truncate group-hover:text-primary transition-colors">
                      {task.company_name}
                    </span>
                    <span className={cn("text-[11px] font-semibold px-1.5 py-0.5 rounded border", typeConfig.badgeColor)}>
                      {typeConfig.badge}
                    </span>
                    {!isCompleted && (
                      <span className="text-[11px] px-1.5 py-0.5 rounded bg-muted/80 text-muted-foreground/60">
                        {task.standard_status}
                      </span>
                    )}
                    {isCompleted && task.outcome_notes && (
                      <span className="text-[11px] text-muted-foreground/40 line-clamp-1 italic">
                        "{task.outcome_notes.slice(0, 60)}{task.outcome_notes.length > 60 ? '...' : ''}"
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2.5 shrink-0">
                  <span className={cn(
                    "text-[12px] font-semibold px-2 py-0.5 rounded-md",
                    isCompleted ? "bg-emerald-50 text-emerald-600"
                      : isLate ? "bg-red-50 text-red-600"
                      : isToday ? "bg-amber-50 text-amber-600"
                      : "bg-muted text-muted-foreground/60",
                  )}>
                    {dueLabel}
                  </span>
                  {!isCompleted && task.phone && (
                    <span className="text-[12px] text-muted-foreground/50 hidden sm:block">{task.phone}</span>
                  )}
                  <ArrowRight className="w-3.5 h-3.5 text-muted-foreground/20" />
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Task Detail Drawer */}
      {selectedTask && (
        <>
          <div className="fixed inset-0 z-40 bg-black/20" onClick={() => { setSelectedTask(null); setOutcomeNotes(""); }} />
          <div className="fixed top-0 right-0 z-50 h-full w-full max-w-lg bg-white shadow-2xl border-l border-border overflow-y-auto">
            <div className="sticky top-0 bg-white border-b border-border z-10 px-5 py-4 flex items-center justify-between">
              <div className="flex items-center gap-2 min-w-0">
                <h2 className="font-bold text-sm truncate">{selectedTask.company_name}</h2>
              </div>
              <Button variant="ghost" size="sm" onClick={() => { setSelectedTask(null); setOutcomeNotes(""); }}>
                <X className="w-4 h-4" />
              </Button>
            </div>

            <div className="p-5 space-y-5">
              {/* Workflow Header */}
              {selectedTask.bucket !== "completed" && selectedTask.discussion && (
                <div className="rounded-[14px] bg-gradient-to-br from-primary/[0.04] to-primary/[0.02] border border-primary/20 p-4 space-y-2">
                  <div className="flex items-center gap-2">
                    <span className={cn("text-xs font-bold px-2 py-0.5 rounded border", getTaskTypeConfig(selectedTask.discussion, selectedTask.next_action).badgeColor)}>
                      {getTaskTypeConfig(selectedTask.discussion, selectedTask.next_action).badge}
                    </span>
                  </div>
                  <p className="text-base font-bold text-foreground">
                    {getTaskTypeConfig(selectedTask.discussion, selectedTask.next_action).label}
                  </p>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {getTaskOrigin(selectedTask.discussion, selectedTask.next_action, selectedTask.last_contact_date)}
                  </p>
                </div>
              )}

              {/* Task Information Card */}
              <div className="rounded-[14px] bg-muted/20 p-4 space-y-3">
                <p className="text-[11px] font-semibold text-muted-foreground/50 uppercase tracking-wider">Task Information</p>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div><p className="text-[11px] text-muted-foreground/60">Lead</p><p className="font-medium truncate">{selectedTask.company_name}</p></div>
                  <div><p className="text-[11px] text-muted-foreground/60">Status</p><p className="font-medium">{selectedTask.standard_status}</p></div>
                  <div><p className="text-[11px] text-muted-foreground/60">Due</p><p className={cn("font-medium", selectedTask.days_to < 0 ? "text-red-600" : selectedTask.days_to === 0 ? "text-amber-600" : "")}>{selectedTask.due_label}{selectedTask.due_date ? ` · ${formatDate(selectedTask.due_date)}` : ""}</p></div>
                  <div><p className="text-[11px] text-muted-foreground/60">Assigned To</p><p className="font-medium">{selectedTask.assigned_to || "—"}</p></div>
                </div>
                {selectedTask.next_action_plan && selectedTask.bucket !== "completed" && (
                  <div className="pt-1 border-t border-border/40">
                    <p className="text-[11px] text-muted-foreground/60 mb-0.5">Action Plan</p>
                    <p className="text-sm font-medium text-primary">{selectedTask.next_action_plan}</p>
                  </div>
                )}
                {selectedTask.phone && <div className="flex items-center gap-2 text-sm"><Phone className="w-3.5 h-3.5 text-muted-foreground/50" /><span>{selectedTask.phone}</span></div>}
                {selectedTask.email && <div className="flex items-center gap-2 text-sm"><MessageSquare className="w-3.5 h-3.5 text-muted-foreground/50" /><span>{selectedTask.email}</span></div>}
              </div>

              {/* Lead Update Section */}
              {selectedTask.bucket !== "completed" && (
                <div className="rounded-[14px] border border-border/60 overflow-hidden">
                  <button
                    onClick={() => setExpandedSection(expandedSection === "lead-update" ? null : "lead-update")}
                    className="w-full flex items-center justify-between px-4 py-3 text-sm font-medium hover:bg-muted/30 transition-colors"
                  >
                    <span className="flex items-center gap-2"><User className="w-4 h-4 text-muted-foreground/50" />Lead Update</span>
                    {expandedSection === "lead-update" ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                  </button>
                  {expandedSection === "lead-update" && (
                    <div className="px-4 pb-4 space-y-4 border-t border-border/40 pt-4">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="text-[11px] font-medium text-muted-foreground/60 mb-1 block">Lead Status</label>
                          <select value={leadStatus} onChange={(e) => setLeadStatus(e.target.value)} className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20">
                            {LEAD_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                          </select>
                        </div>
                        <div>
                          <label className="text-[11px] font-medium text-muted-foreground/60 mb-1 block">Interest Level</label>
                          <select value={interestLevel} onChange={(e) => setInterestLevel(e.target.value)} className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20">
                            <option value="">— Not set —</option>
                            {INTEREST_LEVELS.map((l) => <option key={l} value={l}>{l}</option>)}
                          </select>
                        </div>
                      </div>
                      <div><label className="text-[11px] font-medium text-muted-foreground/60 mb-1 block">Opportunity Value (USD)</label><input type="text" value={dealValue} onChange={(e) => setDealValue(e.target.value)} placeholder="e.g., 50000" className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20" /></div>
                      <div><label className="text-[11px] font-medium text-muted-foreground/60 mb-1 block">Discussion Summary</label><textarea value={discussionSummary} onChange={(e) => setDiscussionSummary(e.target.value)} placeholder="Summarize the key discussion points..." rows={3} className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 resize-none" /></div>
                      <div><label className="text-[11px] font-medium text-muted-foreground/60 mb-1 block">Customer Requirements</label><textarea value={customerRequirements} onChange={(e) => setCustomerRequirements(e.target.value)} placeholder="What does the customer need?" rows={3} className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 resize-none" /></div>
                    </div>
                  )}
                </div>
              )}

              {/* Next Action Section */}
              {selectedTask.bucket !== "completed" && (
                <div className="rounded-[14px] bg-primary/[0.02] border border-primary/20 overflow-hidden">
                  <div className="px-4 py-3 border-b border-primary/10">
                    <p className="text-[11px] font-semibold text-primary uppercase tracking-wider">Next Action</p>
                  </div>
                  <div className="px-4 pb-4 space-y-4 pt-4">
                    {nextActionType && nextActionType !== "No Follow-Up Required" && NEXT_ACTION_TEMPLATES[nextActionType] && (
                      <div className="flex items-center gap-2 text-xs bg-primary/5 text-primary px-3 py-1.5 rounded-lg">
                        <Calendar className="w-3 h-3" />Will create: <strong>{NEXT_ACTION_TEMPLATES[nextActionType]}</strong>{nextFollowupDate && <span>· Due: {formatDate(nextFollowupDate)}</span>}
                      </div>
                    )}
                    <div>
                      <label className="text-[11px] font-medium text-muted-foreground/60 mb-1 block">Action *</label>
                      <select value={nextActionType} onChange={(e) => setNextActionType(e.target.value)} className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20">
                        <option value="">— Select next action —</option>
                        {NEXT_ACTION_OPTIONS.map((a) => <option key={a} value={a}>{a}</option>)}
                      </select>
                    </div>
                    {nextActionType && nextActionType !== "No Follow-Up Required" && (
                      <div>
                        <label className="text-[11px] font-medium text-muted-foreground/60 mb-1 block">Follow-Up Date *</label>
                        <input type="date" value={nextFollowupDate} onChange={(e) => setNextFollowupDate(e.target.value)} className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20" />
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Workflow Preview */}
              {selectedTask.bucket !== "completed" && !wizardSuccess && selectedTask.discussion && (
                <div className="rounded-[14px] bg-blue-50/50 border border-blue-100 p-4 space-y-2">
                  <p className="text-[11px] font-semibold text-blue-700 uppercase tracking-wider">What happens next?</p>
                  <ul className="text-xs text-blue-700 space-y-1">
                    <li className="flex items-center gap-1.5"><ArrowRight className="w-3 h-3 shrink-0" />Complete via guided wizard</li>
                    <li className="flex items-center gap-1.5"><ArrowRight className="w-3 h-3 shrink-0" />Record action + outcome</li>
                    <li className="flex items-center gap-1.5"><ArrowRight className="w-3 h-3 shrink-0" />Auto-create next follow-up</li>
                  </ul>
                </div>
              )}

              {/* Debug View — Admin only */}
              {selectedTask.bucket !== "completed" && !wizardSuccess && user?.role === "Admin" && (
                <details className="rounded-[14px] bg-muted/30 border border-border/40 p-3 text-xs text-muted-foreground">
                  <summary className="flex items-center gap-1.5 font-medium cursor-pointer text-[11px] uppercase tracking-wider"><Bug className="w-3 h-3" /> Workflow Debug</summary>
                  <div className="mt-2 space-y-1 font-mono">
                    {(() => {
                      const debug = getWorkflowDebug(selectedTask);
                      return (<><p>Task Type: <span className="text-foreground">{debug.taskType}</span></p><p>Discussion: <span className="text-foreground">{debug.discussion || "—"}</span></p><p>Next Action: <span className="text-foreground">{debug.nextAction || "—"}</span></p><p>Template: <span className="text-foreground">{debug.template}</span></p><p>Bucket: <span className="text-foreground">{debug.bucket}</span></p><p>Days: <span className="text-foreground">{debug.daysTo}</span></p></>);
                    })()}
                  </div>
                </details>
              )}

              {/* Wizard Success */}
              {wizardSuccess && (
                <div className="rounded-[14px] bg-emerald-50 border border-emerald-200 p-4 text-center">
                  <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
                  <p className="text-sm font-semibold text-emerald-800">Activity Recorded</p>
                  <p className="text-xs text-emerald-600 mt-1">{wizardSuccess}</p>
                </div>
              )}

              {/* Actions */}
              <div className="flex items-center gap-3 pt-2">
                {selectedTask.bucket !== "completed" && !wizardSuccess ? (
                  <>
                    <Button size="lg" className="flex-1 gap-2 bg-primary hover:bg-primary/90 rounded-[12px]" onClick={() => setShowActivityWizard(true)}>
                      <CheckCircle2 className="w-4 h-4" />
                      {getTaskTypeConfig(selectedTask.discussion, selectedTask.next_action).ctaLabel}
                    </Button>
                    <Button variant="outline" size="lg" onClick={() => { navigate(`/leads/${selectedTask.lead_id}`); setSelectedTask(null); }} className="gap-2 rounded-[12px]">
                      <ArrowRight className="w-4 h-4" />Open Lead
                    </Button>
                  </>
                ) : wizardSuccess ? (
                  <Button size="lg" className="flex-1 rounded-[12px]" onClick={() => { setSelectedTask(null); setWizardSuccess(""); }}>Close</Button>
                ) : (
                  <Button variant="outline" size="lg" className="flex-1 rounded-[12px]" onClick={() => { navigate(`/leads/${selectedTask.lead_id}`); setSelectedTask(null); }}>
                    <ArrowRight className="w-4 h-4 mr-2" />Open Lead
                  </Button>
                )}
              </div>
            </div>
          </div>
        </>
      )}

      {/* Activity Wizard */}
      {showActivityWizard && selectedTask && (
        <ActivityWizard
          followupId={selectedTask.followup_id!}
          leadStatus={selectedTask.status}
          assignedTo={selectedTask.assigned_to || ""}
          companyName={selectedTask.company_name}
          taskType={selectedTask.next_action || ""}
          taskDiscussion={selectedTask.discussion || ""}
          onClose={() => setShowActivityWizard(false)}
          onComplete={onWizardComplete}
        />
      )}
    </div>
  );
}