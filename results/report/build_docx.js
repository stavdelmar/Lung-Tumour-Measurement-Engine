// Build the short results report as a formatted Word document.
// Usage (repo root): node results/report/build_docx.js results/figures results/LungMarker_Results.docx
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, WidthType, BorderStyle,
  ShadingType, AlignmentType, HeadingLevel, LevelFormat, PageBreak, Footer, PageNumber, VerticalAlign,
} = require("docx");

const FIG = process.argv[2];
const OUT = process.argv[3];
const FONT = "Calibri";
const INK = "0B0B0B", INK2 = "52514E", RULE = "D9D8D3";
const GREEN = "1BAF7A", ORANGE = "EB6834", BLUE = "2A78D6";
const TINT = { g: "F3FBF7", o: "FFF6F1", b: "F2F7FE" };
const COL = { g: GREEN, o: ORANGE, b: BLUE };
const W = 10092; // content width (A4, 16 mm margins) in DXA

// ---------- text helpers ----------
function runs(text, opts = {}) {
  // **bold** inline markup
  const out = [];
  text.split(/(\*\*[^*]+\*\*)/).forEach((part) => {
    if (!part) return;
    const bold = part.startsWith("**");
    out.push(new TextRun({ text: bold ? part.slice(2, -2) : part, bold: bold || opts.bold, italics: opts.italics,
      size: opts.size || 19, color: opts.color || INK, font: FONT, highlight: opts.highlight }));
  });
  return out;
}
const P = (text, o = {}) => new Paragraph({ children: runs(text, o), spacing: { after: o.after ?? 100, before: o.before ?? 0 }, alignment: o.align });
const H1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text: t, font: FONT })] });
const H2 = (t, dot) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [
  ...(dot ? [new TextRun({ text: "● ", color: COL[dot], font: FONT })] : []), new TextRun({ text: t, font: FONT })] });
const H3 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun({ text: t, font: FONT })] });
const bullet = (t) => new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: runs(t), spacing: { after: 60 } });
const small = (t) => P(t, { size: 16, color: INK2, after: 80 });
const pageBreak = () => new Paragraph({ children: [new PageBreak()] });

function image(file, widthPx, caption) {
  const buf = fs.readFileSync(path.join(FIG, file));
  const [w, h] = { "summary_at_a_glance.png": [2640, 726], "outline_error_vs_expert.png": [2200, 800], "time_before_after.png": [1800, 640] }[file];
  const items = [new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 80, after: 40 },
    children: [new ImageRun({ type: "png", data: buf, transformation: { width: widthPx, height: Math.round(widthPx * h / w) } })] })];
  if (caption) items.push(P(caption, { size: 15, color: INK2, italics: true, after: 120 }));
  return items;
}

// ---------- tables ----------
const none = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const thin = { style: BorderStyle.SINGLE, size: 4, color: RULE };

function tiles(items, cols, kind) {
  // items: [title, body]; coloured top border + tint, white gutters between cells
  const gutter = 140;
  const cw = Math.floor((W - gutter * (cols - 1)) / cols);
  const widths = [];
  for (let i = 0; i < cols; i++) { widths.push(cw); if (i < cols - 1) widths.push(gutter); }
  const rows = [];
  for (let r = 0; r < items.length; r += cols) {
    const cells = [];
    for (let c = 0; c < cols; c++) {
      const it = items[r + c];
      if (it) {
        cells.push(new TableCell({
          width: { size: cw, type: WidthType.DXA },
          shading: { type: ShadingType.CLEAR, color: "auto", fill: TINT[kind] },
          margins: { top: 90, bottom: 100, left: 130, right: 130 },
          borders: { top: { style: BorderStyle.SINGLE, size: 18, color: COL[kind] }, bottom: thin, left: thin, right: thin },
          children: [
            new Paragraph({ spacing: { after: 40 }, children: [new TextRun({ text: it[0], bold: true, size: it[2] || 22, font: FONT, color: INK })] }),
            new Paragraph({ spacing: { after: 0 }, children: runs(it[1], { size: 17 }) }),
            ...(it[3] ? [new Paragraph({ spacing: { before: 50, after: 0 }, children: runs(it[3], { size: 15, color: INK2 }) })] : []),
          ],
        }));
      } else {
        cells.push(new TableCell({ width: { size: cw, type: WidthType.DXA }, borders: { top: none, bottom: none, left: none, right: none }, children: [new Paragraph("")] }));
      }
      if (c < cols - 1) cells.push(new TableCell({ width: { size: gutter, type: WidthType.DXA }, borders: { top: none, bottom: none, left: none, right: none }, children: [new Paragraph("")] }));
    }
    rows.push(new TableRow({ children: cells, cantSplit: true }));
    if (r + cols < items.length) {
      rows.push(new TableRow({ height: { value: 110, rule: "exact" }, children: widths.map((w) => new TableCell({ width: { size: w, type: WidthType.DXA }, borders: { top: none, bottom: none, left: none, right: none }, children: [new Paragraph("")] })) }));
    }
  }
  return [new Table({ width: { size: W, type: WidthType.DXA }, columnWidths: widths, borders: { top: none, bottom: none, left: none, right: none, insideHorizontal: none, insideVertical: none }, rows }),
    new Paragraph({ spacing: { after: 60 }, children: [] })];
}

function flow(boxes, kind = "b") {
  // boxes: [title, body, style] with arrows between; style 'gap' = dashed, 'res' = result
  const arrowW = 360;
  const n = boxes.length;
  const bw = Math.floor((W - arrowW * (n - 1)) / n);
  const widths = []; const cells = [];
  boxes.forEach((b, i) => {
    widths.push(bw);
    const style = b[2];
    const border = style === "gap" ? { style: BorderStyle.DASHED, size: 6, color: "9A9993" } : thin;
    cells.push(new TableCell({
      width: { size: bw, type: WidthType.DXA }, verticalAlign: VerticalAlign.TOP,
      shading: { type: ShadingType.CLEAR, color: "auto", fill: style === "res" ? "E3EEFC" : style === "gap" ? "FFFFFF" : TINT[kind] },
      margins: { top: 80, bottom: 90, left: 110, right: 110 },
      borders: { top: border, bottom: border, left: border, right: border },
      children: [new Paragraph({ spacing: { after: 30 }, children: [new TextRun({ text: b[0], bold: true, size: 17, font: FONT })] }),
                 new Paragraph({ spacing: { after: 0 }, children: runs(b[1], { size: 16 }) })],
    }));
    if (i < n - 1) {
      widths.push(arrowW);
      cells.push(new TableCell({ width: { size: arrowW, type: WidthType.DXA }, verticalAlign: VerticalAlign.CENTER, borders: { top: none, bottom: none, left: none, right: none },
        children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: b[3] || "→", size: 24, color: INK2, font: FONT })] })] }));
    }
  });
  return [new Table({ width: { size: W, type: WidthType.DXA }, columnWidths: widths, borders: { top: none, bottom: none, left: none, right: none, insideHorizontal: none, insideVertical: none }, rows: [new TableRow({ children: cells, cantSplit: true })] }),
    new Paragraph({ spacing: { after: 60 }, children: [] })];
}

function grid(header, rows, fractions, opts = {}) {
  const widths = fractions.map((f) => Math.round(W * f));
  widths[widths.length - 1] = W - widths.slice(0, -1).reduce((a, b) => a + b, 0);
  const cell = (t, i, isHead, isTotal) => new TableCell({
    width: { size: widths[i], type: WidthType.DXA },
    shading: isHead || isTotal ? { type: ShadingType.CLEAR, color: "auto", fill: "F3F2EF" } : undefined,
    margins: { top: 50, bottom: 50, left: 90, right: 90 },
    borders: { top: thin, bottom: thin, left: thin, right: thin },
    children: [new Paragraph({ spacing: { after: 0 }, children: runs(t, { size: 16, bold: isHead || isTotal }) })],
  });
  const trs = [new TableRow({ tableHeader: true, children: header.map((t, i) => cell(t, i, true)) })];
  rows.forEach((r, k) => trs.push(new TableRow({ cantSplit: true, children: r.map((t, i) => cell(t, i, false, opts.totalLast && k === rows.length - 1)) })));
  return [new Table({ width: { size: W, type: WidthType.DXA }, columnWidths: widths, rows: trs }), new Paragraph({ spacing: { after: 80 }, children: [] })];
}

function callout(text, fill = "EEF4FC", border = BLUE) {
  return [new Table({ width: { size: W, type: WidthType.DXA }, columnWidths: [W], rows: [new TableRow({ children: [new TableCell({
    width: { size: W, type: WidthType.DXA }, shading: { type: ShadingType.CLEAR, color: "auto", fill },
    margins: { top: 90, bottom: 90, left: 150, right: 150 },
    borders: { top: none, bottom: none, right: none, left: { style: BorderStyle.SINGLE, size: 18, color: border } },
    children: [new Paragraph({ spacing: { after: 0 }, children: runs(text, { size: 17 }) })] })] })] }),
    new Paragraph({ spacing: { after: 80 }, children: [] })];
}

// ---------- content ----------
const page1 = [
  H1("LungMarker: results"),
  new Paragraph({ spacing: { after: 140 }, children: [
    new TextRun({ text: "Research use only. Not for clinical use. No clinical claims. ", bold: true, size: 17, font: FONT }),
    ...runs("LungMarker helps a researcher measure lung tumours on CT scans faster. An AI finds the tumours and drafts the measurements; the researcher checks and corrects each one, and the results go straight into the lab's Excel sheet, their one source of truth. Built for the Harbor Thoracic Oncology Lab (simulated) and tested on a public set of CT scans: 59 scans from 31 patients, each with one tumour outlined by an expert (RIDER Lung CT).", { size: 17, color: INK2 })] }),
  H2("What works", "g"),
  ...tiles([
    ["52 of 59 found", "The AI found the tumour the expert had marked in 52 of 59 scans (88%), with no hints.", 22, "59 scans, 31 patients"],
    ["24 of 24 matched", "Every tumour found on both of a patient's scans was correctly matched to the earlier scan.", 22, "24 patient pairs"],
    ["3.0 mm vs 2.3 mm", "The AI's measurement of a tumour's longest width is typically 3.0 mm from the expert's; two expert measurements of the same tumour differ by 2.3 mm. No tendency to over- or under-measure.", 22, "52 tumours, 28 patients (expert: 28 patients)"],
  ], 3, "g"),
  H2("What fails, or isn't proven yet", "o"),
  ...tiles([
    ["7 misses, all central", "All 7 missed tumours were in the centre of the chest, next to the heart and main airways (14–52 mm). The app now requires the researcher to check that area before approving; an automatic warning was tried and dropped (too many false alarms).", 22, "7 of 59 scans, 4 of 31 patients"],
    ["19 of 52 off by more than 5 mm", "AI outlines more than 5 mm from the expert's (13 too small, 6 too large). The researcher confirms every outline before it's saved, but some large misses get no \"AI unsure\" warning.", 22, "52 tumours, 28 patients"],
    ["Not tested", "Faint \"ground-glass\" nodules: none in the test scans, and the open set that has them (LNDb) needs approval that takes up to 9 days, ending after the deadline. False alarms: the data marks only one tumour per scan. The lab's own scans.", 22, "0 ground-glass nodules in the 59 test scans"],
  ], 3, "o"),
  ...image("outline_error_vs_expert.png", 640, "Each dot is one of the 52 tumours found (28 patients): how far the AI's measurement is from the expert's (left: longest width, mm; right: volume, %). Blue band: how much the expert's own two measurements of the same tumour differ (2.3 mm, 17%; 28 patients). Within the band: 20 of 52 for width, 27 of 52 for volume. A good first draft, not a final answer, which is why the researcher confirms every value."),
  pageBreak(),
];

const page2 = [
  H2("How I measured the time saved", "b"),
  P("The honest test is the real researcher timing his work with and without the tool. Because the lab's users are simulated, that wasn't possible. Instead I combined what I could collect, agreed the method with Base44's FDE lead (Sam), and labelled every number as an estimate.", { size: 18 }),
  ...callout("**Today's time per incoming scan.** Two-thirds of the scans Daniel receives are follow-ups, which take longer than first (baseline) scans, so the average is weighted:  **Minutes per scan = ⅓ × baseline + ⅔ × follow-up = ⅓ × 39 + ⅔ × 47.5 ≈ 45 min.**  Baseline 39 min: Daniel's log (4 scans). Follow-up 40–55 min, midpoint 47.5: Daniel's own step-by-step account (his log: 55 min, 1 scan; using it gives ≈ 50 min, so we use the lower figure). The lab's target, half: about 22 min per scan."),
  H3("Where the time goes today (one follow-up scan), and what the tool changes"),
  ...grid(["Step", "Daniel today (his account)", "What the tool does", "Effect"], [
    ["Opening the scan", "1–2 min", "Opens with the AI's suggestions ready; earlier scan already linked", "Shortened"],
    ["Finding each earlier nodule and matching it", "~10 min per nodule", "Suggests the match and shows both scans side by side; he confirms", "Shortened, still checked"],
    ["Searching for new nodules", "10–20 min (two passes, 250–400 images)", "AI marks candidates; one check pass, plus the required centre-of-chest check", "Search shortened; check kept"],
    ["Measuring", "2–4 min per nodule", "Measurements drafted; he checks or corrects them", "Shortened, still checked"],
    ["Full outline", "15–25 min per tumour, when needed", "Outline drafted for every nodule; he confirms", "Shortened"],
    ["Typing into Excel", "3–5 min", "One export a day in his format", "Removed"],
    ["New", "—", "Accept or reject each AI suggestion; tick the centre-of-chest check", "Added"],
    ["Total", "40–55 min", "With the tool: its own steps 1–2 min (measured, 7 scans) + his checking (not measured)", ""],
  ], [0.22, 0.22, 0.38, 0.18], { totalLast: true }),
  ...image("time_before_after.png", 520),
  P("**How to read this.** The blue bar is all I could measure: the tool's own steps (opening, accepting, confirming, matching, exporting), 1–2 active minutes per scan over 7 developer runs on public scans (2–5 nodules each; 1 more run excluded, see Annex C). The hatched part is Daniel's time to check each AI suggestion, which only he can show. If checking were instant, a follow-up would take a few minutes; if it took as long as doing it by hand, about 35–52 min. So I give a range for one follow-up (compare it with today's 40–55 min, not the 45-min average), and no single number or percentage saved.", { size: 17 }),
  P("**Limitation and next step.** The lab's users are simulated: they answer questions but can't open the tool, so no real reader was timed and no real usability test was possible. Daniel approved the flow from screenshots and one external tester (a doctor) tried the tool. The measurement itself is built in: the app times every scan the way Daniel logs it today (the whole review, without long breaks) and fills his \"Minutes on scan\" column. **Next step:** Daniel's own timed reviews, with and without the tool, on a small set of the lab's scans.", { size: 17 }),
  pageBreak(),
];

const annex = [
  H2("Annex A · Method"),
  bullet("**Data:** RIDER Lung CT (public, The Cancer Imaging Archive): 31 patients, each scanned twice about 15 minutes apart; 59 scans with an expert outline of one tumour each (RIDER-LungCT-Seg). Tumours 13–93 mm (median 43 mm), mostly solid (53 solid, 6 part-solid), no ground-glass. The lab measures nodules from 4 mm, so these are larger and clearer than its usual cases."),
  bullet("**How the AI ran:** the whole pipeline with no hint: lobes, then nodule finding (TotalSegmentator lung_nodules, full settings, free Colab T4 GPU, median 49 s per scan), then outline and measurement, then matching between each patient's two scans. The finding model was not trained on RIDER."),
  bullet("**How quality was measured:** the AI's outline and the expert's outline of the same tumour are measured the same way, the way Daniel measures: longest width on the slice where the tumour is largest, the longest perpendicular width on that slice, and volume from the 3D outline. Error = AI minus expert, per tumour; we report the median of the absolute error and the median of the signed error (bias)."),
  bullet("**Expert noise (the yardstick):** the expert outlined the same tumour on both of a patient's scans, taken 15 minutes apart. The median difference between those two outlines (28 patients) is 2.3 mm for longest width and 17% for volume. The AI is \"within expert noise\" when its error is no larger."),
  bullet("**Outline setting:** the model's core plus a rim scaled to the core's size (the shipped setting). It was chosen by comparing the model's own outline, MedSAM 2 and four rim variants on these same 52 tumours, so the quality numbers are somewhat optimistic."),
  bullet("**What this measures:** the AI's first draft. The researcher's confirmed values (what goes into the sheet) were not measured."),
  H2("Annex B · Full numbers"),
  ...grid(["Measure", "Sample", "Result"], [
    ["Expert tumour found", "59 scans, 31 patients", "52 / 59 (88%); solid 48 / 53, part-solid 4 / 6"],
    ["Missed tumours", "59 scans", "7 scans, 4 patients; all central, 14–52 mm"],
    ["Longest width, AI vs expert", "52 tumours, 28 patients", "median error 3.0 mm, bias −0.3 mm; 20 / 52 within 2.3 mm; 19 / 52 more than 5 mm off (13 too small, 6 too large)"],
    ["Volume, AI vs expert", "52 tumours, 28 patients", "median error 14%, bias +0.5%; 27 / 52 within 17%"],
    ["Overlap with expert outline (Dice)", "52 tumours", "median 0.76"],
    ["Matched to the earlier scan", "24 patient pairs", "24 / 24; alignment error at the tumour median 2.9 mm (max 13.9)"],
    ["Lobe agrees with expert outline", "52 tumours", "52 / 52"],
    ["Other AI marks per scan", "59 scans", "median 3; 82% reappear on the patient's other scan (a proxy for false alarms only)"],
    ["Small nodules (< 8 mm), same nodule on both scans", "84 pairs, 22 patients", "width differs by median 0.5 mm; volume by ~30%"],
    ["\"AI unsure about the edges\" on likely-too-small outlines", "52 tumours; 322 AI marks", "flags all 4 small faint tumours drawn much too small; fires on 12% of all marks (tuned on 4 cases)"],
    ["Automatic \"check the centre\" warning (dropped)", "59 scans", "best version flagged 4 of the 7 missed scans, but also 49 of the other 52"],
    ["Tool's own steps (developer pilot)", "7 scans, 4 patients", "1–2 active min per scan (median 2)"],
  ], [0.40, 0.22, 0.38]),
  pageBreak(),
  H2("Annex C · All 8 developer runs"),
  ...grid(["Patient (public RIDER)", "Timepoint", "Active min", "Open min", "Nodules reviewed", "Note"], [
    ["RIDER-1225316081", "Baseline", "1", "1", "2", ""],
    ["RIDER-1225316081", "Follow-up 1", "12", "20", "3", "**Excluded:** scan left open while writing messages, so the timer measured something else"],
    ["RIDER-1332496276", "Baseline", "1", "1", "2", ""],
    ["RIDER-1332496276", "Follow-up 1", "1", "1", "2", ""],
    ["RIDER-1500037140", "Baseline", "2", "2", "4", ""],
    ["RIDER-1500037140", "Follow-up 1", "2", "2", "4", ""],
    ["RIDER-1532432635", "Baseline", "2", "2", "5", "incl. 2 rejected"],
    ["RIDER-1532432635", "Follow-up 1", "2", "2", "5", "incl. 1 rejected + 1 not found"],
    ["Included: 7 scans", "", "1–2 (median 2)", "", "2–5", "developer, not a trained reader"],
  ], [0.21, 0.13, 0.12, 0.10, 0.12, 0.32], { totalLast: true }),
  small("18 Oct, final app version, by the developer (Stav). Source: the app's own timer (\"Minutes on scan\" and the approval rows of the edit trail in the Excel export). Active minutes pause after 2 minutes without input or when the tab is hidden; whole minutes, so \"1\" means roughly 0.5–1.5 min. These runs measure the tool's mechanics, not a trained reader's judgement."),
  H2("Annex D · Daniel's step breakdown (his words, Slack, 18 Oct)"),
  ...grid(["Step (follow-up scan)", "Minutes", "Unit"], [
    ["Loading", "1–2", "per scan"],
    ["Re-finding and matching (aligns by bronchi and fissures; slice numbers are unreliable because of breathing)", "~10", "per nodule"],
    ["Finding new nodules (two passes over 250–400 slices)", "10–20", "per scan"],
    ["Measuring", "2–4", "per nodule"],
    ["Full outline", "15–25", "per tumour, when needed"],
    ["Recording", "3–5", "per scan"],
    ["Total (his own figure)", "40–55", "per scan"],
  ], [0.58, 0.14, 0.28], { totalLast: true }),
  small("Some steps are per nodule, so the total is Daniel's own figure, not a sum we calculated. His log (\"Minutes on scan\", last 5 rows): baseline 38, 49, 30, 37 (mean ≈ 39); follow-up 55. About two-thirds of incoming scans are follow-ups (his estimate). He has not broken down a baseline scan."),
  H2("Annex E · Credits"),
  bullet("**RIDER Lung CT:** Zhao, B. et al. (2015). Coffee-break lung CT collection with scan images reconstructed at multiple imaging parameters. The Cancer Imaging Archive. doi:10.7937/k9/tcia.2015.u1x8a5nr (CC BY 3.0)."),
  bullet("**RIDER-LungCT-Seg:** Wee, L., Aerts, H., Kalendralis, P., & Dekker, A. (2020). RIDER Lung CT Segmentation Labels. The Cancer Imaging Archive. doi:10.7937/tcia.2020.jit9grk8."),
  bullet("**TotalSegmentator** (Wasserthal, J. et al., 2023), including the lung_nodules model by BlueMind AI. Apache-2.0."),
  bullet("**MedSAM 2** (Ma, J. et al., 2025, arXiv:2504.03600), compared, not used. **SimpleITK** for lung alignment."),
  bullet("**Base44** for the review app. Full code, raw data and the long version of these results (RESULTS.md) are in the repository; python results/make_figures.py rebuilds every figure and number."),
];

const doc = new Document({
  creator: "Stav Delmar",
  title: "LungMarker results",
  styles: {
    default: { document: { run: { font: FONT, size: 19, color: INK } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 36, bold: true, font: FONT, color: INK }, paragraph: { spacing: { before: 0, after: 80 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, font: FONT, color: INK }, paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 1,
          border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: RULE, space: 2 } } } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 21, bold: true, font: FONT, color: INK }, paragraph: { spacing: { before: 160, after: 60 }, outlineLevel: 2 } },
    ],
  },
  numbering: { config: [{ reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
    style: { paragraph: { indent: { left: 360, hanging: 220 } } } }] }] },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 850, bottom: 900, left: 907, right: 907 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [
      new TextRun({ text: "LungMarker results · research use only · ", size: 14, color: "777777", font: FONT }),
      new TextRun({ children: [PageNumber.CURRENT], size: 14, color: "777777", font: FONT })] })] }) },
    children: [...page1, ...page2, ...annex],
  }],
});

Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(OUT, buf); console.log(OUT); });
