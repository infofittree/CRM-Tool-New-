const H = require("./helpers");
const { h1, h2, h3, p, lead, bullet, num, kpi, spacer, pageBreak, source, figcap, table, hbar, callout } = H;

// ===================== SECTION 4: SERVICE DEMAND ANALYSIS =====================
function section4() {
  // Top services ranked composite (1-10 scale per criterion)
  const svc = [
    ["AI Chatbots / Customer-support AI", 9, 8, 9, 9, "Low–Med", "$1.5–15k + $300–3k/mo"],
    ["Workflow & Business-Process Automation", 9, 8, 8, 8, "Med", "$3–40k + retainer"],
    ["AI Agents (agentic automation)", 10, 9, 6, 8, "High", "$10–80k + usage"],
    ["RAG knowledge assistants", 9, 8, 7, 8, "Med", "$5–40k + $0.5–5k/mo"],
    ["Lead-gen & Sales Automation", 9, 8, 9, 8, "Low–Med", "$2–20k + $500–4k/mo"],
    ["AI Marketing Automation / content", 9, 7, 9, 8, "Low", "$1–15k + $300–3k/mo"],
    ["Data Analytics & BI dashboards", 8, 8, 8, 7, "Med", "$5–60k + support"],
    ["CRM/ERP implementation + AI", 8, 8, 6, 9, "Med–High", "$10–150k + AMC"],
    ["Website / Web-app development", 9, 6, 9, 5, "Low", "$2–50k"],
    ["Custom software / SaaS build", 8, 8, 5, 7, "High", "$15–250k+"],
    ["Predictive analytics / ML models", 7, 9, 5, 7, "High", "$15–120k + MLOps"],
    ["AI Voice agents", 8, 8, 6, 8, "Med–High", "$5–50k + usage"],
    ["Computer-vision (QC, retail, security)", 7, 9, 5, 7, "High", "$15–150k"],
    ["RPA / Intelligent Process Automation", 8, 8, 6, 8, "Med", "$8–80k + licences"],
    ["HR / Recruitment automation", 8, 7, 8, 8, "Low–Med", "$3–30k + SaaS"],
    ["AI Dashboards / exec reporting", 8, 7, 8, 7, "Low–Med", "$3–25k + retainer"],
    ["Cybersecurity (AI-driven)", 8, 8, 5, 9, "High", "$10–120k + MSSP"],
    ["Cloud migration & managed cloud", 7, 8, 6, 9, "Med–High", "$10–200k + managed"],
    ["Digital-transformation consulting", 7, 9, 5, 6, "Med", "$15–250k"],
    ["Supply-chain / inventory optimisation", 7, 9, 5, 7, "High", "$15–150k"],
  ];
  const rows = [["Service", "Dmd", "Profit", "Ease", "Recur.", "Difficulty", "Typical Price (USD)"]];
  svc.forEach((s) => rows.push([s[0],
    { text: String(s[1]), align: H.docx.AlignmentType.CENTER },
    { text: String(s[2]), align: H.docx.AlignmentType.CENTER },
    { text: String(s[3]), align: H.docx.AlignmentType.CENTER },
    { text: String(s[4]), align: H.docx.AlignmentType.CENTER },
    s[5], s[6]]));

  return [
    new H.docx.Paragraph({ pageBreakBefore: true, heading: H.docx.HeadingLevel.HEADING_1, children: [H.t("4. Service Demand Analysis")] }),
    lead("Not all services are equal. The winners combine high demand, recurring revenue, fast sales cycles and AI-native delivery leverage. Below, 20 leading services are scored 1–10 across demand, profitability, ease of selling and recurring potential."),

    h2("4.1 What Businesses Want Most (2025–2030)"),
    p("Demand has shifted decisively from 'build me software' to 'make my business run itself.' The hottest budget lines are customer-facing AI (chatbots/voice), revenue automation (lead-gen/sales/marketing), and back-office process automation — because each maps to a clear ROI (revenue up or cost down). Heavier engagements (custom SaaS, predictive ML, computer vision, digital-transformation programmes) carry larger ticket sizes but longer sales cycles and higher delivery risk."),

    h2("4.2 Service Ranking Matrix"),
    p("Scores 1–10 (10 = best). 'Recur.' = recurring-revenue potential. Pricing reflects SME-to-mid-market projects; enterprise multiples are higher."),
    table([2640, 640, 700, 680, 720, 1180, 2800], rows, { fontSize: 14 }),
    figcap("Figure 4. Service scoring matrix (composite analyst + market view)."),

    h2("4.3 Demand vs. Recurring-Revenue Leaders"),
    hbar([
      { label: "AI Agents", value: 10, display: "10", color: H.GREEN },
      { label: "AI Chatbots", value: 9, display: "9", color: H.GREEN },
      { label: "Workflow Automation", value: 9, display: "9", color: H.GREEN },
      { label: "Lead-gen / Sales Auto", value: 9, display: "9", color: H.BLUE },
      { label: "RAG Assistants", value: 9, display: "9", color: H.BLUE },
      { label: "Marketing Automation", value: 9, display: "9", color: H.BLUE },
      { label: "Web / App Dev", value: 9, display: "9 (low recur.)", color: H.AMBER },
      { label: "Analytics & BI", value: 8, display: "8", color: H.BLUE },
    ], { maxVal: 10 }),
    figcap("Figure 5. Demand score by service (color = recurring-revenue strength: green high, amber low)."),

    h2("4.4 Why Companies Buy — Top Services"),
    table([2500, 3500, 3360], [
      ["Service", "Why they buy", "Industries demanding it most"],
      ["AI Chatbots / Support AI", "Cut support cost 30–60%, 24/7 coverage, faster response", "E-commerce, BFSI, healthcare, real estate, travel, education"],
      ["Workflow Automation", "Eliminate manual ops, fewer errors, scale without headcount", "Manufacturing, logistics, finance, HR, services"],
      ["AI Agents", "Automate multi-step knowledge work end-to-end", "All — esp. ops, sales, support, finance"],
      ["Lead-gen / Sales Automation", "More qualified pipeline, lower CAC, faster follow-up", "B2B services, real estate, exports, SaaS, education"],
      ["Marketing Automation", "Content at scale, personalisation, lower agency cost", "D2C, retail, e-commerce, hospitality"],
      ["Analytics & BI", "Decisions from data, replace gut-feel + manual Excel", "Retail, manufacturing, BFSI, healthcare"],
      ["CRM/ERP + AI", "Single source of truth, automated processes", "Manufacturing, distribution, services, exports"],
    ], { fontSize: 16 }),

    h2("4.5 Profit, Difficulty & Recommended Model"),
    table([2500, 1500, 1600, 3760], [
      ["Service", "Gross margin", "Team needed", "Recommended business model"],
      ["AI Chatbots / RAG", "55–75%", "2–3 (eng + PM)", "Build fee + monthly managed/usage retainer"],
      ["Workflow / RPA / IPA", "50–70%", "2–4", "Build + run (managed automation) retainer"],
      ["Lead-gen / Sales Auto", "60–80%", "1–2 + tools", "Setup + monthly performance retainer"],
      ["Marketing Automation", "60–80%", "1–3", "Monthly retainer (highly recurring)"],
      ["Analytics & BI", "45–65%", "2–4", "Project + dashboard support subscription"],
      ["Custom SaaS / software", "35–55%", "4–8", "Fixed-bid build, then AMC + features"],
      ["Computer vision / ML", "40–60%", "3–5 (ML heavy)", "Project + MLOps managed services"],
      ["Digital-transformation consulting", "55–75%", "1–3 senior", "Advisory retainer → implementation pull-through"],
    ], { fontSize: 16 }),

    h2("4.6 Competitor Saturation"),
    bullet([H.t("High saturation (compete on niche/price): ", { bold: true }), H.t("website/app dev, generic chatbots, basic marketing automation.")]),
    bullet([H.t("Medium (differentiate on vertical/outcome): ", { bold: true }), H.t("workflow automation, analytics/BI, CRM/ERP, RPA.")]),
    bullet([H.t("Low (blue-water for a focused entrant): ", { bold: true }), H.t("vertical AI agents, RAG over private data, AI governance/pilot-rescue, vernacular/SME automation, export & compliance automation.")]),

    h2("4.7 Quick-Win Services for a New Company"),
    callout("Start here — fast cash, fast proof", [
      "1. AI Chatbots / WhatsApp + RAG support bots — short build, instant demo, monthly retainer.",
      "2. Lead-gen & Sales automation — sell to businesses that themselves want growth; performance-linked retainers.",
      "3. Workflow / back-office automation — high pain, clear ROI, sticky 'build + run' revenue.",
      "4. AI marketing / content automation — low delivery risk, recurring, easy upsell.",
      "5. Analytics dashboards — visible value, gateway to larger transformation work.",
      "These 5 are fast to sell, fast to deliver, recurring, and deliverable with a lean AI-native team.",
    ]),
    source("Composite of Grand View, Precedence, Future Market Insights, Technavio service-segment data + practitioner benchmarks (2024–2026). Pricing = market-observed SME/mid-market ranges. Full citations in References."),
  ];
}

// ===================== SECTION 5: INDUSTRY-WISE OPPORTUNITY ANALYSIS =====================
function section5() {
  const ind = [
    ["Manufacturing", "Manual QC, downtime, paper logs, planning by gut", "Vision QC, predictive maintenance, demand forecasting, MES copilots", "$15–150k", "★★★★★"],
    ["Healthcare / Clinics", "Appointment chaos, no-shows, billing, records", "Booking/voice agents, RAG patient FAQ, claims/billing automation", "$5–60k", "★★★★☆"],
    ["Pharma", "R&D data, compliance, pharmacovigilance, sales", "Doc AI, regulatory automation, predictive analytics, rep copilots", "$25–250k", "★★★★☆"],
    ["Education / EdTech", "Admissions, support, grading, personalization", "Admission chatbots, AI tutors, content gen, ops automation", "$3–40k", "★★★★☆"],
    ["Hospitality", "Bookings, reviews, staffing, upsell", "Voice/chat booking, review/CX AI, dynamic pricing", "$3–30k", "★★★★☆"],
    ["Food Processing / Organic Food", "Quality, traceability, demand, exports", "Vision grading, traceability, demand forecasting, export docs", "$10–80k", "★★★★☆"],
    ["Agriculture / Agritech", "Yield, advisory, supply linkage", "Crop/vision AI, vernacular advisory bots, mandi/price analytics", "$5–60k", "★★★☆☆"],
    ["Logistics / Supply Chain", "Routing, tracking, manual coordination", "Route/ETA AI, control-tower dashboards, doc automation", "$15–150k", "★★★★★"],
    ["Real Estate", "Lead handling, slow follow-up, site queries", "Lead-gen + WhatsApp/voice agents, virtual tours, CRM automation", "$2–25k", "★★★★★"],
    ["Finance / Banking / NBFC", "Onboarding, fraud, support, reporting", "KYC/onboarding AI, fraud ML, support bots, reg-reporting automation", "$15–200k", "★★★★☆"],
    ["Insurance", "Underwriting, claims, agent productivity", "Claims automation, risk ML, agent copilots, support AI", "$15–150k", "★★★★☆"],
    ["Retail / E-commerce", "Support volume, personalization, inventory", "Support/voice AI, recommendation, inventory + demand forecasting", "$3–60k", "★★★★★"],
    ["Automotive / Dealerships", "Lead follow-up, service booking, inventory", "Lead + service-booking agents, parts demand ML, CRM automation", "$5–50k", "★★★★☆"],
    ["Export / Import", "Documentation, compliance, comms, leads", "Trade-doc automation, compliance AI, multilingual lead/comms agents", "$5–60k", "★★★★★"],
    ["Construction / Real-estate dev", "Project tracking, procurement, safety", "Vision safety/progress, procurement analytics, doc automation", "$15–120k", "★★★☆☆"],
    ["HR / Recruitment", "Screening, scheduling, onboarding, queries", "Resume-screening AI, scheduling/onboarding bots, HR copilots", "$3–40k", "★★★★☆"],
    ["Legal", "Document review, research, intake", "Contract/doc AI, research copilots, client-intake automation", "$5–60k", "★★★★☆"],
    ["Textile", "Design, QC, order mgmt, exports", "Design GenAI, vision QC, order + export automation", "$8–80k", "★★★★☆"],
    ["Travel", "Bookings, itineraries, support", "Itinerary/voice agents, dynamic packaging, support AI", "$3–40k", "★★★★☆"],
    ["Energy / Utilities", "Asset monitoring, demand, outages", "Predictive maintenance, demand ML, vision inspection", "$25–200k", "★★★☆☆"],
    ["Telecom", "Churn, support, network ops", "Churn ML, support automation, network analytics", "$25–250k", "★★★☆☆"],
    ["Government / Public", "Citizen services, records, grievances", "Multilingual citizen bots, doc digitisation, analytics", "$15–250k", "★★★☆☆"],
  ];
  const rows = [["Industry", "Key pain points", "Highest-ROI AI / automation services", "Project value", "Sell-ability"]];
  ind.forEach((r) => rows.push([{ text: r[0], bold: true }, r[1], r[2], r[3], { text: r[4], align: H.docx.AlignmentType.CENTER }]));

  return [
    new H.docx.Paragraph({ pageBreakBefore: true, heading: H.docx.HeadingLevel.HEADING_1, children: [H.t("5. Industry-Wise Opportunity Analysis")] }),
    lead("Every industry has the same disease — manual, repetitive, error-prone work — and AI is the cure. The art is choosing industries where pain is high, budgets exist, and you can build a repeatable, productised solution rather than a bespoke project each time."),

    p("The matrix below maps 22 industries to their core pain points, the highest-ROI services, typical project value (SME/mid-market) and a sell-ability rating (★ = ease of landing + repeatability). Industries marked ★★★★★ combine acute pain, ready budget and productisable solutions — the priority hunting grounds for a new division, especially in a Gujarat/India context."),

    h2("5.1 Industry Opportunity Matrix"),
    table([1500, 2550, 2950, 1150, 1210], rows, { fontSize: 14 }),
    figcap("Figure 6. Industry × opportunity matrix. Project value = typical SME/mid-market engagement (USD)."),

    h2("5.2 Highest-Priority Industries (★★★★★) — Deeper View"),

    h3("Manufacturing (incl. textile, chemicals, food processing — Gujarat core)"),
    bullet("Pain: manual quality inspection, unplanned downtime, paper-based logs, gut-feel planning, fragmented data."),
    bullet("High-ROI plays: computer-vision QC, predictive maintenance, demand/production forecasting, MES/ERP copilots, energy optimisation."),
    bullet("Monthly recurring: vision-model monitoring, dashboard support, forecast retraining (MLOps retainer)."),
    bullet("Why now: Industry 4.0 push + cheap edge AI; ROI is hard cost savings, easy to prove on the shop floor."),

    h3("Logistics & Supply Chain"),
    bullet("Pain: manual routing/coordination, no real-time visibility, document-heavy operations."),
    bullet("High-ROI plays: route/ETA optimisation, control-tower dashboards, shipment-doc automation, demand-inventory ML."),
    bullet("Recurring: managed optimisation + analytics subscription."),

    h3("Real Estate & Automotive Dealerships"),
    bullet("Pain: leads lost to slow follow-up; repetitive site/service queries; weak CRM hygiene."),
    bullet("High-ROI plays: 24/7 WhatsApp/voice lead-qualification agents, automated follow-up, CRM automation, virtual tours."),
    bullet("Recurring: monthly retainer per location/dealership — highly scalable, productisable."),

    h3("Retail / E-commerce / D2C"),
    bullet("Pain: support volume spikes, weak personalisation, inventory mismatch, rising ad costs."),
    bullet("High-ROI plays: support/voice AI, recommendation engines, demand forecasting, marketing-content automation."),
    bullet("Recurring: support-bot + marketing-automation retainers; usage-based scaling."),

    h3("Export / Import (Gujarat / Surat / Mumbai strength)"),
    bullet("Pain: heavy documentation, compliance complexity, multilingual buyer communication, lead generation abroad."),
    bullet("High-ROI plays: trade-document & compliance automation, multilingual lead-gen + comms agents, market analytics."),
    bullet("Recurring: lead-gen retainers + document-automation subscription — a defensible, under-served niche."),

    h2("5.3 Future Industry Trends"),
    bullet("Vertical AI copilots become standard tools per industry (factory copilot, clinic copilot, dealership copilot)."),
    bullet("Computer vision moves from novelty to default QC/safety layer in manufacturing & construction."),
    bullet("Voice AI becomes the front door for high-volume consumer industries (healthcare, real estate, travel, retail)."),
    bullet("Regulated industries (BFSI, pharma, healthcare) drive demand for governed, on-prem/private AI."),
    bullet("SMEs adopt productised, subscription AI the way they adopted SaaS — opening volume markets."),
    source("Industry pain-point and ROI mapping synthesised from McKinsey, BCG, NASSCOM sector studies, WEF SME AI Playbook 2025, and practitioner benchmarks. Project values are market-observed estimates. Full citations in References."),
  ];
}

module.exports = { section4, section5 };
