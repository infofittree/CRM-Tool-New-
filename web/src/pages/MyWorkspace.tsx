import { useAuth } from "@/lib/auth";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import api from "@/lib/api";
import { cn, formatDate } from "@/lib/utils";
import {
  User, ChevronRight, Building2, Clock, AlertTriangle, Calendar, CheckCircle2, ListTodo, ArrowRight,
} from "lucide-react";
import { useTaskQueue } from "@/hooks/useDashboard";

const STATUS_BADGES: Record<string, string> = {
  "Prospect": "bg-slate-100 text-slate-700",
  "Requirement Qualified": "bg-blue-50 text-blue-700",
  "Technical Discussion": "bg-cyan-50 text-cyan-700",
  "Quotation Sent": "bg-emerald-50 text-emerald-700",
  "Sample Sent": "bg-lime-50 text-lime-700",
  "Negotiation": "bg-amber-50 text-amber-700",
  "Trial Order": "bg-orange-50 text-orange-700",
  "Nurturing": "bg-purple-50 text-purple-700",
  "Order Closed": "bg-green-50 text-green-700",
  "Lost": "bg-red-50 text-red-700",
};

const BAND_STYLES: Record<string, string> = {
  HOT: "bg-red-100 text-red-700 border-red-200",
  WARM: "bg-amber-100 text-amber-700 border-amber-200",
  COLD: "bg-blue-100 text-blue-700 border-blue-200",
};

export default function MyWorkspace() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { data: tasks } = useTaskQueue();
  const { data: leadsData, isLoading } = useQuery({
    queryKey: ["workspace", user?.username],
    queryFn: () =>
      api.get("/leads", { params: { assigned_to: user?.full_name, page_size: 50 } }).then((r) => r.data),
    enabled: !!user,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });

  const overdueTasks = tasks?.overdue || [];
  const todayTasks = tasks?.today_capped || [];
  const upcomingTasks = tasks?.upcoming || [];

  return (
    <div className="p-6 space-y-6 max-w-[1400px] mx-auto">
      <div>
        <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
          <User className="w-4 h-4" />
          <span>Personal dashboard</span>
        </div>
        <h1 className="text-3xl font-bold tracking-tight">My Workspace</h1>
        <p className="text-muted-foreground mt-1">
          Your priorities and assigned leads, {user?.full_name?.split(" ")[0]}
        </p>
      </div>

      {/* Summary bar */}
      <div className="grid grid-cols-4 gap-3">
        {[
          { label: "Due Today", value: todayTasks.length, icon: <Clock className="w-4 h-4" />, color: todayTasks.length > 0 ? "text-accent" : "text-muted-foreground", bg: todayTasks.length > 0 ? "bg-accent/10" : "bg-muted/30" },
          { label: "Overdue", value: overdueTasks.length, icon: <AlertTriangle className="w-4 h-4" />, color: overdueTasks.length > 0 ? "text-destructive" : "text-muted-foreground", bg: overdueTasks.length > 0 ? "bg-destructive/10" : "bg-muted/30" },
          { label: "Upcoming", value: upcomingTasks.length, icon: <Calendar className="w-4 h-4" />, color: "text-primary", bg: "bg-primary/10" },
          { label: "My Leads", value: leadsData?.total || 0, icon: <Building2 className="w-4 h-4" />, color: "text-emerald-600", bg: "bg-emerald-50" },
        ].map((s) => (
          <div key={s.label} className={cn("rounded-xl border border-border/60 p-4", s.bg)}>
            <div className="flex items-center justify-between mb-1">
              <span className={s.color}>{s.icon}</span>
              <span className={cn("text-2xl font-bold", s.color)}>{s.value}</span>
            </div>
            <p className="text-sm font-medium">{s.label}</p>
          </div>
        ))}
      </div>

      {/* Two-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Left: Tasks */}
        <div className="space-y-4">
          {/* Overdue Tasks */}
          {overdueTasks.length > 0 && (
            <div>
              <h2 className="text-sm font-semibold flex items-center gap-2 text-destructive mb-3">
                <AlertTriangle className="w-4 h-4" />
                Overdue Tasks ({overdueTasks.length})
              </h2>
              <div className="space-y-2">
                {overdueTasks.slice(0, 5).map((task: any) => (
                  <TaskRow key={`${task.lead_id}-${task.followup_id || "t"}`} task={task} navigate={navigate} />
                ))}
                {overdueTasks.length > 5 && (
                  <Button variant="ghost" size="sm" className="w-full text-xs" onClick={() => navigate("/tasks")}>
                    View all {overdueTasks.length} overdue <ArrowRight className="w-3 h-3" />
                  </Button>
                )}
              </div>
            </div>
          )}

          {/* Due Today */}
          <div>
            <h2 className="text-sm font-semibold flex items-center gap-2 text-accent mb-3">
              <Clock className="w-4 h-4" />
              Tasks Due Today ({todayTasks.length})
            </h2>
            <div className="space-y-2">
              {todayTasks.length > 0 ? todayTasks.slice(0, 5).map((task: any) => (
                <TaskRow key={`${task.lead_id}-${task.followup_id || "t"}`} task={task} navigate={navigate} />
              )) : (
                <Card>
                  <CardContent className="py-8 text-center">
                    <CheckCircle2 className="w-6 h-6 text-emerald-400/50 mx-auto mb-1" />
                    <p className="text-sm text-muted-foreground">No tasks due today</p>
                  </CardContent>
                </Card>
              )}
            </div>
          </div>

          {/* Upcoming */}
          <div>
            <h2 className="text-sm font-semibold flex items-center gap-2 text-primary mb-3">
              <Calendar className="w-4 h-4" />
              Upcoming Follow-Ups ({upcomingTasks.length})
            </h2>
            <div className="space-y-2">
              {upcomingTasks.slice(0, 5).map((task: any) => (
                <TaskRow key={`${task.lead_id}-${task.followup_id || "t"}`} task={task} navigate={navigate} />
              ))}
              {upcomingTasks.length > 5 && (
                <Button variant="ghost" size="sm" className="w-full text-xs" onClick={() => navigate("/tasks")}>
                  View all upcoming <ArrowRight className="w-3 h-3" />
                </Button>
              )}
            </div>
          </div>
        </div>

        {/* Right: My Leads */}
        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Building2 className="w-4 h-4 text-primary" />
                My Leads ({leadsData?.total || 0})
              </CardTitle>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="space-y-3">
                  {Array.from({ length: 4 }).map((_, i) => (
                    <div key={i} className="flex items-center gap-3">
                      <div className="skeleton h-9 w-9 rounded-lg" />
                      <div className="flex-1 space-y-1">
                        <div className="skeleton h-4 w-32" />
                        <div className="skeleton h-3 w-20" />
                      </div>
                    </div>
                  ))}
                </div>
              ) : leadsData?.items?.length > 0 ? (
                <div className="divide-y divide-border">
                  {leadsData.items.map((lead: any) => (
                    <div
                      key={lead.lead_id}
                      onClick={() => navigate(`/leads/${lead.lead_id}`)}
                      className="py-3 flex items-center justify-between cursor-pointer hover:bg-muted/30 rounded-lg px-2 -mx-2 transition-colors group"
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-primary/60 to-primary flex items-center justify-center text-sm font-bold text-white shrink-0">
                          {(lead.company_name || "?").charAt(0).toUpperCase()}
                        </div>
                        <div className="min-w-0">
                          <p className="font-medium group-hover:text-primary transition-colors truncate">{lead.company_name}</p>
                          <div className="flex items-center gap-2 text-xs text-muted-foreground">
                            <span className={cn("px-1.5 py-0.5 rounded text-xs font-medium", STATUS_BADGES[lead.status] || "")}>
                              {lead.status}
                            </span>
                            {lead.country && <span>• {lead.country}</span>}
                          </div>
                        </div>
                      </div>
                      <ChevronRight className="w-4 h-4 text-muted-foreground/30 group-hover:text-primary/50 transition-colors shrink-0" />
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12">
                  <User className="w-10 h-10 text-muted-foreground/30 mx-auto mb-3" />
                  <p className="text-muted-foreground font-medium">No leads assigned to you</p>
                  <p className="text-xs text-muted-foreground/60 mt-1">Ask your admin to assign leads to you</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

function TaskRow({ task, navigate }: { task: any; navigate: any }) {
  const isLate = task.days_to < 0;
  const dueLabel = isLate ? `${Math.abs(task.days_to)}d overdue` : task.days_to === 0 ? "Today" : `in ${task.days_to}d`;
  return (
    <div
      onClick={() => navigate(`/tasks`)}
      className={cn(
        "flex items-start gap-3 p-3.5 rounded-xl border border-border/60 cursor-pointer hover:shadow-sm transition-all group",
        isLate ? "border-red-200/60" : ""
      )}
    >
      <div className={cn(
        "w-2 h-2 mt-1.5 rounded-full shrink-0",
        isLate ? "bg-destructive" : task.days_to === 0 ? "bg-accent" : "bg-primary/40"
      )} />
      <div className="flex-1 min-w-0">
        <p className="font-medium text-sm truncate group-hover:text-primary transition-colors">{task.company_name}</p>
        <p className="text-xs text-muted-foreground mt-0.5">{task.recommended_action}</p>
      </div>
      <span className={cn(
        "text-xs font-semibold px-2 py-0.5 rounded shrink-0",
        isLate ? "bg-destructive/10 text-destructive" : "bg-muted text-muted-foreground"
      )}>
        {dueLabel}
      </span>
    </div>
  );
}
