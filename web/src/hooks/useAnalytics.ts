import { useQuery } from "@tanstack/react-query";
import api, {
  type ActivityAnalytics,
  type ConversionStage,
  type ExecutiveSummary,
  type FollowupDiscipline,
  type InquiryAnalytics,
  type PipelineStageData,
  type ProductivityScore,
  type SalespersonAnalytics,
  type TeamComparison,
  type TrendMap,
} from "@/lib/api";
import { useSalespersonFilter } from "@/lib/salespersonContext";

const STALE = { staleTime: 60_000, gcTime: 300_000, refetchOnWindowFocus: false };

function sp() {
  const { selectedSalesperson } = useSalespersonFilter();
  return selectedSalesperson;
}

function spParam(s: string | null): Record<string, string> {
  return s ? { salesperson: s } : {};
}

export function useExecutiveSummary() {
  const s = sp();
  return useQuery<ExecutiveSummary>({
    queryKey: ["analytics", "executive-summary", s],
    queryFn: () => api.get("/analytics/executive-summary", { params: spParam(s) }).then((r) => r.data),
    ...STALE,
  });
}

export function useConversionFunnel() {
  const s = sp();
  return useQuery<ConversionStage[]>({
    queryKey: ["analytics", "conversion-funnel", s],
    queryFn: () => api.get("/analytics/conversion-funnel", { params: spParam(s) }).then((r) => r.data),
    ...STALE,
  });
}

export function usePipelineStages() {
  const s = sp();
  return useQuery<PipelineStageData[]>({
    queryKey: ["analytics", "pipeline-stages", s],
    queryFn: () => api.get("/analytics/pipeline-stages", { params: spParam(s) }).then((r) => r.data),
    ...STALE,
  });
}

export function useFollowupDiscipline(days = 30) {
  const s = sp();
  return useQuery<FollowupDiscipline>({
    queryKey: ["analytics", "followup-discipline", days, s],
    queryFn: () => api.get("/analytics/followup-discipline", { params: { days, ...spParam(s) } }).then((r) => r.data),
    ...STALE,
  });
}

export function useActivityAnalytics(days = 30) {
  const s = sp();
  return useQuery<ActivityAnalytics>({
    queryKey: ["analytics", "activity-analytics", days, s],
    queryFn: () => api.get("/analytics/activity-analytics", { params: { days, ...spParam(s) } }).then((r) => r.data),
    ...STALE,
  });
}

export function useInquiryAnalytics() {
  return useQuery<InquiryAnalytics>({
    queryKey: ["analytics", "inquiry"],
    queryFn: () => api.get("/analytics/inquiry").then((r) => r.data),
    ...STALE,
  });
}

export function useTrends(days = 30) {
  const s = sp();
  return useQuery<TrendMap>({
    queryKey: ["analytics", "trends", days, s],
    queryFn: () => api.get("/analytics/trends", { params: { days, ...spParam(s) } }).then((r) => r.data),
    ...STALE,
  });
}

export function useProductivity() {
  const s = sp();
  return useQuery<ProductivityScore[]>({
    queryKey: ["analytics", "productivity", s],
    queryFn: () => api.get("/analytics/productivity", { params: spParam(s) }).then((r) => r.data),
    ...STALE,
  });
}

export function useTeamComparison() {
  const s = sp();
  return useQuery<TeamComparison[]>({
    queryKey: ["analytics", "team-comparison", s],
    queryFn: () => api.get("/analytics/team-comparison", { params: spParam(s) }).then((r) => r.data),
    ...STALE,
  });
}

export function useSalespersonAnalytics(name: string) {
  return useQuery<SalespersonAnalytics>({
    queryKey: ["analytics", "salesperson", name],
    queryFn: () => api.get(`/analytics/salesperson/${encodeURIComponent(name)}`).then((r) => r.data),
    enabled: !!name,
    ...STALE,
  });
}
