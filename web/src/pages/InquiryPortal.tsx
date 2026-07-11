import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import Modal from "@/components/ui/modal";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth";
import api, { Lead } from "@/lib/api";
import {
  fetchInquiries, fetchInquirySummary, createInquiry,
  Inquiry, InquirySummary, InquiryCreate,
  INQUIRY_TYPES, INQUIRY_PRIORITIES,
  DISPLAY_STATUS_LABELS, DISPLAY_STATUS_COLORS, DISPLAY_FILTER_OPTIONS,
  getExpectedResponseText, getDisplaySituation,
} from "@/lib/inquiries";
import InquiryWorkflowModal from "@/components/InquiryWorkflowModal";
import {
  MessageSquare, Search, ChevronLeft, ChevronRight, Clock, CheckCircle2, X, Plus, AlertTriangle,
  Timer,
} from "lucide-react";

const PRIORITY_COLORS: Record<string, string> = {
  LOW: "bg-slate-50 text-slate-500", MEDIUM: "bg-blue-50 text-blue-700",
  HIGH: "bg-orange-50 text-orange-700", URGENT: "bg-red-50 text-red-700",
};

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

export default function InquiryPortal() {
  const { user } = useAuth();
  const isProc = user?.role === "Admin" || user?.role === "Manager" || user?.role === "Procurement";
  const isSales = user?.role === "Salesperson";

  const [inquiries, setInquiries] = useState<Inquiry[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(1);
  const [selectedInquiry, setSelectedInquiry] = useState<Inquiry | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [createForm, setCreateForm] = useState<InquiryCreate>({
    lead_id: "", title: "", type: "PRICING", priority: "MEDIUM", description: "",
  });
  const pageSize = 25;
  const [inqSummary, setInqSummary] = useState<InquirySummary | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const data = await fetchInquiries({ status: statusFilter || undefined, page, page_size: pageSize });
      setInquiries(data);
    } catch { /* ignore */ }
    setLoading(false);
  };

  useEffect(() => { load(); }, [statusFilter, page]);

  useEffect(() => {
    if (isProc) fetchInquirySummary().then(setInqSummary).catch(() => {});
  }, [isProc, inquiries]);

  useEffect(() => {
    if (!showCreate) return;
    api.get("/leads", { params: { page: 1, page_size: 200 } }).then((r) => setLeads(r.data.items || [])).catch(() => {});
  }, [showCreate]);

  const filtered = inquiries.filter((inq) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return inq.title.toLowerCase().includes(q) || inq.company_name?.toLowerCase().includes(q) ||
      inq.lead_id.toLowerCase().includes(q) || inq.created_by?.toLowerCase().includes(q) ||
      inq.assigned_to?.toLowerCase().includes(q);
  });

  const handleCreate = async () => {
    if (!createForm.title.trim() || !createForm.lead_id) return;
    await createInquiry(createForm);
    setShowCreate(false);
    setCreateForm({ lead_id: "", title: "", type: "PRICING", priority: "MEDIUM", description: "" });
    load();
  };

  return (
    <div className="p-5 lg:p-7 space-y-5 max-w-[1400px] mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-[13px] text-muted-foreground/60 font-medium mb-1">
            <MessageSquare className="w-4 h-4" />
            <span>{isProc ? "Procurement" : "Sales"} &gt; Inquiries</span>
          </div>
          <h1 className="text-2xl lg:text-3xl font-bold tracking-tight">
            {isProc ? "Inquiry Workspace" : "My Inquiries"}
          </h1>
          <p className="text-[14px] text-muted-foreground/60 mt-1">
            {filtered.length} inquiry{filtered.length !== 1 ? "ies" : ""}
            {statusFilter ? ` · ${DISPLAY_STATUS_LABELS[statusFilter] || statusFilter.replace(/_/g, " ")}` : ""}
          </p>
        </div>
        {isSales && (
          <Button onClick={() => setShowCreate(true)} className="gap-2 shrink-0">
            <Plus className="w-4 h-4" />New Inquiry
          </Button>
        )}
      </div>

      {/* Procurement Priority Widgets */}
      {isProc && inqSummary && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: "Due Today", value: inqSummary.eod_committed, color: "text-orange-600", bg: "bg-orange-50 border-orange-200", icon: Clock },
            { label: "Overdue", value: inqSummary.overdue, color: "text-red-600", bg: "bg-red-50 border-red-200", icon: AlertTriangle },
            { label: "Will Take Time", value: inqSummary.pending_response, color: "text-blue-600", bg: "bg-blue-50 border-blue-200", icon: Timer },
            { label: "Answered Today", value: inqSummary.responded_today, color: "text-emerald-600", bg: "bg-emerald-50 border-emerald-200", icon: CheckCircle2 },
          ].map((s) => (
            <div key={s.label} className={cn("rounded-xl border p-4 flex items-center gap-4", s.bg)}>
              <div className={cn("p-2.5 rounded-lg", s.bg)}><s.icon className={cn("w-5 h-5", s.color)} /></div>
              <div><p className={cn("text-2xl font-bold", s.color)}>{s.value}</p><p className="text-[12px] text-muted-foreground/70 font-medium">{s.label}</p></div>
            </div>
          ))}
        </div>
      )}

      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground/40" />
          <input type="text" placeholder={isProc ? "Search inquiry, requester, lead..." : "Search by title, company, lead ID..."}
            value={search} onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20" />
        </div>
        <select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
          className="h-10 rounded-lg border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20">
          {DISPLAY_FILTER_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {isProc ? o.label.replace("Awaiting Review", "Open").replace("Expected on Date", "Scheduled") : o.label}
            </option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className="text-center py-20 text-muted-foreground/50 text-sm">Loading...</div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-20 text-muted-foreground/50 text-sm">No inquiries found</div>
      ) : (
        <>
          {/* Sales View — Card List */}
          {isSales && (
            <div className="space-y-3">
              {filtered.map((inq) => {
                const displayStatus = DISPLAY_STATUS_LABELS[inq.status] || inq.status;
                const expectedText = getExpectedResponseText(inq.status, inq.expected_response_date);
                const situation = getDisplaySituation(inq.status, inq.expected_response_date);
                return (
                  <Card key={inq.id} className="cursor-pointer transition-all hover:shadow-sm border-l-4"
                    style={{ borderLeftColor: inq.status === "OVERDUE" ? "#ef4444" : inq.status === "EOD_COMMITTED" ? "#f97316" : inq.status === "RESPONDED" ? "#10b981" : "#e2e8f0" }}
                    onClick={() => setSelectedInquiry(inq)}>
                    <CardContent className="p-4">
                      <div className="grid grid-cols-12 gap-3 text-sm items-start">
                        <div className="col-span-12 md:col-span-3 min-w-0">
                          <h3 className="font-semibold text-sm truncate mb-1">{inq.title}</h3>
                          <span className={cn("text-[10px] font-semibold px-1.5 py-0.5 rounded-full border", DISPLAY_STATUS_COLORS[inq.status] || "")}>{displayStatus}</span>
                        </div>
                        <div className="col-span-6 md:col-span-2">
                          <p className="text-[11px] text-muted-foreground/50 font-medium uppercase tracking-wider mb-0.5">Lead</p>
                          <p className="text-[13px] font-medium truncate">{inq.company_name || inq.lead_id}</p>
                          <p className="text-[11px] text-muted-foreground/50 font-mono">{inq.lead_id}</p>
                        </div>
                        <div className="col-span-6 md:col-span-2">
                          <p className="text-[11px] text-muted-foreground/50 font-medium uppercase tracking-wider mb-0.5">Procurement</p>
                          <p className="text-[13px] font-medium truncate">{inq.assigned_to}</p>
                        </div>
                        <div className="col-span-6 md:col-span-2">
                          <p className="text-[11px] text-muted-foreground/50 font-medium uppercase tracking-wider mb-0.5">Expected Response</p>
                          <p className={cn("text-[13px] font-semibold", inq.status === "OVERDUE" ? "text-red-600" : inq.status === "RESPONDED" ? "text-emerald-600" : "text-foreground/80")}>{expectedText}</p>
                        </div>
                        <div className="col-span-6 md:col-span-2">
                          <p className="text-[11px] text-muted-foreground/50 font-medium uppercase tracking-wider mb-0.5">Status</p>
                          <p className="text-[12px] text-muted-foreground/70 line-clamp-1">{situation}</p>
                        </div>
                        <div className="col-span-12 md:col-span-1 text-right">
                          <p className="text-[11px] text-muted-foreground/50 font-medium uppercase tracking-wider mb-0.5">Updated</p>
                          <p className="text-[12px] text-muted-foreground/70">{timeAgo(inq.updated_at)}</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}

          {/* Procurement View — Table */}
          {isProc && (
            <div className="overflow-x-auto rounded-xl border border-border/60">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-muted/40 border-b border-border/60">
                    <th className="text-left px-4 py-3 text-[11px] font-semibold text-muted-foreground/60 uppercase tracking-wider">Inquiry</th>
                    <th className="text-left px-4 py-3 text-[11px] font-semibold text-muted-foreground/60 uppercase tracking-wider">Requested By</th>
                    <th className="text-left px-4 py-3 text-[11px] font-semibold text-muted-foreground/60 uppercase tracking-wider">Lead</th>
                    <th className="text-left px-4 py-3 text-[11px] font-semibold text-muted-foreground/60 uppercase tracking-wider">Due</th>
                    <th className="text-left px-4 py-3 text-[11px] font-semibold text-muted-foreground/60 uppercase tracking-wider">Age</th>
                    <th className="text-left px-4 py-3 text-[11px] font-semibold text-muted-foreground/60 uppercase tracking-wider">Priority</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((inq) => {
                    const dueClass = inq.status === "OVERDUE" ? "text-red-600 font-semibold" : inq.status === "EOD_COMMITTED" ? "text-orange-600 font-semibold" : inq.status === "RESPONDED" ? "text-emerald-600" : inq.status === "PENDING_RESPONSE" ? "text-blue-600" : "text-muted-foreground/70";
                    return (
                      <tr key={inq.id} className="border-b border-border/40 cursor-pointer hover:bg-muted/20 transition-colors"
                        onClick={() => setSelectedInquiry(inq)}>
                        <td className="px-4 py-3.5">
                          <p className="font-medium truncate max-w-[200px]">{inq.title}</p>
                          <span className={cn("text-[10px] font-semibold px-1.5 py-0.5 rounded-full border mt-1 inline-block", DISPLAY_STATUS_COLORS[inq.status] || "")}>
                            {DISPLAY_STATUS_LABELS[inq.status] || inq.status}
                          </span>
                        </td>
                        <td className="px-4 py-3.5"><p className="text-[13px]">{inq.created_by}</p></td>
                        <td className="px-4 py-3.5">
                          <p className="text-[13px] font-medium">{inq.company_name || "—"}</p>
                          <p className="text-[11px] text-muted-foreground/50 font-mono">{inq.lead_id}</p>
                        </td>
                        <td className="px-4 py-3.5">
                          <span className={cn("text-[13px]", dueClass)}>
                            {inq.status === "RESPONDED" || inq.status === "CLOSED" ? "Done" : inq.expected_response_date ? new Date(inq.expected_response_date).toLocaleDateString() : inq.status === "EOD_COMMITTED" ? "Today" : "—"}
                          </span>
                        </td>
                        <td className="px-4 py-3.5 text-[13px] text-muted-foreground/70">{timeAgo(inq.created_at)}</td>
                        <td className="px-4 py-3.5">
                          <span className={cn("text-[10px] font-semibold px-1.5 py-0.5 rounded", PRIORITY_COLORS[inq.priority] || "")}>{inq.priority}</span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {/* Pagination */}
      {filtered.length >= pageSize && (
        <div className="flex items-center justify-between pt-2">
          <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))} className="gap-1">
            <ChevronLeft className="w-4 h-4" />Previous
          </Button>
          <span className="text-sm text-muted-foreground/60">Page {page}</span>
          <Button variant="outline" size="sm" disabled={filtered.length < pageSize} onClick={() => setPage((p) => p + 1)} className="gap-1">
            Next<ChevronRight className="w-4 h-4" />
          </Button>
        </div>
      )}

      {/* Create Modal (Sales only) */}
      <Modal open={showCreate} onClose={() => setShowCreate(false)}>
        <div className="p-7 pb-2">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-xl font-bold tracking-tight">New Inquiry</h2>
            <Button variant="ghost" size="sm" onClick={() => setShowCreate(false)}><X className="w-4 h-4" /></Button>
          </div>
        </div>
        <div className="px-7 space-y-4">
          <div><label className="text-xs font-medium text-muted-foreground/70 mb-1.5 block">Lead *</label>
            <select value={createForm.lead_id} onChange={(e) => setCreateForm({ ...createForm, lead_id: e.target.value })}
              className="w-full rounded-lg border border-input bg-background px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20">
              <option value="">Select a lead...</option>
              {leads.map((l) => (<option key={l.lead_id} value={l.lead_id}>{l.company_name || l.lead_id} — {l.lead_id}</option>))}
            </select></div>
          <div><label className="text-xs font-medium text-muted-foreground/70 mb-1.5 block">Title *</label>
            <input type="text" value={createForm.title} onChange={(e) => setCreateForm({ ...createForm, title: e.target.value })}
              placeholder="e.g., Pricing for bulk order"
              className="w-full rounded-lg border border-input bg-background px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20" /></div>
          <div className="grid grid-cols-2 gap-4">
            <div><label className="text-xs font-medium text-muted-foreground/70 mb-1.5 block">Type</label>
              <select value={createForm.type} onChange={(e) => setCreateForm({ ...createForm, type: e.target.value })}
                className="w-full rounded-lg border border-input bg-background px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20">
                {INQUIRY_TYPES.map((t) => (<option key={t} value={t}>{t}</option>))}
              </select></div>
            <div><label className="text-xs font-medium text-muted-foreground/70 mb-1.5 block">Priority</label>
              <select value={createForm.priority} onChange={(e) => setCreateForm({ ...createForm, priority: e.target.value })}
                className="w-full rounded-lg border border-input bg-background px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20">
                {INQUIRY_PRIORITIES.map((p) => (<option key={p} value={p}>{p}</option>))}
              </select></div>
          </div>
          <div><label className="text-xs font-medium text-muted-foreground/70 mb-1.5 block">Description</label>
            <textarea value={createForm.description} onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
              placeholder="What do you need from procurement?" rows={3}
              className="w-full rounded-lg border border-input bg-background px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20" /></div>
        </div>
        <div className="flex items-center justify-end gap-3 px-7 py-5">
          <Button variant="outline" onClick={() => setShowCreate(false)}>Cancel</Button>
          <Button onClick={handleCreate} disabled={!createForm.title.trim() || !createForm.lead_id} className="px-6">Submit Inquiry</Button>
        </div>
      </Modal>

      {/* Inquiry Detail Modal */}
      {selectedInquiry && (
        <InquiryWorkflowModal inquiry={selectedInquiry} onClose={() => setSelectedInquiry(null)} />
      )}
    </div>
  );
}
