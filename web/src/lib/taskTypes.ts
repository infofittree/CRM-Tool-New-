export interface TaskTypeDisplay {
  label: string;
  badge: string;
  badgeColor: string;
  ctaLabel: string;
  description: string;
}

const TEMPLATE_CONFIG: Record<string, TaskTypeDisplay> = {
  "Check Customer Response": {
    label: "Response Check Required",
    badge: "📧 Response Check",
    badgeColor: "bg-indigo-100 text-indigo-700 border-indigo-200",
    ctaLabel: "Check Response",
    description: "A message was sent to this customer. Verify whether a response has been received.",
  },
  "Follow-Up Call": {
    label: "Follow-Up Call",
    badge: "📞 Call Back",
    badgeColor: "bg-amber-100 text-amber-700 border-amber-200",
    ctaLabel: "Log Call",
    description: "This is a scheduled follow-up call to reconnect with this lead.",
  },
  "Send Quotation": {
    label: "Send Quotation",
    badge: "📋 Quotation",
    badgeColor: "bg-blue-100 text-blue-700 border-blue-200",
    ctaLabel: "Send Quote",
    description: "Prepare and send a quotation to this customer based on their requirements.",
  },
  "Conduct Meeting": {
    label: "Schedule Meeting",
    badge: "🤝 Meeting",
    badgeColor: "bg-purple-100 text-purple-700 border-purple-200",
    ctaLabel: "Log Meeting",
    description: "Schedule or conduct a meeting with this customer to discuss their needs.",
  },
  "Follow Up On Samples": {
    label: "Samples Follow-Up",
    badge: "📦 Samples",
    badgeColor: "bg-teal-100 text-teal-700 border-teal-200",
    ctaLabel: "Update Samples",
    description: "Follow up on product samples sent to this customer.",
  },
  "Review Procurement Response": {
    label: "Procurement Response",
    badge: "🏭 Procurement",
    badgeColor: "bg-orange-100 text-orange-700 border-orange-200",
    ctaLabel: "Check Response",
    description: "Review the response from the procurement team regarding an inquiry.",
  },
  "Follow-Up": {
    label: "Follow-Up Required",
    badge: "📌 Task",
    badgeColor: "bg-gray-100 text-gray-700 border-gray-200",
    ctaLabel: "Complete Task",
    description: "Follow up with this lead as scheduled.",
  },
};

const NEXT_ACTION_TO_TEMPLATE: Record<string, string> = {
  "Call Again": "Follow-Up Call",
  "Send Quotation": "Send Quotation",
  "Await Customer Response": "Check Customer Response",
  "Schedule Meeting": "Conduct Meeting",
  "Send Samples": "Follow Up On Samples",
  "Request Procurement Information": "Review Procurement Response",
  "Other": "Follow-Up",
};

export function getTaskTypeConfig(discussion?: string | null, nextAction?: string | null): TaskTypeDisplay {
  if (discussion && TEMPLATE_CONFIG[discussion]) {
    return TEMPLATE_CONFIG[discussion];
  }
  if (nextAction) {
    const template = NEXT_ACTION_TO_TEMPLATE[nextAction];
    if (template && TEMPLATE_CONFIG[template]) {
      return TEMPLATE_CONFIG[template];
    }
  }
  return TEMPLATE_CONFIG["Follow-Up"];
}

export function getTaskOrigin(discussion?: string | null, nextAction?: string | null, lastContactDate?: string | null): string {
  const config = getTaskTypeConfig(discussion, nextAction);
  const dateStr = lastContactDate ? new Date(lastContactDate).toLocaleDateString() : null;

  if (discussion === "Check Customer Response" || nextAction === "Await Customer Response") {
    return dateStr ? `Customer was contacted on ${dateStr}. Follow-up is needed to check their response.` : "Customer was contacted. Follow-up is needed to check their response.";
  }
  if (discussion === "Follow-Up Call" || nextAction === "Call Again") {
    return dateStr ? `Last contact was on ${dateStr}. A follow-up call is due.` : "A follow-up call is due for this lead.";
  }
  if (discussion === "Send Quotation" || nextAction === "Send Quotation") {
    return dateStr ? `Requirements were discussed on ${dateStr}. A quotation needs to be sent.` : "A quotation needs to be prepared and sent.";
  }
  if (discussion === "Conduct Meeting" || nextAction === "Schedule Meeting") {
    return dateStr ? `Last discussed on ${dateStr}. A meeting should be scheduled.` : "A meeting should be scheduled with this customer.";
  }
  if (discussion === "Follow Up On Samples" || nextAction === "Send Samples") {
    return dateStr ? `Samples were discussed on ${dateStr}. Follow up is needed.` : "Follow up on samples is needed.";
  }
  if (discussion === "Review Procurement Response" || nextAction === "Request Procurement Information") {
    return "A procurement inquiry response is awaiting review.";
  }
  return dateStr ? `Last contact was on ${dateStr}. Follow-up is due.` : "A follow-up is due for this lead.";
}

export interface WorkflowDebug {
  taskType: string;
  discussion: string | null;
  nextAction: string | null;
  template: string;
  bucket: string;
  daysTo: number;
}

export function getWorkflowDebug(task: any): WorkflowDebug {
  return {
    taskType: task.next_action || (task.discussion || "standard"),
    discussion: task.discussion,
    nextAction: task.next_action,
    template: getTaskTypeConfig(task.discussion, task.next_action).label,
    bucket: task.bucket,
    daysTo: task.days_to,
  };
}
