// Shared helpers for the market research report
const docx = require("docx");
const {
  Paragraph, TextRun, Table, TableRow, TableCell, AlignmentType,
  WidthType, BorderStyle, ShadingType, VerticalAlign, HeadingLevel,
} = docx;

// ---- Palette ----
const NAVY = "1F3864";
const BLUE = "2E75B6";
const LIGHTBLUE = "D9E2F3";
const HEADFILL = "1F3864";
const ZEBRA = "EEF3FA";
const GREEN = "548235";
const AMBER = "BF8F00";
const RED = "C00000";
const GREY = "595959";

const CONTENT_W = 9360; // US Letter, 1" margins

// ---- Text / paragraph helpers ----
function t(text, opts = {}) { return new TextRun({ text, ...opts }); }

function h1(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_1, children: [t(text)] });
}
function h2(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_2, children: [t(text)] });
}
function h3(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_3, children: [t(text)] });
}
function p(text, opts = {}) {
  return new Paragraph({
    spacing: { after: 120, line: 276 },
    alignment: AlignmentType.JUSTIFIED,
    children: typeof text === "string" ? [t(text, opts)] : text,
  });
}
function lead(text) {
  return new Paragraph({
    spacing: { after: 140, line: 276 },
    children: [t(text, { italics: true, color: GREY })],
  });
}
function bullet(text, level = 0) {
  return new Paragraph({
    numbering: { reference: "bullets", level },
    spacing: { after: 40, line: 264 },
    children: typeof text === "string" ? [t(text)] : text,
  });
}
function num(text, level = 0) {
  return new Paragraph({
    numbering: { reference: "numbers", level },
    spacing: { after: 40, line: 264 },
    children: typeof text === "string" ? [t(text)] : text,
  });
}
function kpi(label, value) {
  return new Paragraph({
    spacing: { after: 40 },
    children: [t(value + "  ", { bold: true, size: 22, color: BLUE }), t(label, { color: GREY })],
  });
}
function spacer(after = 80) { return new Paragraph({ spacing: { after }, children: [t("")] }); }
function pageBreak() { return new Paragraph({ children: [new docx.PageBreak()] }); }

function source(text) {
  return new Paragraph({
    spacing: { after: 160 },
    children: [t("Source: " + text, { italics: true, size: 16, color: GREY })],
  });
}
function figcap(text) {
  return new Paragraph({
    spacing: { before: 40, after: 160 },
    children: [t(text, { italics: true, size: 16, color: GREY })],
  });
}

// ---- Table builder ----
// rows: array of arrays of (string | {text, bold, color, fill, align})
// header row is first. colWidths sum to CONTENT_W.
function table(colWidths, rows, opts = {}) {
  const { headerFill = HEADFILL, zebra = true, fontSize = 18, headerColor = "FFFFFF" } = opts;
  const border = { style: BorderStyle.SINGLE, size: 1, color: "B8C4D9" };
  const borders = { top: border, bottom: border, left: border, right: border };
  const trs = rows.map((row, ri) => {
    const isHeader = ri === 0;
    return new TableRow({
      tableHeader: isHeader,
      children: row.map((cell, ci) => {
        const c = typeof cell === "object" && cell !== null ? cell : { text: String(cell) };
        const fill = isHeader ? headerFill : (c.fill || (zebra && ri % 2 === 0 ? ZEBRA : "FFFFFF"));
        const color = isHeader ? headerColor : (c.color || "000000");
        const align = c.align || (isHeader ? AlignmentType.LEFT : AlignmentType.LEFT);
        return new TableCell({
          borders,
          width: { size: colWidths[ci], type: WidthType.DXA },
          shading: { fill, type: ShadingType.CLEAR },
          margins: { top: 50, bottom: 50, left: 110, right: 90 },
          verticalAlign: VerticalAlign.CENTER,
          children: String(c.text).split("\n").map((ln) => new Paragraph({
            alignment: align,
            spacing: { after: 0, line: 240 },
            children: [t(ln, { bold: isHeader || c.bold, color, size: fontSize })],
          })),
        });
      }),
    });
  });
  return new Table({
    width: { size: CONTENT_W, type: WidthType.DXA },
    columnWidths: colWidths,
    rows: trs,
  });
}

// ---- Horizontal bar chart (native Word, no images) ----
// data: [{label, value, display, color}]; barAreaW within row.
function hbar(data, opts = {}) {
  const { labelW = 2700, barAreaW = 4760, valueW = 1900, color = BLUE, maxVal } = opts;
  const max = maxVal || Math.max(...data.map((d) => d.value));
  const noBorder = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
  const noBorders = { top: noBorder, bottom: noBorder, left: noBorder, right: noBorder };
  const rows = data.map((d, i) => {
    let fill = Math.max(12, Math.round((d.value / max) * barAreaW));
    if (fill > barAreaW) fill = barAreaW;
    let rest = barAreaW - fill;
    if (rest < 1) rest = 1;
    const innerBorder = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
    const inner = new Table({
      width: { size: barAreaW, type: WidthType.DXA },
      columnWidths: [fill, rest],
      borders: { top: innerBorder, bottom: innerBorder, left: innerBorder, right: innerBorder, insideHorizontal: innerBorder, insideVertical: innerBorder },
      rows: [new TableRow({
        children: [
          new TableCell({
            width: { size: fill, type: WidthType.DXA },
            shading: { fill: d.color || color, type: ShadingType.CLEAR },
            borders: { top: innerBorder, bottom: innerBorder, left: innerBorder, right: innerBorder },
            margins: { top: 30, bottom: 30, left: 0, right: 0 },
            children: [new Paragraph({ children: [t("", { size: 14 })] })],
          }),
          new TableCell({
            width: { size: rest, type: WidthType.DXA },
            borders: { top: innerBorder, bottom: innerBorder, left: innerBorder, right: innerBorder },
            margins: { top: 30, bottom: 30, left: 0, right: 0 },
            children: [new Paragraph({ children: [t("", { size: 14 })] })],
          }),
        ],
      })],
    });
    return new TableRow({
      children: [
        new TableCell({
          width: { size: labelW, type: WidthType.DXA }, borders: noBorders,
          verticalAlign: VerticalAlign.CENTER,
          margins: { top: 20, bottom: 20, left: 0, right: 80 },
          children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [t(d.label, { size: 17 })] })],
        }),
        new TableCell({
          width: { size: barAreaW, type: WidthType.DXA }, borders: noBorders,
          verticalAlign: VerticalAlign.CENTER,
          margins: { top: 20, bottom: 20, left: 0, right: 0 },
          children: [inner],
        }),
        new TableCell({
          width: { size: valueW, type: WidthType.DXA }, borders: noBorders,
          verticalAlign: VerticalAlign.CENTER,
          margins: { top: 20, bottom: 20, left: 80, right: 0 },
          children: [new Paragraph({ children: [t(d.display, { size: 17, bold: true, color: NAVY })] })],
        }),
      ],
    });
  });
  return new Table({
    width: { size: CONTENT_W, type: WidthType.DXA },
    columnWidths: [labelW, barAreaW, valueW],
    borders: { top: noBorder, bottom: noBorder, left: noBorder, right: noBorder, insideHorizontal: noBorder, insideVertical: noBorder },
    rows,
  });
}

// callout box
function callout(title, lines, fill = LIGHTBLUE) {
  const border = { style: BorderStyle.SINGLE, size: 4, color: BLUE };
  return new Table({
    width: { size: CONTENT_W, type: WidthType.DXA },
    columnWidths: [CONTENT_W],
    rows: [new TableRow({
      children: [new TableCell({
        width: { size: CONTENT_W, type: WidthType.DXA },
        borders: { top: border, bottom: border, left: border, right: border },
        shading: { fill, type: ShadingType.CLEAR },
        margins: { top: 120, bottom: 120, left: 160, right: 160 },
        children: [
          new Paragraph({ spacing: { after: 60 }, children: [t(title, { bold: true, color: NAVY, size: 20 })] }),
          ...lines.map((ln) => new Paragraph({ spacing: { after: 40 }, children: [t(ln, { size: 18 })] })),
        ],
      })],
    })],
  });
}

module.exports = {
  docx, NAVY, BLUE, LIGHTBLUE, ZEBRA, GREEN, AMBER, RED, GREY, CONTENT_W,
  t, h1, h2, h3, p, lead, bullet, num, kpi, spacer, pageBreak, source, figcap,
  table, hbar, callout,
};
