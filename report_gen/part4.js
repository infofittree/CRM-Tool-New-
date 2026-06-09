const H = require("./helpers");
const { h1, h2, h3, p, lead, bullet, num, kpi, spacer, pageBreak, source, figcap, table, hbar, callout } = H;

// ===================== SECTION 11: RISKS =====================
function section11() {
  return [
    new H.docx.Paragraph({ pageBreakBefore: true, heading: H.docx.HeadingLevel.HEADING_1, children: [H.t("11. Risks & Challenges")] }),
    lead("The business is viable, but four risks can sink it: commoditisation, delivery quality, cash-flow lumpiness and regulation. Each is manageable with deliberate strategy — listed below with mitigations."),

    h2("11.1 Risk Register"),
    table([2300, 1300, 1300, 4460], [
      ["Risk", "Likelihood", "Impact", "Mitigation"],
      ["Commoditisation of basic builds", "High", "High", "Move up to vertical IP, outcomes, managed services; avoid competing on commodity dev price"],
      ["Delivery quality / failed projects", "Med", "High", "Scope tightly, productise, set KPIs, pilot-first, strong PM and QA"],
      ["Cash-flow lumpiness (project reliance)", "High", "Med", "Build recurring retainers fast; keep burn low; milestone billing"],
      ["Talent scarcity / attrition", "Med", "Med", "AI-leverage small team; train juniors; partner/contractor bench; equity for key hires"],
      ["Tech disruption (model/platform shift)", "Med", "Med", "Stay model-agnostic; abstract vendors; continuous learning"],
      ["Incumbents move down-market", "Med", "Med", "Out-niche and out-speed them; own SME relationships they can't service profitably"],
      ["Client over-dependence", "Med", "High", "Diversify client base; no single client >20–25% of revenue"],
      ["Data security / breach", "Low-Med", "High", "Security-by-design, NDAs, least-privilege, audits, cyber-insurance"],
      ["Regulatory (DPDP, EU AI Act, sectoral)", "Med", "Med-High", "Build governance into delivery; legal review; data-residency options"],
      ["AI hallucination / liability", "Med", "Med", "Human-in-loop, guardrails, disclaimers, scoped contracts, evals"],
    ], { fontSize: 15 }),

    h2("11.2 Market & Competitive Threats"),
    bullet("Race-to-the-bottom pricing from app/dev shops adding 'AI' as a buzzword — defend with outcomes + proof."),
    bullet("Platform players (OpenAI, hyperscalers, ServiceNow) absorbing functionality you sell — ride them as partners, not rivals."),
    bullet("Buyer fatigue/skepticism after over-hyped pilots — lead with ROI guarantees and references."),

    h2("11.3 Legal, Regulatory & Ethical"),
    bullet([H.t("India DPDP Act 2023: ", { bold: true }), H.t("data-processing consent, security obligations — bake into every build.")]),
    bullet([H.t("EU AI Act / global AI rules: ", { bold: true }), H.t("risk-tiering, transparency, documentation for EU clients.")]),
    bullet([H.t("IP & contracts: ", { bold: true }), H.t("clear ownership of code/models/data; reusable-IP clauses to protect your assets.")]),
    bullet([H.t("Sectoral compliance: ", { bold: true }), H.t("BFSI (RBI), healthcare (data sensitivity), depending on verticals served.")]),
    source("Risk framework synthesised from AI-services delivery practice, India DPDP Act 2023, EU AI Act, and analyst risk commentary (2024–2026). Full citations in References."),
  ];
}

// ===================== SECTION 12: SERVICES TO START FIRST =====================
function section12() {
  return [
    new H.docx.Paragraph({ pageBreakBefore: true, heading: H.docx.HeadingLevel.HEADING_1, children: [H.t("12. Recommended Services to Start First")] }),
    lead("Lead with services that are fast to sell, fast to deliver, recurring, and deliverable by a lean AI-native team. The Top-10 below are ranked on a blend of demand, ease-of-sale, recurring revenue and delivery feasibility."),

    h2("12.1 Top 10 Launch Services (Ranked)"),
    table([620, 2700, 3340, 2700], [
      ["#", "Service", "Why start here", "Model"],
      ["1", "AI Chatbots / WhatsApp + RAG support bots", "Huge demand, short build, killer demo, instant ROI story", "Setup + monthly retainer"],
      ["2", "Lead-gen & Sales Automation", "Every business wants growth; performance-linked; recurring", "Setup + monthly retainer"],
      ["3", "Workflow / Business-Process Automation", "High pain, clear ROI, sticky 'build + run'", "Build + managed retainer"],
      ["4", "AI Marketing & Content Automation", "Low risk, recurring, easy upsell, fast delivery", "Monthly retainer"],
      ["5", "Analytics & BI Dashboards", "Visible value; gateway to bigger transformation work", "Project + support sub."],
      ["6", "AI Voice Agents (booking/support)", "Fast-rising; high-impact for clinics, real estate, retail", "Build + usage/retainer"],
      ["7", "CRM/ERP Setup + AI Automation", "Mid-market staple; large + sticky; cross-sell hub", "Project + AMC"],
      ["8", "AI Agents (vertical, productised)", "Highest growth category; defensible IP", "Build + usage"],
      ["9", "Website / Web-App + AI features", "Easy entry door, cash flow, leads to deeper work", "Project (+ care plan)"],
      ["10", "Digital-Transformation / AI-readiness Advisory", "High-trust entry; pulls through all of the above", "Advisory retainer"],
    ], { fontSize: 15 }),

    h2("12.2 Why This Ranking"),
    bullet("#1–4 are the cash engine: short cycles, recurring revenue, deliverable by 2–3 people, demo-able instantly."),
    bullet("#5–7 raise deal size and stickiness once you have proof and a small team."),
    bullet("#8 (vertical AI agents) is where you build durable IP and the highest margins as you mature."),
    bullet("#9–10 are door-openers — low-friction entry that pulls through higher-value work."),

    h2("12.3 Sequencing"),
    callout("Launch sequence", [
      "Months 0–3: Master #1, #2, #4 (chatbots, lead-gen, marketing automation). Build demos + first case studies.",
      "Months 3–6: Add #3, #5 (workflow automation, dashboards). Convert clients to retainers.",
      "Months 6–12: Add #6, #7, #8 (voice agents, CRM/ERP, vertical agents). Begin productising into subscriptions.",
      "Always pair every project with a recurring component.",
    ]),
  ];
}

// ===================== SECTION 13: BLUE OCEAN =====================
function section13() {
  return [
    new H.docx.Paragraph({ pageBreakBefore: true, heading: H.docx.HeadingLevel.HEADING_1, children: [H.t("13. Blue Ocean Opportunities")] }),
    lead("Where competition is thin and pain is high. The biggest white space is everything the giants ignore: small deals, vernacular markets, specific verticals, and the unglamorous 'make AI actually work in production' problem."),

    h2("13.1 Under-Served Markets"),
    table([2700, 6660], [
      ["Blue-ocean space", "Why it's open + how to win"],
      ["SME/MSME productised AI", "63 M Indian MSMEs, low AI adoption, ignored by majors. Win with cheap, packaged, subscription AI [14]."],
      ["Vernacular / regional-language AI", "Tier-2/3 businesses + their customers need Hindi/Gujarati/regional bots & voice. Almost no productised players."],
      ["Gujarat industrial verticals", "Textile, chemicals, pharma, ceramics, gems, agro/food, exports — specific, high-pain, low-competition for tailored AI."],
      ["Export documentation & compliance", "Massive in Gujarat/Surat/Mumbai; document + multilingual comms automation is barely productised."],
      ["AI pilot-rescue & governance", "Thousands of stalled GenAI pilots; a 'make it work + govern it' offer has little direct competition."],
      ["Vertical voice agents", "Clinics, dealerships, real estate, restaurants — per-location subscription voice AI; fragmented, under-served."],
      ["AI for traditional family businesses", "Owner-led firms with zero digital maturity; huge TAM, needs trust + handholding the majors won't give."],
    ], { fontSize: 16 }),

    h2("13.2 Hidden Opportunities"),
    bullet("'AI Ops as a Service' — ongoing monitoring/retraining/improvement of deployed AI (recurring, defensible)."),
    bullet("Micro-SaaS spun out of repeated client solutions (e.g., a dealership lead-bot product)."),
    bullet("Industry-association / cluster deals — sell one productised solution to many members of a GIDC cluster or export council."),
    bullet("White-label AI for agencies — power web/marketing agencies' 'AI offerings' as their backend."),
    bullet("AI-readiness audits as a paid wedge — low-cost entry that maps every future project."),

    h2("13.3 Blue-Ocean Strategy Summary"),
    callout("The unguarded edge", [
      "Don't fight giants for enterprise top-down. Own the SME/vertical bottom-up market they can't serve profitably.",
      "Be the specialist for a specific industry + region + outcome — not a generalist 'AI company'.",
      "Productise + subscribe: turn services into repeatable products with recurring revenue.",
      "Use vernacular + local trust + AI-native cost as moats competitors can't quickly copy.",
    ]),
  ];
}

// ===================== SECTION 14: ROADMAP =====================
function section14() {
  return [
    new H.docx.Paragraph({ pageBreakBefore: true, heading: H.docx.HeadingLevel.HEADING_1, children: [H.t("14. 12-Month Implementation Roadmap")] }),
    lead("A focused, capital-light 12-month plan: validate → land first clients → build recurring revenue → productise → scale delivery and geography. Targets are illustrative for a lean founder-led launch."),

    h2("14.1 Month-by-Month Plan"),
    table([1150, 3400, 2400, 2410], [
      ["Month", "Focus & key actions", "Goal / KPI", "Build/Hire"],
      ["1", "Pick niche(s) + 5 core services; brand, site, demos; define offers/pricing", "Positioning + 3 demo assets live", "Founder + 1 eng/PM"],
      ["2", "Launch outbound (LinkedIn, email, WhatsApp); build lead lists; first calls", "30+ meetings booked", "+1 SDR/intern"],
      ["3", "Close first 3–5 paid pilots; deliver fast; capture results", "₹3–8L / $5–15k revenue; 3 case studies", "+1 eng (contract)"],
      ["4", "Convert pilots to retainers; refine offers; double outbound", "First recurring MRR; 6–8 clients", "—"],
      ["5", "Add workflow automation + dashboards; publish case studies/content", "MRR growing; inbound starts", "+1 delivery"],
      ["6", "First Gulf/export client; partnerships (hyperscaler/agency)", "10–15 clients; 1 export logo", "+1 sales"],
      ["7", "Productise top 2 services into packages/subscriptions", "2 productised offers; higher close rate", "—"],
      ["8", "Add voice agents + CRM/ERP; raise deal sizes", "Avg deal size up 30–50%", "+1–2 eng"],
      ["9", "Systematise delivery (SOPs, QA, MLOps); reduce founder load", "Delivery runs without founder", "Delivery lead"],
      ["10", "Scale outbound + content; expand US/UK pipeline", "20–30 clients; pipeline 3× capacity", "+1–2 sales/SDR"],
      ["11", "Launch first micro-SaaS / IP from repeated solution", "MVP live; first subscribers", "Product eng"],
      ["12", "Review, optimise unit economics; plan Year-2 scale & funding", "Stable MRR, 55%+ margins, Year-2 plan", "Team 10–15"],
    ], { fontSize: 14 }),

    h2("14.2 Quarterly Milestones"),
    table([1500, 3000, 4860], [
      ["Quarter", "Theme", "Target outcome"],
      ["Q1 (M1–3)", "Validate & Land", "5–8 paying clients, 3 case studies, first revenue"],
      ["Q2 (M4–6)", "Recurring & Export", "Retainer base, 10–15 clients, first export logo"],
      ["Q3 (M7–9)", "Productise & Systematise", "Packaged offers, bigger deals, founder-independent delivery"],
      ["Q4 (M10–12)", "Scale & IP", "20–30 clients, micro-SaaS MVP, Year-2 scale plan"],
    ], { fontSize: 16 }),

    h2("14.3 Illustrative Revenue Trajectory"),
    hbar([
      { label: "Q1", value: 8, display: "₹6–12L / $10–20k" },
      { label: "Q2", value: 22, display: "₹18–30L / $30–55k" },
      { label: "Q3", value: 45, display: "₹40–60L / $70–120k" },
      { label: "Q4", value: 80, display: "₹75L–1.2Cr / $130–230k" },
    ], { maxVal: 80, color: H.GREEN }),
    figcap("Figure 11. Illustrative cumulative revenue trajectory (lean founder-led launch; actuals depend on execution)."),
  ];
}

// ===================== SECTION 15: EXECUTIVE SUMMARY (final recommendation) =====================
function section15() {
  return [
    new H.docx.Paragraph({ pageBreakBefore: true, heading: H.docx.HeadingLevel.HEADING_1, children: [H.t("15. Actionable Executive Summary & Final Recommendation")] }),
    lead("The verdict: yes — launch it, but not as a generalist. Win a niche at home, build recurring revenue, then export. Below is the decisive, do-this-now recommendation."),

    h2("15.1 Should You Start This Business?"),
    p("Yes. The markets are large, fast-growing and structurally favourable to an AI-native challenger. Demand outstrips supply in the SME/mid-market and vertical segments. The risk is not market size — it is focus. The single biggest failure mode is trying to offer all 30 services to everyone. Win by going narrow first."),
    callout("The one-line strategy", [
      "Become the #1 AI & automation partner for a specific industry + region (start: Gujarat manufacturing / exports + SME services), with productised, outcome-based offers — then export delivery to the Gulf and US/UK.",
    ]),

    h2("15.2 Decisive Answers"),
    table([2500, 6860], [
      ["Question", "Recommendation"],
      ["Which niche first?", "Gujarat/India SME + mfg/export verticals (your access + acute pain + low competition). Add e-commerce/real-estate SMEs."],
      ["Which services first?", "AI chatbots/WhatsApp bots, lead-gen & sales automation, workflow automation, AI marketing — then dashboards & voice agents."],
      ["Which country first?", "India (home) for proof + cash flow → UAE/Gulf for big margins → US/UK for scale."],
      ["How to get clients fast?", "Niche productised offer + free demo/audit + small paid pilot + risk reversal, pushed via LinkedIn + email + WhatsApp + referrals."],
      ["Business model?", "Hybrid land-and-expand: project → retainer → subscription → SaaS IP. Target 55–75% margins, growing recurring base."],
      ["Biggest risk to manage?", "Commoditisation + cash lumpiness — beat both with vertical IP, outcomes, and fast recurring revenue."],
    ], { fontSize: 16 }),

    h2("15.3 Revenue Roadmap (Year 1, illustrative)"),
    bullet("Q1: first 5–8 clients, ₹6–12L / $10–20k, 3 case studies."),
    bullet("Q2: retainer base + export logo, 10–15 clients."),
    bullet("Q3: productised offers, bigger deals, founder-independent delivery."),
    bullet("Q4: 20–30 clients, micro-SaaS MVP, stable MRR at 55%+ margins; Year-2 scale/funding plan."),

    h2("15.4 Hiring Roadmap"),
    table([1700, 3000, 4660], [
      ["Stage", "Hire", "Why"],
      ["Founding (M1–3)", "Founder(s) + 1 AI engineer/PM + 1 SDR/intern", "Sell + deliver lean; prove model"],
      ["Traction (M4–9)", "+1–2 engineers, +1 sales, +1 delivery/PM", "Scale delivery + pipeline"],
      ["Scale (M10–12)", "Delivery lead, product engineer, +sales/SDR", "Founder-independent delivery + IP + growth"],
    ], { fontSize: 16 }),

    h2("15.5 Recommended Technology Stack"),
    table([2300, 7060], [
      ["Layer", "Recommended tools"],
      ["Foundation models", "OpenAI (GPT), Anthropic Claude, Google Gemini; open models (Llama, Mistral) for private/on-prem"],
      ["Orchestration / agents", "LangChain / LlamaIndex / LangGraph, n8n / Make for workflow automation"],
      ["RAG / vector DB", "Pinecone / Weaviate / pgvector; embeddings via OpenAI/Cohere"],
      ["Automation / RPA", "n8n, Make, Zapier (SME); UiPath / Automation Anywhere / Power Automate (enterprise)"],
      ["Conversational / voice", "WhatsApp Business API (AiSensy/Wati/Gupshup), Twilio, Vapi/ElevenLabs for voice"],
      ["Data / BI", "BigQuery / Snowflake / Postgres; Power BI / Metabase / Looker Studio"],
      ["Cloud / MLOps", "AWS / Azure / GCP; Docker, GitHub Actions, MLflow/LangSmith for monitoring"],
      ["Build / SaaS", "Next.js / React, Node/Python (FastAPI), Supabase/Postgres"],
      ["GTM stack", "Apollo/Clay (lists), LinkedIn, instantly/smartlead (email), CRM (HubSpot/Zoho), Loom (demos)"],
    ], { fontSize: 15 }),

    h2("15.6 Final Word"),
    callout("Do this now", [
      "1. Pick ONE niche + 4 core services this week.",
      "2. Build 3 killer demos and a productised, risk-reversed offer.",
      "3. Start 100+ outbound touches/week across LinkedIn, email and WhatsApp.",
      "4. Land 5 paid pilots in 90 days; convert to retainers; publish case studies.",
      "5. Reinvest into productisation, recurring revenue, and export delivery.",
      "Speed of proof beats breadth of services. Go narrow, get proof, then scale.",
    ], "E2EFDA"),
  ];
}

// ===================== REFERENCES =====================
function references() {
  const refs = [
    "Precedence Research — Artificial Intelligence Market (USD 757.58 B in 2025 → USD 4,216.29 B by 2035, 18.73% CAGR). precedenceresearch.com/artificial-intelligence-market",
    "NextMSC — AI Market 2025–2030 (USD 224.41 B in 2024 → USD 1,236.47 B by 2030, 32.9% CAGR); market.us — AI Market (38.5% CAGR). nextmsc.com; market.us/report/artificial-intelligence-market",
    "Grand View Research — Artificial Intelligence as a Service Market (USD 16.08 B 2024 → USD 105.04 B 2030, 36.1% CAGR). grandviewresearch.com/industry-analysis/artificial-intelligence-as-a-service-market-report",
    "Grand View Research / GM Insights / Fortune Business Insights — Generative AI Market (USD 22–104 B 2025 → USD 325–990 B, 29–43% CAGR). grandviewresearch.com/industry-analysis/generative-ai-market-report",
    "Precedence Research — IT Services Market (USD 1.61 T 2025 → USD 3.17 T 2035, ~7% CAGR); Grand View Research IT Services report. precedenceresearch.com/it-services-market",
    "Gartner — Worldwide IT Spending Forecasts (USD 5.43 T 2025; >USD 6 T 2026). gartner.com/en/newsroom (2025–2026 press releases)",
    "Future Market Insights — AI Consulting Services Market (USD 11.07 B 2025 → USD 90.99 B 2035, 26.2% CAGR). futuremarketinsights.com/reports/ai-consulting-services-market",
    "Business Research Insights — AI Consulting Market (26.49% CAGR; alt. USD 22.27 B 2025 → USD 257.6 B 2033, 35.8% CAGR). businessresearchinsights.com",
    "Precedence Research / SkyQuest / Technavio / Mordor — RPA & Hyperautomation Markets (RPA USD 11–28 B 2025, 24–36% CAGR; Hyperautomation USD 16–66 B, 17–20% CAGR). precedenceresearch.com/hyperautomation-market",
    "Grand View Research — Digital Transformation Market (→ USD 4,617.78 B by 2030, 28.5% CAGR). grandviewresearch.com/industry-analysis/digital-transformation-market",
    "The Business Research Company — Digital Transformation Global Market (→ USD 5,010.76 B 2030, 18.5% CAGR). thebusinessresearchcompany.com",
    "Grand View Research / Precedence / Technavio — SaaS Market (USD 399–408 B 2024–25 → USD 774 B–1.37 T, 12–22% CAGR). grandviewresearch.com/industry-analysis/saas-market-report",
    "NASSCOM-BCG & indiaai.gov.in — India AI market → ~USD 17 B by 2027 (25–35% CAGR); NASSCOM Strategic Review 2025 (India tech industry ~USD 282.6 B FY2025, approaching USD 300 B FY2026). nasscom.in",
    "World Economic Forum — Transforming Small Businesses: An AI Playbook for India's SMEs (2025) (India ~63 M MSMEs, low AI adoption). reports.weforum.org",
    "TiE Indore MP / RPRealtyPlus — India Tier-2 tech surge (40% of tech startups from tier-2/3; 30–40% lower costs). mp.tie.org; rprealtyplus.com",
    "Accenture — FY2025 results 8-K (USD 69.7 B revenue, ~799k staff, USD 5.9 B GenAI bookings); Wipro 6-K FY2025. sec.gov (EDGAR)",
    "Fractal Analytics — GetLatka (USD 330 M ARR, USD 2.4 B valuation); Crunchbase; Inc42; Tradebrains; TechFundingNews (DRHP, IPO). getlatka.com/companies/fractal.ai; crunchbase.com",
    "UiPath FY2025 8-K (USD 1.43 B revenue, USD 1.67 B ARR); Palantir FY2025 8-K (USD 3.7 B+ revenue, profitable). sec.gov (EDGAR)",
    "Growjo — Quantiphi revenue & competitors; Crunchbase (Quantiphi funding). growjo.com/company/Quantiphi",
    "Forrester — The AI Effect: Q2 2025 Technology Services Earnings (Accenture, Capgemini, Cognizant, HCLTech, IBM, Infosys, TCS, Tech Mahindra, Wipro). forrester.com/blogs",
    "Company financial disclosures & investor relations: TCS, Infosys, HCLTech, Deloitte, PwC, IBM, Capgemini, Cognizant, ServiceNow, Automation Anywhere, DataRobot (FY2024–25).",
    "Company websites, Crunchbase, Tracxn, Inc42, YourStory for Indian competitor directory (Section 3). Private financials are estimates.",
  ];
  const rows = [["#", "Source"]];
  refs.forEach((r, i) => rows.push([{ text: String(i + 1), align: H.docx.AlignmentType.CENTER }, r]));
  return [
    new H.docx.Paragraph({ pageBreakBefore: true, heading: H.docx.HeadingLevel.HEADING_1, children: [H.t("References & Sources")] }),
    p("Market figures are drawn from leading research houses and are presented as ranges where analyst estimates diverge. Private-company financials are best-available estimates and flagged as such throughout. All sources accessed 2025–2026."),
    table([700, 8660], rows, { fontSize: 15 }),
    spacer(160),
    h2("Methodology & Disclaimer"),
    p("This report synthesises secondary research from public market-research publications, analyst forecasts, company filings and industry bodies, combined with practitioner benchmarking for pricing, demand scoring and go-to-market guidance. Market-size ranges reflect genuine divergence in analyst scope and methodology; mid-points are used for planning, not as precise predictions. Pricing, revenue trajectories, scores and timelines are illustrative planning aids, not guarantees. Figures should be independently verified before being used in investment, financing or contractual decisions. This document is strategic guidance, not financial, legal or investment advice."),
  ];
}

module.exports = { section11, section12, section13, section14, section15, references };
