import api from "./api";

export interface Inquiry {
  id: number;
  lead_id: string;
  created_by: string;
  assigned_to: string;
  title: string;
  type: string;
  priority: string;
  description: string | null;
  response: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  responded_at: string | null;
  commitment_type: string | null;
  expected_response_date: string | null;
  committed_at: string | null;
  company_name: string | null;
  contact_person: string | null;
}

export interface InquiryCreate {
  lead_id: string;
  title: string;
  type: string;
  priority: string;
  description?: string;
}

export interface InquiryUpdate {
  response?: string;
  status?: string;
}

export interface CommitmentRequest {
  commitment_type: string;
  expected_response_date?: string;
  response?: string;
}

export interface InquirySummary {
  total_open: number;
  eod_committed: number;
  pending_response: number;
  overdue: number;
  responded_today: number;
}

export async function fetchInquiries(params?: {
  lead_id?: string;
  status?: string;
  page?: number;
  page_size?: number;
}): Promise<Inquiry[]> {
  const res = await api.get("/inquiries", { params });
  return res.data;
}

export async function fetchInquirySummary(): Promise<InquirySummary> {
  const res = await api.get("/inquiries/summary");
  return res.data;
}

export async function createInquiry(body: InquiryCreate): Promise<Inquiry> {
  const res = await api.post("/inquiries", body);
  return res.data;
}

export async function updateInquiry(id: number, body: InquiryUpdate): Promise<Inquiry> {
  const res = await api.put(`/inquiries/${id}`, body);
  return res.data;
}

export async function commitInquiry(id: number, body: CommitmentRequest): Promise<Inquiry> {
  const res = await api.post(`/inquiries/${id}/commit`, body);
  return res.data;
}

export async function checkOverdueInquiries(): Promise<{ updated: Record<string, number> }> {
  const res = await api.post("/inquiries/check-overdue");
  return res.data;
}

export const INQUIRY_TYPES = ["PRICING", "AVAILABILITY", "PACKAGING", "DOCUMENTATION", "MOQ", "LEAD_TIME", "CUSTOM"] as const;
export const INQUIRY_PRIORITIES = ["LOW", "MEDIUM", "HIGH", "URGENT"] as const;
export const INQUIRY_STATUSES = ["OPEN", "EOD_COMMITTED", "PENDING_RESPONSE", "RESPONDED", "OVERDUE", "CLOSED"] as const;

export const COMMITMENT_TYPES = [
  { value: "ANSWER_NOW", label: "Answer Now" },
  { value: "BY_EOD", label: "By End Of Day" },
  { value: "WILL_TAKE_TIME", label: "Will Take Time" },
] as const;

export const COMMITMENT_LABELS: Record<string, string> = {
  ANSWER_NOW: "Answer Now",
  BY_EOD: "By End Of Day",
  WILL_TAKE_TIME: "Will Take Time",
};

/* ── Business-language display helpers ── */

/** Maps technical status → sales-facing display label */
export const DISPLAY_STATUS_LABELS: Record<string, string> = {
  OPEN: "Awaiting Review",
  EOD_COMMITTED: "Expected Today",
  PENDING_RESPONSE: "Expected on Date",
  RESPONDED: "Answered",
  OVERDUE: "Overdue",
  CLOSED: "Closed",
};

/** Maps technical status → background/text color classes for the badge */
export const DISPLAY_STATUS_COLORS: Record<string, string> = {
  OPEN: "bg-amber-50 text-amber-700 border-amber-200",
  EOD_COMMITTED: "bg-orange-50 text-orange-700 border-orange-200",
  PENDING_RESPONSE: "bg-blue-50 text-blue-700 border-blue-200",
  RESPONDED: "bg-emerald-50 text-emerald-700 border-emerald-200",
  OVERDUE: "bg-red-50 text-red-700 border-red-200",
  CLOSED: "bg-slate-100 text-slate-500 border-slate-200",
};

/** Maps technical status → descriptive "current situation" text for sales view */
export function getDisplaySituation(status: string, expectedResponseDate: string | null): string {
  switch (status) {
    case "OPEN":
      return "Awaiting procurement review";
    case "EOD_COMMITTED":
      return "Procurement will respond by end of day";
    case "PENDING_RESPONSE":
      return expectedResponseDate
        ? `Procurement expects to respond by ${new Date(expectedResponseDate).toLocaleDateString()}`
        : "Procurement expects to respond soon";
    case "RESPONDED":
      return "Response provided";
    case "OVERDUE":
      return "Response overdue";
    case "CLOSED":
      return "Inquiry closed";
    default:
      return status;
  }
}

/** Human-readable "Expected Response" string for sales view */
export function getExpectedResponseText(status: string, expectedResponseDate: string | null): string {
  switch (status) {
    case "OPEN":
      return "Awaiting Review";
    case "EOD_COMMITTED":
      return "Today";
    case "PENDING_RESPONSE":
      return expectedResponseDate ? new Date(expectedResponseDate).toLocaleDateString() : "Soon";
    case "RESPONDED":
      return "Answered";
    case "OVERDUE":
      return "Overdue";
    case "CLOSED":
      return "—";
    default:
      return status;
  }
}

/** Sales-facing filter options (business language, not technical statuses) */
export const DISPLAY_FILTER_OPTIONS = [
  { value: "", label: "All Inquiries" },
  { value: "OPEN", label: "Awaiting Review" },
  { value: "EOD_COMMITTED", label: "Expected Today" },
  { value: "PENDING_RESPONSE", label: "Expected on Date" },
  { value: "RESPONDED", label: "Answered" },
  { value: "REVISION_REQUESTED", label: "Revision Requested" },
  { value: "REVISED_RESPONSE", label: "Revised Quote" },
  { value: "OVERDUE", label: "Overdue" },
  { value: "CLOSED", label: "Closed" },
] as const;

// ── Revision / Negotiation ──────────────────────────────────────────────────

export interface InquiryRevision {
  id: number;
  inquiry_id: number;
  revision_number: number;
  created_by: string;
  reason: string;
  customer_feedback: string | null;
  target_price: string | null;
  quantity: string | null;
  packaging: string | null;
  delivery_timeline: string | null;
  payment_terms: string | null;
  additional_requirements: string | null;
  status: string;
  created_at: string;
  responded_at: string | null;
  responded_by: string | null;
}

export interface RevisionCreate {
  reason: string;
  customer_feedback?: string;
  target_price?: string;
  quantity?: string;
  packaging?: string;
  delivery_timeline?: string;
  payment_terms?: string;
  additional_requirements?: string;
}

export const REVISION_REASONS: { value: string; label: string }[] = [
  { value: "budget", label: "Customer budget lower" },
  { value: "competitor", label: "Competitor quoted lower" },
  { value: "discount", label: "Customer requesting discount" },
  { value: "quantity", label: "Quantity changed" },
  { value: "spec", label: "Product specification changed" },
  { value: "packaging", label: "Packaging changed" },
  { value: "delivery", label: "Delivery timeline changed" },
  { value: "payment", label: "Payment terms changed" },
  { value: "freight", label: "Freight/Incoterms changed" },
  { value: "other_quotation", label: "Customer requested another quotation" },
  { value: "customer_feedback", label: "Customer Feedback" },
];

export const REVISION_STATUS_LABELS: Record<string, string> = {
  PENDING: "Awaiting Response",
  RESPONDED: "Responded",
};

export async function requestRevision(inquiryId: number, body: RevisionCreate): Promise<any> {
  const res = await api.post(`/inquiries/${inquiryId}/revision`, body);
  return res.data;
}

export async function fetchInquiryRevisions(inquiryId: number): Promise<InquiryRevision[]> {
  const res = await api.get(`/inquiries/${inquiryId}/revisions`);
  return res.data;
}

export async function respondToRevision(inquiryId: number, revId: number, body: { response?: string }): Promise<any> {
  const res = await api.post(`/inquiries/${inquiryId}/revisions/${revId}/respond`, body);
  return res.data;
}
