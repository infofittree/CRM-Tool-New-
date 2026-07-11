import { useState, useMemo, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useLeads, useLeadFilterOptions } from "@/hooks/useLeads";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn, scoreBand } from "@/lib/utils";
import {
  Plus, Search, ChevronLeft, ChevronRight, ChevronDown, X,
  Building2, Globe, Phone, User, ArrowUpRight, Filter,
} from "lucide-react";

const STATUSES = ["", "Prospect", "Requirement Qualified", "Technical Discussion", "Quotation Sent", "Sample Sent", "Negotiation", "Trial Order", "Nurturing", "Order Closed", "Lost"];

const STATUS_PILLS: Record<string, string> = {
  "Prospect": "bg-slate-100 text-slate-700",
  "Requirement Qualified": "bg-blue-50 text-blue-700",
  "Technical Discussion": "bg-cyan-50 text-cyan-700",
  "Quotation Sent": "bg-emerald-50 text-emerald-700",
  "Sample Sent": "bg-lime-50 text-lime-700",
  "Negotiation": "bg-amber-50 text-amber-700",
  "Trial Order": "bg-orange-50 text-orange-700",
  "Nurturing": "bg-purple-50 text-purple-700",
  "Order Closed": "bg-green-50 text-green-700",
  "Lost": "bg-red-50 text-red-700",
};

const PRIORITY_PILLS: Record<string, string> = {
  HIGH: "bg-red-50 text-red-700",
  MEDIUM: "bg-amber-50 text-amber-700",
  LOW: "bg-blue-50 text-blue-700",
};

const AVATAR_GRADIENTS = [
  "from-primary/70 to-primary",
  "from-purple-500 to-purple-600",
  "from-amber-500 to-orange-600",
  "from-cyan-500 to-blue-600",
  "from-pink-500 to-rose-600",
  "from-emerald-500 to-teal-600",
];

function FilterDropdown({ label, options, value, onChange }: {
  label: string; options: string[]; value: string; onChange: (v: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className={cn(
          "flex items-center gap-1 text-[11px] font-semibold uppercase tracking-wider transition-colors duration-180",
          value ? "text-primary" : "text-muted-foreground/50 hover:text-muted-foreground",
        )}
      >
        {label}
        <ChevronDown className={cn("w-3 h-3 transition-transform duration-180", open && "rotate-180")} />
        {value && <X className="w-3 h-3 ml-0.5 hover:text-destructive transition-colors" onClick={(e) => { e.stopPropagation(); onChange(""); }} />}
      </button>
      {open && (
        <div className="absolute top-full left-0 mt-1.5 z-50 bg-white border border-border/60 rounded-xl shadow-[var(--shadow-dropdown)] py-1 min-w-[160px] max-h-[240px] overflow-y-auto animate-slide-down">
          <button
            onClick={() => { onChange(""); setOpen(false); }}
            className={cn("w-full text-left px-3 py-2 text-xs hover:bg-muted/40 transition-colors duration-150", !value && "font-semibold text-primary")}
          >
            All {label}s
          </button>
          {options.map((opt) => (
            <button
              key={opt}
              onClick={() => { onChange(opt); setOpen(false); }}
              className={cn("w-full text-left px-3 py-2 text-xs hover:bg-muted/40 transition-colors duration-150", value === opt && "font-semibold text-primary bg-primary/5")}
            >
              {opt || "—"}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function LeadManagement() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [countryFilter, setCountryFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [assignedFilter, setAssignedFilter] = useState("");
  const [scoreFilter, setScoreFilter] = useState("");
  const [productFilter, setProductFilter] = useState("");
  const pageSize = 25;
  const { data, isLoading } = useLeads(page, pageSize, search, status, countryFilter, priorityFilter, assignedFilter);
  const { data: filterOptions } = useLeadFilterOptions();
  const navigate = useNavigate();

  const totalPages = data ? Math.ceil(data.total / pageSize) : 1;

  // Use backend-provided unique values for filter dropdowns (no duplicates)
  const uniqueCountries = filterOptions?.countries || [];
  const uniquePriorities = filterOptions?.priorities || [];
  const uniqueAssigned = filterOptions?.assigned || [];
  const uniqueScores = ["HOT", "WARM", "COLD"];

  // Client-side filtering for score and product
  const filteredItems = useMemo(() => {
    if (!data?.items) return [];
    return data.items.filter((l: any) => {
      if (scoreFilter) {
        const band = scoreBand(l.lead_score);
        if (band.label !== scoreFilter) return false;
      }
      if (productFilter) {
        const pi = (l.product_interest || "").toLowerCase();
        if (!pi.includes(productFilter.toLowerCase())) return false;
      }
      return true;
    });
  }, [data, scoreFilter, productFilter]);

  const hasActiveFilters = countryFilter || priorityFilter || assignedFilter || scoreFilter || productFilter;
  const uniqueProducts = filterOptions?.products || [];

  return (
    <div className="p-5 lg:p-7 space-y-5 max-w-[1400px] mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-[13px] text-muted-foreground/60 font-medium mb-1">
            <Building2 className="w-4 h-4" />
            <span>Lead database</span>
          </div>
          <h1 className="text-2xl lg:text-3xl font-bold tracking-tight">Leads</h1>
          {data && (
            <p className="text-[14px] text-muted-foreground/60 mt-1">
              {filteredItems.length}{hasActiveFilters ? ` of ${data.total}` : ""} lead{(hasActiveFilters ? filteredItems.length : data.total) !== 1 ? "s" : ""} in pipeline
              {hasActiveFilters && (
                <button onClick={() => { setCountryFilter(""); setPriorityFilter(""); setAssignedFilter(""); setScoreFilter(""); setProductFilter(""); }} className="ml-2 text-primary hover:underline text-xs">
                  Clear filters
                </button>
              )}
            </p>
          )}
        </div>
        <Button onClick={() => navigate("/data-entry")} className="gap-2 shrink-0">
          <Plus className="w-4 h-4" />
          New Lead
        </Button>
      </div>

      {/* Search + Status Filter */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground/40" />
          <input
            type="text"
            placeholder="Search by company, contact, email..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            className="w-full h-10 pl-9 pr-4 rounded-xl border border-input bg-background text-sm transition-all duration-180 placeholder:text-muted-foreground/40 hover:border-muted-foreground/25 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/15 focus-visible:border-primary/40"
          />
        </div>
        <select
          value={status}
          onChange={(e) => { setStatus(e.target.value); setPage(1); }}
          className="h-10 px-3 rounded-xl border border-input bg-background text-sm transition-all duration-150 hover:border-muted-foreground/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/30 appearance-none cursor-pointer"
        >
          {STATUSES.map((s) => (
            <option key={s} value={s}>{s || "All Statuses"}</option>
          ))}
        </select>
        <select
          value={assignedFilter}
          onChange={(e) => { setAssignedFilter(e.target.value); setPage(1); }}
          className="h-10 px-3 rounded-xl border border-input bg-background text-sm transition-all duration-150 hover:border-muted-foreground/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/30 appearance-none cursor-pointer"
        >
          <option value="">All Salespeople</option>
          {uniqueAssigned.map((name) => (
            <option key={name} value={name}>{name}</option>
          ))}
        </select>
        {uniqueProducts.length > 0 && (
          <select
            value={productFilter}
            onChange={(e) => { setProductFilter(e.target.value); setPage(1); }}
            className="h-10 px-3 rounded-xl border border-input bg-background text-sm transition-all duration-150 hover:border-muted-foreground/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/30 appearance-none cursor-pointer"
          >
            <option value="">All Products</option>
            {uniqueProducts.map((p: string) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
        )}
      </div>

      {/* Active filter chips */}
      {hasActiveFilters && (
        <div className="flex items-center gap-2 flex-wrap">
          <Filter className="w-3.5 h-3.5 text-muted-foreground/40" />
          {countryFilter && <FilterChip label={`Country: ${countryFilter}`} onClear={() => setCountryFilter("")} />}
          {priorityFilter && <FilterChip label={`Priority: ${priorityFilter}`} onClear={() => setPriorityFilter("")} />}
          {assignedFilter && <FilterChip label={`Assigned: ${assignedFilter}`} onClear={() => setAssignedFilter("")} />}
          {scoreFilter && <FilterChip label={`Score: ${scoreFilter}`} onClear={() => setScoreFilter("")} />}
          {productFilter && <FilterChip label={`Product: ${productFilter}`} onClear={() => setProductFilter("")} />}
        </div>
      )}

      {/* Table */}
      <Card className="overflow-hidden border-border/40">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border/40 bg-muted/20">
                <th className="text-left py-3 px-5 min-w-[180px]">
                  <span className="text-[11px] font-semibold text-muted-foreground/50 uppercase tracking-wider">Company</span>
                </th>
                <th className="text-left py-3 px-5">
                  <span className="text-[11px] font-semibold text-muted-foreground/50 uppercase tracking-wider">Contact</span>
                </th>
                <th className="text-left py-3.5 px-4">
                  <FilterDropdown label="Country" options={uniqueCountries} value={countryFilter} onChange={(v) => { setCountryFilter(v); setPage(1); }} />
                </th>
                <th className="text-left py-3.5 px-4">
                  <FilterDropdown label="Status" options={STATUSES.filter(Boolean)} value={status} onChange={(v) => { setStatus(v); setPage(1); }} />
                </th>
                <th className="text-left py-3.5 px-4">
                  <FilterDropdown label="Priority" options={uniquePriorities} value={priorityFilter} onChange={(v) => { setPriorityFilter(v); setPage(1); }} />
                </th>
                <th className="text-left py-3.5 px-4">
                  <FilterDropdown label="Assigned" options={uniqueAssigned} value={assignedFilter} onChange={setAssignedFilter} />
                </th>
                <th className="text-left py-3.5 px-4">
                  <FilterDropdown label="Score" options={uniqueScores} value={scoreFilter} onChange={setScoreFilter} />
                </th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                Array.from({ length: 8 }).map((_, i) => (
                  <tr key={i} className="border-b border-border/30">
                    {Array.from({ length: 7 }).map((_, j) => (
                      <td key={j} className="py-3.5 px-4"><div className="skeleton h-4 w-full" /></td>
                    ))}
                  </tr>
                ))
              ) : filteredItems.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-16 text-center">
                    <Search className="w-8 h-8 text-muted-foreground/20 mx-auto mb-3" />
                    <p className="text-muted-foreground/60 font-medium">No leads found</p>
                    <p className="text-xs text-muted-foreground/40 mt-1">
                      {hasActiveFilters ? "Try adjusting your column filters" : "Try adjusting your search or filters"}
                    </p>
                  </td>
                </tr>
              ) : (
                filteredItems.map((lead: any, idx: number) => {
                  const band = scoreBand(lead.lead_score);
                  const grad = AVATAR_GRADIENTS[idx % AVATAR_GRADIENTS.length];
                  return (
                    <tr
                      key={lead.lead_id}
                      onClick={() => navigate(`/leads/${lead.lead_id}`)}
                      className="border-b border-border/30 hover:bg-primary/[0.02] cursor-pointer transition-colors duration-150 group"
                    >
                      <td className="py-3 px-5">
                        <div className="flex items-center gap-3">
                          <div className={cn(
                            "w-9 h-9 rounded-xl bg-gradient-to-br flex items-center justify-center text-sm font-bold text-white shrink-0 shadow-sm",
                            grad,
                          )}>
                            {(lead.company_name || "?").charAt(0).toUpperCase()}
                          </div>
                          <div>
                            <span className="font-medium text-foreground/85 group-hover:text-primary transition-colors duration-180">
                              {lead.company_name || "—"}
                            </span>
                            {lead.industry && (
                              <p className="text-[12px] text-muted-foreground/50">{lead.industry}</p>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-1.5">
                          <User className="w-3.5 h-3.5 text-muted-foreground/30 shrink-0" />
                          <div>
                            <span className="text-muted-foreground/80">{lead.contact_person || "—"}</span>
                            {lead.phone && <p className="text-[12px] text-muted-foreground/50 flex items-center gap-1 mt-0.5"><Phone className="w-3 h-3" />{lead.phone}</p>}
                          </div>
                        </div>
                      </td>
                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-1.5">
                          <Globe className="w-3.5 h-3.5 text-muted-foreground/30 shrink-0" />
                          <span className="text-muted-foreground/80">{lead.country || "—"}</span>
                        </div>
                      </td>
                      <td className="py-3.5 px-4">
                        <span className={cn(
                          "inline-flex px-2.5 py-1 rounded-full text-[11px] font-semibold",
                          STATUS_PILLS[lead.status || ""] || "bg-muted text-muted-foreground",
                        )}>
                          {lead.status || "—"}
                        </span>
                      </td>
                      <td className="py-3.5 px-4">
                        <span className={cn(
                          "inline-flex px-2.5 py-1 rounded-full text-[11px] font-semibold",
                          PRIORITY_PILLS[lead.priority_level] || "bg-muted text-muted-foreground",
                        )}>
                          {lead.priority_level || "—"}
                        </span>
                      </td>
                      <td className="py-3.5 px-4">
                        <span className="text-muted-foreground/70 text-[13px]">{lead.assigned_to || "—"}</span>
                      </td>
                      <td className="py-3.5 px-4">
                        <span className={cn("text-[11px] font-bold", band.color)}>{band.label}</span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Pagination */}
      {data && data.total > pageSize && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground/60">
            Page <span className="font-medium text-foreground/70">{page}</span> of <span className="font-medium text-foreground/70">{totalPages}</span>
            {" · "}
            <span className="font-medium text-foreground/70">{(page - 1) * pageSize + 1}</span>–<span className="font-medium text-foreground/70">{Math.min(page * pageSize, data.total)}</span> of <span className="font-medium text-foreground/70">{data.total}</span>
          </p>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))} className="gap-1.5">
              <ChevronLeft className="w-4 h-4" />
              Previous
            </Button>
            <Button variant="outline" size="sm" disabled={page * pageSize >= data.total} onClick={() => setPage((p) => p + 1)} className="gap-1.5">
              Next
              <ChevronRight className="w-4 h-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

function FilterChip({ label, onClear }: { label: string; onClear: () => void }) {
  return (
    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-primary/10 text-primary text-xs font-medium">
      {label}
      <button onClick={onClear} className="hover:text-destructive transition-colors">
        <X className="w-3 h-3" />
      </button>
    </span>
  );
}
