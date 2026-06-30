import React, { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  PieChart, Pie, Cell,
  Tooltip, ResponsiveContainer, Legend,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  LineChart, Line,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle, MetricCard } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { SkeletonChart } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import api from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useSalespersonFilter } from "@/lib/salespersonContext";
import {
  useExecutiveSummary, useConversionFunnel, usePipelineStages,
  useFollowupDiscipline, useActivityAnalytics, useInquiryAnalytics,
  useProductivity, useTeamComparison, useTrends,
} from "@/hooks/useAnalytics";
import {
  BarChart3, TrendingUp, Clock,
  CheckCircle2, Activity, Users, Target, Phone, Mail,
  AlertTriangle, MessageSquare, Download, Calendar,
} from "lucide-react";

const PIE_COLORS = ["#22c55e", "#eab308", "#3b82f6", "#f97316", "#8b5cf6", "#ec4899", "#14b8a6", "#ef4444", "#6366f1"];

const tooltipStyle = {
  background: "hsl(0 0% 100%)",
  border: "1px solid hsl(0 0% 90%)",
  borderRadius: "8px",
  fontSize: "13px",
  boxShadow: "0 4px 12px rgba(0,0,0,0.08)",
};

export default function Analytics() {
  const { user } = useAuth();
  const { selectedSalesperson } = useSalespersonFilter();
  const isSalesperson = user?.role === "Salesperson";
  const myName = user?.full_name || "";
  const [startDate, setStartDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() - 30);
    return d.toISOString().split("T")[0];
  });
  const [endDate, setEndDate] = useState(() => new Date().toISOString().split("T")[0]);

  const { data: execSummary, isLoading: execLoading } = useExecutiveSummary();
  const { data: funnel, isLoading: funnelLoading } = useConversionFunnel();
  const { data: stages, isLoading: stagesLoading } = usePipelineStages();
  const { data: fuDisc, isLoading: fuLoading } = useFollowupDiscipline();
  const { data: activity, isLoading: actLoading } = useActivityAnalytics();
  const { data: inquiry, isLoading: inqLoading } = useInquiryAnalytics(!isSalesperson);
  const { data: prodScores, isLoading: prodLoading } = useProductivity();
  const { data: teamComp, isLoading: teamLoading } = useTeamComparison();
  const { data: trends } = useTrends();
  const [weekStart, setWeekStart] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() - d.getDay());
    return d.toISOString().split("T")[0];
  });
  const [weekEnd, setWeekEnd] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() - d.getDay() + 6);
    return d.toISOString().split("T")[0];
  });
  const { data: leads } = useQuery({
    queryKey: ["analytics", "export-leads", selectedSalesperson],
    queryFn: () => api.get("/dashboard/leads", { params: { limit: 2000, ...(selectedSalesperson ? { salesperson: selectedSalesperson } : {}) } }).then((r) => r.data.items),
    staleTime: 60_000,
    refetchOnWindowFocus: false,
  });

  const filteredLeads = useMemo(() => {
    if (!leads) return [];
    return leads.filter((l: any) => {
      const d = l.created_date || l.created_at;
      if (!d) return true;
      return d >= startDate && d <= endDate;
    });
  }, [leads, startDate, endDate]);

  const exportCsv = (data: any[], filename: string) => {
    const headers = ["Lead ID", "Company", "Contact", "Phone", "Email", "Country", "Status", "Source", "Priority", "Score", "Created", "Salesperson", "Interest", "Deal Value", "Requirements"];
    const rows = data.map((l: any) =>
      [l.lead_id, l.company_name, l.contact_person, l.phone, l.email, l.country, l.status, l.lead_source, l.priority_level, l.lead_score, l.created_date, l.assigned_to, l.interest_level, l.potential_deal_value, l.customer_requirements]
        .map((v) => `"${v ?? ""}"`)
        .join(",")
    );
    const csv = [headers.join(","), ...rows].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const scope = selectedSalesperson ? selectedSalesperson.replace(/\s+/g, "_").toLowerCase() : "all_team";
  const today = new Date().toISOString().split("T")[0];

  const funnelData = (funnel || []).map((f) => ({ name: f.stage, value: f.count }));

  // Weekly Review data (for salesperson)
  const { data: weeklyLeads, isLoading: weeklyLoading } = useQuery({
    queryKey: ["analytics", "weekly-review", weekStart, weekEnd],
    queryFn: () => api.get("/dashboard/leads", { params: { limit: 2000 } }).then((r) => r.data.items),
    staleTime: 30_000,
    refetchOnWindowFocus: false,
    enabled: isSalesperson,
  });

  const filteredWeeklyLeads = useMemo(() => {
    if (!weeklyLeads) return [];
    return weeklyLeads.filter((l: any) => {
      const d = l.created_date || l.created_at;
      if (!d) return true;
      return d >= weekStart && d <= weekEnd;
    });
  }, [weeklyLeads, weekStart, weekEnd]);

  const WEEKLY_STATUSES = ["Prospect", "Requirement Qualified", "Technical Discussion", "Quotation Sent", "Sample Sent", "Negotiation", "Trial Order", "Nurturing", "Order Closed", "Lost"];
  const STATUS_COLORS: Record<string, string> = {
    "Prospect": "#94a3b8", "Requirement Qualified": "#3b82f6",
    "Technical Discussion": "#06b6d4", "Quotation Sent": "#10b981",
    "Sample Sent": "#84cc16", "Negotiation": "#f59e0b",
    "Trial Order": "#f97316", "Nurturing": "#a855f7",
    "Order Closed": "#22c55e", "Lost": "#ef4444",
  };
  const TREND_COLORS = ["hsl(142 76% 36%)", "hsl(200 60% 50%)", "hsl(30 80% 55%)", "hsl(340 80% 55%)"];

  const statusCounts = WEEKLY_STATUSES.map((s) => ({
    status: s,
    count: filteredWeeklyLeads.filter((l: any) => l.status === s).length,
  }));
  const weeklyTotal = statusCounts.reduce((a, s) => a + s.count, 0);

  const trendChartData = useMemo(() => {
    if (!trends) return [];
    return (["7d", "30d", "90d"] as const).map((p) => ({
      period: p,
      "Leads Created": trends[p]?.leads_created || 0,
      "Tasks Done": trends[p]?.tasks_completed || 0,
      "Activities": trends[p]?.activities || 0,
      "Converted": trends[p]?.converted || 0,
    }));
  }, [trends]);
  return (
    <div className="p-6 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
            <BarChart3 className="w-4 h-4" />
            <span>Performance analytics{selectedSalesperson ? ` · ${selectedSalesperson}` : ""}</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight">Analytics</h1>
        </div>
      </div>

      {/* Date Range + Export */}
      <Card className="border-border/60">
        <CardContent className="p-4">
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4 text-muted-foreground" />
              <span className="text-sm font-medium">Date Range</span>
            </div>
            <div className="flex items-center gap-3">
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="h-9 px-3 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
              <span className="text-muted-foreground">—</span>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="h-9 px-3 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
              <span className="text-xs text-muted-foreground">{filteredLeads.length} leads in range</span>
            </div>
            <div className="flex items-center gap-2 ml-auto">
              <Button
                onClick={() => exportCsv(leads || [], `analytics_${scope}_full_${today}.csv`)}
                disabled={!leads}
                variant="outline"
                size="sm"
                className="gap-2"
              >
                <Download className="w-3.5 h-3.5" />
                Full Export
              </Button>
              <Button
                onClick={() => exportCsv(filteredLeads, `analytics_${scope}_${startDate}_to_${endDate}.csv`)}
                disabled={!leads}
                size="sm"
                className="gap-2"
              >
                <Download className="w-3.5 h-3.5" />
                Export Range
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 1. Performance KPIs */}
      <Section title="Performance KPIs" icon={<BarChart3 className="w-4 h-4" />}>
        {execLoading ? <SkeletonChart /> : execSummary ? (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <MetricCard title="Total Leads" value={execSummary.total_leads} subtitle="In scope" icon={<Users className="w-4 h-4" />} />
            <MetricCard title="Won" value={execSummary.won} subtitle="Closed deals" color="text-green-600" icon={<CheckCircle2 className="w-4 h-4" />} />
            <MetricCard title="Conversion" value={`${execSummary.conversion_rate}%`} subtitle="Close rate" color="text-primary" icon={<TrendingUp className="w-4 h-4" />} />
            <MetricCard title="Avg Deal" value={`$${execSummary.avg_deal_value.toLocaleString()}`} subtitle="Estimated value" color="text-blue-600" icon={<Target className="w-4 h-4" />} />
          </div>
        ) : <Empty />}
      </Section>

      {/* 2. Activity Analytics */}
      <Section title="Activity Analytics (30d)" icon={<Activity className="w-4 h-4" />}>
        {actLoading ? <SkeletonChart /> : activity ? (
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
            <MetricCard title="Total" value={activity.total_activities} subtitle="All activities" icon={<Activity className="w-4 h-4" />} />
            <MetricCard title="Calls" value={activity.calls} icon={<Phone className="w-4 h-4" />} />
            <MetricCard title="WhatsApp" value={activity.whatsapp} icon={<MessageSquare className="w-4 h-4" />} />
            <MetricCard title="Emails" value={activity.emails} icon={<Mail className="w-4 h-4" />} />
            <MetricCard title="Meetings" value={activity.meetings} icon={<Users className="w-4 h-4" />} />
            <MetricCard title="Follow-ups" value={activity.followups} icon={<Clock className="w-4 h-4" />} />
            <MetricCard title="Avg/Day" value={activity.avg_per_day} subtitle="Daily average" icon={<TrendingUp className="w-4 h-4" />} />
          </div>
        ) : <Empty />}
      </Section>

      {/* 3. Conversion Funnel */}
      <Section title="Conversion Funnel" icon={<TrendingUp className="w-4 h-4" />}>
        {funnelLoading ? <SkeletonChart /> : funnelData.length > 0 ? (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie data={funnelData} cx="50%" cy="50%" outerRadius={100} innerRadius={50} dataKey="value" paddingAngle={2}>
                  {funnelData.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} stroke="transparent" />)}
                </Pie>
                <Tooltip contentStyle={tooltipStyle} />
                <Legend iconType="circle" iconSize={8} formatter={(v) => <span className="text-sm text-muted-foreground">{v}</span>} />
              </PieChart>
            </ResponsiveContainer>
            <div className="space-y-2">
              {funnelData.map((f, i) => {
                const pct = funnelData[0]?.value ? ((f.value / funnelData[0].value) * 100).toFixed(1) : "0";
                return (
                  <div key={f.name} className="flex items-center gap-3 text-sm">
                    <div className="w-3 h-3 rounded-full shrink-0" style={{ backgroundColor: PIE_COLORS[i % PIE_COLORS.length] }} />
                    <span className="w-48 truncate font-medium">{f.name}</span>
                    <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                      <div className="h-full rounded-full" style={{ width: `${pct}%`, backgroundColor: PIE_COLORS[i % PIE_COLORS.length] }} />
                    </div>
                    <span className="font-semibold w-12 text-right">{f.value}</span>
                  </div>
                );
              })}
            </div>
          </div>
        ) : <Empty />}
      </Section>

      {/* 4. Pipeline Stages */}
      <Section title="Pipeline Stage Analytics" icon={<BarChart3 className="w-4 h-4" />}>
        {stagesLoading ? <SkeletonChart /> : stages && stages.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-muted-foreground">
                  <th className="text-left py-2 px-3 font-medium">Stage</th>
                  <th className="text-right py-2 px-3 font-medium">Count</th>
                  <th className="text-right py-2 px-3 font-medium">Avg Days</th>
                  <th className="text-right py-2 px-3 font-medium">Avg Value</th>
                </tr>
              </thead>
              <tbody>
                {stages.map((s) => (
                  <tr key={s.stage} className="border-b last:border-0 hover:bg-muted/30">
                    <td className="py-2 px-3 font-medium">{s.stage}</td>
                    <td className="py-2 px-3 text-right">{s.count}</td>
                    <td className="py-2 px-3 text-right">{s.avg_days_in_stage}d</td>
                    <td className="py-2 px-3 text-right">${s.avg_deal_value.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : <Empty />}
      </Section>

      {/* 5. Follow-Up Discipline */}
      <Section title="Follow-Up Discipline (30d)" icon={<Clock className="w-4 h-4" />}>
        {fuLoading ? <SkeletonChart /> : fuDisc ? (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <MetricCard title="Total" value={fuDisc.total_followups} subtitle="Follow-ups" icon={<Activity className="w-4 h-4" />} />
            <MetricCard title="Completed" value={fuDisc.completed} subtitle={`${fuDisc.completion_pct}% rate`} color="text-green-600" icon={<CheckCircle2 className="w-4 h-4" />} />
            <MetricCard title="Overdue" value={fuDisc.overdue} subtitle={fuDisc.overdue > 0 ? "Needs attention" : "All clear"} color={fuDisc.overdue > 0 ? "text-destructive" : "text-muted-foreground"} icon={<AlertTriangle className="w-4 h-4" />} />
            <MetricCard title="Completion" value={`${fuDisc.completion_pct}%`} subtitle="Rate" color={fuDisc.completion_pct >= 70 ? "text-green-600" : "text-amber-600"} icon={<TrendingUp className="w-4 h-4" />} />
          </div>
        ) : <Empty />}
      </Section>

      {/* 6. Inquiry Analytics */}
      {inquiry && (
        <Section title="Inquiry Analytics" icon={<MessageSquare className="w-4 h-4" />}>
          {inqLoading ? <SkeletonChart /> : (
            <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
              <MetricCard title="Total" value={inquiry.total_inquiries} icon={<MessageSquare className="w-4 h-4" />} />
              <MetricCard title="Open" value={inquiry.open} color="text-blue-600" icon={<Activity className="w-4 h-4" />} />
              <MetricCard title="EOD Committed" value={inquiry.eod_committed} color="text-amber-600" icon={<Clock className="w-4 h-4" />} />
              <MetricCard title="Overdue" value={inquiry.overdue} color={inquiry.overdue > 0 ? "text-destructive" : "text-muted-foreground"} icon={<AlertTriangle className="w-4 h-4" />} />
              <MetricCard title="Responded" value={inquiry.responded} color="text-green-600" icon={<CheckCircle2 className="w-4 h-4" />} />
              <MetricCard title="SLA" value={`${inquiry.response_sla_pct}%`} subtitle="Response rate" color="text-primary" icon={<Target className="w-4 h-4" />} />
            </div>
          )}
        </Section>
      )}

      {/* 7. Productivity Score (salesperson sees only their own) */}
      <Section title={isSalesperson ? "My Productivity Score" : "Productivity Scores"} icon={<Target className="w-4 h-4" />}>
        {prodLoading ? <SkeletonChart /> : prodScores && prodScores.length > 0 ? (
          isSalesperson ? (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {prodScores.filter((p) => p.assigned_to === myName).slice(0, 1).map((p) => (
                <Card key={p.assigned_to} className="border-border/60">
                  <CardContent className="p-5 text-center">
                    <p className="text-sm text-muted-foreground mb-1">{p.assigned_to}</p>
                    <p className={cn("text-4xl font-bold", p.score >= 70 ? "text-green-600" : p.score >= 40 ? "text-amber-600" : "text-muted-foreground")}>
                      {p.score}
                    </p>
                    <div className="mt-3 h-2 bg-muted rounded-full overflow-hidden">
                      <div className={cn("h-full rounded-full", p.score >= 70 ? "bg-green-500" : p.score >= 40 ? "bg-amber-500" : "bg-muted-foreground/30")}
                        style={{ width: `${p.score}%` }} />
                    </div>
                    <p className="text-xs text-muted-foreground mt-2">
                      {p.score >= 70 ? "Great performance!" : p.score >= 40 ? "Keep pushing!" : "Room for improvement"}
                    </p>
                  </CardContent>
                </Card>
              )) || <Empty />}
            </div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
              {prodScores.slice(0, 12).map((p) => (
                <Card key={p.assigned_to} className="border-border/60">
                  <CardContent className="p-4 text-center">
                    <p className="text-xs text-muted-foreground mb-1">{p.assigned_to}</p>
                    <p className={cn("text-2xl font-bold", p.score >= 70 ? "text-green-600" : p.score >= 40 ? "text-amber-600" : "text-muted-foreground")}>
                      {p.score}
                    </p>
                    <div className="mt-2 h-1.5 bg-muted rounded-full overflow-hidden">
                      <div className={cn("h-full rounded-full", p.score >= 70 ? "bg-green-500" : p.score >= 40 ? "bg-amber-500" : "bg-muted-foreground/30")}
                        style={{ width: `${p.score}%` }} />
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )
        ) : <Empty />}
      </Section>

      {/* ── Weekly Review (Salesperson only) ──────────────────────────── */}
      {isSalesperson && (
        <>
          {/* Pipeline Funnel + Date Range — FIRST */}
          <Section title="Pipeline Funnel" icon={<BarChart3 className="w-4 h-4" />}>
            <Card className="border-border/40">
              <CardContent className="pt-5">
                <div className="flex items-center gap-3 mb-4">
                  <Calendar className="w-4 h-4 text-muted-foreground" />
                  <input type="date" value={weekStart} onChange={(e) => setWeekStart(e.target.value)} className="h-9 px-3 rounded-xl border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/15" />
                  <span className="text-muted-foreground">—</span>
                  <input type="date" value={weekEnd} onChange={(e) => setWeekEnd(e.target.value)} className="h-9 px-3 rounded-xl border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/15" />
                  <span className="text-xs text-muted-foreground ml-auto">{weeklyTotal} leads</span>
                </div>
                {weeklyLoading ? <SkeletonChart /> : (
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={statusCounts} margin={{ top: 10, right: 10, left: 0, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(0 0% 93%)" vertical={false} />
                      <XAxis dataKey="status" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
                      <YAxis axisLine={false} tickLine={false} />
                      <Tooltip contentStyle={{ background: "hsl(0 0% 100%)", border: "1px solid hsl(0 0% 90%)", borderRadius: "8px", fontSize: "13px" }} />
                      <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={60}>
                        {statusCounts.map((entry) => (
                          <Cell key={entry.status} fill={STATUS_COLORS[entry.status] || "#94a3b8"} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </CardContent>
            </Card>
          </Section>

          {/* Activity Trends — SECOND */}
          {trendChartData.length > 0 && (
            <Section title="Activity Trends (7/30/90 Day)" icon={<TrendingUp className="w-4 h-4" />}>
              <Card className="border-border/40">
                <CardContent className="pt-5">
                  <div className="space-y-4">
                    <ResponsiveContainer width="100%" height={220}>
                      <LineChart data={trendChartData} margin={{ top: 10, right: 20, left: 0, bottom: 5 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="hsl(0 0% 93%)" vertical={false} />
                        <XAxis dataKey="period" tick={{ fontSize: 12 }} axisLine={false} tickLine={false} />
                        <YAxis axisLine={false} tickLine={false} />
                        <Tooltip contentStyle={{ background: "hsl(0 0% 100%)", border: "1px solid hsl(0 0% 90%)", borderRadius: "8px", fontSize: "13px" }} />
                        <Legend iconType="circle" iconSize={8} />
                        <Line type="monotone" dataKey="Leads Created" stroke={TREND_COLORS[0]} strokeWidth={2} dot={{ r: 4 }} />
                        <Line type="monotone" dataKey="Tasks Done" stroke={TREND_COLORS[1]} strokeWidth={2} dot={{ r: 4 }} />
                        <Line type="monotone" dataKey="Activities" stroke={TREND_COLORS[2]} strokeWidth={2} dot={{ r: 4 }} />
                        <Line type="monotone" dataKey="Converted" stroke={TREND_COLORS[3]} strokeWidth={2} dot={{ r: 4 }} />
                      </LineChart>
                    </ResponsiveContainer>
                    {trends && (
                      <div className="grid grid-cols-3 gap-3">
                        {([
                          { label: "7-Day", key: "7d" },
                          { label: "30-Day", key: "30d" },
                          { label: "90-Day", key: "90d" },
                        ] as const).map((m) => (
                          <div key={m.label} className="rounded-xl bg-muted/30 p-3 text-center">
                            <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">{m.label}</p>
                            <div className="mt-2 space-y-1 text-sm">
                              <div className="flex justify-between"><span className="text-muted-foreground/70">Leads</span><span className="font-semibold">{trends[m.key]?.leads_created || 0}</span></div>
                              <div className="flex justify-between"><span className="text-muted-foreground/70">Tasks</span><span className="font-semibold">{trends[m.key]?.tasks_completed || 0}</span></div>
                              <div className="flex justify-between"><span className="text-muted-foreground/70">Conv</span><span className="font-semibold">{trends[m.key]?.converted || 0}</span></div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            </Section>
          )}

          {/* Status Grid */}
          <Section title="Pipeline by Status" icon={<Target className="w-4 h-4" />}>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
              {statusCounts.map(({ status, count }) => (
                <Card key={status} className="border-border/40 hover-lift">
                  <CardContent className="p-4 text-center">
                    <p className="text-[12px] text-muted-foreground/60 mb-1">{status}</p>
                    <p className="text-3xl font-bold tracking-tight" style={{ color: STATUS_COLORS[status] || "#94a3b8" }}>
                      {count}
                    </p>
                  </CardContent>
                </Card>
              ))}
            </div>
          </Section>
        </>
      )}

      {/* 8. Team Comparison (always at bottom) */}
      <Section title="Team Comparison" icon={<Users className="w-4 h-4" />}>
        {teamLoading ? <SkeletonChart /> : teamComp && teamComp.length > 0 ? (
          <Card className="border-border/60">
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b bg-muted/30">
                      <th className="text-left py-3 px-4 font-semibold text-muted-foreground/60 text-[11px] uppercase">Salesperson</th>
                      <th className="text-right py-3 px-4 font-semibold text-muted-foreground/60 text-[11px] uppercase">Leads</th>
                      <th className="text-right py-3 px-4 font-semibold text-muted-foreground/60 text-[11px] uppercase">Active</th>
                      <th className="text-right py-3 px-4 font-semibold text-muted-foreground/60 text-[11px] uppercase">Won</th>
                      <th className="text-right py-3 px-4 font-semibold text-muted-foreground/60 text-[11px] uppercase">Conv%</th>
                      <th className="text-right py-3 px-4 font-semibold text-muted-foreground/60 text-[11px] uppercase">Eng 30d</th>
                      <th className="text-right py-3 px-4 font-semibold text-muted-foreground/60 text-[11px] uppercase">Overdue</th>
                    </tr>
                  </thead>
                  <tbody>
                    {teamComp.map((t) => (
                      <tr key={t.assigned_to} className={cn("border-b last:border-0 hover:bg-muted/20 transition-colors", isSalesperson && t.assigned_to === myName && "bg-primary/[0.04]")}>
                        <td className="py-3 px-4 font-medium">
                          {t.assigned_to}
                          {isSalesperson && t.assigned_to === myName && <span className="ml-1.5 text-[10px] font-semibold text-primary bg-primary/10 px-1.5 py-0.5 rounded-full">You</span>}
                        </td>
                        <td className="py-3 px-4 text-right">{t.total_leads}</td>
                        <td className="py-3 px-4 text-right">{t.active_leads}</td>
                        <td className="py-3 px-4 text-right text-green-600">{t.won}</td>
                        <td className="py-3 px-4 text-right">{t.conversion_rate}%</td>
                        <td className="py-3 px-4 text-right">{t.engagement_30d}</td>
                        <td className={cn("py-3 px-4 text-right", t.overdue_tasks > 0 ? "text-destructive font-semibold" : "")}>{t.overdue_tasks}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        ) : <Empty />}
      </Section>
    </div>
  );
}

function Section({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <div>
      <h2 className="text-[15px] font-semibold flex items-center gap-2 text-foreground/90 mb-3">{icon}{title}</h2>
      {children}
    </div>
  );
}

function Empty() {
  return <p className="text-center text-muted-foreground py-8 text-sm">No data available</p>;
}
