import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useTaskQueue } from "@/hooks/useDashboard";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth";
import api, { type Task } from "@/lib/api";
import TaskWorkflowModal from "@/components/TaskWorkflowModal";
import { getTaskTypeConfig } from "@/lib/taskTypes";
import {
  Clock, AlertTriangle, Calendar, ArrowRight, CheckCircle2, Building2,
} from "lucide-react";

type TabKey = "all" | "calls" | "responses" | "procurement" | "meetings" | "quotations";
const QUICK_FILTERS: { key: TabKey; label: string }[] = [
  { key: "all", label: "All Tasks" }, { key: "calls", label: "Call Back" }, { key: "responses", label: "Responses" },
  { key: "procurement", label: "Procurement" }, { key: "meetings", label: "Meetings" }, { key: "quotations", label: "Quotations" },
];

export default function Tasks() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [selectedTab, setSelectedTab] = useState<TabKey>("all");
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);

  const { data, isLoading } = useTaskQueue();
  const { data: leadsData } = useQuery({
    queryKey: ["tasks", "my-leads", user?.full_name],
    queryFn: () => api.get("/leads", { params: { assigned_to: user?.full_name, page_size: 1 } }).then((r) => r.data.total || 0),
    enabled: !!user, staleTime: 60000, refetchOnWindowFocus: false,
  });

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
                <div className="space-y-2">{group.tasks.map((task: any) => (<TaskCard key={`${task.lead_id}-${task.followup_id || "no-fu"}`} task={task} onClick={() => setSelectedTask(task)} />))}</div>
              </div>
            ))}
            {groupedDone.map((group) => (
              <div key={group.key}>
                <div className="flex items-center gap-2 mb-3"><CheckCircle2 className="w-4 h-4 text-emerald-500" /><h3 className="text-[15px] font-semibold text-emerald-600">{group.label}</h3><span className="text-xs font-medium text-muted-foreground bg-muted px-2 py-0.5 rounded-full">{group.tasks.length}</span></div>
                <div className="space-y-2">{group.tasks.map((task: any) => (<TaskCard key={`${task.lead_id}-${task.followup_id || "no-fu"}-done`} task={task} onClick={() => setSelectedTask(task)} />))}</div>
              </div>
            ))}
          </>
        )}
      </div>

      {/* Task Workflow Modal — single modal, no stacking dialogs */}
      {selectedTask && (
        <TaskWorkflowModal task={selectedTask} onClose={() => setSelectedTask(null)} />
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
