import React, { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import api from "@/lib/api";
import { useAuth } from "@/lib/auth";
import {
  useTaskQueue, usePipelineHealth, useDashboardLeads,
} from "@/hooks/useDashboard";
import { useExecutiveSummary, useProductivity } from "@/hooks/useAnalytics";
import { fetchInquirySummary, type InquirySummary } from "@/lib/inquiries";
import {
  TrendingUp, Users, Sparkles, BarChart3, ListTodo,
  ArrowRight, Target, CheckCircle2, AlertTriangle, Clock, Timer,
  MessageSquare, AlertCircle, Inbox, CircleDot, Flame, Eye,
} from "lucide-react";
import { useSalespersonFilter } from "@/lib/salespersonContext";

function getGreeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 18) return "Good afternoon";
  return "Good evening";
}

function StatCard({ label, value, icon: Icon, color, bg }: {
  label: string; value: string | number; icon: React.ElementType; color: string; bg: string;
}) {
  return (
    <div className={cn("rounded-2xl border p-4 transition-all duration-200 hover-lift", bg)}>
      <div className="flex items-center justify-between mb-2.5">
        <Icon className={cn("w-4 h-4", color)} />
        <span className={cn("text-2xl font-bold tabular-nums tracking-tight", color)}>{value}</span>
      </div>
      <p className="text-[13px] font-medium text-foreground/70">{label}</p>
    </div>
  );
}

function ActionItem({ title, description, icon: Icon, color, onClick, badge }: {
  title: string; description: string; icon: React.ElementType; color: string; onClick: () => void; badge?: string;
}) {
  return (
    <div onClick={onClick} className="flex items-start gap-3.5 p-4 rounded-2xl border border-border/50 cursor-pointer hover:shadow-[var(--shadow-card-hover)] hover:border-primary/15 transition-all duration-200 group bg-card">
      <div className={cn("w-10 h-10 rounded-xl flex items-center justify-center shrink-0 transition-transform duration-200 group-hover:scale-105", color)}>
        <Icon className="w-[18px] h-[18px]" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className="text-[13px] font-semibold group-hover:text-primary transition-colors duration-180">{title}</p>
          {badge && <span className="text-[10px] font-bold bg-destructive/10 text-destructive px-1.5 py-0.5 rounded-full">{badge}</span>}
        </div>
        <p className="text-[12px] text-muted-foreground/50 mt-0.5 leading-relaxed">{description}</p>
      </div>
      <ArrowRight className="w-4 h-4 text-muted-foreground/20 group-hover:text-primary/50 transition-all duration-200 shrink-0 mt-0.5 group-hover:translate-x-0.5" />
    </div>
  );
}

export default function Dashboard() {
  const { user } = useAuth();
  const { selectedSalesperson, setSelectedSalesperson } = useSalespersonFilter();
  const { data: tasks } = useTaskQueue();
  const { data: allLeads } = useDashboardLeads(500);
  const { data: pipelineHealth } = usePipelineHealth();
  const { data: execSummary } = useExecutiveSummary();
  const { data: prodScores } = useProductivity();
  const { data: inquirySummary } = useQuery<InquirySummary>({
    queryKey: ["inquiry-summary"],
    queryFn: fetchInquirySummary,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
  const navigate = useNavigate();

  const role = user?.role;
  const isMgmt = role === "Admin" || role === "Manager";
  const isProcurement = role === "Procurement";
  const isSalesperson = role === "Salesperson";

  const todayTasks = tasks?.today_capped || [];
  const overdueTasks = tasks?.overdue || [];
  const upcomingTasks = tasks?.upcoming || [];

  // ── Salesperson Dashboard ────────────────────────────────────────────
  if (isSalesperson) {
    const priorityTasks = [...overdueTasks.slice(0, 3), ...todayTasks.slice(0, 5 - Math.min(overdueTasks.length, 3))].slice(0, 5);

    return (
      <div className="p-5 lg:p-7 space-y-6 max-w-[1400px] mx-auto">
        {/* Hero */}
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-primary via-primary/90 to-primary/80 p-7 lg:p-9 text-white shadow-lg shadow-primary/10">
          <div className="absolute inset-0 opacity-[0.03]">
            <svg className="w-full h-full" viewBox="0 0 800 400">
              <defs><pattern id="g" width="60" height="60" patternUnits="userSpaceOnUse"><path d="M60 0L0 0 0 60" fill="none" stroke="white" strokeWidth="1" /></pattern></defs>
              <rect width="100%" height="100%" fill="url(#g)" />
            </svg>
          </div>
          <div className="relative z-10 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-5">
            <div className="flex-1">
              <div className="flex items-center gap-2.5 mb-3">
                <Sparkles className="w-4 h-4 text-white/60" />
                <span className="text-[11px] font-semibold text-white/55 tracking-widest uppercase">Today's Work</span>
              </div>
              <h1 className="text-2xl lg:text-[28px] font-bold tracking-tight leading-tight">{getGreeting()}, {user?.full_name?.split(" ")[0]}</h1>
              <p className="text-white/65 mt-2.5 text-[14px] max-w-lg leading-relaxed">
                {todayTasks.length > 0 || overdueTasks.length > 0 ? (
                  <>You have <span className="text-white font-semibold">{overdueTasks.length > 0 ? `${overdueTasks.length} overdue, ` : ""}{todayTasks.length} due today</span>. Start with your highest priority task below.</>
                ) : "All caught up! Check your pipeline below."}
              </p>
            </div>
            <div className="flex items-center gap-4 shrink-0">
              <div className="hidden lg:flex items-center gap-6 px-5 py-3 rounded-xl bg-white/[0.08] backdrop-blur-sm border border-white/[0.08]">
                {[
                  { label: "Overdue", value: overdueTasks.length, urgent: overdueTasks.length > 0 },
                  { label: "Today", value: todayTasks.length, urgent: false },
                  { label: "Active", value: execSummary?.active_leads || allLeads?.length || 0, urgent: false },
                ].map((s) => (
                  <div key={s.label} className="text-center">
                    <p className={cn("text-xl font-bold tabular-nums", s.urgent ? "text-amber-300" : "text-white")}>{s.value}</p>
                    <p className="text-[11px] text-white/50 font-medium mt-0.5">{s.label}</p>
                  </div>
                ))}
              </div>
              <Button onClick={() => navigate("/tasks")} className="bg-white text-primary hover:bg-white/90 shadow-lg gap-2 font-semibold" size="lg">
                <ListTodo className="w-4 h-4" />Start Working
              </Button>
            </div>
          </div>
        </div>

        {/* Context Banner */}
        {selectedSalesperson && (
          <div className="flex items-center gap-3 px-5 py-3 rounded-xl bg-blue-50 border border-blue-200 text-sm">
            <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center shrink-0"><Users className="w-4 h-4 text-blue-600" /></div>
            <div>
              <p className="font-semibold text-blue-800">Viewing <span className="underline decoration-blue-300 underline-offset-2">{selectedSalesperson}</span></p>
              <p className="text-[12px] text-blue-600/70">All data reflects this salesperson's activity</p>
            </div>
            <Button variant="ghost" size="sm" className="ml-auto text-blue-600 hover:text-blue-800 hover:bg-blue-100 gap-1 text-xs" onClick={() => setSelectedSalesperson(null)}>Clear filter</Button>
          </div>
        )}

        {/* Priorities + Pipeline */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          <div className="lg:col-span-2">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-[15px] font-semibold flex items-center gap-2 text-foreground/90">
                <ListTodo className="w-4 h-4 text-primary" />Today's Priorities
                {priorityTasks.length > 0 && <span className="text-[11px] font-medium text-muted-foreground bg-muted px-2 py-0.5 rounded-full">{priorityTasks.length}</span>}
              </h2>
              <Button variant="ghost" size="sm" onClick={() => navigate("/tasks")} className="gap-1 text-[13px]">View all <ArrowRight className="w-3.5 h-3.5" /></Button>
            </div>
            {priorityTasks.length > 0 ? (
              <div className="space-y-2">
                {priorityTasks.map((task: any) => {
                  const isLate = task.days_to < 0;
                  const isDue = task.days_to === 0;
                  return (
                    <div key={`${task.lead_id}-${task.followup_id || "t"}`} onClick={() => navigate(`/leads/${task.lead_id}`)} className={cn("group flex items-center gap-3.5 p-3.5 rounded-[14px] border bg-card cursor-pointer transition-all duration-150", isLate ? "border-red-200/60 hover:border-red-300/60 hover:shadow-sm" : "border-border/60 hover:border-primary/20 hover:shadow-sm")}>
                      <div className={cn("w-2.5 h-2.5 rounded-full shrink-0", isLate ? "bg-destructive" : isDue ? "bg-accent" : "bg-primary/40")} />
                      <div className="flex-1 min-w-0">
                        <p className="font-semibold text-[14px] truncate">{task.company_name}</p>
                        <p className="text-[12px] mt-0.5 text-muted-foreground/60 line-clamp-1">{task.next_action_plan || task.recommended_action}</p>
                      </div>
                      <span className={cn("text-[12px] font-semibold px-2 py-0.5 rounded-md shrink-0", isLate ? "bg-red-50 text-destructive" : isDue ? "bg-amber-50 text-accent" : "bg-muted text-muted-foreground/60")}>
                        {isLate ? `${Math.abs(task.days_to)}d overdue` : isDue ? "Today" : `in ${task.days_to}d`}
                      </span>
                    </div>
                  );
                })}
              </div>
            ) : (
              <Card className="border-border/60"><CardContent className="py-12 text-center"><CheckCircle2 className="w-8 h-8 text-emerald-400/50 mx-auto mb-2" /><p className="text-muted-foreground/70 font-medium">All caught up!</p></CardContent></Card>
            )}
          </div>
          <div className="space-y-4">
            <Card className="border-border/60 rounded-[14px]">
              <CardHeader className="pb-2"><CardTitle className="text-[14px] flex items-center gap-2 font-semibold"><BarChart3 className="w-4 h-4 text-primary" />Pipeline Health</CardTitle></CardHeader>
              <CardContent>
                {pipelineHealth ? (
                  <div className="space-y-3">
                    {[
                      { label: "Healthy", value: pipelineHealth.healthy, color: "bg-emerald-500", textColor: "text-emerald-600" },
                      { label: "Need Attention", value: pipelineHealth.attention_needed, color: "bg-amber-500", textColor: "text-amber-600" },
                      { label: "At Risk", value: pipelineHealth.at_risk, color: "bg-red-500", textColor: "text-red-600" },
                    ].map((s) => (
                      <div key={s.label} className="flex items-center justify-between p-3 rounded-xl bg-muted/20">
                        <div className="flex items-center gap-2.5"><div className={cn("w-2.5 h-2.5 rounded-full", s.color)} /><span className={cn("text-sm font-medium", s.textColor)}>{s.label}</span></div>
                        <span className={cn("text-lg font-bold", s.textColor)}>{s.value}</span>
                      </div>
                    ))}
                  </div>
                ) : <div className="space-y-3">{Array.from({ length: 3 }).map((_, i) => <div key={i} className="skeleton h-12 rounded-xl" />)}</div>}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    );
  }

  // ── Procurement Dashboard ────────────────────────────────────────────
  if (isProcurement) {
    const { data: inquiries } = useQuery({
      queryKey: ["dashboard", "inquiries"],
      queryFn: () => api.get("/inquiries", { params: { page_size: 50 } }).then((r) => r.data),
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    });

    const openInquiries = (inquiries || []).filter((i: any) => i.status === "OPEN");
    const eodInquiries = (inquiries || []).filter((i: any) => i.status === "EOD_COMMITTED");
    const overdueInquiries = (inquiries || []).filter((i: any) => i.status === "OVERDUE");
    const pendingInquiries = (inquiries || []).filter((i: any) => i.status === "PENDING_RESPONSE");
    const recentResponded = (inquiries || []).filter((i: any) => i.status === "RESPONDED").slice(0, 5);

    return (
      <div className="p-5 lg:p-7 space-y-6 max-w-[1400px] mx-auto">
        {/* Hero */}
        <div className="relative overflow-hidden rounded-[18px] bg-gradient-to-br from-amber-500 via-orange-500 to-orange-600 p-6 lg:p-8 text-white shadow-lg shadow-orange-100/20">
          <div className="absolute inset-0 opacity-[0.04]">
            <svg className="w-full h-full" viewBox="0 0 800 400">
              <defs><pattern id="pg" width="40" height="40" patternUnits="userSpaceOnUse"><circle cx="20" cy="20" r="1.5" fill="white" /></pattern></defs>
              <rect width="100%" height="100%" fill="url(#pg)" />
            </svg>
          </div>
          <div className="relative z-10 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
            <div className="flex-1">
              <div className="flex items-center gap-2.5 mb-2">
                <Inbox className="w-5 h-5 text-white/70" />
                <span className="text-sm font-medium text-white/70 tracking-wide uppercase">Procurement Queue</span>
              </div>
              <h1 className="text-2xl lg:text-3xl font-bold tracking-tight">{getGreeting()}, {user?.full_name?.split(" ")[0]}</h1>
              <p className="text-white/70 mt-2 text-[15px] max-w-lg leading-relaxed">
                {(openInquiries.length + eodInquiries.length + overdueInquiries.length) > 0 ? (
                  <>You have <span className="text-white font-semibold">{overdueInquiries.length > 0 ? `${overdueInquiries.length} overdue, ` : ""}{openInquiries.length + eodInquiries.length + pendingInquiries.length} pending inquiries</span>. Review and respond below.</>
                ) : "All inquiries are resolved. Great work!"}
              </p>
            </div>
            <div className="flex items-center gap-4 shrink-0">
              <div className="hidden lg:flex items-center gap-5 px-4 py-2.5 rounded-xl bg-white/10 backdrop-blur-sm">
                {[
                  { label: "Overdue", value: overdueInquiries.length, urgent: overdueInquiries.length > 0 },
                  { label: "Pending", value: openInquiries.length + eodInquiries.length + pendingInquiries.length, urgent: false },
                  { label: "Resolved Today", value: inquirySummary?.responded_today || 0, urgent: false },
                ].map((s) => (
                  <div key={s.label} className="text-center">
                    <p className={cn("text-lg font-bold", s.urgent ? "text-amber-300" : "text-white")}>{s.value}</p>
                    <p className="text-[11px] text-white/60 font-medium">{s.label}</p>
                  </div>
                ))}
              </div>
              <Button onClick={() => navigate("/inquiries")} className="bg-white text-orange-600 hover:bg-white/90 shadow-lg gap-2 font-semibold" size="lg">
                <Eye className="w-4 h-4" />View Queue
              </Button>
            </div>
          </div>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <StatCard label="Awaiting Review" value={openInquiries.length} icon={CircleDot} color="text-amber-600" bg="bg-amber-50/80 border-amber-100" />
          <StatCard label="EOD Committed" value={eodInquiries.length} icon={Flame} color="text-orange-600" bg="bg-orange-50/80 border-orange-100" />
          <StatCard label="Overdue" value={overdueInquiries.length} icon={AlertCircle} color="text-red-500" bg="bg-red-50/80 border-red-100" />
          <StatCard label="Responded Today" value={inquirySummary?.responded_today || 0} icon={CheckCircle2} color="text-emerald-600" bg="bg-emerald-50/80 border-emerald-100" />
        </div>

        {/* Urgent Queue */}
        {overdueInquiries.length > 0 && (
          <div>
            <h2 className="text-[15px] font-semibold flex items-center gap-2 text-destructive mb-3">
              <AlertCircle className="w-4 h-4" />Overdue — Needs Immediate Attention ({overdueInquiries.length})
            </h2>
            <div className="space-y-2">
              {overdueInquiries.slice(0, 5).map((inq: any) => (
                <div key={inq.id} onClick={() => navigate("/inquiries")} className="flex items-center gap-3 p-3.5 rounded-xl border border-red-200/60 bg-red-50/30 cursor-pointer hover:shadow-sm transition-all group">
                  <div className="w-2.5 h-2.5 rounded-full bg-destructive shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-sm group-hover:text-destructive transition-colors">{inq.title}</p>
                    <p className="text-xs text-muted-foreground/60">{inq.company_name || inq.lead_id} · {inq.type}</p>
                  </div>
                  <span className="text-[11px] font-semibold bg-red-100 text-red-700 px-2 py-0.5 rounded-full shrink-0">Overdue</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Pending Queue */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          <div>
            <h2 className="text-[15px] font-semibold flex items-center gap-2 text-foreground/90 mb-3">
              <Inbox className="w-4 h-4 text-amber-500" />Awaiting Review ({openInquiries.length})
            </h2>
            <div className="space-y-2">
              {openInquiries.length > 0 ? openInquiries.slice(0, 5).map((inq: any) => (
                <div key={inq.id} onClick={() => navigate("/inquiries")} className="flex items-center gap-3 p-3.5 rounded-xl border border-border/60 cursor-pointer hover:shadow-sm transition-all group">
                  <div className="w-2.5 h-2.5 rounded-full bg-amber-400 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-sm group-hover:text-primary transition-colors">{inq.title}</p>
                    <p className="text-xs text-muted-foreground/60">{inq.company_name || inq.lead_id} · {inq.type}</p>
                  </div>
                  <span className="text-[11px] font-medium text-muted-foreground">{new Date(inq.created_at).toLocaleDateString()}</span>
                </div>
              )) : (
                <Card className="border-border/60"><CardContent className="py-8 text-center"><CheckCircle2 className="w-6 h-6 text-emerald-400/50 mx-auto mb-1" /><p className="text-sm text-muted-foreground">No pending reviews</p></CardContent></Card>
              )}
            </div>
          </div>
          <div>
            <h2 className="text-[15px] font-semibold flex items-center gap-2 text-foreground/90 mb-3">
              <Flame className="w-4 h-4 text-orange-500" />EOD Committed ({eodInquiries.length})
            </h2>
            <div className="space-y-2">
              {eodInquiries.length > 0 ? eodInquiries.slice(0, 5).map((inq: any) => (
                <div key={inq.id} onClick={() => navigate("/inquiries")} className="flex items-center gap-3 p-3.5 rounded-xl border border-border/60 cursor-pointer hover:shadow-sm transition-all group">
                  <div className="w-2.5 h-2.5 rounded-full bg-orange-400 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-sm group-hover:text-primary transition-colors">{inq.title}</p>
                    <p className="text-xs text-muted-foreground/60">{inq.company_name || inq.lead_id} · {inq.type}</p>
                  </div>
                  <span className="text-[11px] font-medium text-orange-600">Due today</span>
                </div>
              )) : (
                <Card className="border-border/60"><CardContent className="py-8 text-center"><CheckCircle2 className="w-6 h-6 text-emerald-400/50 mx-auto mb-1" /><p className="text-sm text-muted-foreground">No EOD commitments</p></CardContent></Card>
              )}
            </div>
          </div>
        </div>

        {/* Pending with dates */}
        {pendingInquiries.length > 0 && (
          <div>
            <h2 className="text-[15px] font-semibold flex items-center gap-2 text-foreground/90 mb-3">
              <Clock className="w-4 h-4 text-blue-500" />Pending Response ({pendingInquiries.length})
            </h2>
            <div className="space-y-2">
              {pendingInquiries.slice(0, 5).map((inq: any) => (
                <div key={inq.id} onClick={() => navigate("/inquiries")} className="flex items-center gap-3 p-3.5 rounded-xl border border-border/60 cursor-pointer hover:shadow-sm transition-all group">
                  <div className="w-2.5 h-2.5 rounded-full bg-blue-400 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-sm group-hover:text-primary transition-colors">{inq.title}</p>
                    <p className="text-xs text-muted-foreground/60">{inq.company_name || inq.lead_id} · {inq.type}</p>
                  </div>
                  <span className="text-[11px] font-medium text-blue-600">
                    {inq.expected_response_date ? `By ${new Date(inq.expected_response_date).toLocaleDateString()}` : "Pending"}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Recently Responded */}
        {recentResponded.length > 0 && (
          <div>
            <h2 className="text-[15px] font-semibold flex items-center gap-2 text-foreground/90 mb-3">
              <CheckCircle2 className="w-4 h-4 text-emerald-500" />Recently Resolved
            </h2>
            <div className="space-y-2">
              {recentResponded.map((inq: any) => (
                <div key={inq.id} onClick={() => navigate("/inquiries")} className="flex items-center gap-3 p-3.5 rounded-xl border border-border/60 opacity-70 cursor-pointer hover:opacity-100 transition-all group">
                  <div className="w-2.5 h-2.5 rounded-full bg-emerald-400 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium">{inq.title}</p>
                    <p className="text-xs text-muted-foreground/60">{inq.company_name || inq.lead_id}</p>
                  </div>
                  <span className="text-[11px] font-medium text-emerald-600">Resolved</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  // ── Admin / Manager Dashboard ────────────────────────────────────────
  const leadsWithoutFollowup = execSummary?.leads_without_followup || 0;
  const overdueTasksCount = execSummary?.overdue_tasks || overdueTasks.length;
  const dueTodayCount = execSummary?.due_today || todayTasks.length;
  const pendingInquiriesCount = (inquirySummary?.total_open || 0) + (inquirySummary?.eod_committed || 0);
  const overdueInquiriesCount = inquirySummary?.overdue || 0;
  const stalledLeads = pipelineHealth?.stalled || 0;
  const atRiskLeads = pipelineHealth?.at_risk || 0;
  const topProducers = prodScores?.slice(0, 3) || [];

  return (
    <div className="p-5 lg:p-7 space-y-6 max-w-[1400px] mx-auto">
      {/* Hero */}
      <div className="relative overflow-hidden rounded-[18px] bg-gradient-to-br from-primary via-primary/90 to-primary/80 p-6 lg:p-8 text-white shadow-lg shadow-primary/10">
        <div className="absolute inset-0 opacity-[0.03]">
          <svg className="w-full h-full" viewBox="0 0 800 400">
            <defs><pattern id="g" width="60" height="60" patternUnits="userSpaceOnUse"><path d="M60 0L0 0 0 60" fill="none" stroke="white" strokeWidth="1" /></pattern></defs>
            <rect width="100%" height="100%" fill="url(#g)" />
          </svg>
        </div>
        <div className="relative z-10 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-2.5 mb-2">
              <Sparkles className="w-5 h-5 text-white/70" />
              <span className="text-sm font-medium text-white/70 tracking-wide uppercase">Management Overview</span>
            </div>
            <h1 className="text-2xl lg:text-3xl font-bold tracking-tight">{getGreeting()}, {user?.full_name?.split(" ")[0]}</h1>
            <p className="text-white/70 mt-2 text-[15px] max-w-lg leading-relaxed">
              {(overdueTasksCount + leadsWithoutFollowup + pendingInquiriesCount + overdueInquiriesCount) > 0 ? (
                <>You have <span className="text-white font-semibold">{overdueTasksCount} overdue tasks, {leadsWithoutFollowup} leads without follow-up</span>, and <span className="text-white font-semibold">{pendingInquiriesCount + overdueInquiriesCount} pending inquiries</span>.</>
              ) : "Everything is on track. No action items need attention."}
            </p>
          </div>
          <div className="flex items-center gap-4 shrink-0">
            <div className="hidden lg:flex items-center gap-5 px-4 py-2.5 rounded-xl bg-white/10 backdrop-blur-sm">
              {[
                { label: "Overdue", value: overdueTasksCount, urgent: overdueTasksCount > 0 },
                { label: "No Follow-up", value: leadsWithoutFollowup, urgent: leadsWithoutFollowup > 0 },
                { label: "Active", value: execSummary?.active_leads || 0, urgent: false },
              ].map((s) => (
                <div key={s.label} className="text-center">
                  <p className={cn("text-lg font-bold", s.urgent ? "text-amber-300" : "text-white")}>{s.value}</p>
                  <p className="text-[11px] text-white/60 font-medium">{s.label}</p>
                </div>
              ))}
            </div>
            <Button onClick={() => navigate("/team")} className="bg-white text-primary hover:bg-white/90 shadow-lg gap-2 font-semibold" size="lg">
              <BarChart3 className="w-4 h-4" />View Analytics
            </Button>
          </div>
        </div>
      </div>

      {/* Context Banner */}
      {selectedSalesperson && (
        <div className="flex items-center gap-3 px-5 py-3 rounded-xl bg-blue-50 border border-blue-200 text-sm">
          <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center shrink-0"><Users className="w-4 h-4 text-blue-600" /></div>
          <div>
            <p className="font-semibold text-blue-800">Viewing <span className="underline decoration-blue-300 underline-offset-2">{selectedSalesperson}</span></p>
            <p className="text-[12px] text-blue-600/70">All data reflects this salesperson's activity</p>
          </div>
          <Button variant="ghost" size="sm" className="ml-auto text-blue-600 hover:text-blue-800 hover:bg-blue-100 gap-1 text-xs" onClick={() => setSelectedSalesperson(null)}>Clear filter</Button>
        </div>
      )}

      {/* Action Items */}
      <div>
        <h2 className="text-[15px] font-semibold flex items-center gap-2 text-foreground/90 mb-3">
          <AlertTriangle className="w-4 h-4 text-amber-500" />Action Items
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <ActionItem title={`${overdueTasksCount} Overdue Tasks`} description="Follow-ups past their due date" icon={Clock} color="bg-red-50 text-red-600" onClick={() => navigate("/tasks")} badge={overdueTasksCount > 0 ? String(overdueTasksCount) : undefined} />
          <ActionItem title={`${leadsWithoutFollowup} No Follow-up`} description="Leads with no scheduled follow-up" icon={AlertCircle} color="bg-amber-50 text-amber-600" onClick={() => navigate("/team")} badge={leadsWithoutFollowup > 0 ? String(leadsWithoutFollowup) : undefined} />
          <ActionItem title={`${stalledLeads + atRiskLeads} At Risk / Stalled`} description="Leads needing attention" icon={Timer} color="bg-orange-50 text-orange-600" onClick={() => navigate("/team")} badge={(stalledLeads + atRiskLeads) > 0 ? String(stalledLeads + atRiskLeads) : undefined} />
          <ActionItem title={`${pendingInquiriesCount + overdueInquiriesCount} Pending Inquiries`} description="Open or overdue procurement inquiries" icon={MessageSquare} color="bg-blue-50 text-blue-600" onClick={() => navigate("/inquiries")} badge={(pendingInquiriesCount + overdueInquiriesCount) > 0 ? String(pendingInquiriesCount + overdueInquiriesCount) : undefined} />
        </div>
      </div>

      {/* Two-column: Pipeline Health + Summary */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <Card className="border-border/60 rounded-[14px]">
          <CardHeader className="pb-2"><CardTitle className="text-[14px] flex items-center gap-2 font-semibold"><BarChart3 className="w-4 h-4 text-primary" />Pipeline Health</CardTitle></CardHeader>
          <CardContent>
            {pipelineHealth ? (
              <div className="space-y-3">
                {[
                  { label: "Healthy", value: pipelineHealth.healthy, color: "bg-emerald-500", textColor: "text-emerald-600", icon: <CheckCircle2 className="w-4 h-4" /> },
                  { label: "Need Attention", value: pipelineHealth.attention_needed, color: "bg-amber-500", textColor: "text-amber-600", icon: <AlertTriangle className="w-4 h-4" /> },
                  { label: "At Risk", value: pipelineHealth.at_risk, color: "bg-red-500", textColor: "text-red-600", icon: <Timer className="w-4 h-4" /> },
                  { label: "Stalled", value: pipelineHealth.stalled, color: "bg-slate-400", textColor: "text-slate-600", icon: <Clock className="w-4 h-4" /> },
                ].map((s) => (
                  <div key={s.label} className="flex items-center justify-between p-3 rounded-xl bg-muted/20">
                    <div className="flex items-center gap-2.5"><div className={cn("w-2.5 h-2.5 rounded-full", s.color)} /><span className={cn("text-sm font-medium", s.textColor)}>{s.label}</span></div>
                    <span className={cn("text-lg font-bold", s.textColor)}>{s.value}</span>
                  </div>
                ))}
                {pipelineHealth.total > 0 && (
                  <div className="flex gap-1 h-2 rounded-full overflow-hidden">
                    {[
                      { value: pipelineHealth.healthy, color: "bg-emerald-500" },
                      { value: pipelineHealth.attention_needed, color: "bg-amber-500" },
                      { value: pipelineHealth.at_risk, color: "bg-red-500" },
                      { value: pipelineHealth.stalled, color: "bg-slate-400" },
                    ].map((s, i) => s.value > 0 && <div key={i} className={s.color} style={{ width: `${(s.value / pipelineHealth.total) * 100}%` }} />)}
                  </div>
                )}
              </div>
            ) : <div className="space-y-3">{Array.from({ length: 4 }).map((_, i) => <div key={i} className="skeleton h-12 rounded-xl" />)}</div>}
          </CardContent>
        </Card>

        <Card className="border-border/60 rounded-[14px]">
          <CardHeader className="pb-2"><CardTitle className="text-[14px] flex items-center gap-2 font-semibold"><Target className="w-4 h-4 text-primary" />Pipeline Summary</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <SummaryRow label="Total Leads" value={execSummary?.total_leads || 0} />
            <SummaryRow label="Active Pipeline" value={execSummary?.active_leads || 0} color="text-primary" />
            <SummaryRow label="Converted" value={execSummary?.won || 0} color="text-emerald-600" />
            <SummaryRow label="Conversion Rate" value={`${execSummary?.conversion_rate || 0}%`} color="text-primary" />
            <SummaryRow label="Avg Deal Value" value={`$${(execSummary?.avg_deal_value || 0).toLocaleString()}`} color="text-blue-600" />
            <SummaryRow label="Activities (30d)" value={execSummary?.activities_30d || 0} />
          </CardContent>
        </Card>

        <Card className="border-border/60 rounded-[14px]">
          <CardHeader className="pb-2"><CardTitle className="text-[14px] flex items-center gap-2 font-semibold"><MessageSquare className="w-4 h-4 text-primary" />Inquiry Status</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <SummaryRow label="Open" value={inquirySummary?.total_open || 0} color="text-amber-600" />
            <SummaryRow label="EOD Committed" value={inquirySummary?.eod_committed || 0} color="text-orange-600" />
            <SummaryRow label="Pending Response" value={inquirySummary?.pending_response || 0} color="text-blue-600" />
            <SummaryRow label="Overdue" value={inquirySummary?.overdue || 0} color="text-destructive" />
            <SummaryRow label="Responded Today" value={inquirySummary?.responded_today || 0} color="text-emerald-600" />
          </CardContent>
        </Card>
      </div>

      {/* Top Producers */}
      {topProducers.length > 0 && (
        <div>
          <h2 className="text-[15px] font-semibold flex items-center gap-2 text-foreground/90 mb-3">
            <TrendingUp className="w-4 h-4 text-primary" />Top Producers
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {topProducers.map((p, i) => (
              <Card key={p.assigned_to} className={cn("rounded-[14px]", i === 0 ? "ring-2 ring-amber-400/50" : "border-border/60")}>
                <CardContent className="p-4 flex items-center gap-3">
                  <div className={cn("w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold text-white shrink-0", i === 0 ? "bg-gradient-to-br from-amber-500 to-orange-600" : "bg-gradient-to-br from-primary/60 to-primary")}>
                    {p.assigned_to.charAt(0)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{p.assigned_to}</p>
                    <div className="flex items-center gap-2 mt-0.5">
                      <div className="h-1.5 rounded-full flex-1 bg-muted overflow-hidden">
                        <div className={cn("h-full rounded-full", p.score >= 70 ? "bg-green-500" : p.score >= 40 ? "bg-amber-500" : "bg-muted-foreground/30")} style={{ width: `${p.score}%` }} />
                      </div>
                      <span className={cn("text-xs font-bold", p.score >= 70 ? "text-green-600" : "text-amber-600")}>{p.score}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

const SummaryRow = React.memo(function SummaryRow({
  label, value, color = "text-foreground",
}: { label: string; value: string | number; color?: string }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-muted-foreground/70">{label}</span>
      <span className={cn("font-semibold", color)}>{value}</span>
    </div>
  );
});
