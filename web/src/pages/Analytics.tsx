import React, { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  PieChart, Pie, Cell,
  Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle, MetricCard } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { SkeletonChart } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import api from "@/lib/api";
import { useSalespersonFilter } from "@/lib/salespersonContext";
import {
  useExecutiveSummary, useConversionFunnel, usePipelineStages,
  useFollowupDiscipline, useActivityAnalytics, useInquiryAnalytics,
  useProductivity, useTeamComparison,
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
  const { selectedSalesperson } = useSalespersonFilter();
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
  const { data: inquiry, isLoading: inqLoading } = useInquiryAnalytics();
  const { data: prodScores, isLoading: prodLoading } = useProductivity();
  const { data: teamComp, isLoading: teamLoading } = useTeamComparison();
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

      {/* 7. Lead Health Summary */}
      <Section title="Productivity Scores" icon={<Target className="w-4 h-4" />}>
        {prodLoading ? <SkeletonChart /> : prodScores && prodScores.length > 0 ? (
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
        ) : <Empty />}
      </Section>

      {/* 8. Team Comparison */}
      <Section title="Team Comparison" icon={<Users className="w-4 h-4" />}>
        {teamLoading ? <SkeletonChart /> : teamComp && teamComp.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-muted-foreground">
                  <th className="text-left py-2 px-3 font-medium">Salesperson</th>
                  <th className="text-right py-2 px-3 font-medium">Leads</th>
                  <th className="text-right py-2 px-3 font-medium">Active</th>
                  <th className="text-right py-2 px-3 font-medium">Won</th>
                  <th className="text-right py-2 px-3 font-medium">Conv%</th>
                  <th className="text-right py-2 px-3 font-medium">Tasks Done</th>
                  <th className="text-right py-2 px-3 font-medium">Task%</th>
                  <th className="text-right py-2 px-3 font-medium">Eng 30d</th>
                  <th className="text-right py-2 px-3 font-medium">Overdue</th>
                </tr>
              </thead>
              <tbody>
                {teamComp.map((t) => (
                  <tr key={t.assigned_to} className="border-b last:border-0 hover:bg-muted/30">
                    <td className="py-2 px-3 font-medium">{t.assigned_to}</td>
                    <td className="py-2 px-3 text-right">{t.total_leads}</td>
                    <td className="py-2 px-3 text-right">{t.active_leads}</td>
                    <td className="py-2 px-3 text-right text-green-600">{t.won}</td>
                    <td className="py-2 px-3 text-right">{t.conversion_rate}%</td>
                    <td className="py-2 px-3 text-right">{t.completed_tasks}</td>
                    <td className="py-2 px-3 text-right">{t.task_completion_pct}%</td>
                    <td className="py-2 px-3 text-right">{t.engagement_30d}</td>
                    <td className={cn("py-2 px-3 text-right", t.overdue_tasks > 0 ? "text-destructive font-semibold" : "")}>{t.overdue_tasks}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
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
