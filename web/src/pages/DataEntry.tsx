import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import api from "@/lib/api";
import { cn } from "@/lib/utils";
import { useToast } from "@/components/ui/toast";
import { fetchProducts, type Product } from "@/lib/products";
import { Save, X, Building2, AlertCircle, CheckCircle2 } from "lucide-react";

const defaultForm = {
  company_name: "",
  contact_person: "",
  phone: "",
  email: "",
  country: "",
  status: "Prospect",
  lead_source: "",
  lead_category: "B",
  priority_level: "MEDIUM",
  remarks: "",
  next_action_plan: "",
  next_follow_up: "",
  followup_mode: "",
};

const LEAD_CATEGORIES = ["A", "B", "C"];
const LEAD_SOURCES = ["Website", "Referral", "Alibaba", "Trade Show", "LinkedIn", "Cold Call", "Email Campaign", "WhatsApp", "Other"];
const FOLLOWUP_MODES = ["call", "email", "whatsapp", "meeting"];

export default function DataEntry() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const defaultFollowupDate = (() => { const d = new Date(); d.setDate(d.getDate() + 2); return d.toISOString().split("T")[0]; })();
  const [form, setForm] = useState({ ...defaultForm, next_follow_up: defaultFollowupDate });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [products, setProducts] = useState<Product[]>([]);
  const [selectedProductIds, setSelectedProductIds] = useState<number[]>([]);

  useEffect(() => { fetchProducts().then(setProducts).catch(() => {}); }, []);

  const handleChange = (field: string, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!form.contact_person.trim()) { setError("Contact Person is required"); return; }
    if (!form.lead_source) { setError("Lead Source is required"); return; }
    if (!form.lead_category) { setError("Lead Category is required"); return; }
    if (!form.next_action_plan.trim() && form.status !== "Lost") { setError("Next Action Plan is required — describe what will be done on the follow-up"); return; }
    if (!form.next_follow_up && form.status !== "Lost") { setError("Follow-Up Date is required"); return; }
    if (form.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) { setError("Please enter a valid email address"); return; }
    setSaving(true);
    try {
      const payload: Record<string, any> = {};
      for (const [k, v] of Object.entries(form)) {
        if (v !== "" && v !== null && v !== undefined) payload[k] = v;
      }
      if (selectedProductIds.length > 0) payload.product_ids = selectedProductIds;
      const res = await api.post("/leads", payload);
      toast("success", `Lead created: ${res.data.lead_id}`);
      setForm({ ...defaultForm });
    } catch (err: any) {
      const msg = err.response?.data?.detail || "Failed to create lead. Please check your input and try again.";
      setError(msg);
      toast("error", msg);
    } finally {
      setSaving(false);
    }
  };

  const hasChanges = Object.values(form).some((v) => v !== "");

  return (
    <div className="p-6 space-y-6 max-w-3xl mx-auto">
      <div>
        <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
          <Building2 className="w-4 h-4" />
          <span>Lead creation</span>
        </div>
        <h1 className="text-3xl font-bold tracking-tight">Data Entry</h1>
        <p className="text-muted-foreground mt-1">Create a new lead in the CRM</p>
      </div>

      <Card>
        <CardHeader className="pb-4">
          <CardTitle className="text-lg">New Lead</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <FormField label="Company Name" value={form.company_name} onChange={(v) => handleChange("company_name", v)} placeholder="e.g. Acme Corp (optional)" />
              <FormField label="Contact Person *" value={form.contact_person} onChange={(v) => handleChange("contact_person", v)} placeholder="Full name (required)" />
              <FormField label="Phone" value={form.phone} onChange={(v) => handleChange("phone", v)} placeholder="+1 234 567 890" />
              <FormField label="Email" value={form.email} onChange={(v) => handleChange("email", v)} placeholder="contact@company.com" />
              <FormField label="Country" value={form.country} onChange={(v) => handleChange("country", v)} placeholder="e.g. United States" />
              <div>
                <label className="text-sm font-medium text-foreground block mb-1.5">Lead Source *</label>
                <select
                  value={form.lead_source}
                  onChange={(e) => handleChange("lead_source", e.target.value)}
                  className="w-full h-10 px-3 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring focus:border-ring transition-colors appearance-none cursor-pointer"
                >
                  <option value="">— Select source —</option>
                  {LEAD_SOURCES.map((s) => (<option key={s} value={s}>{s}</option>))}
                </select>
              </div>
              <div>
                <label className="text-sm font-medium text-foreground block mb-1.5">Lead Category *</label>
                <select
                  value={form.lead_category}
                  onChange={(e) => handleChange("lead_category", e.target.value)}
                  className="w-full h-10 px-3 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring focus:border-ring transition-colors appearance-none cursor-pointer"
                >
                  {LEAD_CATEGORIES.map((c) => (<option key={c} value={c}>{c}</option>))}
                </select>
              </div>
              <div>
                <label className="text-sm font-medium text-foreground block mb-1.5">Status</label>
                <select
                  value={form.status}
                  onChange={(e) => handleChange("status", e.target.value)}
                  className="w-full h-10 px-3 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring focus:border-ring transition-colors appearance-none cursor-pointer"
                >
                  {["Prospect", "Requirement Qualified", "Technical Discussion", "Quotation Sent", "Sample Sent", "Negotiation", "Trial Order", "Nurturing", "Order Closed", "Lost"].map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-sm font-medium text-foreground block mb-1.5">Priority</label>
                <select
                  value={form.priority_level}
                  onChange={(e) => handleChange("priority_level", e.target.value)}
                  className="w-full h-10 px-3 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring focus:border-ring transition-colors appearance-none cursor-pointer"
                >
                  {["HIGH", "MEDIUM", "LOW"].map((p) => (
                    <option key={p} value={p}>{p}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Products of Interest */}
            {products.length > 0 && (
              <div>
                <label className="text-sm font-medium text-foreground block mb-1.5">Products of Interest</label>
                <div className="flex flex-wrap gap-2">
                  {products.map((p) => {
                    const selected = selectedProductIds.includes(p.id);
                    return (
                      <button key={p.id} type="button"
                        onClick={() => setSelectedProductIds((prev) => selected ? prev.filter((id) => id !== p.id) : [...prev, p.id])}
                        className={cn("px-3 py-1.5 rounded-lg text-xs font-medium border transition-all", selected ? "bg-primary/10 text-primary border-primary/30" : "bg-background border-border/60 text-muted-foreground hover:border-primary/20")}>
                        {p.name}
                        <span className="ml-1 text-[10px] opacity-60">{p.category}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            <div>
              <label className="text-sm font-medium text-foreground block mb-1.5">Remarks</label>
              <textarea
                value={form.remarks}
                onChange={(e) => handleChange("remarks", e.target.value)}
                rows={3}
                placeholder="Any additional notes about this lead..."
                className="w-full px-3 py-2.5 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring focus:border-ring transition-colors resize-none"
              />
            </div>
            <div>
              <label className="text-sm font-medium text-foreground block mb-1.5">Next Action Plan *</label>
              <textarea
                value={form.next_action_plan}
                onChange={(e) => handleChange("next_action_plan", e.target.value)}
                rows={2}
                placeholder="What will be done on the first follow-up? (e.g. Send quotation, schedule demo)"
                className="w-full px-3 py-2.5 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring focus:border-ring transition-colors resize-none"
              />
            </div>

            {/* Schedule First Follow-Up */}
            <div className="border-t border-border/40 pt-5">
              <p className="text-sm font-semibold text-foreground mb-3">Schedule First Follow-Up *</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium text-foreground block mb-1.5">Follow-Up Date *</label>
                  <input
                    type="date"
                    value={form.next_follow_up}
                    onChange={(e) => handleChange("next_follow_up", e.target.value)}
                    className="w-full h-10 px-3 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring focus:border-ring transition-colors"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium text-foreground block mb-1.5">Follow-Up Mode</label>
                  <select
                    value={form.followup_mode}
                    onChange={(e) => handleChange("followup_mode", e.target.value)}
                    className="w-full h-10 px-3 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring focus:border-ring transition-colors appearance-none cursor-pointer"
                  >
                    <option value="">— Select mode —</option>
                    {FOLLOWUP_MODES.map((m) => (<option key={m} value={m}>{m.charAt(0).toUpperCase() + m.slice(1)}</option>))}
                  </select>
                </div>
              </div>
            </div>

            {error && (
              <div className="flex items-center gap-2 p-3 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive text-sm">
                <AlertCircle className="w-4 h-4 shrink-0" />
                {error}
              </div>
            )}

            <div className="flex items-center gap-3 pt-2">
              <Button type="submit" disabled={saving} className="gap-2" loading={saving}>
                <Save className="w-4 h-4" />
                {saving ? "Saving..." : "Save Lead"}
              </Button>
              {hasChanges && (
                <Button variant="ghost" type="button" onClick={() => setForm({ ...defaultForm })} className="gap-2">
                  <X className="w-4 h-4" />
                  Clear
                </Button>
              )}
              <Button variant="outline" type="button" onClick={() => navigate("/leads")}>
                Cancel
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

function FormField({
  label,
  value,
  onChange,
  placeholder,
  maxLength = 255,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  maxLength?: number;
}) {
  return (
    <div>
      <label className="text-sm font-medium text-foreground block mb-1.5">{label}</label>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        maxLength={maxLength}
        className="w-full h-10 px-3 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring focus:border-ring transition-colors"
      />
    </div>
  );
}
