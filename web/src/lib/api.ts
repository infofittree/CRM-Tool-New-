import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_URL || "/api/v1";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401) {
      sessionStorage.removeItem("access_token");
      sessionStorage.removeItem("user");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export interface User {
  username: string;
  full_name: string;
  role: string;
  phone?: string | null;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface DashboardCounts {
  total: number;
  active: number;
  nurturing: number;
  converted: number;
  conversion_rate: number;
  overdue_followups: number;
  due_today_followups: number;
}

export interface EngagementStats {
  total: number;
  calls: number;
  whatsapp: number;
  emails: number;
  meetings: number;
  followups: number;
  today_done: number;
  by_user: Record<string, number>;
}

export interface Lead {
  lead_id: string;
  company_name: string | null;
  contact_person: string | null;
  phone: string | null;
  email: string | null;
  country: string | null;
  continent: string | null;
  status: string | null;
  assigned_to: string | null;
  lead_source: string | null;
  lead_category: string | null;
  lead_score: number;
  priority_level: string;
  last_contact_date: string | null;
  created_date: string | null;
  next_action_plan: string | null;
  lost_reason: string | null;
  industry: string | null;
  website: string | null;
  city: string | null;
  designation: string | null;
  alternate_number: string | null;
  whatsapp_number: string | null;
  product_interest: string | null;
  product_ids: number[] | null;
  inquiry_date: string | null;
  buyer_engagement_frequency: string | null;
  remarks: string | null;
  internal_notes: string | null;
  procurement_remarks: string | null;
  interest_level: string | null;
  potential_deal_value: string | null;
  customer_requirements: string | null;
  has_pending_followup: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface FollowUp {
  followup_id: number;
  lead_id: string;
  followup_date: string | null;
  discussion: string | null;
  next_action: string | null;
  next_followup: string | null;
  mode: string | null;
  status: string | null;
  updated_by: string | null;
  created_at: string | null;
  outcome_notes: string | null;
  completed_at: string | null;
  completed_by: string | null;
}

export interface Task {
  lead_id: string;
  company_name: string;
  assigned_to: string | null;
  status: string;
  standard_status: string;
  score: number;
  band: string;
  lead_category: string | null;
  buyer_engagement_frequency: string | null;
  recommended_action: string;
  reason: string | null;
  next_action_plan: string | null;
  due_date: string | null;
  due_label: string;
  days_to: number;
  last_contact_date: string | null;
  phone: string | null;
  email: string | null;
  contact_person: string | null;
  country: string | null;
  product_interest: string | null;
  bucket: string;
  interest_level: string | null;
  potential_deal_value: string | null;
  customer_requirements: string | null;
  followup_id: number | null;
  discussion: string | null;
  next_action: string | null;
  outcome_notes: string | null;
  completed_at: string | null;
  completed_by: string | null;
}

export interface TaskQueue {
  today_capped: Task[];
  upcoming: Task[];
  overdue: Task[];
  completed: Task[];
  summary: Record<string, number>;
}

export interface PaginatedLeads {
  items: Lead[];
  total: number;
  page: number;
  page_size: number;
}

export interface SalespersonStat {
  assigned_to: string;
  assigned_leads: number;
  active_leads: number;
  conversions: number;
  conversion_rate: number;
  overdue_followups: number;
}

export interface ActivityEntry {
  timestamp: string;
  action: string;
  user_name: string;
  lead_id: string;
  remarks: string | null;
}

export interface CompleteFollowupRequest {
  outcome_notes: string;
  lead_status?: string;
  interest_level?: string;
  potential_deal_value?: string;
  customer_requirements?: string;
  discussion_summary?: string;
  next_action_type?: string;
  next_followup_date?: string;
}

export interface FollowUpCompleteResponse {
  followup: FollowUp;
  next_followup: FollowUp | null;
}

export interface LeadHealthResponse {
  health: string;
  risk_level: string;
  warnings: string[];
  last_activity_days: number | null;
  next_followup_date: string | null;
}

export interface PipelineHealthResponse {
  healthy: number;
  attention_needed: number;
  at_risk: number;
  stalled: number;
  total: number;
}

export interface TodayPrioritiesResponse {
  overdue_tasks: number;
  due_today: number;
  at_risk_leads: number;
  stalled_leads: number;
  leads_without_followup: number;
}

export interface SalespersonKpi {
  assigned_to: string;
  tasks_due_today: number;
  overdue_tasks: number;
  upcoming_tasks: number;
  completed_tasks: number;
  overdue_pct: number;
  completion_pct: number;
  avg_delay_days: number;
}

export interface CrmAlert {
  alert_id: number;
  lead_id: string | null;
  alert_type: string;
  message: string;
  is_read: boolean;
  created_at: string | null;
}

export interface ConversionStage {
  stage: string;
  count: number;
}

export interface PipelineStageData {
  stage: string;
  count: number;
  avg_days_in_stage: number;
  avg_deal_value: number;
}

export interface FollowupDiscipline {
  total_followups: number;
  completed: number;
  overdue: number;
  completion_pct: number;
  avg_delay_days: number;
}

export interface ActivityAnalytics {
  total_activities: number;
  calls: number;
  whatsapp: number;
  emails: number;
  meetings: number;
  followups: number;
  activity_logs: number;
  avg_per_day: number;
}

export interface InquiryAnalytics {
  total_inquiries: number;
  open: number;
  responded: number;
  overdue: number;
  eod_committed: number;
  closed: number;
  response_sla_pct: number;
  common_types: { type: string; count: number }[];
}

export interface TrendData {
  leads_created: number;
  tasks_completed: number;
  activities: number;
  converted: number;
  total_leads: number;
}

export type TrendPeriod = "7d" | "30d" | "90d";
export type TrendMap = Record<TrendPeriod, TrendData>;

export interface ProductivityScore {
  assigned_to: string;
  score: number;
}

export interface TeamComparison {
  assigned_to: string;
  total_leads: number;
  active_leads: number;
  won: number;
  lost: number;
  conversion_rate: number;
  overdue_tasks: number;
  completed_tasks: number;
  task_completion_pct: number;
  engagement_30d: number;
}

export interface ExecutiveSummary {
  total_leads: number;
  active_leads: number;
  won: number;
  conversion_rate: number;
  overdue_tasks: number;
  due_today: number;
  activities_30d: number;
  leads_without_followup: number;
  avg_deal_value: number;
}

export interface SalespersonAnalytics {
  kpi: ExecutiveSummary;
  conversion_funnel: ConversionStage[];
  pipeline_stages: PipelineStageData[];
  followup_discipline: FollowupDiscipline;
  activity_analytics: ActivityAnalytics;
  productivity_score: number;
}

export interface ActivityWizardRequest {
  actions: string[];
  call_outcome?: string;
  customer_interest?: string;
  expect_response?: boolean;
  response_check_date?: string;
  meeting_outcome?: string;
  customer_requirements?: string[];
  not_interested_reason?: string;
  notes?: string;
  followup_date?: string;
}

export interface ActivityWizardResponse {
  followup_id: number;
  next_followup_id: number | null;
  next_action_type: string | null;
  next_action_template: string | null;
  next_followup_date: string | null;
  lead_status: string | null;
  lead_interest: string | null;
  lead_updates: string[];
  timeline_entries: string[];
}

export async function completeFollowup(followupId: number, data: CompleteFollowupRequest): Promise<FollowUpCompleteResponse> {
  const res = await api.patch(`/followups/${followupId}/complete`, data);
  return res.data;
}

export async function completeActivity(followupId: number, data: ActivityWizardRequest): Promise<ActivityWizardResponse> {
  const res = await api.post(`/followups/${followupId}/complete-activity`, data);
  return res.data;
}

// ── Lead Handover ────────────────────────────────────────────────────────────

export interface LeadHandover {
  id: number;
  lead_id: string;
  from_user: string;
  to_user: string;
  reason: string;
  notes: string | null;
  status: "PENDING" | "ACCEPTED" | "DECLINED" | "CANCELLED";
  requested_at: string;
  responded_at: string | null;
  responded_by: string | null;
  created_by: string;
  company_name: string | null;
}

export interface HandoverCreate {
  to_user: string;
  reason: string;
  notes?: string;
}

export async function createHandover(leadId: string, data: HandoverCreate): Promise<LeadHandover> {
  const res = await api.post(`/leads/${leadId}/handover`, data);
  return res.data;
}

export async function acceptHandover(handoverId: number): Promise<LeadHandover> {
  const res = await api.post(`/handovers/${handoverId}/accept`);
  return res.data;
}

export async function declineHandover(handoverId: number): Promise<LeadHandover> {
  const res = await api.post(`/handovers/${handoverId}/decline`);
  return res.data;
}

export async function fetchLeadHandovers(leadId: string): Promise<LeadHandover[]> {
  const res = await api.get(`/leads/${leadId}/handovers`);
  return res.data;
}

export async function fetchMyPendingHandovers(): Promise<LeadHandover[]> {
  const res = await api.get("/me/handovers");
  return res.data;
}

export default api;
