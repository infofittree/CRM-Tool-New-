import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import Modal from "@/components/ui/modal";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth";
import api, { Lead } from "@/lib/api";
import {
  fetchInquiries, fetchInquirySummary, updateInquiry, createInquiry, commitInquiry,
  Inquiry, InquirySummary, InquiryCreate,
  INQUIRY_TYPES, INQUIRY_PRIORITIES, COMMITMENT_LABELS,
  DISPLAY_STATUS_LABELS, DISPLAY_STATUS_COLORS, DISPLAY_FILTER_OPTIONS,
  getDisplaySituation, getExpectedResponseText,
} from "@/lib/inquiries";
import {
  MessageSquare, Search, ChevronLeft, ChevronRight, Clock, CheckCircle2, X, ExternalLink, Plus, AlertTriangle,
  User, Calendar, Timer, ArrowRight, Building2, Flag,
} from "lucide-react";

/* ── Shared ── */

const PRIORITY_COLORS: Record<string, string> = {
  LOW: "bg-slate-50 text-slate-500", MEDIUM: "bg-blue-50 text-blue-700",
  HIGH: "bg-orange-50 text-orange-700", URGENT: "bg-red-50 text-red-700",
};

const TYPE_COLORS: Record<string, string> = {
  PRICING: "bg-violet-50 text-violet-700", AVAILABILITY: "bg-cyan-50 text-cyan-700",
  PACKAGING: "bg-teal-50 text-teal-700", DOCUMENTATION: "bg-indigo-50 text-indigo-700",
  MOQ: "bg-amber-50 text-amber-700", LEAD_TIME: "bg-rose-50 text-rose-700",
  CUSTOM: "bg-slate-100 text-slate-600",
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

function daysRemaining(dateStr: string | null): string | null {
  if (!dateStr) return null;
  const diff = Math.ceil((new Date(dateStr).getTime() - Date.now()) / (1000 * 60 * 60 * 24));
  if (diff < 0) return `${Math.abs(diff)}d late`;
  if (diff === 0) return "Today";
  return `${diff}d`;
}

/* ── Timeline step for drawer ── */

function TimelineStep({ done, label, sub, isLast }: { done: boolean; label: string; sub?: string; isLast?: boolean }) {
  return (
    <div className="flex gap-3">
      <div className="flex flex-col items-center">
        <div className={cn("w-3 h-3 rounded-full border-2 shrink-0 mt-0.5", done ? "bg-emerald-500 border-emerald-500" : "bg-white border-muted-foreground/30")} />
        {!isLast && <div className={cn("w-px flex-1 my-0.5", done ? "bg-emerald-200" : "bg-muted-foreground/15")} />}
      </div>
      <div className={cn("pb-4 text-sm", done ? "text-foreground/80" : "text-muted-foreground/50")}>
        <p className="font-medium">{label}</p>
        {sub && <p className="text-[12px] text-muted-foreground/60">{sub}</p>}
      </div>
    </div>
  );
}

/* ── Main Component ── */

export default function InquiryPortal() {
  const { user } = useAuth();
  const navigate = useNavigate();
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

  /* ── Procurement-only state ── */
  const [committing, setCommitting] = useState(false);
  const [commitType, setCommitType] = useState<string>("BY_EOD");
  const [commitDate, setCommitDate] = useState("");
  const [commitResponse, setCommitResponse] = useState("");
  const [respondText, setRespondText] = useState("");
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

  /* ── Handlers ── */

  const handleCreate = async () => {
    if (!createForm.title.trim() || !createForm.lead_id) return;
    await createInquiry(createForm);
    setShowCreate(false);
    setCreateForm({ lead_id: "", title: "", type: "PRICING", priority: "MEDIUM", description: "" });
    load();
  };

  const handleCommit = async () => {
    if (!selectedInquiry) return;
    await commitInquiry(selectedInquiry.id, {
      commitment_type: commitType,
      expected_response_date: commitType === "WILL_TAKE_TIME" && commitDate ? new Date(commitDate).toISOString() : undefined,
      response: commitType === "ANSWER_NOW" ? commitResponse : undefined,
    });
    setCommitting(false);
    setCommitType("BY_EOD");
    setCommitDate("");
    setCommitResponse("");
    load();
    const updated = await fetchInquiries({ lead_id: selectedInquiry.lead_id });
    setSelectedInquiry(updated.find((i) => i.id === selectedInquiry.id) || null);
  };

  const handleRespond = async (id: number) => {
    if (!respondText.trim()) return;
    await updateInquiry(id, { response: respondText });
    setRespondText("");
    load();
    if (selectedInquiry?.id === id) {
      const updated = await fetchInquiries({ lead_id: selectedInquiry.lead_id });
      setSelectedInquiry(updated.find((i) => i.id === id) || null);
    }
  };

  const handleClose = async (id: number) => {
    await updateInquiry(id, { status: "CLOSED" });
    load();
    if (selectedInquiry?.id === id) setSelectedInquiry({ ...selectedInquiry, status: "CLOSED" });
  };

  /* ── Render ── */

  return (
    <div className="p-5 lg:p-7 space-y-5 max-w-[1400px] mx-auto">
      {/* ── Header ── */}
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

      {/* ── Procurement Priority Widgets ── */}
      {isProc && inqSummary && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: "Due Today", value: inqSummary.eod_committed, color: "text-orange-600", bg: "bg-orange-50 border-orange-200", icon: Clock },
            { label: "Overdue", value: inqSummary.overdue, color: "text-red-600", bg: "bg-red-50 border-red-200", icon: AlertTriangle },
            { label: "Will Take Time", value: inqSummary.pending_response, color: "text-blue-600", bg: "bg-blue-50 border-blue-200", icon: Timer },
            { label: "Answered Today", value: inqSummary.responded_today, color: "text-emerald-600", bg: "bg-emerald-50 border-emerald-200", icon: CheckCircle2 },
          ].map((s) => (
            <div key={s.label} className={cn("rounded-xl border p-4 flex items-center gap-4", s.bg)}>
              <div className={cn("p-2.5 rounded-lg", s.bg)}>
                <s.icon className={cn("w-5 h-5", s.color)} />
              </div>
              <div>
                <p className={cn("text-2xl font-bold", s.color)}>{s.value}</p>
                <p className="text-[12px] text-muted-foreground/70 font-medium">{s.label}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── Filters ── */}
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
          {/* ══════════════════════════════════════════ */}
          {/* SALES VIEW — Card List                     */}
          {/* ══════════════════════════════════════════ */}
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
                        {/* Inquiry */}
                        <div className="col-span-12 md:col-span-3 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <h3 className="font-semibold text-sm truncate">{inq.title}</h3>
                          </div>
                          <span className={cn("text-[10px] font-semibold px-1.5 py-0.5 rounded-full border shrink-0", DISPLAY_STATUS_COLORS[inq.status] || "")}>
                            {displayStatus}
                          </span>
                        </div>
                        {/* Lead */}
                        <div className="col-span-6 md:col-span-2">
                          <p className="text-[11px] text-muted-foreground/50 font-medium uppercase tracking-wider mb-0.5">Lead</p>
                          <p className="text-[13px] font-medium truncate">{inq.company_name || inq.lead_id}</p>
                          <p className="text-[11px] text-muted-foreground/50 font-mono">{inq.lead_id}</p>
                        </div>
                        {/* Assigned To */}
                        <div className="col-span-6 md:col-span-2">
                          <p className="text-[11px] text-muted-foreground/50 font-medium uppercase tracking-wider mb-0.5">Procurement</p>
                          <p className="text-[13px] font-medium truncate">{inq.assigned_to}</p>
                        </div>
                        {/* Expected Response */}
                        <div className="col-span-6 md:col-span-2">
                          <p className="text-[11px] text-muted-foreground/50 font-medium uppercase tracking-wider mb-0.5">Expected Response</p>
                          <p className={cn("text-[13px] font-semibold", inq.status === "OVERDUE" ? "text-red-600" : inq.status === "RESPONDED" ? "text-emerald-600" : "text-foreground/80")}>
                            {expectedText}
                          </p>
                        </div>
                        {/* Current Situation */}
                        <div className="col-span-6 md:col-span-2">
                          <p className="text-[11px] text-muted-foreground/50 font-medium uppercase tracking-wider mb-0.5">Status</p>
                          <p className="text-[12px] text-muted-foreground/70 line-clamp-1">{situation}</p>
                        </div>
                        {/* Last Updated */}
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

          {/* ══════════════════════════════════════════ */}
          {/* PROCUREMENT VIEW — Table                   */}
          {/* ══════════════════════════════════════════ */}
          {isProc && (
            <div className="overflow-x-auto rounded-xl border border-border/60">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-muted/40 border-b border-border/60">
                    <th className="text-left px-4 py-3 text-[11px] font-semibold text-muted-foreground/60 uppercase tracking-wider">Inquiry</th>
                    <th className="text-left px-4 py-3 text-[11px] font-semibold text-muted-foreground/60 uppercase tracking-wider">Requested By</th>
                    <th className="text-left px-4 py-3 text-[11px] font-semibold text-muted-foreground/60 uppercase tracking-wider">Lead</th>
                    <th className="text-left px-4 py-3 text-[11px] font-semibold text-muted-foreground/60 uppercase tracking-wider">Commitment</th>
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
                        <td className="px-4 py-3.5">
                          <p className="text-[13px]">{inq.created_by}</p>
                        </td>
                        <td className="px-4 py-3.5">
                          <p className="text-[13px] font-medium">{inq.company_name || "—"}</p>
                          <p className="text-[11px] text-muted-foreground/50 font-mono">{inq.lead_id}</p>
                        </td>
                        <td className="px-4 py-3.5">
                          {inq.commitment_type ? (
                            <span className="text-[12px]">{COMMITMENT_LABELS[inq.commitment_type] || inq.commitment_type}</span>
                          ) : (
                            <span className="text-[12px] text-muted-foreground/40">—</span>
                          )}
                        </td>
                        <td className="px-4 py-3.5">
                          <span className={cn("text-[13px]", dueClass)}>
                            {inq.status === "RESPONDED" || inq.status === "CLOSED"
                              ? "Done"
                              : inq.expected_response_date
                                ? new Date(inq.expected_response_date).toLocaleDateString()
                                : inq.status === "EOD_COMMITTED"
                                  ? "Today"
                                  : "—"}
                          </span>
                        </td>
                        <td className="px-4 py-3.5 text-[13px] text-muted-foreground/70">
                          {timeAgo(inq.created_at)}
                        </td>
                        <td className="px-4 py-3.5">
                          <span className={cn("text-[10px] font-semibold px-1.5 py-0.5 rounded", PRIORITY_COLORS[inq.priority] || "")}>
                            {inq.priority}
                          </span>
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

      {/* ── Pagination ── */}
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

      {/* ── Create Modal (Sales only) ── */}
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

      {/* ══════════════════════════════════════════ */}
      {/* DRAWER                                      */}
      {/* ══════════════════════════════════════════ */}
      {selectedInquiry && (
        <>
          <div className="fixed inset-0 z-40 bg-black/20" onClick={() => { setSelectedInquiry(null); setCommitting(false); }} />
          <div className="fixed top-0 right-0 z-50 h-full w-full max-w-lg bg-white shadow-2xl border-l border-border overflow-y-auto">

            {/* ── Drawer Header ── */}
            <div className="sticky top-0 bg-white border-b border-border z-10 px-5 py-4 flex items-center justify-between">
              <div className="flex items-center gap-2 min-w-0">
                <span className={cn("text-[11px] font-semibold px-2 py-0.5 rounded-full border shrink-0", DISPLAY_STATUS_COLORS[selectedInquiry.status] || "")}>
                  {isSales ? (DISPLAY_STATUS_LABELS[selectedInquiry.status] || selectedInquiry.status) : selectedInquiry.status.replace(/_/g, " ")}
                </span>
                <h2 className="font-bold text-sm truncate">{selectedInquiry.title}</h2>
              </div>
              <Button variant="ghost" size="sm" onClick={() => { setSelectedInquiry(null); setCommitting(false); }}><X className="w-4 h-4" /></Button>
            </div>

            <div className="p-5 space-y-5">

              {/* ══════════════════════════════════ */}
              {/* SALES DRAWER                        */}
              {/* ══════════════════════════════════ */}
              {isSales && (
                <>
                  {/* Response Hero */}
                  {selectedInquiry.response ? (
                    <div className="rounded-xl bg-gradient-to-br from-emerald-50 to-white border border-emerald-200 p-5 space-y-3">
                      <div className="flex items-center gap-2 text-emerald-700">
                        <CheckCircle2 className="w-5 h-5" />
                        <span className="font-bold text-base">Procurement Response</span>
                      </div>
                      <p className="text-sm leading-relaxed whitespace-pre-wrap">{selectedInquiry.response}</p>
                      <div className="flex items-center gap-4 text-[12px] text-muted-foreground/60 pt-1 border-t border-emerald-100">
                        {selectedInquiry.assigned_to && (
                          <span className="flex items-center gap-1"><User className="w-3.5 h-3.5" />{selectedInquiry.assigned_to}</span>
                        )}
                        {selectedInquiry.responded_at && (
                          <span className="flex items-center gap-1"><Calendar className="w-3.5 h-3.5" />{new Date(selectedInquiry.responded_at).toLocaleDateString()}</span>
                        )}
                      </div>
                    </div>
                  ) : (
                    /* Status Banner (before response) */
                    <div className={cn("rounded-xl border p-4 flex items-start gap-3",
                      selectedInquiry.status === "OVERDUE" ? "bg-red-50 border-red-200" : "bg-amber-50 border-amber-200")}>
                      <div className={cn("p-2 rounded-full shrink-0", selectedInquiry.status === "OVERDUE" ? "bg-red-100" : "bg-amber-100")}>
                        {selectedInquiry.status === "OVERDUE" ? (
                          <AlertTriangle className="w-5 h-5 text-red-600" />
                        ) : selectedInquiry.status === "EOD_COMMITTED" ? (
                          <Clock className="w-5 h-5 text-orange-600" />
                        ) : (
                          <Timer className="w-5 h-5 text-amber-600" />
                        )}
                      </div>
                      <div>
                        <p className={cn("font-semibold text-sm", selectedInquiry.status === "OVERDUE" ? "text-red-800" : "text-amber-800")}>
                          {selectedInquiry.status === "EOD_COMMITTED"
                            ? "Procurement will respond by end of day"
                            : selectedInquiry.status === "OVERDUE"
                              ? "Response is overdue"
                              : selectedInquiry.status === "PENDING_RESPONSE"
                                ? selectedInquiry.expected_response_date
                                  ? `Procurement expects to respond by ${new Date(selectedInquiry.expected_response_date).toLocaleDateString()}`
                                  : "Procurement is reviewing this inquiry"
                                : "Awaiting procurement review"}
                        </p>
                        <p className="text-[12px] text-muted-foreground/70 mt-1">
                          {selectedInquiry.assigned_to
                            ? `Contact: ${selectedInquiry.assigned_to}`
                            : "Assigning to procurement..."}
                        </p>
                      </div>
                    </div>
                  )}

                  {/* Timeline */}
                  <div>
                    <p className="text-[11px] font-semibold text-muted-foreground/50 uppercase tracking-wider mb-3">Timeline</p>
                    <div className="pl-1">
                      <TimelineStep done label="Inquiry Created" sub={new Date(selectedInquiry.created_at).toLocaleString()} />
                      <TimelineStep done={!!selectedInquiry.assigned_to} label="Assigned to Procurement" sub={selectedInquiry.assigned_to || undefined} />
                      <TimelineStep done={selectedInquiry.status === "EOD_COMMITTED" || selectedInquiry.status === "PENDING_RESPONSE" || selectedInquiry.status === "RESPONDED" || selectedInquiry.status === "OVERDUE" || selectedInquiry.status === "CLOSED"}
                        label="Response Commitment"
                        sub={selectedInquiry.commitment_type ? (COMMITMENT_LABELS[selectedInquiry.commitment_type] || selectedInquiry.commitment_type) : undefined} />
                      <TimelineStep isLast done={!!selectedInquiry.response}
                        label="Response Submitted"
                        sub={selectedInquiry.responded_at ? new Date(selectedInquiry.responded_at).toLocaleString() : undefined} />
                    </div>
                  </div>

                  {/* People & Dates */}
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div><p className="text-[11px] font-semibold text-muted-foreground/50 uppercase tracking-wider">Created By</p><p className="font-medium">{selectedInquiry.created_by}</p></div>
                    <div><p className="text-[11px] font-semibold text-muted-foreground/50 uppercase tracking-wider">Procurement Contact</p><p className="font-medium">{selectedInquiry.assigned_to}</p></div>
                    <div><p className="text-[11px] font-semibold text-muted-foreground/50 uppercase tracking-wider">Created</p><p className="font-medium">{new Date(selectedInquiry.created_at).toLocaleDateString()}</p></div>
                    <div><p className="text-[11px] font-semibold text-muted-foreground/50 uppercase tracking-wider">Last Updated</p><p className="font-medium">{timeAgo(selectedInquiry.updated_at)}</p></div>
                  </div>

                  {/* Lead link */}
                  <div>
                    <p className="text-[11px] font-semibold text-muted-foreground/50 uppercase tracking-wider mb-1">Lead</p>
                    <Button variant="outline" size="sm" className="gap-1.5 text-xs" onClick={() => { navigate(`/leads/${selectedInquiry.lead_id}`); setSelectedInquiry(null); }}>
                      <Building2 className="w-3.5 h-3.5" />{selectedInquiry.company_name || selectedInquiry.lead_id}<span className="text-muted-foreground/50 font-mono">#{selectedInquiry.lead_id}</span>
                    </Button>
                  </div>

                  {/* Original Inquiry */}
                  {selectedInquiry.description && (
                    <div>
                      <p className="text-[11px] font-semibold text-muted-foreground/50 uppercase tracking-wider mb-1.5">Original Inquiry</p>
                      <div className="bg-muted/30 rounded-lg p-3.5 text-sm leading-relaxed whitespace-pre-wrap">{selectedInquiry.description}</div>
                    </div>
                  )}
                </>
              )}

              {/* ══════════════════════════════════ */}
              {/* PROCUREMENT DRAWER                  */}
              {/* ══════════════════════════════════ */}
              {isProc && (
                <>
                  {/* Inquiry Information */}
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div><p className="text-[11px] font-semibold text-muted-foreground/50 uppercase tracking-wider">Requested By</p><p className="font-medium">{selectedInquiry.created_by}</p></div>
                    <div><p className="text-[11px] font-semibold text-muted-foreground/50 uppercase tracking-wider">Assigned To</p><p className="font-medium">{selectedInquiry.assigned_to}</p></div>
                    <div><p className="text-[11px] font-semibold text-muted-foreground/50 uppercase tracking-wider">Type</p><p className="font-medium">{selectedInquiry.type}</p></div>
                    <div><p className="text-[11px] font-semibold text-muted-foreground/50 uppercase tracking-wider">Priority</p>
                      <span className={cn("text-[10px] font-semibold px-1.5 py-0.5 rounded", PRIORITY_COLORS[selectedInquiry.priority] || "")}>{selectedInquiry.priority}</span>
                    </div>
                    <div><p className="text-[11px] font-semibold text-muted-foreground/50 uppercase tracking-wider">Created</p><p className="font-medium">{new Date(selectedInquiry.created_at).toLocaleString()}</p></div>
                    <div><p className="text-[11px] font-semibold text-muted-foreground/50 uppercase tracking-wider">Age</p><p className="font-medium">{timeAgo(selectedInquiry.created_at)}</p></div>
                  </div>

                  {/* Lead link */}
                  <div>
                    <p className="text-[11px] font-semibold text-muted-foreground/50 uppercase tracking-wider mb-1">Lead</p>
                    <Button variant="outline" size="sm" className="gap-1.5 text-xs" onClick={() => { navigate(`/leads/${selectedInquiry.lead_id}`); setSelectedInquiry(null); }}>
                      <Building2 className="w-3.5 h-3.5" />{selectedInquiry.company_name || selectedInquiry.lead_id}<span className="text-muted-foreground/50 font-mono">#{selectedInquiry.lead_id}</span>
                    </Button>
                  </div>

                  {/* Description */}
                  {selectedInquiry.description && (
                    <div><p className="text-[11px] font-semibold text-muted-foreground/50 uppercase tracking-wider mb-1.5">Inquiry Details</p>
                      <div className="bg-muted/30 rounded-lg p-3.5 text-sm leading-relaxed whitespace-pre-wrap">{selectedInquiry.description}</div></div>
                  )}

                  {/* Response (if already answered) */}
                  {selectedInquiry.response ? (
                    <div>
                      <p className="text-[11px] font-semibold text-emerald-600 uppercase tracking-wider mb-1.5">
                        Your Response · {selectedInquiry.responded_at ? new Date(selectedInquiry.responded_at).toLocaleDateString() : ""}
                      </p>
                      <div className="bg-emerald-50/50 rounded-lg p-3.5 text-sm leading-relaxed whitespace-pre-wrap">{selectedInquiry.response}</div>
                      <div className="flex items-center gap-2 mt-3">
                        <Button size="sm" variant="outline" className="gap-1.5" onClick={() => handleClose(selectedInquiry.id)}>
                          <CheckCircle2 className="w-3.5 h-3.5" />Close Inquiry
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <>
                      {/* Commitment Cards */}
                      {!committing && (
                        <div>
                          <p className="text-[11px] font-semibold text-muted-foreground/50 uppercase tracking-wider mb-3">Commitment Actions</p>
                          <div className="space-y-2.5">
                            <button onClick={() => { setCommitting(true); setCommitType("ANSWER_NOW"); }}
                              className="w-full text-left flex items-center gap-4 p-4 rounded-xl border-2 border-emerald-200 hover:border-emerald-400 hover:bg-emerald-50/50 transition-all group">
                              <div className="w-10 h-10 rounded-lg bg-emerald-100 flex items-center justify-center group-hover:bg-emerald-200 transition-colors">
                                <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                              </div>
                              <div className="flex-1">
                                <p className="font-semibold text-sm">Answer Now</p>
                                <p className="text-[12px] text-muted-foreground/60">Respond immediately</p>
                              </div>
                              <ArrowRight className="w-4 h-4 text-muted-foreground/30 group-hover:text-emerald-600 transition-colors" />
                            </button>
                            <button onClick={() => { setCommitting(true); setCommitType("BY_EOD"); }}
                              className="w-full text-left flex items-center gap-4 p-4 rounded-xl border-2 border-orange-200 hover:border-orange-400 hover:bg-orange-50/50 transition-all group">
                              <div className="w-10 h-10 rounded-lg bg-orange-100 flex items-center justify-center group-hover:bg-orange-200 transition-colors">
                                <Clock className="w-5 h-5 text-orange-600" />
                              </div>
                              <div className="flex-1">
                                <p className="font-semibold text-sm">By End Of Day</p>
                                <p className="text-[12px] text-muted-foreground/60">Respond before EOD</p>
                              </div>
                              <ArrowRight className="w-4 h-4 text-muted-foreground/30 group-hover:text-orange-600 transition-colors" />
                            </button>
                            <button onClick={() => { setCommitting(true); setCommitType("WILL_TAKE_TIME"); }}
                              className="w-full text-left flex items-center gap-4 p-4 rounded-xl border-2 border-blue-200 hover:border-blue-400 hover:bg-blue-50/50 transition-all group">
                              <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center group-hover:bg-blue-200 transition-colors">
                                <Calendar className="w-5 h-5 text-blue-600" />
                              </div>
                              <div className="flex-1">
                                <p className="font-semibold text-sm">Will Take Time</p>
                                <p className="text-[12px] text-muted-foreground/60">Set a future response date</p>
                              </div>
                              <ArrowRight className="w-4 h-4 text-muted-foreground/30 group-hover:text-blue-600 transition-colors" />
                            </button>
                          </div>
                        </div>
                      )}

                      {/* Commitment Form */}
                      {committing && (
                        <div className="rounded-xl border-2 border-amber-200 bg-amber-50/20 p-5 space-y-4">
                          <p className="font-bold text-sm flex items-center gap-2">
                            {commitType === "ANSWER_NOW" ? <CheckCircle2 className="w-4 h-4 text-emerald-600" /> : commitType === "BY_EOD" ? <Clock className="w-4 h-4 text-orange-600" /> : <Calendar className="w-4 h-4 text-blue-600" />}
                            {commitType === "ANSWER_NOW" ? "Respond Now" : commitType === "BY_EOD" ? "Commit By End Of Day" : "Set Expected Response Date"}
                          </p>

                          {commitType === "ANSWER_NOW" && (
                            <div>
                              <label className="text-xs font-medium text-muted-foreground/70 mb-1.5 block">Your Response *</label>
                              <textarea value={commitResponse} onChange={(e) => setCommitResponse(e.target.value)} placeholder="Pricing, MOQ, lead time, or any relevant information..." rows={5}
                                className="w-full rounded-lg border border-input bg-background px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20" />
                            </div>
                          )}

                          {commitType === "BY_EOD" && (
                            <div className="bg-orange-50 rounded-lg p-4 text-[13px] text-orange-800 space-y-1">
                              <p className="font-semibold">One-click commitment</p>
                              <p className="text-orange-600/70">Sales will see: <strong>Expected Today</strong></p>
                            </div>
                          )}

                          {commitType === "WILL_TAKE_TIME" && (
                            <div>
                              <label className="text-xs font-medium text-muted-foreground/70 mb-1.5 block">Expected Response Date *</label>
                              <input type="date" value={commitDate} onChange={(e) => setCommitDate(e.target.value)}
                                className="w-full rounded-lg border border-input bg-background px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20" />
                            </div>
                          )}

                          <div className="flex items-center gap-2 pt-1">
                            <Button size="sm" onClick={handleCommit}
                              disabled={commitType === "ANSWER_NOW" && !commitResponse.trim() || commitType === "WILL_TAKE_TIME" && !commitDate}
                              className="px-5">
                              {commitType === "ANSWER_NOW" ? "Submit Response" : commitType === "BY_EOD" ? "Confirm EOD Commitment" : "Set Date"}
                            </Button>
                            <Button size="sm" variant="outline" onClick={() => setCommitting(false)}>Cancel</Button>
                          </div>
                        </div>
                      )}

                      {/* Respond textarea fallback */}
                      {!committing && !selectedInquiry.response && selectedInquiry.status === "RESPONDED" && (
                        <div>
                          <p className="text-[11px] font-semibold text-muted-foreground/50 uppercase tracking-wider mb-1.5">Response</p>
                          <textarea placeholder="Type your response..." value={respondText} onChange={(e) => setRespondText(e.target.value)} rows={4}
                            className="w-full rounded-lg border border-input bg-background p-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20" />
                          <div className="flex items-center gap-2 mt-2">
                            <Button size="sm" onClick={() => handleRespond(selectedInquiry.id)} disabled={!respondText.trim()}>Send Response</Button>
                          </div>
                        </div>
                      )}
                    </>
                  )}

                  {/* Previous commitment info */}
                  {selectedInquiry.commitment_type && selectedInquiry.status !== "RESPONDED" && selectedInquiry.status !== "CLOSED" && !committing && (
                    <div className="rounded-lg bg-muted/30 p-3.5 space-y-1.5 text-sm">
                      <p className="text-[11px] font-semibold text-muted-foreground/50 uppercase tracking-wider">Current Commitment</p>
                      <p><span className="text-muted-foreground/60">Type:</span> {COMMITMENT_LABELS[selectedInquiry.commitment_type] || selectedInquiry.commitment_type}</p>
                      {selectedInquiry.expected_response_date && <p><span className="text-muted-foreground/60">Due:</span> {new Date(selectedInquiry.expected_response_date).toLocaleDateString()}</p>}
                      {selectedInquiry.committed_at && <p><span className="text-muted-foreground/60">Committed:</span> {new Date(selectedInquiry.committed_at).toLocaleString()}</p>}
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
