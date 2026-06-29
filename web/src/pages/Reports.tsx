import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle, MetricCard } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import api from "@/lib/api";
import { useSalespersonFilter } from "@/lib/salespersonContext";
import { useExecutiveSummary } from "@/hooks/useAnalytics";
import {
  Download, FileSpreadsheet, TrendingUp, Users, Activity,
  Calendar, Clock,
} from "lucide-react";

type MetricOption = "leads" | "followups" | "activities" | "all";

export default function Reports() {
  const { selectedSalesperson } = useSalespersonFilter();
  const { data: execSummary } = useExecutiveSummary();
  const [startDate, setStartDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() - 30);
    return d.toISOString().split("T")[0];
  });
  const [endDate, setEndDate] = useState(() => new Date().toISOString().split("T")[0]);
  const [metrics, setMetrics] = useState<MetricOption>("all");

  const { data: leads, isLoading } = useQuery({
    queryKey: ["reports", selectedSalesperson],
    queryFn: () => api.get("/dashboard/leads", { params: { limit: 500, ...(selectedSalesperson ? { salesperson: selectedSalesperson } : {}) } }).then((r) => r.data.items),
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

  const activeLeads = filteredLeads.filter((l: any) => l.status !== "Lost" && l.status !== "Order Closed");
  const converted = filteredLeads.filter((l: any) => l.status === "Order Closed");
  const rate = filteredLeads.length ? ((converted.length / filteredLeads.length) * 100).toFixed(1) : "0.0";

  const handleExport = (format: "csv" | "tsv") => {
    if (!leads) return;
    const scope = selectedSalesperson ? selectedSalesperson.replace(/\s+/g, "_").toLowerCase() : "all_team";
    const sep = format === "tsv" ? "\t" : ",";
    const headers = ["Lead ID", "Company", "Contact", "Phone", "Email", "Country", "Status", "Source", "Priority", "Score", "Created", "Salesperson", "Interest", "Deal Value", "Requirements"].join(sep);
    const rows = filteredLeads.map((l: any) =>
      [l.lead_id, l.company_name, l.contact_person, l.phone, l.email, l.country, l.status, l.lead_source, l.priority_level, l.lead_score, l.created_date, l.assigned_to, l.interest_level, l.potential_deal_value, l.customer_requirements]
        .map((v) => `"${v ?? ""}"`)
        .join(sep)
    ).join("\n");
    const csv = [headers, rows].join("\n");
    const blob = new Blob([csv], { type: format === "tsv" ? "text/tab-separated-values" : "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `leads_${scope}_${startDate}_to_${endDate}.${format === "tsv" ? "tsv" : "csv"}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
          <FileSpreadsheet className="w-4 h-4" />
          <span>Export & reports{selectedSalesperson ? ` · ${selectedSalesperson}` : ""}</span>
        </div>
        <h1 className="text-3xl font-bold tracking-tight">Reports</h1>
        <p className="text-muted-foreground mt-1">Export your CRM data{selectedSalesperson ? ` for ${selectedSalesperson}` : ""}</p>
      </div>

      {/* Summary KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Total Leads"
          value={filteredLeads.length}
          subtitle={`${startDate} to ${endDate}`}
          loading={isLoading}
          icon={<Users className="w-4 h-4" />}
        />
        <MetricCard
          title="Active Pipeline"
          value={activeLeads.length}
          subtitle="Excluding Closed/Lost"
          loading={isLoading}
          color="text-primary"
          icon={<TrendingUp className="w-4 h-4" />}
        />
        <MetricCard
          title="Converted"
          value={converted.length}
          subtitle="Closed won"
          loading={isLoading}
          color="text-green-600"
          icon={<Activity className="w-4 h-4" />}
        />
        <MetricCard
          title="Conversion Rate"
          value={`${rate}%`}
          subtitle="Overall"
          loading={isLoading}
          color="text-primary"
          icon={<TrendingUp className="w-4 h-4" />}
        />
      </div>

      {/* Date Range + Metrics */}
      <Card>
        <CardContent className="p-4 space-y-4">
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
            <div className="flex items-center gap-2 ml-auto">
              <Clock className="w-4 h-4 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">{filteredLeads.length} leads in range</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Export */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Download className="w-4 h-4 text-primary" />
            Export Data
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">Leads database{selectedSalesperson ? ` — ${selectedSalesperson}` : ""}</p>
              <p className="text-xs text-muted-foreground mt-0.5">
                {filteredLeads.length} leads · {startDate} to {endDate}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button onClick={() => handleExport("csv")} disabled={!leads} className="gap-2">
                <Download className="w-4 h-4" />
                CSV
              </Button>
              <Button onClick={() => handleExport("tsv")} disabled={!leads} variant="outline" className="gap-2">
                <Download className="w-4 h-4" />
                TSV
              </Button>
            </div>
          </div>
          {execSummary && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-3 border-t border-border/40">
              <MetricCard title="Total" value={execSummary.total_leads} icon={<Users className="w-4 h-4" />} />
              <MetricCard title="Won" value={execSummary.won} color="text-green-600" icon={<Activity className="w-4 h-4" />} />
              <MetricCard title="Conversion" value={`${execSummary.conversion_rate}%`} color="text-primary" icon={<TrendingUp className="w-4 h-4" />} />
              <MetricCard title="Avg Deal" value={`$${execSummary.avg_deal_value.toLocaleString()}`} color="text-blue-600" icon={<TrendingUp className="w-4 h-4" />} />
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
