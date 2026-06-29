import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  PieChart, Pie, Cell,
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle, MetricCard } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { SkeletonChart } from "@/components/ui/skeleton";
import api from "@/lib/api";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth";
import { useSalespersonFilter } from "@/lib/salespersonContext";
import { useDashboardLeads } from "@/hooks/useDashboard";
import {
  useExecutiveSummary, useConversionFunnel, usePipelineStages,
  useFollowupDiscipline, useActivityAnalytics, useInquiryAnalytics,
  useProductivity, useTeamComparison,
} from "@/hooks/useAnalytics";
import { fetchInquirySummary } from "@/lib/inquiries";
import {
  Trophy, Users, Target, AlertTriangle, TrendingUp, Clock, CheckCircle2, MessageSquare,
  Activity, BarChart3, Phone, Mail, Zap, Download, Calendar,
} from "lucide-react";

const PIE_COLORS = ["#22c55e", "#eab308", "#3b82f6", "#f97316", "#8b5cf6", "#ec4899", "#14b8a6", "#ef4444", "#6366f1"];

const AVATAR_GRADIENTS = [
  "from-primary/80 to-primary",
  "from-amber-500 to-orange-600",
  "from-cyan-500 to-blue-600",
  "from-purple-500 to-purple-600",
  "from-rose-500 to-pink-600",
];

const tooltipStyle = {
  background: "hsl(0 0% 100%)",
  border: "1px solid hsl(0 0% 90%)",
  borderRadius: "8px",
  fontSize: "13px",
  boxShadow: "0 4px 12px rgba(0,0,0,0.08)",
};

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

function StatBox({ label, value, color }: { label: string; value: string | number; color?: string }) {
  return (
    <div className="rounded-lg bg-muted/50 p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className={`text-lg font-semibold mt-0.5 ${color || "text-foreground"}`}>{value}</p>
    </div>
  );
}

export default function Team() {
  const { user } = useAuth();
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
    queryKey: ["team", "export-leads", selectedSalesperson],
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

  const { data: allStats, isLoading: statsLoading } = useQuery({
    queryKey: ["team", "all"],
    queryFn: () => api.get("/dashboard/salesperson-stats").then((r) => r.data.items),
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });

  const { data: indLeads } = useDashboardLeads(1000);
  const { data: indStats } = useQuery({
    queryKey: ["team", "individual", selectedSalesperson],
    queryFn: () => api.get("/dashboard/salesperson-stats", { params: selectedSalesperson ? { salesperson: selectedSalesperson } : {} }).then((r) => r.data.items),
    staleTime: 30_000,
    enabled: !!selectedSalesperson,
  });

  const { data: indInquirySummary } = useQuery({
    queryKey: ["team", "inquiry-summary", selectedSalesperson],
    queryFn: fetchInquirySummary,
    staleTime: 30_000,
    enabled: !!selectedSalesperson,
  });

  const { data: indEngagement } = useQuery({
    queryKey: ["team", "engagement", selectedSalesperson],
    queryFn: () => api.get("/dashboard/engagement", { params: { days: 30, ...(selectedSalesperson ? { salesperson: selectedSalesperson } : {}) } }).then((r) => r.data),
    staleTime: 30_000,
    enabled: !!selectedSalesperson,
  });

  const profile = indStats?.[0] || null;
  const indLeadsList = indLeads || [];
  const inactiveLeads = profile ? (profile.assigned_leads - profile.active_leads) : 0;
  const totalTasks = indEngagement ? (indEngagement.followups || 0) : 0;
  const sorted = allStats?.slice().sort((a: any, b: any) => b.conversion_rate - a.conversion_rate) || [];

  const compChartData = useMemo(() => {
    if (!teamComp) return [];
    return teamComp.map((t) => ({
      name: t.assigned_to.split(" ")[0],
      Leads: t.total_leads,
      Won: t.won,
      Engagement: t.engagement_30d,
    }));
  }, [teamComp]);

  if (selectedSalesperson && profile) {
    return (
      <div className="p-6 space-y-6">
        <div>
          <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
            <Users className="w-4 h-4" />
            <span>Individual performance</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight">{selectedSalesperson}</h1>
          <p className="text-muted-foreground mt-1">Detailed performance breakdown</p>
        </div>

        <Card className="overflow-hidden">
          <div className="bg-gradient-to-r from-primary/5 to-transparent p-6 flex items-center gap-4">
            <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-primary to-primary/70 flex items-center justify-center text-2xl font-bold text-white shadow-sm">
              {selectedSalesperson.charAt(0).toUpperCase()}
            </div>
            <div>
              <p className="text-lg font-bold">{selectedSalesperson}</p>
              <div className="flex items-center gap-3 text-sm text-muted-foreground mt-1">
                <span>{profile.assigned_leads} assigned leads</span>
                <span>·</span>
                <span>{profile.conversion_rate}% conversion</span>
              </div>
            </div>
          </div>
        </Card>

        <div>
          <h2 className="text-sm font-semibold text-muted-foreground/70 uppercase tracking-wider mb-3 flex items-center gap-2">
            <Target className="w-4 h-4" />Lead Ownership
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <MetricCard title="Assigned" value={profile.assigned_leads} subtitle="Total leads" color="text-primary" icon={<Users className="w-4 h-4" />} />
            <MetricCard title="Active" value={profile.active_leads} subtitle="In pipeline" color="text-green-600" icon={<TrendingUp className="w-4 h-4" />} />
            <MetricCard title="Inactive" value={inactiveLeads} subtitle="Not progressing" color={inactiveLeads > 10 ? "text-destructive" : "text-muted-foreground"} icon={<Clock className="w-4 h-4" />} />
            <MetricCard title="Closed" value={profile.conversions} subtitle="Won deals" color="text-emerald-600" icon={<CheckCircle2 className="w-4 h-4" />} />
          </div>
        </div>

        <div>
          <h2 className="text-sm font-semibold text-muted-foreground/70 uppercase tracking-wider mb-3 flex items-center gap-2">
            <Activity className="w-4 h-4" />Follow-up Metrics
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <MetricCard title="Follow-ups (30d)" value={totalTasks} subtitle="Total logged" color="text-blue-600" icon={<Phone className="w-4 h-4" />} />
            <MetricCard title="Overdue" value={profile.overdue_followups} subtitle="Past due" color={profile.overdue_followups > 0 ? "text-destructive" : "text-muted-foreground"} icon={<AlertTriangle className="w-4 h-4" />} />
            <MetricCard title="Engagements (30d)" value={indEngagement?.total || 0} subtitle="All types" color="text-indigo-600" icon={<Mail className="w-4 h-4" />} />
            <MetricCard title="Due Today" value={0} subtitle="Today's tasks" color="text-amber-600" icon={<Clock className="w-4 h-4" />} />
          </div>
        </div>

        <div>
          <h2 className="text-sm font-semibold text-muted-foreground/70 uppercase tracking-wider mb-3 flex items-center gap-2">
            <BarChart3 className="w-4 h-4" />Conversion Metrics
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <MetricCard title="Overall Rate" value={`${profile.conversion_rate}%`} subtitle="Leads → Closed" color="text-emerald-600" icon={<TrendingUp className="w-4 h-4" />} />
            <MetricCard title="Total Leads" value={profile.assigned_leads} subtitle="Ever assigned" color="text-primary" icon={<Users className="w-4 h-4" />} />
            <MetricCard title="Active Pipeline" value={profile.active_leads} subtitle="Still open" color="text-blue-600" icon={<Target className="w-4 h-4" />} />
            <MetricCard title="Conversion Target" value={profile.conversion_rate >= 15 ? "Met" : "Below"} subtitle="Target: 15%" color={profile.conversion_rate >= 15 ? "text-emerald-600" : "text-destructive"} icon={<CheckCircle2 className="w-4 h-4" />} />
          </div>
        </div>

        <div>
          <h2 className="text-sm font-semibold text-muted-foreground/70 uppercase tracking-wider mb-3 flex items-center gap-2">
            <Activity className="w-4 h-4" />Productivity
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <MetricCard title="Inquiries Created" value={indInquirySummary?.total_open || 0} subtitle="Open inquiries" color="text-amber-600" icon={<MessageSquare className="w-4 h-4" />} />
            <MetricCard title="Inquiries Resolved" value={indInquirySummary?.responded_today || 0} subtitle="Answered today" color="text-emerald-600" icon={<CheckCircle2 className="w-4 h-4" />} />
            <MetricCard title="Leads" value={indLeadsList.length} subtitle="In dashboard scope" color="text-primary" icon={<Users className="w-4 h-4" />} />
            <MetricCard title="Active Statuses" value={new Set(indLeadsList.map((l: any) => l.status)).size} subtitle="Unique statuses" color="text-indigo-600" icon={<BarChart3 className="w-4 h-4" />} />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
            <Users className="w-4 h-4" />
            <span>Team performance & analytics</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight">Analytics & Team</h1>
          <p className="text-muted-foreground mt-1">{sorted.length} team members · full performance overview</p>
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
              <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className="h-9 px-3 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
              <span className="text-muted-foreground">—</span>
              <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} className="h-9 px-3 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
              <span className="text-xs text-muted-foreground">{filteredLeads.length} leads in range</span>
            </div>
            <div className="flex items-center gap-2 ml-auto">
              <Button onClick={() => exportCsv(leads || [], `team_${scope}_full_${today}.csv`)} disabled={!leads} variant="outline" size="sm" className="gap-2">
                <Download className="w-3.5 h-3.5" />Full Export
              </Button>
              <Button onClick={() => exportCsv(filteredLeads, `team_${scope}_${startDate}_to_${endDate}.csv`)} disabled={!leads} size="sm" className="gap-2">
                <Download className="w-3.5 h-3.5" />Export Range
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Performance KPIs */}
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

      {/* Activity Analytics */}
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

      {/* Conversion Funnel */}
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

      {/* Pipeline Stages */}
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

      {/* Follow-Up Discipline */}
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

      {/* Inquiry Analytics */}
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

      {/* Productivity Scores */}
      {prodScores && prodScores.length > 0 && (
        <Section title="Productivity Scores" icon={<Zap className="w-4 h-4" />}>
          {prodLoading ? <SkeletonChart /> : (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
              {prodScores.slice(0, 12).map((p, i) => (
                <Card key={p.assigned_to} className={cn("border-border/60", i === 0 && "ring-2 ring-amber-400/50")}>
                  <CardContent className="p-4 text-center">
                    <div className={cn(
                      "w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold text-white mx-auto mb-2",
                      i === 0 ? "bg-gradient-to-br from-amber-500 to-orange-600" : "bg-gradient-to-br from-primary/60 to-primary",
                    )}>
                      {p.assigned_to.charAt(0).toUpperCase()}
                    </div>
                    <p className="text-xs text-muted-foreground">{p.assigned_to}</p>
                    <p className={cn("text-2xl font-bold mt-1", p.score >= 70 ? "text-green-600" : p.score >= 40 ? "text-amber-600" : "text-muted-foreground")}>
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
          )}
        </Section>
      )}

      {/* Side-by-side comparison chart */}
      {compChartData.length > 1 && (
        <Section title="Team Comparison" icon={<BarChart3 className="w-4 h-4" />}>
          <Card>
            <CardContent className="pt-4">
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={compChartData} margin={{ top: 10, right: 10, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(0 0% 93%)" vertical={false} />
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Bar dataKey="Leads" fill="hsl(142 76% 36%)" radius={[4, 4, 0, 0]} maxBarSize={40} />
                  <Bar dataKey="Won" fill="hsl(200 60% 50%)" radius={[4, 4, 0, 0]} maxBarSize={40} />
                  <Bar dataKey="Engagement" fill="hsl(30 80% 55%)" radius={[4, 4, 0, 0]} maxBarSize={40} />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Section>
      )}

      {/* Leaderboard */}
      {statsLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="rounded-xl border border-border/60 p-6 space-y-4">
              <div className="flex items-center gap-3">
                <div className="skeleton h-12 w-12 rounded-full" />
                <div className="flex-1 space-y-1.5">
                  <div className="skeleton h-4 w-24" />
                  <div className="skeleton h-3 w-16" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                {Array.from({ length: 4 }).map((_, j) => (
                  <div key={j} className="skeleton h-12 w-full" />
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <Section title="Rankings" icon={<Trophy className="w-4 h-4" />}>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {sorted.map((stat: any, i: number) => (
              <Card
                key={stat.assigned_to}
                className={cn(
                  "relative overflow-hidden transition-all duration-200 hover:shadow-lg cursor-pointer",
                  i === 0 && "ring-2 ring-amber-400/50"
                )}
              >
                {i === 0 && (
                  <div className="absolute top-0 right-0 w-16 h-16">
                    <div className="absolute -top-4 -right-4 w-12 h-12 bg-amber-400 rotate-45" />
                    <Trophy className="absolute top-1.5 right-1.5 w-4 h-4 text-white" />
                  </div>
                )}
                <CardContent className="p-5">
                  <div className="flex items-center gap-3 mb-4">
                    <div className={cn(
                      "w-12 h-12 rounded-xl bg-gradient-to-br flex items-center justify-center text-lg font-bold text-white shadow-sm shrink-0",
                      AVATAR_GRADIENTS[i % AVATAR_GRADIENTS.length]
                    )}>
                      {(stat.assigned_to || "?").charAt(0).toUpperCase()}
                    </div>
                    <div>
                      <p className="font-semibold">{stat.assigned_to}</p>
                      <p className="text-xs text-muted-foreground">
                        {i === 0 ? "Top Performer" : `#${i + 1} in ranking`}
                      </p>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <StatBox label="Leads" value={stat.assigned_leads} />
                    <StatBox label="Active" value={stat.active_leads} />
                    <StatBox label="Conversions" value={stat.conversions} color="text-green-600" />
                    <StatBox label="Rate" value={`${stat.conversion_rate}%`} color="text-primary font-bold" />
                  </div>
                  {stat.overdue_followups > 0 && (
                    <div className="mt-3 flex items-center gap-1.5 text-xs text-destructive bg-destructive/5 rounded-lg px-3 py-1.5">
                      <AlertTriangle className="w-3 h-3" />
                      {stat.overdue_followups} overdue follow-up{stat.overdue_followups !== 1 ? "s" : ""}
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </Section>
      )}
    </div>
  );
}
