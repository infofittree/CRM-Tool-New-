const H = require("./helpers");
const { h1, h2, h3, p, lead, bullet, num, kpi, spacer, pageBreak, source, figcap, table, hbar, callout } = H;

// ===================== SECTION 6: GEOGRAPHICAL DEMAND =====================
function section6() {
  const ctry = [
    ["USA", "92", "$50–250k", "Very High", "Med (remote OK)", "Healthcare, BFSI, SaaS, retail, real estate"],
    ["UAE", "85", "$20–120k", "Med", "High", "Real estate, retail, govt, logistics, hospitality"],
    ["UK", "84", "$25–150k", "High", "Med-High", "BFSI, professional services, retail, healthcare"],
    ["Saudi Arabia", "82", "$30–200k", "Med", "Med-High", "Govt (Vision 2030), energy, construction, retail"],
    ["Singapore", "80", "$25–150k", "High", "High", "BFSI, logistics, trade, SaaS"],
    ["Germany", "79", "$30–180k", "High", "Med", "Manufacturing, automotive, logistics, Mittelstand"],
    ["Australia", "78", "$25–140k", "Med", "High", "Retail, healthcare, mining, real estate"],
    ["Canada", "77", "$25–140k", "Med", "High", "BFSI, retail, healthcare, SaaS"],
    ["Netherlands", "76", "$25–150k", "Med", "High", "Logistics, agritech, BFSI, retail"],
    ["India", "62", "$2–60k", "Med (fragmented)", "Very High (home)", "Mfg, exports, retail, real estate, healthcare, SME"],
  ];
  const rows = [["Country", "Readiness*", "Avg deal size", "Competition", "Remote ease", "Best industries to target"]];
  ctry.forEach((c) => rows.push([{ text: c[0], bold: true }, { text: c[1], align: H.docx.AlignmentType.CENTER }, c[2], c[3], c[4], c[5]]));

  return [
    new H.docx.Paragraph({ pageBreakBefore: true, heading: H.docx.HeadingLevel.HEADING_1, children: [H.t("6. Geographical Demand Analysis")] }),
    lead("Win at home, sell to the world. The optimal strategy for an India-based AI division: build proof and cash flow domestically, then export high-margin remote delivery to the US, UK, UAE and Gulf — where deal sizes are 5–20× larger."),

    h2("6.1 Country Attractiveness Ranking"),
    p("'Readiness' is a composite (0–100) of AI adoption, IT/digital-transformation spend, SME + enterprise demand and ease of remote delivery. The USA leads on spend and deal size; the Gulf (UAE, Saudi) offers fast-moving, less-saturated demand and cultural openness to outsourced delivery; India is the home base — lower deal sizes but unmatched access and the lowest delivery cost."),
    hbar([
      { label: "USA", value: 92, display: "92" },
      { label: "UAE", value: 85, display: "85" },
      { label: "UK", value: 84, display: "84" },
      { label: "Saudi Arabia", value: 82, display: "82" },
      { label: "Singapore", value: 80, display: "80" },
      { label: "Germany", value: 79, display: "79" },
      { label: "Australia", value: 78, display: "78" },
      { label: "Canada", value: 77, display: "77" },
      { label: "Netherlands", value: 76, display: "76" },
      { label: "India", value: 62, display: "62 (home)", color: H.AMBER },
    ], { maxVal: 100 }),
    figcap("Figure 7. Composite market-readiness score by target country (analyst composite)."),

    h2("6.2 Country Demand Matrix"),
    table([1350, 1150, 1700, 1700, 1650, 1810], rows, { fontSize: 14 }),
    figcap("Figure 8. *Readiness = composite of AI adoption, IT spend, SME + enterprise demand, remote-delivery ease."),

    h2("6.3 Entry Strategy by Geography"),
    table([1700, 7660], [
      ["Market", "Recommended entry approach"],
      ["India (home)", "Land first clients here for proof, cash flow and case studies. Target Gujarat manufacturing/exports/SME + metro mid-market. In-person + WhatsApp + referrals."],
      ["UAE / Gulf", "Highest-ROI export market: large deals, fast decisions, open to remote/offshore. Use LinkedIn, partnerships, occasional on-site. Vision-2030 (KSA) public + retail spend."],
      ["USA", "Largest deals; win via niche positioning + cold email/LinkedIn + productised offers. Time-zone overlap manageable; price 5–20× India."],
      ["UK / Canada / Australia", "English-language, remote-friendly mid-market. Cold outbound + content + referrals."],
      ["Germany / Netherlands / Singapore", "Manufacturing/logistics/BFSI; partner- and referral-led; localisation and trust matter more."],
    ], { fontSize: 16 }),

    h2("6.4 B2B Outreach Strategy by Region"),
    bullet([H.t("India: ", { bold: true }), H.t("WhatsApp + phone + in-person + referrals + local business networks (industry associations, GIDC clusters, export councils).")]),
    bullet([H.t("Gulf: ", { bold: true }), H.t("LinkedIn + warm intros + local partner/reseller + occasional on-site demos; relationship-led.")]),
    bullet([H.t("USA/UK/AU/CA: ", { bold: true }), H.t("Cold email + LinkedIn + niche content + targeted AI demos; productised, outcome-led offers.")]),
    bullet([H.t("EU/SG: ", { bold: true }), H.t("Partnerships, marketplaces (hyperscaler/ISV), and referrals; compliance and data-residency messaging.")]),

    h2("6.5 Recommended Geographic Sequencing"),
    callout("Geo roadmap", [
      "Phase 1 (0–6 mo): India home market — Gujarat + metros. Build 5–10 reference clients.",
      "Phase 2 (6–12 mo): UAE/Gulf remote delivery for larger margins + 1–2 anchor logos.",
      "Phase 3 (12–24 mo): USA/UK productised offers via outbound + content once case studies exist.",
      "Always-on: remote-first delivery keeps delivery cost low and margins high across all geos.",
    ]),
    source("Composite of Gartner IT-spend forecasts, IDC, Statista country AI-adoption data, NASSCOM export data, and Gulf Vision-2030 programmes (2024–2026). Deal sizes are market-observed. Full citations in References."),
  ];
}

// ===================== SECTION 7: CUSTOMER PERSONA =====================
function section7() {
  const personas = [
    ["Startups", "No process, scaling chaos, limited cash", "$500–10k", "Founder", "1–3 wks", "Need to scale without hiring", "Founder networks, Twitter/LinkedIn, communities"],
    ["SMEs / MSMEs", "Manual ops, owner-dependent, thin margins", "$1–15k", "Owner / MD", "1–4 wks", "Cost pain, competitor uses AI, growth stall", "WhatsApp, referrals, in-person, local networks"],
    ["Mid-size firms", "Silos, legacy systems, scaling pains", "$10–80k", "CXO / Function head", "1–3 mo", "Efficiency mandate, board pressure", "LinkedIn, case studies, referrals, events"],
    ["Enterprises", "Bureaucracy, governance, legacy", "$50–500k+", "CIO/CDO + procurement", "3–9 mo", "Strategic AI mandate, competitive risk", "Partnerships, RFPs, thought leadership"],
    ["Factories / Mfg", "Downtime, QC, paper logs", "$10–150k", "Plant head / Owner", "1–3 mo", "Quality/cost pressure, exports", "In-person, industry assoc., referrals"],
    ["Exporters", "Docs, compliance, foreign leads", "$3–60k", "Owner / Export head", "2–6 wks", "Order growth, compliance load", "Export councils, WhatsApp, LinkedIn, referrals"],
    ["E-commerce / D2C", "Support volume, ads cost, inventory", "$2–40k", "Founder / Marketing head", "1–4 wks", "Margin pressure, scale", "LinkedIn, communities, content, ads"],
  ];
  const rows = [["Persona", "Pain points", "Budget", "Decision-maker", "Sales cycle", "Buying trigger", "Best channel"]];
  personas.forEach((r) => rows.push([{ text: r[0], bold: true }, r[1], r[2], r[3], r[4], r[5], r[6]]));

  return [
    new H.docx.Paragraph({ pageBreakBefore: true, heading: H.docx.HeadingLevel.HEADING_1, children: [H.t("7. Customer Persona Analysis")] }),
    lead("Sell to the owner who feels the pain and controls the budget. For a new division, the SME/mid-market owner-operator and the manufacturing/export business owner are the fastest 'yes' — short cycles, clear ROI, direct decision-makers."),

    h2("7.1 Persona Matrix"),
    table([1250, 1700, 1050, 1450, 1050, 1600, 1260], rows, { fontSize: 13 }),
    figcap("Figure 9. Customer persona matrix — budgets in USD per engagement."),

    h2("7.2 Priority Personas for a New Entrant"),
    callout("Best first customers", [
      "SME / MSME owners — feel pain daily, decide fast, pay for clear ROI. Reach via WhatsApp, referrals, in-person.",
      "Manufacturing & export business owners (Gujarat core) — budget + acute, specific pain (QC, docs, leads).",
      "E-commerce / D2C founders — tech-comfortable, fast cycles, recurring marketing/support needs.",
      "Avoid (at first): large enterprises — long cycles, procurement, references required you don't yet have.",
    ]),

    h2("7.3 Buying Triggers to Listen For"),
    bullet("\"My team can't keep up / I can't find or afford staff\" → automation pitch."),
    bullet("\"A competitor is using AI / we're falling behind\" → FOMO; lead with a demo."),
    bullet("\"We're losing leads / support is overwhelmed\" → chatbot/voice + lead-automation."),
    bullet("\"Too much manual paperwork / Excel hell\" → workflow + document automation."),
    bullet("\"We have data but no insight\" → analytics/BI dashboards."),

    h2("7.4 Most Effective Sales Method by Persona"),
    table([2200, 7160], [
      ["Persona", "What actually closes them"],
      ["SME / MSME owner", "Live WhatsApp/voice demo on THEIR use case + ROI in rupees + a small paid pilot."],
      ["Mfg / export owner", "On-site or video walkthrough of a similar plant/exporter case + payback math."],
      ["E-commerce / D2C", "Free mini-audit + a working demo bot + month-1 results guarantee."],
      ["Mid-size CXO", "Business case + case study + phased pilot with defined KPIs."],
      ["Enterprise", "Partnership/RFP, security + governance proof, reference logos, POC."],
    ], { fontSize: 16 }),
    source("Persona budgets and cycles synthesised from SME B2B benchmarks, NASSCOM/WEF SME studies, and practitioner sales data (2024–2026). Full citations in References."),
  ];
}

// ===================== SECTION 8: BUSINESS MODEL =====================
function section8() {
  return [
    new H.docx.Paragraph({ pageBreakBefore: true, heading: H.docx.HeadingLevel.HEADING_1, children: [H.t("8. Business Model Strategy")] }),
    lead("Start as a productised agency, evolve into managed services + retainers, and graduate select solutions into SaaS. The goal: convert one-off project cash into compounding recurring revenue with AI-leveraged delivery margins of 55–75%."),

    h2("8.1 Model Options Compared"),
    table([1750, 1500, 1500, 1450, 3160], [
      ["Model", "Recurring", "Margin", "Scalability", "Fit for a new division"],
      ["Pure agency / projects", "Low", "40–60%", "Low (linear)", "Good for cash + proof; weak long-term"],
      ["Consulting / advisory", "Med", "55–75%", "Med", "High-trust entry; pulls through delivery"],
      ["Retainer / managed services", "High", "50–70%", "Med-High", "Best near-term recurring engine"],
      ["Subscription (productised)", "High", "60–80%", "High", "Productise top services into monthly plans"],
      ["SaaS / product", "Very High", "70–85%", "Very High", "Long-term: graduate proven solutions into IP"],
      ["Hybrid (recommended)", "High", "55–75%", "High", "Project → retainer → SaaS ladder"],
    ], { fontSize: 16 }),

    h2("8.2 Recommended Model — The Hybrid 'Land-and-Expand' Ladder"),
    num("Land with a productised project (chatbot, automation, dashboard) — fast cash, fast proof."),
    num("Expand into a monthly managed/retainer relationship (run + improve + monitor) — recurring revenue."),
    num("Cross-sell adjacent automations across the client's business — grow account value."),
    num("Productise repeatable solutions into subscriptions, then into SaaS IP — compounding margin and enterprise value."),
    p("This ladder uses low-risk projects to fund a growing base of recurring revenue, while AI-native delivery keeps margins high. It also de-risks the business: by month 12 a meaningful share of revenue should be recurring, smoothing the lumpiness of project sales."),

    h2("8.3 Pricing Strategy"),
    table([2300, 7060], [
      ["Pricing lever", "Recommendation"],
      ["Productised packages", "Fixed-price 'good/better/best' tiers per service (e.g., Chatbot Starter / Pro / Enterprise) — removes scoping friction, speeds sales."],
      ["Monthly retainers", "₹25k–₹3L+/mo (India) or $500–$5k+/mo (export) for run + support + improvements."],
      ["Outcome / performance", "Where measurable (leads, cost saved), add success fees — aligns incentives, justifies premium."],
      ["Usage-based", "For AI agents/bots: base fee + per-conversation/token pass-through with margin."],
      ["Value-based (enterprise)", "Price to % of ROI delivered, not cost of build — captures premium on high-impact work."],
      ["Geographic arbitrage", "Same delivery, priced 5–20× higher for US/UK/Gulf vs India — protect margin, fund growth."],
    ], { fontSize: 16 }),

    h2("8.4 Indicative Pricing Table"),
    table([2600, 2253, 2253, 2254], [
      ["Service package", "India (₹)", "Gulf ($)", "US/UK ($)"],
      ["AI Chatbot / WhatsApp bot — setup", "₹40k–2L", "$2–8k", "$4–15k"],
      ["Chatbot managed — monthly", "₹15k–60k", "$400–1.5k", "$800–3k"],
      ["Workflow / RPA automation — build", "₹1.5–8L", "$5–25k", "$10–40k"],
      ["Lead-gen + sales automation — monthly", "₹40k–2L", "$1–4k", "$2–6k"],
      ["Analytics / BI dashboard — project", "₹2–12L", "$6–30k", "$10–50k"],
      ["AI agent (custom) — build", "₹3–20L", "$10–60k", "$20–80k"],
      ["Digital-transformation advisory — monthly", "₹1.5–6L", "$4–15k", "$8–25k"],
    ], { fontSize: 16 }),
    figcap("Figure 10. Indicative pricing — protect margin via geographic arbitrage and productised tiers."),
    source("Pricing synthesised from market-observed SME/mid-market rates across India, Gulf and US/UK (2024–2026). Indicative only. Full citations in References."),
  ];
}

// ===================== SECTION 9: GO-TO-MARKET =====================
function section9() {
  return [
    new H.docx.Paragraph({ pageBreakBefore: true, heading: H.docx.HeadingLevel.HEADING_1, children: [H.t("9. Go-To-Market Strategy")] }),
    lead("First 100 clients = niche focus + relentless outbound + undeniable demos + visible proof. Pick one vertical, dominate it with a productised offer, let case studies and referrals compound."),

    h2("9.1 The First-100-Clients Engine"),
    p("Do not be a generalist. Choose one or two verticals (e.g., Gujarat manufacturing/exports + e-commerce/real-estate SMEs), build a productised offer with a killer demo, and run a multi-channel outbound machine. The sequence that works for a new B2B AI services firm:"),
    table([1650, 7710], [
      ["Channel", "Exact execution"],
      ["LinkedIn", "Optimise founder profile as 'AI for [niche]'. Post 4–5×/week (case studies, before/after automations, demos). DM 20–30 targeted prospects/day with a value-first hook + Loom demo. Build to inbound."],
      ["Cold email", "Build niche lists (Apollo/Clay). 50–100 personalised emails/day, 3–4 step sequence, lead with a specific pain + a 60-sec demo video + soft CTA (audit). A/B test relentlessly."],
      ["WhatsApp (India)", "For SME/local: short personalised messages + voice notes + a working demo link. Highest reply rate in India; follow up by call."],
      ["Outbound calls / in-person", "For mfg/export owners: phone + factory/office visits with a live demo on their use case. Relationship + ROI math closes."],
      ["AI demos", "Pre-build vertical demo bots/automations (clinic bot, dealership bot, exporter doc-bot). 'Show, don't tell' — the demo is the pitch."],
      ["SEO + content", "Rank for '[service] for [industry] in [city]'. Publish use-cases, ROI calculators, comparison guides. Compounds over 6–12 months."],
      ["Case studies", "Turn every early win into a 1-page result story (metrics + quote + before/after). Your #1 sales asset."],
      ["Referrals", "Ask every happy client for 2 intros; add a referral fee. Warm intros convert 3–5× cold."],
      ["Partnerships", "Co-sell with hyperscalers (AWS/Azure/Google), UiPath/ServiceNow partners, web/marketing agencies, CAs/consultants, industry associations and export councils."],
    ], { fontSize: 15 }),

    h2("9.2 90-Day Outbound Cadence (illustrative weekly targets)"),
    table([3100, 2086, 2087, 2087], [
      ["Activity", "Per week", "Reply target", "Meetings target"],
      ["LinkedIn DMs", "120–150", "8–15%", "5–8"],
      ["Cold emails", "300–500", "3–6%", "4–8"],
      ["WhatsApp (India SME)", "100–150", "15–25%", "6–10"],
      ["Calls / visits", "20–40", "—", "4–8"],
      ["Content posts", "5–7", "Inbound", "1–3 (compounding)"],
    ], { fontSize: 16 }),
    p("At these volumes a disciplined founder-led motion realistically books 15–25 qualified meetings/week within 60–90 days, converting to 4–10 new clients/month as positioning and case studies sharpen."),

    h2("9.3 The Offer That Converts"),
    callout("Productised, low-risk first offer", [
      "Niche + outcome: 'We build a 24/7 AI sales agent for [real-estate / dealerships / exporters] that captures and follows up every lead — or you don't pay month 2.'",
      "Free value first: a 15-min audit or a working demo bot trained on their content.",
      "Small paid pilot (₹25–75k / $1–3k) → prove ROI → convert to monthly retainer.",
      "Risk reversal: month-1 guarantee or pilot pricing removes the 'will it work' objection.",
    ]),

    h2("9.4 Content & Brand Engine"),
    bullet("Founder thought leadership on LinkedIn (the #1 channel for B2B AI services in 2025)."),
    bullet("Vertical case-study library + short demo videos (YouTube/Reels/Shorts) for proof + SEO."),
    bullet("Lead magnets: ROI calculators, 'AI readiness' audits, industry automation playbooks."),
    bullet("Email newsletter nurturing prospects with use-cases until they're ready to buy."),
    source("GTM playbook synthesised from B2B SaaS/agency growth benchmarks and AI-services practitioner data (2024–2026). Conversion ranges are illustrative. Full citations in References."),
  ];
}

// ===================== SECTION 10: SWOT =====================
function section10() {
  const cell = (title, items, fill, color) => new H.docx.TableCell({
    width: { size: 4680, type: H.docx.WidthType.DXA },
    borders: { top: { style: H.docx.BorderStyle.SINGLE, size: 4, color }, bottom: { style: H.docx.BorderStyle.SINGLE, size: 4, color }, left: { style: H.docx.BorderStyle.SINGLE, size: 4, color }, right: { style: H.docx.BorderStyle.SINGLE, size: 4, color } },
    shading: { fill, type: H.docx.ShadingType.CLEAR },
    margins: { top: 120, bottom: 120, left: 140, right: 140 },
    children: [
      new H.docx.Paragraph({ spacing: { after: 80 }, children: [H.t(title, { bold: true, size: 22, color })] }),
      ...items.map((it) => new H.docx.Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 40 }, children: [H.t(it, { size: 16 })] })),
    ],
  });
  const swot = new H.docx.Table({
    width: { size: H.CONTENT_W, type: H.docx.WidthType.DXA },
    columnWidths: [4680, 4680],
    rows: [
      new H.docx.TableRow({ children: [
        cell("STRENGTHS", [
          "AI-native, lean delivery → lower cost, faster than incumbents",
          "No legacy/headcount baggage; can price aggressively",
          "Founder domain + local (Gujarat/India) market access",
          "Productised, vertical focus vs generalist competitors",
          "Geographic arbitrage: India cost, global pricing",
        ], "E2EFDA", H.GREEN),
        cell("WEAKNESSES", [
          "No brand, track record or case studies yet",
          "Limited capital and small initial team",
          "Trust gap vs established firms for big deals",
          "Founder-dependent sales early on",
          "Talent acquisition/retention in hot AI market",
        ], "FBE4D5", H.AMBER),
      ] }),
      new H.docx.TableRow({ children: [
        cell("OPPORTUNITIES", [
          "Huge under-served SME/mid-market + Gujarat verticals",
          "GenAI/agentic wave — early-mover positioning",
          "Pilot-rescue & AI governance demand rising",
          "Export delivery to high-value US/UK/Gulf markets",
          "Partnerships (hyperscalers, platforms, agencies)",
        ], "DEEBF7", H.BLUE),
        cell("THREATS", [
          "Commoditisation (low-code + foundation models)",
          "Tier-1/2 firms moving down-market",
          "Price competition from app/dev shops",
          "Fast tech change; model/platform disruption",
          "Regulatory shifts (DPDP, EU AI Act); buyer skepticism",
        ], "F2DCDB", H.RED),
      ] }),
    ],
  });
  return [
    new H.docx.Paragraph({ pageBreakBefore: true, heading: H.docx.HeadingLevel.HEADING_1, children: [H.t("10. SWOT Analysis")] }),
    lead("The strategic balance: a nimble, AI-native challenger with strong local access and cost advantage, but no track record yet — racing to build proof before commoditisation and incumbents close the window."),
    swot,
    spacer(120),
    h2("10.1 Strategic Implications (SWOT → Action)"),
    bullet([H.t("Strengths × Opportunities: ", { bold: true }), H.t("Use AI-native speed + local access to dominate one Gujarat/India vertical fast, then export delivery globally.")]),
    bullet([H.t("Weaknesses × Opportunities: ", { bold: true }), H.t("Close the trust gap with free demos, paid pilots, risk reversal and rapid case-study production.")]),
    bullet([H.t("Strengths × Threats: ", { bold: true }), H.t("Out-run commoditisation by building vertical IP and outcome-based offers competitors can't easily copy.")]),
    bullet([H.t("Weaknesses × Threats: ", { bold: true }), H.t("Avoid enterprise RFPs early; stay capital-light, recurring-revenue-focused, and partnership-leveraged.")]),
    source("SWOT synthesised from the competitive, market and demand analysis in Sections 1–9. Full citations in References."),
  ];
}

module.exports = { section6, section7, section8, section9, section10 };
