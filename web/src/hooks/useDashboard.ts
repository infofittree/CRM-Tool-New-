import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import api, {
  type CrmAlert,
  type DashboardCounts,
  type EngagementStats,
  type Lead,
  type LeadHealthResponse,
  type PipelineHealthResponse,
  type SalespersonKpi,
  type SalespersonStat,
  type TodayPrioritiesResponse,
  type TaskQueue,
  type ActivityEntry,
} from "@/lib/api";
import { useSalespersonFilter } from "@/lib/salespersonContext";

const STALE = { staleTime: 30_000, gcTime: 120_000, refetchOnWindowFocus: false };

/** Read salesperson from shared context (used by Analytics and fallback). */
function sp() {
  const { selectedSalesperson } = useSalespersonFilter();
  return selectedSalesperson;
}

/**
 * Resolve the effective salesperson name:
 * use the explicit override when provided, otherwise fall back to context.
 */
function resolve(override?: string | null): string | null {
  return override !== undefined ? override : sp();
}

export function useDashboardCounts(salespersonOverride?: string | null) {
  const s = resolve(salespersonOverride);
  return useQuery<DashboardCounts>({
    queryKey: ["dashboard", "counts", s],
    queryFn: () => api.get("/dashboard/counts", { params: s ? { salesperson: s } : {} }).then((r) => r.data),
    ...STALE,
  });
}

export function useEngagementStats(days = 7, salespersonOverride?: string | null) {
  const s = resolve(salespersonOverride);
  return useQuery<EngagementStats>({
    queryKey: ["dashboard", "engagement", days, s],
    queryFn: () => api.get("/dashboard/engagement", { params: { days, ...(s ? { salesperson: s } : {}) } }).then((r) => r.data),
    ...STALE,
  });
}

export function useSalespersonStats(salespersonOverride?: string | null) {
  const s = resolve(salespersonOverride);
  return useQuery<SalespersonStat[]>({
    queryKey: ["dashboard", "salesperson-stats", s],
    queryFn: () => api.get("/dashboard/salesperson-stats", { params: s ? { salesperson: s } : {} }).then((r) => r.data.items),
    ...STALE,
  });
}

export function useRecentActivities(limit = 12, salespersonOverride?: string | null) {
  const s = resolve(salespersonOverride);
  return useQuery<ActivityEntry[]>({
    queryKey: ["dashboard", "activities", limit, s],
    queryFn: () => api.get("/dashboard/activities", { params: { limit, ...(s ? { salesperson: s } : {}) } }).then((r) => r.data.items),
    ...STALE,
  });
}

export function useDashboardLeads(limit = 500, salespersonOverride?: string | null) {
  const s = resolve(salespersonOverride);
  return useQuery<Lead[]>({
    queryKey: ["dashboard", "leads", limit, s],
    queryFn: () => api.get("/dashboard/leads", { params: { limit, ...(s ? { salesperson: s } : {}) } }).then((r) => r.data.items),
    ...STALE,
    staleTime: 60_000,
  });
}

export function useTaskQueue(upcomingDays = 7, maxToday = 20, salespersonOverride?: string | null) {
  const s = resolve(salespersonOverride);
  const query = useQuery<TaskQueue>({
    queryKey: ["tasks", upcomingDays, maxToday, s],
    queryFn: () => api.get("/followups/tasks", {
      params: { upcoming_days: upcomingDays, max_today: maxToday, ...(s ? { salesperson: s } : {}) },
    }).then((r) => r.data),
    ...STALE,
  });

  return query;
}

export function usePipelineHealth(salespersonOverride?: string | null) {
  const s = resolve(salespersonOverride);
  return useQuery<PipelineHealthResponse>({
    queryKey: ["dashboard", "pipeline-health", s],
    queryFn: () => api.get("/dashboard/pipeline-health", { params: s ? { salesperson: s } : {} }).then((r) => r.data),
    ...STALE,
  });
}

export function useTodayPriorities(salespersonOverride?: string | null) {
  const s = resolve(salespersonOverride);
  return useQuery<TodayPrioritiesResponse>({
    queryKey: ["dashboard", "today-priorities", s],
    queryFn: () => api.get("/dashboard/today-priorities", { params: s ? { salesperson: s } : {} }).then((r) => r.data),
    ...STALE,
  });
}

export function useSalespersonKpi(salespersonOverride?: string | null) {
  const s = resolve(salespersonOverride);
  return useQuery<SalespersonKpi[]>({
    queryKey: ["dashboard", "salesperson-kpi", s],
    queryFn: () => api.get("/dashboard/salesperson-kpi", { params: s ? { salesperson: s } : {} }).then((r) => r.data.items),
    ...STALE,
  });
}

export function useAlerts(salespersonOverride?: string | null) {
  const query = useQuery<CrmAlert[]>({
    queryKey: ["dashboard", "alerts"],
    queryFn: () => api.get("/dashboard/alerts").then((r) => r.data.items),
    ...STALE,
  });

  const filter = salespersonOverride;
  const data = useMemo(() => {
    if (!filter || !query.data) return query.data;
    return query.data.filter((a: any) => {
      const name = a.user_name || a.assigned_to || a.created_by;
      return name?.toLowerCase() === filter.toLowerCase();
    });
  }, [query.data, filter]);

  return { ...query, data };
}

export function useLeadHealth(leadId: string) {
  return useQuery<LeadHealthResponse>({
    queryKey: ["dashboard", "lead-health", leadId],
    queryFn: () => api.get(`/dashboard/lead-health/${leadId}`).then((r) => r.data),
    enabled: !!leadId,
    ...STALE,
  });
}
