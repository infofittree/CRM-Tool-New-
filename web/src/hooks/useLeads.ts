import { useQuery } from "@tanstack/react-query";
import api, { type Lead, type PaginatedLeads } from "@/lib/api";

const STALE = { staleTime: 30_000, gcTime: 120_000, refetchOnWindowFocus: false };

export function useLeads(page = 1, pageSize = 25, search = "", status = "", country = "", priority = "") {
  return useQuery<PaginatedLeads>({
    queryKey: ["leads", page, pageSize, search, status, country, priority],
    queryFn: () =>
      api
        .get("/leads", { params: { page, page_size: pageSize, search, status, country, priority_level: priority } })
        .then((r) => r.data),
    placeholderData: (prev) => prev,
    ...STALE,
  });
}

export function useLead(id: string) {
  return useQuery<Lead>({
    queryKey: ["lead", id],
    queryFn: () => api.get(`/leads/${id}`).then((r) => r.data),
    enabled: !!id,
    ...STALE,
  });
}

export function useLeadFollowups(id: string) {
  return useQuery({
    queryKey: ["lead-followups", id],
    queryFn: () => api.get(`/leads/${id}/followups`).then((r) => r.data),
    enabled: !!id,
    ...STALE,
  });
}
