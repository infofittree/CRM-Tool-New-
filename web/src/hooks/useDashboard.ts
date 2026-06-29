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

function sp() {
  const { selectedSalesperson } = useSalespersonFilter();
  return selectedSalesperson;
}

export function useDashboardCounts() {
  const s = sp();
  return useQuery<DashboardCounts>({
    queryKey: ["dashboard", "counts", s],
    queryFn: () => api.get("/dashboard/counts", { params: s ? { salesperson: s } : {} }).then((r) => r.data),
    ...STALE,
  });
}

export function useEngagementStats(days = 7) {
  const s = sp();
  return useQuery<EngagementStats>({
    queryKey: ["dashboard", "engagement", days, s],
    queryFn: () => api.get("/dashboard/engagement", { params: { days, ...(s ? { salesperson: s } : {}) } }).then((r) => r.data),
    ...STALE,
  });
}

export function useSalespersonStats() {
  const s = sp();
  return useQuery<SalespersonStat[]>({
    queryKey: ["dashboard", "salesperson-stats", s],
    queryFn: () => api.get("/dashboard/salesperson-stats", { params: s ? { salesperson: s } : {} }).then((r) => r.data.items),
    ...STALE,
  });
}

export function useRecentActivities(limit = 12) {
  const s = sp();
  return useQuery<ActivityEntry[]>({
    queryKey: ["dashboard", "activities", limit, s],
    queryFn: () => api.get("/dashboard/activities", { params: { limit, ...(s ? { salesperson: s } : {}) } }).then((r) => r.data.items),
    ...STALE,
  });
}

export function useDashboardLeads(limit = 500) {
  const s = sp();
  return useQuery<Lead[]>({
    queryKey: ["dashboard", "leads", limit, s],
    queryFn: () => api.get("/dashboard/leads", { params: { limit, ...(s ? { salesperson: s } : {}) } }).then((r) => r.data.items),
    ...STALE,
    staleTime: 60_000,
  });
}

export function useTaskQueue(upcomingDays = 7, maxToday = 20) {
  return useQuery<TaskQueue>({
    queryKey: ["tasks", upcomingDays, maxToday],
    queryFn: () => api.get(`/followups/tasks?upcoming_days=${upcomingDays}&max_today=${maxToday}`).then((r) => r.data),
    ...STALE,
  });
}

export function usePipelineHealth() {
  const s = sp();
  return useQuery<PipelineHealthResponse>({
    queryKey: ["dashboard", "pipeline-health", s],
    queryFn: () => api.get("/dashboard/pipeline-health", { params: s ? { salesperson: s } : {} }).then((r) => r.data),
    ...STALE,
  });
}

export function useTodayPriorities() {
  const s = sp();
  return useQuery<TodayPrioritiesResponse>({
    queryKey: ["dashboard", "today-priorities", s],
    queryFn: () => api.get("/dashboard/today-priorities", { params: s ? { salesperson: s } : {} }).then((r) => r.data),
    ...STALE,
  });
}

export function useSalespersonKpi() {
  const s = sp();
  return useQuery<SalespersonKpi[]>({
    queryKey: ["dashboard", "salesperson-kpi", s],
    queryFn: () => api.get("/dashboard/salesperson-kpi", { params: s ? { salesperson: s } : {} }).then((r) => r.data.items),
    ...STALE,
  });
}

export function useAlerts() {
  return useQuery<CrmAlert[]>({
    queryKey: ["dashboard", "alerts"],
    queryFn: () => api.get("/dashboard/alerts").then((r) => r.data.items),
    ...STALE,
  });
}

export function useLeadHealth(leadId: string) {
  return useQuery<LeadHealthResponse>({
    queryKey: ["dashboard", "lead-health", leadId],
    queryFn: () => api.get(`/dashboard/lead-health/${leadId}`).then((r) => r.data),
    enabled: !!leadId,
    ...STALE,
  });
}
