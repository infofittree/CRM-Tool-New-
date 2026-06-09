const fs = require("fs");
const path = require("path");
const H = require("./helpers");
const {
  docx, NAVY, BLUE, LIGHTBLUE, GREY, CONTENT_W,
  t, h1, h2, p, lead, bullet, num, kpi, spacer, table, hbar, callout, figcap,
} = H;
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, LevelFormat,
  Header, Footer, PageNumber, TableOfContents, BorderStyle, PageOrientation,
} = docx;

const P1 = require("./part1");
const P2 = require("./part2");
const P3 = require("./part3");
const P4 = require("./part4");

// ---------- Title page ----------
function titlePage() {
  const rule = (color, size = 12) => new Paragraph({
    border: { bottom: { style: BorderStyle.SINGLE, size, color, space: 1 } },
    spacing: { after: 200 }, children: [t("")],
  });
  return [
    new Paragraph({ spacing: { before: 1400, after: 0 }, alignment: AlignmentType.CENTER,
      children: [t("MARKET RESEARCH & GO-TO-MARKET STRATEGY", { size: 26, bold: true, color: BLUE, allCaps: true })] }),
    spacer(120),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 },
      children: [t("AI & IT Solutions as a Service", { size: 56, bold: true, color: NAVY })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 },
      children: [t("Launching a New Division for AI-Powered Business Transformation", { size: 26, italics: true, color: GREY })] }),
    rule(BLUE, 18),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 },
      children: [t("A McKinsey-/BCG-Style Strategic Assessment", { size: 24, color: NAVY, bold: true })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 },
      children: [t("Global Market · Special Focus: India & Gujarat", { size: 22, color: GREY })] }),
    spacer(400),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 },
      children: [t("15 Sections · Market Sizing · Competitor Matrix · Industry & Country Analysis · GTM · Roadmap", { size: 18, color: GREY, italics: true })] }),
    spacer(600),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 40 },
      children: [t("Prepared: June 2026", { size: 20, color: NAVY, bold: true })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 40 },
      children: [t("Strategy & Market Research Report", { size: 18, color: GREY })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 400 },
      children: [t("CONFIDENTIAL — Internal Strategic Planning Document", { size: 16, color: GREY, italics: true })] }),
  ];
}

// ---------- TOC ----------
function tocSection() {
  return [
    new Paragraph({ heading: HeadingLevel.HEADING_1, children: [t("Table of Contents")] }),
    new TableOfContents("Table of Contents", { hyperlink: true, headingStyleRange: "1-2" }),
  ];
}

// ---------- Executive summary ----------
function executiveSummary() {
  return [
    new Paragraph({ pageBreakBefore: true, heading: HeadingLevel.HEADING_1, children: [t("Executive Summary")] }),
    lead("A new AI & IT Solutions division is a strong bet — if it is launched as a focused, productised, AI-native challenger rather than a generalist trying to sell 30 services to everyone."),

    p("This report assesses the opportunity to launch an “AI & IT Solutions as a Service” division across six overlapping markets — AI, IT services, AI consulting, automation, digital transformation and SaaS — that together represent over USD 8 trillion in annual technology spend and are compounding at double-digit rates through 2035. The headline conclusion: the market opportunity is large and structurally favourable, but success depends entirely on focus, productisation and speed of proof."),

    h2("Key Findings"),
    kpi("Total addressable technology spend across the six target markets", "$8 T+"),
    kpi("AI-as-a-Service CAGR to 2030 (the steepest-growing pool)", "36%"),
    kpi("India tech-industry revenue (FY2025), approaching $300 B in FY2026", "$282 B"),
    kpi("India AI market by 2027 (NASSCOM-BCG)", "$17 B"),
    kpi("Indian MSMEs — large, under-served, low AI adoption", "63 M"),
    spacer(80),

    h2("The Strategic Thesis"),
    bullet([t("Don't fight giants top-down. ", { bold: true }), t("Accenture, TCS, Deloitte and peers own the enterprise but ignore the SME/mid-market and specific verticals — the largest unguarded opportunity.")]),
    bullet([t("Go narrow, then scale. ", { bold: true }), t("Win one industry + region (start: Gujarat manufacturing/exports + SME services), with productised, outcome-based offers.")]),
    bullet([t("Recurring over one-off. ", { bold: true }), t("Use low-risk projects to fund a growing base of retainers and subscriptions — target 55–75% margins.")]),
    bullet([t("Win at home, sell to the world. ", { bold: true }), t("Build proof and cash flow in India; export high-margin remote delivery to the UAE/Gulf and US/UK at 5–20× deal sizes.")]),
    bullet([t("Lead with quick wins. ", { bold: true }), t("AI chatbots/WhatsApp bots, lead-gen & sales automation, workflow automation and AI marketing — fast to sell, fast to deliver, recurring.")]),

    callout("Bottom line", [
      "Yes, launch it. Become the #1 AI & automation partner for a focused industry + region, with productised, risk-reversed, outcome-based offers — then expand services, geographies and IP.",
      "First niche: Gujarat/India SME + manufacturing/export verticals. First services: chatbots, lead-gen, workflow & marketing automation. First market: India → Gulf → US/UK.",
      "Land 5 paid pilots in 90 days, convert to retainers, publish case studies, and reinvest into recurring revenue and IP. Speed of proof beats breadth of services.",
    ]),
    p("The remainder of this report provides the detailed market sizing, competitor matrix, industry and country analysis, customer personas, business-model and pricing strategy, go-to-market execution plan, SWOT, risk register, blue-ocean opportunities and a month-by-month 12-month roadmap that support this recommendation.", { }),
  ];
}

// ---------- Assemble ----------
const children = [
  ...titlePage(),
  new Paragraph({ children: [new docx.PageBreak()] }),
  ...tocSection(),
  ...executiveSummary(),
  ...P1.section1(),
  ...P1.section2(),
  ...P1.section3(),
  ...P2.section4(),
  ...P2.section5(),
  ...P3.section6(),
  ...P3.section7(),
  ...P3.section8(),
  ...P3.section9(),
  ...P3.section10(),
  ...P4.section11(),
  ...P4.section12(),
  ...P4.section13(),
  ...P4.section14(),
  ...P4.section15(),
  ...P4.references(),
];

const doc = new Document({
  creator: "Strategy & Market Research",
  title: "AI & IT Solutions as a Service — Market Research & GTM Strategy",
  description: "Market research report",
  styles: {
    default: { document: { run: { font: "Arial", size: 21, color: "222222" } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: "Arial", color: NAVY },
        paragraph: { spacing: { before: 280, after: 160 }, outlineLevel: 0,
          border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: BLUE, space: 4 } } } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 25, bold: true, font: "Arial", color: BLUE },
        paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 22, bold: true, font: "Arial", color: "1F3864" },
        paragraph: { spacing: { before: 140, after: 60 }, outlineLevel: 2 } },
    ],
  },
  numbering: {
    config: [
      { reference: "bullets", levels: [
        { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 460, hanging: 260 } } } },
        { level: 1, format: LevelFormat.BULLET, text: "–", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 920, hanging: 260 } } } },
      ] },
      { reference: "numbers", levels: [
        { level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 460, hanging: 260 } } } },
      ] },
    ],
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
      },
    },
    headers: {
      default: new Header({ children: [new Paragraph({
        border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: "B8C4D9", space: 2 } },
        tabStops: [{ type: docx.TabStopType.RIGHT, position: 9360 }],
        children: [
          t("AI & IT Solutions as a Service", { size: 16, color: GREY }),
          t("\tMarket Research & GTM Strategy", { size: 16, color: GREY, italics: true }),
        ],
      })] }),
    },
    footers: {
      default: new Footer({ children: [new Paragraph({
        border: { top: { style: BorderStyle.SINGLE, size: 4, color: "B8C4D9", space: 2 } },
        tabStops: [{ type: docx.TabStopType.CENTER, position: 4680 }, { type: docx.TabStopType.RIGHT, position: 9360 }],
        children: [
          t("Confidential", { size: 15, color: GREY }),
          new TextRun({ children: ["\tPage ", PageNumber.CURRENT], size: 15, color: GREY }),
          t("\tJune 2026", { size: 15, color: GREY }),
        ],
      })] }),
    },
    children,
  }],
});

const out = path.join(__dirname, "..", "AI_IT_Solutions_Market_Research_Report.docx");
Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(out, buf);
  console.log("WROTE " + out + " (" + (buf.length / 1024).toFixed(0) + " KB)");
}).catch((e) => { console.error(e); process.exit(1); });
