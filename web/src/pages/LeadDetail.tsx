import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useLead, useLeadFollowups } from "@/hooks/useLeads";
import { useLeadHealth } from "@/hooks/useDashboard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import Modal from "@/components/ui/modal";
import { cn, formatDate, scoreBand } from "@/lib/utils";
import { useAuth } from "@/lib/auth";
import api from "@/lib/api";
import {
  fetchInquiries, createInquiry, Inquiry, InquiryCreate, INQUIRY_TYPES, INQUIRY_PRIORITIES,
  DISPLAY_STATUS_LABELS, DISPLAY_STATUS_COLORS,
} from "@/lib/inquiries";
import {
  ArrowLeft, Phone, Mail, Globe, MapPin, Building2,
  User, Briefcase, Calendar, Target, FileText,
  MessageSquare, Clock, ChevronRight, Plus, X, AlertTriangle, Activity, Pencil, ArrowRightLeft,
} from "lucide-react";
import TransferLeadModal from "@/components/TransferLeadModal";

const PRIORITY_BADGES: Record<string, string> = {
  HIGH: "bg-red-50 text-red-700 border-red-200",
  MEDIUM: "bg-amber-50 text-amber-700 border-amber-200",
  LOW: "bg-blue-50 text-blue-700 border-blue-200",
};

const STATUS_BADGES: Record<string, string> = {
  "Prospect": "bg-slate-100 text-slate-700 border-slate-200",
  "Requirement Qualified": "bg-blue-50 text-blue-700 border-blue-200",
  "Technical Discussion": "bg-cyan-50 text-cyan-700 border-cyan-200",
  "Quotation Sent": "bg-emerald-50 text-emerald-700 border-emerald-200",
  "Sample Sent": "bg-lime-50 text-lime-700 border-lime-200",
  "Negotiation": "bg-amber-50 text-amber-700 border-amber-200",
  "Trial Order": "bg-orange-50 text-orange-700 border-orange-200",
  "Nurturing": "bg-purple-50 text-purple-700 border-purple-200",
  "Order Closed": "bg-green-50 text-green-700 border-green-200",
  "Lost": "bg-red-50 text-red-700 border-red-200",
};

const INQUIRY_STATUS_COLORS = DISPLAY_STATUS_COLORS;

export default function LeadDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { data: lead, isLoading } = useLead(id || "");
  const { data: followups } = useLeadFollowups(id || "");
  const { data: health } = useLeadHealth(id || "");
  const [inquiries, setInquiries] = useState<Inquiry[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [showEdit, setShowEdit] = useState(false);
  const [showTransfer, setShowTransfer] = useState(false);
  const [editForm, setEditForm] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState<InquiryCreate>({
    lead_id: id || "",
    title: "",
    type: "PRICING",
    priority: "MEDIUM",
    description: "",
  });

  useEffect(() => {
    if (!id) return;
    fetchInquiries({ lead_id: id }).then(setInquiries).catch(() => {});
  }, [id]);

  const handleCreate = async () => {
    if (!form.title.trim()) return;
    await createInquiry(form);
    setShowCreate(false);
    setForm({ lead_id: id || "", title: "", type: "PRICING", priority: "MEDIUM", description: "" });
    fetchInquiries({ lead_id: id }).then(setInquiries).catch(() => {});
  };

  if (isLoading) {
    return (
      <div className="p-6 space-y-6">
        <div className="flex items-center gap-4">
          <div className="skeleton h-9 w-20" />
          <div className="space-y-2">
            <div className="skeleton h-7 w-48" />
            <div className="skeleton h-4 w-24" />
          </div>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <div className="skeleton h-64 w-full rounded-xl" />
            <div className="skeleton h-48 w-full rounded-xl" />
          </div>
          <div className="space-y-6">
            <div className="skeleton h-48 w-full rounded-xl" />
            <div className="skeleton h-32 w-full rounded-xl" />
          </div>
        </div>
      </div>
    );
  }

  if (!lead) {
    return (
      <div className="p-6 flex flex-col items-center justify-center min-h-[50vh] gap-4">
        <FileText className="w-12 h-12 text-muted-foreground/30" />
        <div className="text-center">
          <p className="text-lg font-medium">Lead not found</p>
          <p className="text-sm text-muted-foreground">The lead you're looking for doesn't exist or has been removed</p>
        </div>
        <Button variant="outline" onClick={() => navigate("/leads")}>
          <ArrowLeft className="w-4 h-4" />
          Back to Leads
        </Button>
      </div>
    );
  }

  const band = scoreBand(lead.lead_score);
  const avatarInitial = (lead.company_name || lead.contact_person || "?").charAt(0).toUpperCase();

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => navigate("/leads")} className="gap-1.5">
            <ArrowLeft className="w-4 h-4" />
            Back
          </Button>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary/70 to-primary flex items-center justify-center text-lg font-bold text-white shadow-sm">
              {avatarInitial}
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight">{lead.company_name || "Untitled"}</h1>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <span className="font-mono">#{lead.lead_id}</span>
                {lead.contact_person && (
                  <>
                    <span>•</span>
                    <span>{lead.contact_person}</span>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" className="gap-1.5" onClick={() => {
            setEditForm({
              contact_person: lead.contact_person || "",
              phone: lead.phone || "",
              email: lead.email || "",
              company_name: lead.company_name || "",
              country: lead.country || "",
              city: lead.city || "",
              industry: lead.industry || "",
              website: lead.website || "",
              product_interest: lead.product_interest || "",
              status: lead.status || "",
              priority_level: lead.priority_level || "",
              remarks: lead.remarks || "",
              internal_notes: lead.internal_notes || "",
            });
            setShowEdit(true);
          }}>
            <Pencil className="w-3.5 h-3.5" /> Edit
          </Button>
          {user?.role !== "Procurement" && (
            <Button variant="outline" size="sm" onClick={() => setShowTransfer(true)} className="gap-1.5">
              <ArrowRightLeft className="w-3.5 h-3.5" /> Transfer
            </Button>
          )}
          <span className={cn("text-xs font-semibold px-2.5 py-1 rounded-md", band.color === "text-band-hot" ? "bg-red-50 text-red-700" : band.color === "text-band-warm" ? "bg-amber-50 text-amber-700" : "bg-blue-50 text-blue-700")}>
            {band.label}
          </span>
          <span className={cn("px-2.5 py-1 rounded-full text-xs font-medium border", PRIORITY_BADGES[lead.priority_level] || "")}>
            {lead.priority_level}
          </span>
          <span className={cn("px-2.5 py-1 rounded-full text-xs font-medium border", STATUS_BADGES[lead.status || ""] || "bg-muted text-muted-foreground border-border")}>
            {lead.status || "—"}
          </span>
          {lead.has_pending_followup === false && lead.status !== "Order Closed" && lead.status !== "Lost" && (
            <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-amber-50 text-amber-700 border border-amber-200 flex items-center gap-1">
              <AlertTriangle className="w-3 h-3" /> At Risk
            </span>
          )}
        </div>
      </div>

      {/* Three-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Main info columns */}
        <div className="lg:col-span-2 space-y-6">
          {/* Contact + Company combined */}
          <Card>
            <CardHeader className="pb-3 flex flex-row items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <Building2 className="w-4 h-4 text-primary" />
                Account Details
              </CardTitle>
              {lead.industry && (
                <span className="text-xs bg-muted text-muted-foreground px-2 py-0.5 rounded-full">{lead.industry}</span>
              )}
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-8">
                <div className="space-y-3">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/70 flex items-center gap-1.5">
                    <User className="w-3 h-3" />
                    Contact
                  </h4>
                  <div className="space-y-2">
                    <DetailItem icon={<User className="w-3.5 h-3.5" />} label="Name" value={lead.contact_person} />
                    <DetailItem icon={<Briefcase className="w-3.5 h-3.5" />} label="Designation" value={lead.designation} />
                    <DetailItem icon={<Phone className="w-3.5 h-3.5" />} label="Phone" value={lead.phone} />
                    <DetailItem icon={<Phone className="w-3.5 h-3.5" />} label="Alternate" value={lead.alternate_number} />
                    <DetailItem icon={<MessageSquare className="w-3.5 h-3.5" />} label="WhatsApp" value={lead.whatsapp_number} />
                    <DetailItem icon={<Mail className="w-3.5 h-3.5" />} label="Email" value={lead.email} />
                  </div>
                </div>
                <div className="space-y-3">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/70 flex items-center gap-1.5">
                    <Building2 className="w-3 h-3" />
                    Company
                  </h4>
                  <div className="space-y-2">
                    <DetailItem icon={<Globe className="w-3.5 h-3.5" />} label="Website" value={lead.website} />
                    <DetailItem icon={<MapPin className="w-3.5 h-3.5" />} label="City" value={lead.city} />
                    <DetailItem icon={<MapPin className="w-3.5 h-3.5" />} label="Country" value={lead.country} />
                    <DetailItem icon={<Globe className="w-3.5 h-3.5" />} label="Continent" value={lead.continent} />
                    <DetailItem icon={<Target className="w-3.5 h-3.5" />} label="Product" value={lead.product_interest || (lead.product_ids && lead.product_ids.length > 0 ? `Linked (${lead.product_ids.length} products)` : null)} />
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Pipeline Info */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Target className="w-4 h-4 text-primary" />
                Pipeline Details
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-8">
                <div className="space-y-2">
                  <DetailItem icon={<FileText className="w-3.5 h-3.5" />} label="Lead Source" value={lead.lead_source} />
                  <DetailItem icon={<User className="w-3.5 h-3.5" />} label="Assigned To" value={lead.assigned_to} />
                  <DetailItem icon={<Target className="w-3.5 h-3.5" />} label="Category" value={lead.lead_category} />
                  <DetailItem icon={<MessageSquare className="w-3.5 h-3.5" />} label="Engagement" value={lead.buyer_engagement_frequency} />
                </div>
                <div className="space-y-2">
                  <DetailItem icon={<Calendar className="w-3.5 h-3.5" />} label="Created" value={lead.created_date ? formatDate(lead.created_date) : null} />
                  <DetailItem icon={<Calendar className="w-3.5 h-3.5" />} label="Inquiry" value={lead.inquiry_date ? formatDate(lead.inquiry_date) : null} />
                  <DetailItem icon={<Clock className="w-3.5 h-3.5" />} label="Last Contact" value={lead.last_contact_date ? formatDate(lead.last_contact_date) : null} />
                  {lead.interest_level && <DetailItem icon={<Target className="w-3.5 h-3.5" />} label="Interest" value={lead.interest_level} />}
                  {lead.potential_deal_value && <DetailItem icon={<Target className="w-3.5 h-3.5" />} label="Deal Value" value={`$${lead.potential_deal_value}`} />}
                  {lead.next_action_plan && (
                    <DetailItem icon={<FileText className="w-3.5 h-3.5" />} label="Next Action" value={lead.next_action_plan} />
                  )}
                </div>
              </div>
              {lead.lost_reason && (
                <div className="mt-4 p-3 rounded-lg bg-destructive/5 border border-destructive/10">
                  <p className="text-xs font-medium text-destructive mb-0.5">Lost Reason</p>
                  <p className="text-sm text-muted-foreground">{lead.lost_reason}</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Customer Requirements */}
          {lead.customer_requirements && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <FileText className="w-4 h-4 text-primary" />
                  Customer Requirements
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground whitespace-pre-wrap leading-relaxed">{lead.customer_requirements}</p>
              </CardContent>
            </Card>
          )}

          {/* Remarks */}
          {lead.remarks && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <FileText className="w-4 h-4 text-primary" />
                  Remarks
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground whitespace-pre-wrap leading-relaxed">{lead.remarks}</p>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Right sidebar */}
        <div className="space-y-6">
          {/* Lead Health Card */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Activity className="w-4 h-4 text-primary" />
                Lead Health
              </CardTitle>
            </CardHeader>
            <CardContent>
              {health ? (
                <div className="space-y-3">
                  <div className={cn(
                    "text-sm font-semibold px-3 py-1.5 rounded-lg inline-block",
                    health.health === "healthy" ? "bg-emerald-50 text-emerald-700" :
                    health.health === "attention_needed" ? "bg-amber-50 text-amber-700" :
                    health.health === "at_risk" ? "bg-red-50 text-red-700" :
                    "bg-slate-100 text-slate-600"
                  )}>
                    {health.health === "healthy" ? "Healthy" :
                     health.health === "attention_needed" ? "Needs Attention" :
                     health.health === "at_risk" ? "At Risk" : "Stalled"}
                  </div>
                  {health.next_followup_date && (
                    <div className="flex items-center gap-2 text-sm">
                      <Calendar className="w-3.5 h-3.5 text-muted-foreground/50" />
                      <span className="text-muted-foreground/60">Next: </span>
                      <span className="font-medium">{formatDate(health.next_followup_date)}</span>
                    </div>
                  )}
                  {health.last_activity_days != null && (
                    <div className="flex items-center gap-2 text-sm">
                      <Clock className="w-3.5 h-3.5 text-muted-foreground/50" />
                      <span className="text-muted-foreground/60">Activity: </span>
                      <span className="font-medium">{health.last_activity_days === 0 ? "Today" : `${health.last_activity_days}d ago`}</span>
                    </div>
                  )}
                  <div className="flex items-center gap-2 text-sm">
                    <AlertTriangle className="w-3.5 h-3.5 text-muted-foreground/50" />
                    <span className="text-muted-foreground/60">Risk: </span>
                    <span className={cn(
                      "font-medium capitalize",
                      health.risk_level === "high" ? "text-red-600" :
                      health.risk_level === "medium" ? "text-amber-600" : "text-emerald-600"
                    )}>{health.risk_level}</span>
                  </div>
                  {health.warnings.length > 0 && (
                    <div className="pt-2 border-t border-border/40 space-y-1">
                      {health.warnings.map((w, i) => (
                        <p key={i} className="text-xs text-destructive/80 flex items-start gap-1.5">
                          <AlertTriangle className="w-3 h-3 shrink-0 mt-0.5" />{w}
                        </p>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <div className="space-y-2">
                  <div className="skeleton h-6 w-24" />
                  <div className="skeleton h-4 w-32" />
                  <div className="skeleton h-4 w-28" />
                </div>
              )}
            </CardContent>
          </Card>

          {/* Score Card */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Target className="w-4 h-4 text-primary" />
                Lead Score
              </CardTitle>
            </CardHeader>
            <CardContent className="text-center">
              <div className={cn(
                "w-20 h-20 rounded-full mx-auto flex items-center justify-center text-2xl font-bold border-4",
                band.color === "text-band-hot" ? "border-red-200 bg-red-50 text-red-700" :
                band.color === "text-band-warm" ? "border-amber-200 bg-amber-50 text-amber-700" :
                "border-blue-200 bg-blue-50 text-blue-700"
              )}>
                {lead.lead_score}
              </div>
              <p className={cn("text-sm font-semibold mt-2", band.color)}>{band.label}</p>
              <p className="text-xs text-muted-foreground mt-0.5">Out of 100</p>
            </CardContent>
          </Card>

          {/* Follow-ups Timeline */}
          <Card>
            <CardHeader className="pb-3 flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <MessageSquare className="w-4 h-4 text-primary" />
                Follow-ups ({followups?.length || 0})
              </CardTitle>
            </CardHeader>
            <CardContent>
              {followups && followups.length > 0 ? (
                <div className="relative">
                  <div className="absolute left-[5px] top-1 bottom-1 w-px bg-gradient-to-b from-primary/30 to-transparent" />
                  <div className="space-y-4">
                    {followups.map((fu: any, idx: number) => (
                      <div key={fu.followup_id} className="flex items-start gap-3 relative">
                        <div className={cn(
                          "w-[11px] h-[11px] rounded-full border-2 border-background shrink-0 mt-1 relative z-10",
                          idx === 0 ? "bg-primary" : "bg-muted-foreground/30"
                        )} />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between gap-2">
                            <p className="text-sm font-medium">
                              {fu.followup_date ? formatDate(fu.followup_date) : "No date"}
                            </p>
                            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                              {fu.mode && <span className="bg-muted px-1.5 py-0.5 rounded">{fu.mode}</span>}
                              {fu.updated_by && <span>{fu.updated_by}</span>}
                            </div>
                          </div>
                          {fu.discussion && (
                            <p className="text-sm text-muted-foreground mt-1">{fu.discussion}</p>
                          )}
                          {fu.outcome_notes && (
                            <div className="mt-2 p-2 rounded-lg bg-emerald-50/50 border border-emerald-100">
                              <p className="text-[10px] font-semibold text-emerald-600 uppercase tracking-wider mb-0.5">Outcome</p>
                              <p className="text-sm text-emerald-800 whitespace-pre-wrap">{fu.outcome_notes}</p>
                              {fu.completed_by && (
                                <p className="text-[11px] text-emerald-600/60 mt-1">by {fu.completed_by}{fu.completed_at && ` · ${new Date(fu.completed_at).toLocaleDateString()}`}</p>
                              )}
                            </div>
                          )}
                          {(fu.next_action || fu.next_followup) && (
                            <div className="flex flex-wrap gap-x-3 gap-y-0.5 mt-1.5 text-xs text-muted-foreground">
                              {fu.next_action && <span>Next: {fu.next_action}</span>}
                              {fu.next_followup && <span>Due: {formatDate(fu.next_followup)}</span>}
                            </div>
                          )}
                        </div>
                        <ChevronRight className="w-4 h-4 text-muted-foreground/30 shrink-0" />
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="text-center py-8">
                  <MessageSquare className="w-8 h-8 text-muted-foreground/30 mx-auto mb-2" />
                  <p className="text-sm text-muted-foreground">No follow-ups recorded</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Inquiries Timeline */}
          <Card>
            <CardHeader className="pb-3 flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <MessageSquare className="w-4 h-4 text-primary" />
                Inquiries ({inquiries.length})
              </CardTitle>
              <Button size="sm" variant="outline" className="gap-1.5 text-xs h-8" onClick={() => setShowCreate(true)}>
                <Plus className="w-3.5 h-3.5" />
                New
              </Button>
            </CardHeader>
            <CardContent>
              {inquiries.length > 0 ? (
                <div className="space-y-3">
                  {inquiries.map((inq) => (
                    <div key={inq.id} className="p-3 rounded-lg border border-border/60 space-y-1.5">
                      <div className="flex items-center justify-between gap-2">
                        <p className="text-sm font-medium truncate">{inq.title}</p>
                        <span className={cn("text-[10px] font-semibold px-1.5 py-0.5 rounded shrink-0", DISPLAY_STATUS_COLORS[inq.status] || "")}>
                          {DISPLAY_STATUS_LABELS[inq.status] || inq.status.replace(/_/g, " ")}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 text-[11px] text-muted-foreground/60">
                        <span>{inq.type}</span>
                        <span>·</span>
                        <span>{inq.priority}</span>
                        <span>·</span>
                        <span>{new Date(inq.created_at).toLocaleDateString()}</span>
                        {inq.commitment_type && inq.status !== "CLOSED" && inq.status !== "OPEN" && (
                          <>
                            <span>·</span>
                            <span className={inq.status === "OVERDUE" ? "text-red-600/80 font-semibold" : "text-amber-600/80"}>
                              {inq.commitment_type === "BY_EOD" ? "By EOD" : inq.commitment_type === "ANSWER_NOW" ? "Answer Now" : "Pending"}
                            </span>
                          </>
                        )}
                        {inq.expected_response_date && inq.status !== "CLOSED" && (
                          <>
                            <span>·</span>
                            <span className={inq.status === "OVERDUE" ? "text-red-600/80" : "text-muted-foreground/60"}>
                              {new Date(inq.expected_response_date).toLocaleDateString()}
                            </span>
                          </>
                        )}
                      </div>
                      {inq.description && (
                        <p className="text-[12px] text-muted-foreground/80 line-clamp-2">{inq.description}</p>
                      )}
                      {inq.commitment_type && inq.status !== "RESPONDED" && inq.status !== "CLOSED" && (
                        <div className="mt-1 pt-1 border-t border-border/40">
                          <p className="text-[10px] font-semibold text-amber-600 uppercase tracking-wider">
                            Procurement: {inq.commitment_type === "BY_EOD" ? "By EOD" : inq.commitment_type === "ANSWER_NOW" ? "Answer Now" : "Will Take Time"}
                          </p>
                          {inq.expected_response_date && <p className="text-[12px] text-muted-foreground/80">Expected: {new Date(inq.expected_response_date).toLocaleDateString()}</p>}
                        </div>
                      )}
                      {inq.response && (
                        <div className="mt-1 pt-1.5 border-t border-border/40">
                          <p className="text-[10px] font-semibold text-emerald-600 uppercase tracking-wider">Response</p>
                          <p className="text-[12px] text-muted-foreground/80 line-clamp-2">{inq.response}</p>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8">
                  <MessageSquare className="w-8 h-8 text-muted-foreground/30 mx-auto mb-2" />
                  <p className="text-sm text-muted-foreground">No inquiries yet</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Create Inquiry Modal */}
      <Modal open={showCreate} onClose={() => setShowCreate(false)}>
        <div className="p-7 pb-2">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-xl font-bold tracking-tight">New Inquiry</h2>
            <Button variant="ghost" size="sm" onClick={() => setShowCreate(false)}>
              <X className="w-4 h-4" />
            </Button>
          </div>
        </div>
        <div className="px-7 space-y-4">
          <div>
            <label className="text-xs font-medium text-muted-foreground/70 mb-1.5 block">Title *</label>
            <input
              type="text"
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              placeholder="e.g., Pricing for bulk order"
              className="w-full rounded-lg border border-input bg-background px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-medium text-muted-foreground/70 mb-1.5 block">Type</label>
              <select
                value={form.type}
                onChange={(e) => setForm({ ...form, type: e.target.value })}
                className="w-full rounded-lg border border-input bg-background px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
              >
                {INQUIRY_TYPES.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground/70 mb-1.5 block">Priority</label>
              <select
                value={form.priority}
                onChange={(e) => setForm({ ...form, priority: e.target.value })}
                className="w-full rounded-lg border border-input bg-background px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
              >
                {INQUIRY_PRIORITIES.map((p) => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
            </div>
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground/70 mb-1.5 block">Description</label>
            <textarea
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="What do you need from procurement?"
              rows={3}
              className="w-full rounded-lg border border-input bg-background px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
          </div>
        </div>
        <div className="flex items-center justify-end gap-3 px-7 py-5">
          <Button variant="outline" onClick={() => setShowCreate(false)}>Cancel</Button>
          <Button onClick={handleCreate} disabled={!form.title.trim()} className="px-6">
            Submit Inquiry
          </Button>
        </div>
      </Modal>

      {/* Edit Lead Modal */}
      {showEdit && (
        <Modal open={showEdit} onClose={() => setShowEdit(false)}>
          <div className="p-7">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-bold">Edit Lead</h2>
              <button onClick={() => setShowEdit(false)} className="p-2 rounded-lg hover:bg-muted/60 transition-colors">
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="grid grid-cols-2 gap-4">
              {[
                { key: "company_name", label: "Company Name", type: "text" },
                { key: "contact_person", label: "Contact Person", type: "text" },
                { key: "phone", label: "Phone", type: "text" },
                { key: "email", label: "Email", type: "text" },
                { key: "country", label: "Country", type: "text" },
                { key: "city", label: "City", type: "text" },
                { key: "industry", label: "Industry", type: "text" },
                { key: "website", label: "Website", type: "text" },
                { key: "product_interest", label: "Product Interest", type: "text" },
                { key: "status", label: "Status", type: "select", options: ["Prospect", "Requirement Qualified", "Technical Discussion", "Quotation Sent", "Sample Sent", "Negotiation", "Trial Order", "Nurturing", "Order Closed", "Lost"] },
                { key: "priority_level", label: "Priority", type: "select", options: ["HIGH", "MEDIUM", "LOW"] },
              ].map((field) => (
                <div key={field.key}>
                  <label className="text-[11px] font-medium text-muted-foreground/60 mb-1 block">{field.label}</label>
                  {field.type === "select" ? (
                    <select value={editForm[field.key] || ""} onChange={(e) => setEditForm({ ...editForm, [field.key]: e.target.value })} className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20">
                      {field.options!.map((o) => <option key={o} value={o}>{o}</option>)}
                    </select>
                  ) : (
                    <input type="text" value={editForm[field.key] || ""} onChange={(e) => setEditForm({ ...editForm, [field.key]: e.target.value })} className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20" />
                  )}
                </div>
              ))}
              <div className="col-span-2">
                <label className="text-[11px] font-medium text-muted-foreground/60 mb-1 block">Remarks</label>
                <textarea value={editForm.remarks || ""} onChange={(e) => setEditForm({ ...editForm, remarks: e.target.value })} rows={2} className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 resize-none" />
              </div>
              <div className="col-span-2">
                <label className="text-[11px] font-medium text-muted-foreground/60 mb-1 block">Internal Notes</label>
                <textarea value={editForm.internal_notes || ""} onChange={(e) => setEditForm({ ...editForm, internal_notes: e.target.value })} rows={2} className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 resize-none" />
              </div>
            </div>
            <div className="flex items-center justify-end gap-3 mt-6 pt-4 border-t border-border/40">
              <Button variant="outline" onClick={() => setShowEdit(false)}>Cancel</Button>
              <Button onClick={async () => {
                setSaving(true);
                try {
                  await api.put(`/leads/${id}`, editForm);
                  setShowEdit(false);
                  window.location.reload();
                } catch {
                  // Error silently handled — save failure is rare
                } finally {
                  setSaving(false);
                }
              }} disabled={saving} className="px-6">
                {saving ? "Saving..." : "Save Changes"}
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* Transfer Lead Modal */}
      {showTransfer && lead && (
        <TransferLeadModal lead={lead} onClose={() => setShowTransfer(false)} />
      )}
    </div>
  );
}

function DetailItem({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string | null | undefined;
}) {
  return (
    <div className="flex items-center gap-2.5 text-sm">
      <span className="text-muted-foreground/50 shrink-0">{icon}</span>
      <span className="text-muted-foreground/70 min-w-[72px] text-xs">{label}</span>
      <span className="font-medium truncate">{value || "—"}</span>
    </div>
  );
}
