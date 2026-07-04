import { useState, useMemo, useCallback, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { completeActivity, type ActivityWizardResponse } from "@/lib/api";
import {
  Phone, Mail, MessageSquare, MessageCircle, Users, MoreHorizontal,
  CheckCircle2, ArrowRight, ArrowLeft, Calendar, Loader2, X, ThumbsUp, ThumbsDown, HelpCircle, AlertTriangle,
} from "lucide-react";

interface ActivityWizardProps {
  followupId: number;
  leadStatus: string;
  assignedTo: string;
  companyName: string;
  taskType?: string;
  taskDiscussion?: string;
  onClose: () => void;
  onComplete: (result: ActivityWizardResponse) => void;
}

type ActionKey = "call" | "email" | "whatsapp" | "meeting" | "other";

const ACTION_OPTIONS: { key: ActionKey; label: string; icon: React.ReactNode }[] = [
  { key: "call", label: "Call", icon: <Phone className="w-5 h-5" /> },
  { key: "email", label: "Email", icon: <Mail className="w-5 h-5" /> },
  { key: "whatsapp", label: "WhatsApp", icon: <MessageSquare className="w-5 h-5" /> },
  { key: "meeting", label: "Meeting", icon: <Users className="w-5 h-5" /> },
  { key: "other", label: "Other", icon: <MoreHorizontal className="w-5 h-5" /> },
];

const CALL_OUTCOMES = [
  { value: "connected", label: "Connected" },
  { value: "not_answered", label: "Not Answered" },
  { value: "wrong_number", label: "Wrong Number" },
  { value: "call_back_later", label: "Call Back Later" },
];

const INTEREST_OPTIONS = [
  { value: "interested", label: "Interested" },
  { value: "not_interested", label: "Not Interested" },
  { value: "maybe", label: "Maybe" },
];

const MEETING_OUTCOMES = [
  { value: "interested", label: "Interested" },
  { value: "needs_proposal", label: "Needs Proposal" },
  { value: "needs_pricing", label: "Needs Pricing" },
  { value: "needs_samples", label: "Needs Samples" },
  { value: "not_interested", label: "Not Interested" },
  { value: "other", label: "Other" },
];

const REQUIREMENT_OPTIONS = [
  "Pricing", "Quotation", "Samples", "Meeting",
  "Documentation", "Lead Time", "Availability", "Other",
];

const NOT_INTERESTED_REASONS = [
  { value: "price", label: "Price" },
  { value: "competitor", label: "Competitor" },
  { value: "no_requirement", label: "No Requirement" },
  { value: "timing", label: "Timing" },
  { value: "other", label: "Other" },
];

const RESPONSE_CHECK_OPTIONS = [
  { value: "tomorrow", label: "Tomorrow" },
  { value: "2_days", label: "2 Days" },
  { value: "3_days", label: "3 Days" },
  { value: "custom", label: "Custom Date" },
];

const RESPONSE_CHANNELS: { key: ActionKey; label: string; icon: React.ReactNode }[] = [
  { key: "email", label: "Email", icon: <Mail className="w-4 h-4" /> },
  { key: "whatsapp", label: "WhatsApp", icon: <MessageSquare className="w-4 h-4" /> },
  { key: "call", label: "Call", icon: <Phone className="w-4 h-4" /> },
  { key: "other", label: "Other", icon: <MoreHorizontal className="w-4 h-4" /> },
];

const NO_RESPONSE_ACTIONS = [
  { value: "send_reminder", label: "Send Reminder", desc: "Re-send message and check again" },
  { value: "call_customer", label: "Call Customer", desc: "Follow up by phone" },
  { value: "wait_longer", label: "Wait Longer", desc: "Check again on a later date" },
  { value: "custom", label: "Custom Action", desc: "Do something else" },
];

export default function ActivityWizard({ followupId, leadStatus, assignedTo, companyName, taskType, taskDiscussion, onClose, onComplete }: ActivityWizardProps) {
  const isResponseCheck = taskType === "Await Customer Response" || taskDiscussion === "Check Customer Response";
  const [step, setStep] = useState(1);
  const [submitting, setSubmitting] = useState(false);
  const [wizardError, setWizardError] = useState("");

  // ── Response check state ──
  const [responded, setResponded] = useState<boolean | null>(null);
  const [noResponseAction, setNoResponseAction] = useState<string>("");
  const [responseChannel, setResponseChannel] = useState<ActionKey | "">("");

  // Step 1 state
  const [selectedActions, setSelectedActions] = useState<ActionKey[]>([]);

  // Step 2 state — Call
  const [callOutcome, setCallOutcome] = useState<string>("");
  const [customerInterest, setCustomerInterest] = useState<string>("");

  // Step 2 state — Email/WhatsApp/SMS
  const [expectResponse, setExpectResponse] = useState<boolean | null>(null);
  const [responseCheckDate, setResponseCheckDate] = useState<string>("");

  // Step 2 state — Meeting
  const [meetingOutcome, setMeetingOutcome] = useState<string>("");

  // Shared state
  const [customerRequirements, setCustomerRequirements] = useState<string[]>([]);
  const [notInterestedReason, setNotInterestedReason] = useState<string>("");
  const [customResponseDate, setCustomResponseDate] = useState("");
  const [followupDate, setFollowupDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() + 2);
    return d.toISOString().split("T")[0];
  });
  const [nextFollowupMode, setNextFollowupMode] = useState<ActionKey | "">("");
  const [notes, setNotes] = useState("");

  // Reset to generic mode when "No" is selected on response check
  useEffect(() => {
    if (responded === false) {
      setSelectedActions([]);
      setCallOutcome("");
      setCustomerInterest("");
      setMeetingOutcome("");
      setCustomerRequirements([]);
      setNotInterestedReason("");
    }
  }, [responded]);

  const toggleAction = (key: ActionKey) => {
    setSelectedActions((prev) =>
      prev.includes(key) ? prev.filter((a) => a !== key) : [...prev, key]
    );
  };

  const toggleRequirement = (req: string) => {
    setCustomerRequirements((prev) =>
      prev.includes(req) ? prev.filter((r) => r !== req) : [...prev, req]
    );
  };

  const hasAction = (key: ActionKey) => selectedActions.includes(key);
  const showMessageFlow = hasAction("email") || hasAction("whatsapp");
  const showCallFlow = hasAction("call");
  const showMeetingFlow = hasAction("meeting");
  const showInterestedFlow = customerInterest === "interested" || customerInterest === "maybe" || meetingOutcome === "interested";
  const showNotInterested = customerInterest === "not_interested" || meetingOutcome === "not_interested";
  const responseDateVal = responseCheckDate === "custom" ? customResponseDate : responseCheckDate;

  const canProceedStep1 = useMemo(() => {
    if (isResponseCheck && responded === null) return false;
    if (isResponseCheck && responded === true && !responseChannel) return false;
    if (isResponseCheck && responded === false && !noResponseAction) return false;
    if (!isResponseCheck && selectedActions.length === 0) return false;
    return true;
  }, [isResponseCheck, responded, responseChannel, noResponseAction, selectedActions]);

  const canProceedStep2 = useMemo(() => {
    if (showCallFlow && !callOutcome) return false;
    if (callOutcome === "connected" && !customerInterest) return false;
    if (showMessageFlow && expectResponse === null) return false;
    if (expectResponse && !responseCheckDate) return false;
    if (showMeetingFlow && !meetingOutcome) return false;
    if (customerInterest === "interested" && customerRequirements.length === 0) return false;
    return true;
  }, [showCallFlow, callOutcome, customerInterest, showMessageFlow, expectResponse, responseCheckDate, showMeetingFlow, meetingOutcome, customerRequirements]);

  // Determine if we're currently in "no response" follow-up flow
  const isNoResponseFollowUp = responded === false;
  const showInterestAfterResponse = responded === true;

  const buildPayload = useCallback(() => {
    const payload: any = {};

    if (isResponseCheck && responded === true) {
      // Customer responded — map channel + interest + requirements
      const channel = responseChannel || "email";
      payload.actions = [channel];
      payload.customer_interest = customerInterest || "interested";
      if (customerRequirements.length > 0) payload.customer_requirements = customerRequirements;
      if (notInterestedReason) payload.not_interested_reason = notInterestedReason;
    } else if (isResponseCheck && responded === false) {
      // Customer didn't respond — map to follow-up action
      if (noResponseAction === "send_reminder") {
        payload.actions = ["email"];
        payload.expect_response = true;
        payload.response_check_date = responseDateVal || "tomorrow";
      } else if (noResponseAction === "call_customer") {
        payload.actions = ["call"];
        payload.call_outcome = "call_back_later";
      } else if (noResponseAction === "wait_longer") {
        payload.actions = ["email"];
        payload.expect_response = true;
        payload.response_check_date = responseDateVal || "2_days";
      } else if (noResponseAction === "custom") {
        payload.actions = ["other"];
      }
    } else {
      // Standard flow
      payload.actions = selectedActions;
      if (callOutcome) payload.call_outcome = callOutcome;
      if (customerInterest) payload.customer_interest = customerInterest;
      if (expectResponse !== null) payload.expect_response = expectResponse;
      if (responseCheckDate) payload.response_check_date = responseDateVal;
      if (meetingOutcome) payload.meeting_outcome = meetingOutcome;
      if (customerRequirements.length > 0) payload.customer_requirements = customerRequirements;
      if (notInterestedReason) payload.not_interested_reason = notInterestedReason;
    }

    if (notes.trim()) payload.notes = notes.trim();
    if (followupDate) payload.followup_date = followupDate;
    if (nextFollowupMode) payload.next_followup_mode = nextFollowupMode;

    return payload;
  }, [isResponseCheck, responded, responseChannel, customerInterest, customerRequirements, notInterestedReason, noResponseAction, responseDateVal, responseCheckDate, selectedActions, callOutcome, expectResponse, meetingOutcome, notes, followupDate, nextFollowupMode]);

  const handleSubmit = useCallback(async () => {
    setSubmitting(true);
    setWizardError("");
    try {
      const payload = buildPayload();
      const result = await completeActivity(followupId, payload);
      onComplete(result);
    } catch (err: any) {
      const msg = err.response?.data?.detail || "Failed to complete activity. Please try again.";
      setWizardError(msg);
      console.error("Activity wizard submission failed:", err);
    } finally {
      setSubmitting(false);
    }
  }, [buildPayload, followupId, onComplete]);

  const totalSteps = 4;

  const responseDateForDisplay = responseCheckDate === "custom" ? customResponseDate : responseCheckDate;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b">
          <div>
            <h2 className="text-lg font-bold">Complete Activity</h2>
            <p className="text-sm text-muted-foreground">{companyName}</p>
            {isResponseCheck && (
              <span className="inline-block mt-1 text-xs bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded-full">Check Customer Response</span>
            )}
          </div>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-muted transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Progress */}
        <div className="px-5 pt-4 pb-2">
          <div className="flex items-center gap-1.5">
            {Array.from({ length: totalSteps }).map((_, i) => (
              <div key={i} className="flex-1 flex items-center gap-1.5">
                <div className={cn(
                  "w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-colors",
                  i + 1 === step ? "bg-primary text-white" : i + 1 < step ? "bg-green-500 text-white" : "bg-muted text-muted-foreground"
                )}>
                  {i + 1 < step ? <CheckCircle2 className="w-3.5 h-3.5" /> : i + 1}
                </div>
                {i + 1 < totalSteps && <div className={cn("flex-1 h-0.5 rounded", i + 1 < step ? "bg-green-500" : "bg-muted")} />}
              </div>
            ))}
          </div>
          <p className="text-xs text-muted-foreground mt-2 text-center">Step {step} of {totalSteps}</p>
        </div>

        {/* Body */}
        <div className="p-5 space-y-5 min-h-[280px]">
          {/* ── STEP 1 ── */}
          {step === 1 && (
            <div className="space-y-4">
              {isResponseCheck ? (
                <>
                  <p className="text-sm font-medium text-muted-foreground">Did the customer respond to your message?</p>
                  <div className="grid grid-cols-2 gap-3">
                    <button
                      onClick={() => { setResponded(true); setStep(2); }}
                      className={cn(
                        "flex flex-col items-center gap-2 p-6 rounded-xl border-2 transition-all",
                        "hover:border-primary/30 hover:bg-primary/5"
                      )}
                    >
                      <ThumbsUp className="w-8 h-8 text-green-500" />
                      <span className="font-semibold text-sm">Yes</span>
                      <span className="text-xs text-muted-foreground">Customer replied</span>
                    </button>
                    <button
                      onClick={() => { setResponded(false); }}
                      className={cn(
                        "flex flex-col items-center gap-2 p-6 rounded-xl border-2 transition-all",
                        "hover:border-primary/30 hover:bg-primary/5"
                      )}
                    >
                      <ThumbsDown className="w-8 h-8 text-amber-500" />
                      <span className="font-semibold text-sm">No</span>
                      <span className="text-xs text-muted-foreground">No reply yet</span>
                    </button>
                  </div>

                  {/* If No — ask what to do next (inline, not separate step) */}
                  {responded === false && (
                    <div className="space-y-4 pt-4 border-t mt-4">
                      <p className="text-sm font-medium">What should happen next?</p>
                      <div className="space-y-2">
                        {NO_RESPONSE_ACTIONS.map((a) => (
                          <button
                            key={a.value}
                            onClick={() => setNoResponseAction(a.value)}
                            className={cn(
                              "w-full text-left px-4 py-3 rounded-xl border text-sm transition-all",
                              noResponseAction === a.value ? "border-primary bg-primary/5 ring-2 ring-primary/20" : "border-border/60 hover:border-primary/30"
                            )}
                          >
                            <span className="font-medium block">{a.label}</span>
                            <span className="text-xs text-muted-foreground">{a.desc}</span>
                          </button>
                        ))}
                      </div>
                      {noResponseAction && noResponseAction !== "custom" && (
                        <div>
                          <p className="text-sm text-muted-foreground mb-2">When?</p>
                          <div className="grid grid-cols-2 gap-2">
                            {RESPONSE_CHECK_OPTIONS.map((o) => (
                              <button
                                key={o.value}
                                onClick={() => setResponseCheckDate(o.value)}
                                className={cn(
                                  "px-4 py-2.5 rounded-xl border text-sm font-medium transition-all",
                                  responseCheckDate === o.value ? "border-primary bg-primary/5 text-primary" : "border-border/60 hover:border-primary/30"
                                )}
                              >
                                {o.label}
                              </button>
                            ))}
                          </div>
                          {responseCheckDate === "custom" && (
                            <input
                              type="date"
                              value={customResponseDate}
                              onChange={(e) => setCustomResponseDate(e.target.value)}
                              className="mt-2 w-full h-10 px-3 rounded-xl border border-input bg-background text-sm"
                            />
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </>
              ) : (
                <>
                  <p className="text-sm font-medium text-muted-foreground">What actions did you perform?</p>
                  <p className="text-xs text-muted-foreground/60 -mt-3">Select all that apply</p>
                  <div className="grid grid-cols-2 gap-3">
                    {ACTION_OPTIONS.map((opt) => {
                      const isSelected = selectedActions.includes(opt.key);
                      return (
                        <button
                          key={opt.key}
                          onClick={() => toggleAction(opt.key)}
                          className={cn(
                            "flex items-center gap-3 p-4 rounded-xl border-2 text-left transition-all",
                            isSelected ? "border-primary bg-primary/5 ring-2 ring-primary/20" : "border-border/60 hover:border-primary/30 hover:bg-muted/30"
                          )}
                        >
                          <div className={cn("p-2 rounded-lg", isSelected ? "bg-primary text-white" : "bg-muted text-muted-foreground")}>
                            {opt.icon}
                          </div>
                          <span className={cn("font-medium text-sm", isSelected ? "text-primary" : "text-foreground")}>{opt.label}</span>
                        </button>
                      );
                    })}
                  </div>
                </>
              )}
            </div>
          )}

          {/* ── STEP 2 ── */}
          {step === 2 && showInterestAfterResponse && (
            <div className="space-y-5">
              <p className="text-sm font-medium text-muted-foreground">How did they respond?</p>
              <div className="grid grid-cols-3 gap-2">
                {RESPONSE_CHANNELS.map((ch) => (
                  <button
                    key={ch.key}
                    onClick={() => setResponseChannel(ch.key)}
                    className={cn(
                      "flex flex-col items-center gap-2 p-4 rounded-xl border text-sm font-medium transition-all",
                      responseChannel === ch.key ? "border-primary bg-primary/5 text-primary ring-2 ring-primary/20" : "border-border/60 hover:border-primary/30"
                    )}
                  >
                    {ch.icon}
                    {ch.label}
                  </button>
                ))}
              </div>

              {responseChannel && (
                <>
                  <div className="pt-3 border-t">
                    <p className="text-sm font-medium mb-2">Customer Interest</p>
                    <div className="grid grid-cols-3 gap-2">
                      {INTEREST_OPTIONS.map((o) => (
                        <button
                          key={o.value}
                          onClick={() => setCustomerInterest(o.value)}
                          className={cn(
                            "px-4 py-2.5 rounded-xl border text-sm font-medium transition-all",
                            customerInterest === o.value ? "border-primary bg-primary/5 text-primary" : "border-border/60 hover:border-primary/30"
                          )}
                        >
                          {o.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Interested → Requirements */}
                  {customerInterest && customerInterest !== "not_interested" && (
                    <div className="space-y-3 pt-3 border-t">
                      <p className="text-sm font-medium">What does the customer require?</p>
                      <div className="flex flex-wrap gap-2">
                        {REQUIREMENT_OPTIONS.map((req) => (
                          <button
                            key={req}
                            onClick={() => toggleRequirement(req)}
                            className={cn(
                              "px-3 py-1.5 rounded-lg border text-xs font-medium transition-all",
                              customerRequirements.includes(req) ? "border-primary bg-primary/5 text-primary" : "border-border/60 hover:border-primary/30"
                            )}
                          >
                            {req}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Not interested → Reason */}
                  {customerInterest === "not_interested" && (
                    <div className="space-y-3 pt-3 border-t">
                      <p className="text-sm font-medium">Reason</p>
                      <div className="grid grid-cols-2 gap-2">
                        {NOT_INTERESTED_REASONS.map((r) => (
                          <button
                            key={r.value}
                            onClick={() => setNotInterestedReason(r.value)}
                            className={cn(
                              "px-4 py-2.5 rounded-xl border text-sm font-medium transition-all",
                              notInterestedReason === r.value ? "border-primary bg-primary/5 text-primary" : "border-border/60 hover:border-primary/30"
                            )}
                          >
                            {r.label}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Maybe → Requirements */}
                  {customerInterest === "maybe" && (
                    <div className="space-y-3 pt-3 border-t">
                      <p className="text-sm font-medium">What does the customer require?</p>
                      <div className="flex flex-wrap gap-2">
                        {REQUIREMENT_OPTIONS.map((req) => (
                          <button
                            key={req}
                            onClick={() => toggleRequirement(req)}
                            className={cn(
                              "px-3 py-1.5 rounded-lg border text-xs font-medium transition-all",
                              customerRequirements.includes(req) ? "border-primary bg-primary/5 text-primary" : "border-border/60 hover:border-primary/30"
                            )}
                          >
                            {req}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {step === 2 && !isResponseCheck && (
            <div className="space-y-5">
              {/* ── Call Flow ── */}
              {showCallFlow && (
                <div className="space-y-4">
                  <div>
                    <p className="text-sm font-medium mb-2">Call Outcome</p>
                    <div className="grid grid-cols-2 gap-2">
                      {CALL_OUTCOMES.map((o) => (
                        <button
                          key={o.value}
                          onClick={() => { setCallOutcome(o.value); if (o.value !== "connected") setCustomerInterest(""); }}
                          className={cn(
                            "px-4 py-2.5 rounded-xl border text-sm font-medium transition-all",
                            callOutcome === o.value ? "border-primary bg-primary/5 text-primary" : "border-border/60 hover:border-primary/30"
                          )}
                        >
                          {o.label}
                        </button>
                      ))}
                    </div>
                  </div>
                  {callOutcome === "connected" && (
                    <div>
                      <p className="text-sm font-medium mb-2">Customer Interest</p>
                      <div className="grid grid-cols-3 gap-2">
                        {INTEREST_OPTIONS.map((o) => (
                          <button
                            key={o.value}
                            onClick={() => setCustomerInterest(o.value)}
                            className={cn(
                              "px-4 py-2.5 rounded-xl border text-sm font-medium transition-all",
                              customerInterest === o.value ? "border-primary bg-primary/5 text-primary" : "border-border/60 hover:border-primary/30"
                            )}
                          >
                            {o.label}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                  {callOutcome === "call_back_later" && (
                    <div>
                      <p className="text-sm text-muted-foreground mb-2">When should we retry?</p>
                      <div className="grid grid-cols-2 gap-2">
                        {RESPONSE_CHECK_OPTIONS.filter(o => o.value !== "custom").map((o) => (
                          <button
                            key={o.value}
                            onClick={() => setResponseCheckDate(o.value)}
                            className={cn(
                              "px-4 py-2.5 rounded-xl border text-sm font-medium transition-all",
                              responseCheckDate === o.value ? "border-primary bg-primary/5 text-primary" : "border-border/60 hover:border-primary/30"
                            )}
                          >
                            {o.label}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* ── Message Flow ── */}
              {showMessageFlow && (
                <div className="space-y-4 pt-3 border-t">
                  <p className="text-sm font-medium text-muted-foreground">Email / WhatsApp</p>
                  <div>
                    <p className="text-sm text-muted-foreground mb-2">Do you expect a response?</p>
                    <div className="flex gap-2">
                      <button
                        onClick={() => setExpectResponse(true)}
                        className={cn(
                          "flex-1 px-4 py-2.5 rounded-xl border text-sm font-medium transition-all",
                          expectResponse === true ? "border-primary bg-primary/5 text-primary" : "border-border/60 hover:border-primary/30"
                        )}
                      >
                        Yes
                      </button>
                      <button
                        onClick={() => { setExpectResponse(false); setResponseCheckDate(""); }}
                        className={cn(
                          "flex-1 px-4 py-2.5 rounded-xl border text-sm font-medium transition-all",
                          expectResponse === false ? "border-primary bg-primary/5 text-primary" : "border-border/60 hover:border-primary/30"
                        )}
                      >
                        No
                      </button>
                    </div>
                  </div>
                  {expectResponse && (
                    <div>
                      <p className="text-sm text-muted-foreground mb-2">When should we check for a reply?</p>
                      <div className="grid grid-cols-2 gap-2">
                        {RESPONSE_CHECK_OPTIONS.map((o) => (
                          <button
                            key={o.value}
                            onClick={() => setResponseCheckDate(o.value)}
                            className={cn(
                              "px-4 py-2.5 rounded-xl border text-sm font-medium transition-all",
                              responseCheckDate === o.value ? "border-primary bg-primary/5 text-primary" : "border-border/60 hover:border-primary/30"
                            )}
                          >
                            {o.label}
                          </button>
                        ))}
                      </div>
                      {responseCheckDate === "custom" && (
                        <input
                          type="date"
                          value={customResponseDate}
                          onChange={(e) => setCustomResponseDate(e.target.value)}
                          className="mt-2 w-full h-10 px-3 rounded-xl border border-input bg-background text-sm"
                        />
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* ── Meeting Flow ── */}
              {showMeetingFlow && (
                <div className="space-y-4 pt-3 border-t">
                  <div>
                    <p className="text-sm font-medium mb-2">Meeting Outcome</p>
                    <div className="grid grid-cols-2 gap-2">
                      {MEETING_OUTCOMES.map((o) => (
                        <button
                          key={o.value}
                          onClick={() => setMeetingOutcome(o.value)}
                          className={cn(
                            "px-4 py-2.5 rounded-xl border text-sm font-medium transition-all",
                            meetingOutcome === o.value ? "border-primary bg-primary/5 text-primary" : "border-border/60 hover:border-primary/30"
                          )}
                        >
                          {o.label}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* ── Interested → Requirements ── */}
              {showInterestedFlow && (
                <div className="space-y-3 pt-3 border-t">
                  <p className="text-sm font-medium">What does the customer require?</p>
                  <div className="flex flex-wrap gap-2">
                    {REQUIREMENT_OPTIONS.map((req) => (
                      <button
                        key={req}
                        onClick={() => toggleRequirement(req)}
                        className={cn(
                          "px-3 py-1.5 rounded-lg border text-xs font-medium transition-all",
                          customerRequirements.includes(req) ? "border-primary bg-primary/5 text-primary" : "border-border/60 hover:border-primary/30"
                        )}
                      >
                        {req}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* ── Not Interested → Reason ── */}
              {showNotInterested && (
                <div className="space-y-3 pt-3 border-t">
                  <p className="text-sm font-medium">Reason</p>
                  <div className="grid grid-cols-2 gap-2">
                    {NOT_INTERESTED_REASONS.map((r) => (
                      <button
                        key={r.value}
                        onClick={() => setNotInterestedReason(r.value)}
                        className={cn(
                          "px-4 py-2.5 rounded-xl border text-sm font-medium transition-all",
                          notInterestedReason === r.value ? "border-primary bg-primary/5 text-primary" : "border-border/60 hover:border-primary/30"
                        )}
                      >
                        {r.label}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ── STEP 3 ── */}
          {step === 3 && (
            <div className="space-y-5">
              <p className="text-sm font-medium text-muted-foreground">Complete This Task</p>
              <div className="space-y-4">

                {/* Session Notes — required */}
                <div>
                  <p className="text-sm font-medium mb-2">What happened in this session? <span className="text-destructive">*</span></p>
                  <textarea
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    maxLength={500}
                    rows={3}
                    className="w-full px-3 py-2 rounded-xl border border-input bg-background text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary/20"
                    placeholder="Describe what was discussed, any decisions made, customer response..."
                  />
                  <p className="text-[11px] text-muted-foreground/50 mt-1">{notes.length}/500</p>
                </div>

                {/* Schedule Next Follow-Up */}
                {!showNotInterested && customerInterest !== "not_interested" && !notInterestedReason && (
                  <div className="border-t border-border/40 pt-4">
                    <p className="text-sm font-semibold mb-3">Schedule Next Follow-Up <span className="text-destructive">*</span></p>

                    {/* Follow-Up Mode */}
                    <div className="mb-3">
                      <p className="text-xs font-medium text-muted-foreground mb-2">Mode</p>
                      <div className="flex flex-wrap gap-2">
                        {RESPONSE_CHANNELS.map((ch) => (
                          <button
                            key={ch.key}
                            onClick={() => setNextFollowupMode(ch.key)}
                            className={cn(
                              "flex items-center gap-1.5 px-3 py-2 rounded-xl border text-sm font-medium transition-all",
                              nextFollowupMode === ch.key
                                ? "border-primary bg-primary/5 text-primary"
                                : "border-border/60 hover:border-primary/30"
                            )}
                          >
                            {ch.icon}
                            {ch.label}
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Follow-Up Date */}
                    <div>
                      <p className="text-xs font-medium text-muted-foreground mb-2">Date</p>
                      <input
                        type="date"
                        value={followupDate}
                        onChange={(e) => setFollowupDate(e.target.value)}
                        className="w-full h-10 px-3 rounded-xl border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
                      />
                    </div>

                    {/* Preview */}
                    {nextFollowupMode && followupDate && (
                      <div className="mt-3 rounded-xl bg-primary/5 border border-primary/20 p-3 flex items-center gap-2 text-sm text-primary">
                        <CheckCircle2 className="w-4 h-4 shrink-0" />
                        Will create: <strong>Follow-Up {nextFollowupMode.charAt(0).toUpperCase() + nextFollowupMode.slice(1)}</strong> on <strong>{followupDate}</strong>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ── STEP 4 ── */}
          {step === 4 && (
            <div className="space-y-5">
              <p className="text-sm font-medium text-muted-foreground">Review & Complete</p>
              <div className="rounded-xl bg-muted/30 p-4 space-y-3 text-sm">
                {isResponseCheck && responded !== null ? (
                  <>
                    <div className="flex items-center gap-2">
                      <HelpCircle className="w-4 h-4 text-muted-foreground" />
                      <span className="font-medium">Response Check:</span>
                      <span>{responded ? "Customer responded" : "No response"}</span>
                    </div>
                    {responded && responseChannel && (
                      <div className="flex items-center gap-2">
                        <MessageSquare className="w-4 h-4 text-green-600" />
                        <span className="font-medium">Channel:</span>
                        <span>{responseChannel}</span>
                      </div>
                    )}
                    {!responded && noResponseAction && (
                      <div className="flex items-center gap-2">
                        <ArrowRight className="w-4 h-4 text-amber-600" />
                        <span className="font-medium">Next:</span>
                        <span>{NO_RESPONSE_ACTIONS.find(a => a.value === noResponseAction)?.label}</span>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="flex items-center gap-2">
                    <Phone className="w-4 h-4 text-muted-foreground" />
                    <span className="font-medium">Actions:</span>
                    <span>{selectedActions.map(a => a.charAt(0).toUpperCase() + a.slice(1)).join(", ")}</span>
                  </div>
                )}

                {customerInterest && (
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-green-600" />
                    <span className="font-medium">Interest:</span>
                    <span>{customerInterest}</span>
                  </div>
                )}

                {customerRequirements.length > 0 && (
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-green-600" />
                    <span className="font-medium">Requirements:</span>
                    <span>{customerRequirements.join(", ")}</span>
                  </div>
                )}

                {notInterestedReason && (
                  <div className="flex items-center gap-2 text-destructive">
                    <X className="w-4 h-4" />
                    <span className="font-medium">Lost:</span>
                    <span>{NOT_INTERESTED_REASONS.find(r => r.value === notInterestedReason)?.label}</span>
                  </div>
                )}

                {followupDate && customerInterest !== "not_interested" && !notInterestedReason && (
                  <div className="flex items-center gap-2">
                    <Calendar className="w-4 h-4 text-primary" />
                    <span className="font-medium">Next Follow-Up:</span>
                    <span>{nextFollowupMode ? `${nextFollowupMode.charAt(0).toUpperCase() + nextFollowupMode.slice(1)} on ` : ""}{followupDate}</span>
                  </div>
                )}

                {notes.trim() && (
                  <div className="pt-2 border-t text-muted-foreground">
                    <p className="font-medium mb-1">Session Notes:</p>
                    <p className="text-xs">{notes}</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        {wizardError && (
          <div className="mx-5 mb-3 p-3 rounded-xl bg-destructive/8 border border-destructive/15 text-destructive text-sm flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            {wizardError}
          </div>
        )}
        <div className="flex items-center justify-between p-5 border-t">
          <Button variant="ghost" onClick={() => step > 1 ? setStep(step - 1) : onClose()} className="gap-2">
            <ArrowLeft className="w-4 h-4" />
            {step === 1 ? "Cancel" : "Back"}
          </Button>

          {step < totalSteps ? (
            <Button onClick={() => setStep(step + 1)}
              disabled={
                (step === 1 && !canProceedStep1) ||
                (step === 2 && (
                  (isResponseCheck && showInterestAfterResponse && !responseChannel) ||
                  (!isResponseCheck && !canProceedStep2)
                )) ||
                (step === 3 && (
                  !notes.trim() ||
                  (!showNotInterested && customerInterest !== "not_interested" && !notInterestedReason && (!nextFollowupMode || !followupDate))
                ))
              }
              className="gap-2"
            >
              Next
              <ArrowRight className="w-4 h-4" />
            </Button>
          ) : (
            <Button onClick={handleSubmit} disabled={submitting} className="gap-2 bg-green-600 hover:bg-green-700">
              {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
              {submitting ? "Submitting..." : "Complete Activity"}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
