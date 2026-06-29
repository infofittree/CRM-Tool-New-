import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, Cell, LineChart, Line, Legend,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SkeletonChart } from "@/components/ui/skeleton";
import api from "@/lib/api";
import { useSalespersonFilter } from "@/lib/salespersonContext";
import { useTrends } from "@/hooks/useAnalytics";
import { Calendar, BarChart3, TrendingUp, Activity, Target } from "lucide-react";
import { cn } from "@/lib/utils";

const statuses = ["Prospect", "Requirement Qualified", "Technical Discussion", "Quotation Sent", "Sample Sent", "Negotiation", "Trial Order", "Nurturing", "Order Closed", "Lost"];

const STATUS_COLORS: Record<string, string> = {
  "Prospect": "#94a3b8", "Requirement Qualified": "#3b82f6",
  "Technical Discussion": "#06b6d4", "Quotation Sent": "#10b981",
  "Sample Sent": "#84cc16", "Negotiation": "#f59e0b",
  "Trial Order": "#f97316", "Nurturing": "#a855f7",
  "Order Closed": "#22c55e", "Lost": "#ef4444",
};

const TREND_COLORS = ["hsl(142 76% 36%)", "hsl(200 60% 50%)", "hsl(30 80% 55%)", "hsl(340 80% 55%)"];

const tooltipStyle = {
  background: "hsl(0 0% 100%)",
  border: "1px solid hsl(0 0% 90%)",
  borderRadius: "8px",
  fontSize: "13px",
};

export default function WeeklyReview() {
  const { selectedSalesperson } = useSalespersonFilter();
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

  const { data: leads, isLoading } = useQuery({
    queryKey: ["weekly-review", weekStart, weekEnd, selectedSalesperson],
    queryFn: () => api.get("/dashboard/leads", { params: { limit: 500, ...(selectedSalesperson ? { salesperson: selectedSalesperson } : {}) } }).then((r) => r.data.items),
    staleTime: 60_000,
    refetchOnWindowFocus: false,
  });

  const { data: trends } = useTrends();

  const statusCounts = statuses.map((s) => ({
    status: s,
    count: leads?.filter((l: any) => l.status === s).length || 0,
  }));

  const total = statusCounts.reduce((a, s) => a + s.count, 0);

  const trendChartData = useMemo(() => {
    if (!trends) return [];
    const periods = ["7d", "30d", "90d"] as const;
    return periods.map((p) => ({
      period: p,
      "Leads Created": trends[p]?.leads_created || 0,
      "Tasks Done": trends[p]?.tasks_completed || 0,
      "Activities": trends[p]?.activities || 0,
      "Converted": trends[p]?.converted || 0,
    }));
  }, [trends]);

  const metrics = useMemo(() => {
    if (!trends) return null;
    return [
      { label: "7-Day", leads: trends["7d"]?.leads_created, tasks: trends["7d"]?.tasks_completed, conv: trends["7d"]?.converted },
      { label: "30-Day", leads: trends["30d"]?.leads_created, tasks: trends["30d"]?.tasks_completed, conv: trends["30d"]?.converted },
      { label: "90-Day", leads: trends["90d"]?.leads_created, tasks: trends["90d"]?.tasks_completed, conv: trends["90d"]?.converted },
    ];
  }, [trends]);

  return (
    <div className="p-6 space-y-6">
      <div>
        <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
          <BarChart3 className="w-4 h-4" />
          <span>Pipeline review{selectedSalesperson ? ` · ${selectedSalesperson}` : ""}</span>
        </div>
        <h1 className="text-3xl font-bold tracking-tight">Weekly Review</h1>
        <p className="text-muted-foreground mt-1">{total} leads in scope</p>
      </div>

      {/* Trend chart */}
      {trendChartData.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-primary" />
              Activity Trends (7/30/90 Day)
            </CardTitle>
          </CardHeader>
          <CardContent>
            {trends ? (
              <div className="space-y-4">
                <ResponsiveContainer width="100%" height={250}>
                  <LineChart data={trendChartData} margin={{ top: 10, right: 20, left: 0, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(0 0% 93%)" vertical={false} />
                    <XAxis dataKey="period" tick={{ fontSize: 12 }} axisLine={false} tickLine={false} />
                    <YAxis axisLine={false} tickLine={false} />
                    <Tooltip contentStyle={tooltipStyle} />
                    <Legend iconType="circle" iconSize={8} />
                    <Line type="monotone" dataKey="Leads Created" stroke={TREND_COLORS[0]} strokeWidth={2} dot={{ r: 4 }} />
                    <Line type="monotone" dataKey="Tasks Done" stroke={TREND_COLORS[1]} strokeWidth={2} dot={{ r: 4 }} />
                    <Line type="monotone" dataKey="Activities" stroke={TREND_COLORS[2]} strokeWidth={2} dot={{ r: 4 }} />
                    <Line type="monotone" dataKey="Converted" stroke={TREND_COLORS[3]} strokeWidth={2} dot={{ r: 4 }} />
                  </LineChart>
                </ResponsiveContainer>
                <div className="grid grid-cols-3 gap-3">
                  {metrics?.map((m) => (
                    <div key={m.label} className="rounded-xl bg-muted/30 p-3 text-center">
                      <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">{m.label}</p>
                      <div className="mt-2 space-y-1 text-sm">
                        <div className="flex justify-between">
                          <span className="text-muted-foreground/70">Leads</span>
                          <span className="font-semibold">{m.leads}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground/70">Tasks</span>
                          <span className="font-semibold">{m.tasks}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground/70">Conv</span>
                          <span className="font-semibold">{m.conv}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : <SkeletonChart />}
          </CardContent>
        </Card>
      )}

      {/* Date picker */}
      <Card>
        <CardContent className="p-4">
          <div className="flex items-center gap-4">
            <Calendar className="w-4 h-4 text-muted-foreground" />
            <div className="flex items-center gap-3">
              <div>
                <label className="text-xs text-muted-foreground block mb-1">Week Start</label>
                <input
                  type="date"
                  value={weekStart}
                  onChange={(e) => setWeekStart(e.target.value)}
                  className="h-9 px-3 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                />
              </div>
              <span className="text-muted-foreground mt-5">—</span>
              <div>
                <label className="text-xs text-muted-foreground block mb-1">Week End</label>
                <input
                  type="date"
                  value={weekEnd}
                  onChange={(e) => setWeekEnd(e.target.value)}
                  className="h-9 px-3 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                />
              </div>
            </div>
            <div className="ml-auto text-sm text-muted-foreground">
              <span className="font-medium text-foreground">{total}</span> leads total{selectedSalesperson ? ` for ${selectedSalesperson}` : ""}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Status funnel chart */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-primary" />
            Pipeline Funnel
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <SkeletonChart />
          ) : (
            <ResponsiveContainer width="100%" height={350}>
              <BarChart data={statusCounts} margin={{ top: 10, right: 10, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(0 0% 93%)" vertical={false} />
                <XAxis dataKey="status" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis axisLine={false} tickLine={false} />
                <Tooltip contentStyle={tooltipStyle} />
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

      {/* Status grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {statusCounts.map(({ status, count }) => (
          <Card key={status} className="border-border/60">
            <CardContent className="p-4 text-center">
              <p className="text-sm text-muted-foreground mb-1">{status}</p>
              <p className="text-3xl font-bold tracking-tight" style={{ color: STATUS_COLORS[status] || "#94a3b8" }}>
                {count}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
