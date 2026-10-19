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
  H1("LungMarker: results summary"),
  new Paragraph({ spacing: { after: 160 }, children: [
    new TextRun({ text: "Research use only. Not for clinical use. No clinical claims. ", bold: true, size: 17, font: FONT }),
    ...runs("LungMarker helps a researcher measure lung tumours on CT scans faster. An AI finds the tumours and drafts the measurements; the researcher checks and corrects each one, and the results go straight into the lab's Excel sheet. Built in 7 days for the Harbor Thoracic Oncology Lab (simulated), tested on a public set of CT scans. 19 Oct 2026.", { size: 17, color: INK2 })] }),
  H2("What worked", "g"),
  ...tiles([
    ["Asking first changed the product", "We assumed drawing outlines was the slow part. Daniel showed us it's **searching** for tumours. So we built \"find\" first, which saves the most time.", 20],
    ["52 / 59 · 24 / 24", "tumours found, and tumours matched to the earlier scan. Measurements are typically **3.0 mm** from the expert's; two expert measurements of the same tumour differ by 2.3 mm."],
    ["Fits how the lab works", "Scans grouped by patient, export straight into their 18-column Excel sheet, a record of every change. It answers why last year's tool failed: no editing, no export, installation, cost.", 20],
    ["Works end to end in the browser", "The Base44 app and the AI engine we built are connected; the original CT scans (DICOM) open and scroll in the browser. Nothing to install.", 20],
    ["Honesty built into the tool", "A required check of the centre of the chest, an \"AI unsure\" label, and \"Not found\" rows so a tumour from the earlier scan is never silently dropped.", 20],
    ["Fast, with checks on real output", "First milestone reached a day early. Checking real Excel exports caught data bugs (a nodule that disappeared, rejections missing from the record) before they reached the lab.", 20],
  ], 3, "g"),
  H2("What didn't work, or isn't proven yet", "o"),
  ...tiles([
    ["Real time saved: not measured", "The lab's user is simulated and can't use the tool. We timed only the tool's own steps (~1–2 min per scan), so time saved is a range, not a number.", 20],
    ["Central tumours: 7 of 59 missed", "All misses were in the centre of the chest. The fix for now is a required manual check; an automatic warning gave too many false alarms.", 20],
    ["Faint \"ground-glass\" nodules: not tested", "None in the practice scans. The open dataset that has them (LNDb) needs registration and approval, up to 9 days, after the deadline. We chose not to use it before approval.", 20],
    ["Outlines: 19 of 52 off by more than 5 mm", "The researcher confirms every one, but some large ones get no \"unsure\" warning.", 20],
    ["Usability testing was limited", "Daniel can't open links, so we used screenshots and one external tester.", 20],
    ["Base44: strong at structure, weak at fine UI", "The builder set up the app well, but detailed screen work and the sync → Publish order slowed testing, so much of the work moved to code.", 20],
    ["Not a real deployment yet", "The AI runs in batches on a free cloud GPU (Colab). In a hospital it needs one server, a data-privacy review and a written yearly cost.", 20],
  ], 2, "o"),
  small("How the time saved was measured, with all sample sizes: page 4. Full version and raw data: RESULTS.md in the repository."),
  pageBreak(),
];

const page2 = [
  H2("What works", "g"),
  H3("The pieces connect end to end"),
  ...flow([
    ["1 · CT scans", "Original scans in the hospital format (DICOM), here from a public research set"],
    ["2 · Our AI engine", "Finds tumours, outlines and measures them, matches them to the earlier scan"],
    ["3 · Results online", "Scan images and AI drafts saved as files in cloud storage"],
    ["4 · Base44 app", "The researcher reviews, corrects and approves, in the browser"],
    ["5 · Excel", "One click: rows in the lab's own sheet format, plus a log of every change"],
  ], "g"),
  small("The app picks up new scans by itself. In real use, step 2 would run on one server inside the hospital, because real scans can't leave it."),
  H3("How close is the AI to an expert?"),
  P("We ran the AI on a public set of 59 CT scans (31 patients, each scanned twice 15 minutes apart), where an expert had outlined one tumour per scan, and measured both outlines the way Daniel measures."),
  ...image("outline_error_vs_expert.png", 640, "Each dot is one tumour: how far the AI's measurement is from the expert's (left: longest width in mm; right: volume in %). Blue band: how much the expert's own two measurements of the same tumour differ."),
  bullet("**Finding:** the tumour was found in 52 of 59 scans (88%), and matched to the same patient's other scan in 24 of 24 cases."),
  bullet("**Measuring:** the AI's longest-width measurement is typically about 3 mm from the expert's, with no tendency to over- or under-measure (52 tumours, 28 patients). The expert's own two measurements of the same tumour differ by about 2.3 mm; the AI is within that for 20 of 52 tumours. A good first draft, not a final answer."),
  bullet("**Volume:** typically 14% from the expert; within the expert's own variation (17%) for 27 of 52."),
  H3("What the researcher gets"),
  bullet("**Excel in the lab's format:** the same 18 columns, order and formats as Daniel's sheet; only new rows each day; a second sheet logs what the AI drafted and what he changed. Checked on real exports and by 30 automated checks."),
  bullet("**Review that respects his judgement:** accept or reject each AI suggestion, fix outlines by hand, add anything it missed. Nothing is saved until he confirms."),
  bullet("**Organised by patient:** a patient's scans are grouped, and the earlier scan opens next to the new one."),
  pageBreak(),
];

const page3 = [
  H2("What doesn't work (yet), and how I would fix it", "o"),
  ...tiles([
    ["Central tumours missed", "7 of 59 scans (4 of 31 patients). Every miss was in the centre of the chest, where the lungs meet the heart and main airways, including large tumours (14–52 mm). The lab says these are common in its patients.", 20, "Now: the app won't let a scan be approved until the researcher confirms they checked that area. An automatic warning was tried and dropped: it flagged almost every scan."],
    ["Some outlines far off", "19 of 52 AI outlines were more than 5 mm off the expert's (13 too small, 6 too large).", 20, "Now: nothing is saved until the researcher confirms the outline; some likely-too-small outlines are flagged \"AI unsure about the edges\"."],
    ["No real usability test", "The lab's users are simulated chat personas: they answer questions but can't open links or use the tool. We used screenshots and one external tester instead.", 20, "Impact: the time saved is an estimate, and ease of use is untested with the real user."],
    ["Not yet tested", "Faint \"ground-glass\" nodules: none in the practice scans; the open set that has them (LNDb) needs approval that takes up to 9 days, after the deadline. Also untested: false alarms, the lab's own scans. Small nodules' volume varies ~30% between repeat scans.", 20],
    ["Base44 limits", "Strong at setting up the app's structure and data, weak at fine screen detail; the GitHub sync → Publish order caused confusing test results. Much of the work moved to code.", 20],
    ["Not a real deployment", "The AI runs in batches on a free cloud GPU. In a hospital it needs one server inside the network, a data-privacy review and a written yearly cost.", 20],
  ], 2, "o"),
  H3("How I would fix the central-tumour miss"),
  P("The AI model sees almost nothing at those spots, and three of the four missed tumours grow along blood vessels, so a simple rule can't tell them apart from normal vessels. It needs a different model, not a setting."),
  bullet("**A stronger computer with a GPU.** Everything ran on free tools this week. With a GPU (or paid cloud GPU time), I would run a second AI model trained on lung-cancer scans that include central tumours, and use it only where it disagrees with the current one."),
  bullet("**A bigger test.** We had only 4 patients with central tumours, too few to judge any fix. Next: a larger public set, then a sample of the lab's own scans inside the hospital, counting misses and false alarms."),
  bullet("**A paid model, carefully.** Commercial tools exist but weren't evaluated, and price is why the lab dropped last year's tool. Only if a test shows it catches central tumours and the yearly cost fits a research budget."),
  bullet("**Until then,** the required manual check of the centre of the chest stays."),
  H3("How I would run the usability test with real users"),
  bullet("**Watch, don't help:** give Daniel a real task (\"a follow-up scan for patient X came in, record it as you would for the study\"), ask him to think aloud, don't explain, then talk it through; rank problems by how serious and how hard to fix."),
  bullet("**Time it properly:** Daniel times his own work on a set of the lab's scans, with and without the tool, the same way both times."),
  bullet("**Check the final numbers:** compare the values he confirms with the tool against his manual ones on the same scans."),
  small("**Other limits:** the public scans have mostly large, clear tumours (13–93 mm; the lab measures from 4 mm); we measured the AI's first draft, not the researcher's corrected values; settings were tuned on the same tumours, so the numbers are a little optimistic."),
  pageBreak(),
];

const page4 = [
  H2("How we measured the time saved", "b"),
  P("The honest test is the real researcher timing his work with and without the tool. Because the lab's users are simulated, that wasn't possible. Instead we combined what we could collect, agreed the method with Base44's FDE lead (Sam), and label every number as an estimate."),
  ...flow([
    ["Today, by hand", "Daniel broke his work into steps: **40–55 min** for one follow-up scan (his log agrees: 55 min).", "", "+"],
    ["The tool's own steps", "Timed on 7 scans in the app: opening, clicking, confirming, exporting take **1–2 min**.", "", "+"],
    ["Not measured", "How long Daniel needs to check each AI suggestion. Only a real user can show this.", "gap"],
    ["Result: an estimate", "Between a few minutes and close to today's time. We can't yet say if the lab's goal (half) is met.", "res"],
  ], "b"),
  H3("Where the time goes today, and what the tool changes"),
  ...grid(["Step (follow-up scan)", "Daniel today", "What the tool does", "Effect"], [
    ["Opening the scan", "1–2 min", "Opens with the AI's suggestions ready; earlier scan already linked", "Shorter"],
    ["Finding each old nodule again and matching it", "~10 min per nodule (lines up by airways)", "Suggests the match and shows the two scans side by side; he confirms", "Shorter, still checked"],
    ["Searching for new nodules", "10–20 min (two full passes through 250–400 images)", "AI marks candidates; one check pass, plus the required centre-of-chest check", "Shorter, still checked"],
    ["Measuring", "2–4 min per nodule", "Measurements drafted; he checks or corrects them", "Shorter, still checked"],
    ["Full outline", "15–25 min per tumour, when needed", "Outline drafted for every nodule; he confirms", "Shorter, done for more nodules"],
    ["Typing into Excel", "3–5 min", "One export a day in his format", "Removed"],
    ["New", "—", "Accept or reject each AI suggestion; tick the centre-of-chest check", "Added"],
    ["Total", "40–55 min", "Tool's own steps 1–2 min (measured) + his checking (not measured)", ""],
  ], [0.22, 0.22, 0.38, 0.18], { totalLast: true }),
  ...image("time_before_after.png", 600),
  ...callout("**How to read this.** The blue bar is all we could measure: the tool's own steps. The hatched part is Daniel's checking time, which only he can show. If checking were instant, a scan would take a few minutes; if it took as long as doing it by hand, about 35–52 min. So we give a range, not a single number or a percentage saved. What it does show: the tool's mechanics are not where the time goes."),
  small("Daniel's steps are in his own words (18 Oct). Developer runs: 7 scans (4 patients, first scan and follow-up), 1 more excluded because it was left open; every run is in the appendix. A first (baseline) scan takes about 39 min by hand."),
  pageBreak(),
];

const page5 = [
  H2("Feedback from a potential user"),
  P("Since the lab's users are simulated, I also asked a doctor friend to try the tool as a potential user."),
  ...callout("[TO FILL IN — her role/specialty, what she did with the tool (which scans, how long), and what she said: what was clear, where she hesitated, what she would change. Note that she is a friend, not a member of the lab.]", "FFF3C4", "C98500"),
  H2("Next steps"),
  bullet("**A real test with the real user:** inside the hospital, on a small set of the lab's own scans, with the AI engine on one hospital server. Daniel times his work with and without the tool, and we run a proper usability session. This turns the time range into a number."),
  bullet("**Central tumours:** a second AI model on a GPU, tested on a bigger set; the manual check stays until then."),
  bullet("**Faint nodules:** once LNDb access is approved, test on its faint \"ground-glass\" and part-solid nodules (73 suitable nodules counted)."),
  bullet("**Cost:** write down the full yearly cost before any rollout (Base44 plan, one hospital server, IT time, any paid GPU or model) so the lab can compare it with last year's tool."),
  H2("Why this differs from last year's tool"),
  P("The lab tried a vendor tool last year and dropped it. Their four reasons, and what's different:"),
  ...grid(["Last year's problem", "LungMarker", "Honest caveat"], [
    ["**Could only accept or reject** the AI's outline", "The researcher can edit any outline and value; every change is logged", "Not yet tried by the real researcher"],
    ["**No export to their sheet**", "One-click export in their exact Excel format", "Checked on public test scans"],
    ["**Needed hospital IT to install**", "Runs in the browser; nothing to install on anyone's computer", "The AI engine still needs one hospital server and a data-privacy review"],
    ["**Too expensive**", "Free, open-source AI models; low-cost app platform", "Yearly cost not yet written down"],
  ], [0.26, 0.40, 0.34]),
  pageBreak(),
];

const appendix = [
  H2("Appendix A · Every timed run (developer pilot, 18 Oct, final app version)"),
  ...grid(["Patient (public RIDER)", "Timepoint", "Active min", "Open min", "Nodules", "Note"], [
    ["RIDER-1225316081", "Baseline", "1", "1", "2", ""],
    ["RIDER-1225316081", "Follow-up 1", "12", "20", "3", "**Excluded:** scan left open while writing messages"],
    ["RIDER-1332496276", "Baseline", "1", "1", "2", ""],
    ["RIDER-1332496276", "Follow-up 1", "1", "1", "2", ""],
    ["RIDER-1500037140", "Baseline", "2", "2", "4", ""],
    ["RIDER-1500037140", "Follow-up 1", "2", "2", "4", ""],
    ["RIDER-1532432635", "Baseline", "2", "2", "5", "incl. 2 rejected"],
    ["RIDER-1532432635", "Follow-up 1", "2", "2", "5", "incl. 1 rejected + 1 not found"],
    ["Included: 7 scans", "", "1–2 (median 2)", "", "2–5", "developer, not a reader"],
  ], [0.22, 0.14, 0.13, 0.11, 0.10, 0.30], { totalLast: true }),
  small("Source: the app's own timer (\"Minutes on scan\" and the approval rows of the edit trail in the Excel export). Active minutes pause after 2 min without input or when the tab is hidden; whole minutes, so \"1\" means roughly 0.5–1.5 min."),
  H3("Appendix B · Daniel's manual baseline (his words, Slack, 18 Oct)"),
  P("Per follow-up scan: loading 1–2 min; re-finding and matching ~10 min per nodule (aligns by bronchi and fissures; slice numbers are unreliable because of breathing); finding new nodules 10–20 min (two passes over 250–400 slices); measuring 2–4 min per nodule; full outline 15–25 min per tumour when needed; recording 3–5 min; total 40–55 min. His log (\"Minutes on scan\", last 5 rows): baseline 38, 49, 30, 37; follow-up 55. About two-thirds of incoming scans are follow-ups (his estimate)."),
  H3("Appendix C · Technical method"),
  bullet("**Finding:** TotalSegmentator lung_nodules (nnU-Net, ~1,350 training CTs partly from LIDC-IDRI, not RIDER; Apache-2.0) at full settings, on a free Colab T4 GPU (median 49 s per scan). Lobes: TotalSegmentator total."),
  bullet("**Outline:** the model's core plus a rim scaled to the core's size (shipped setting). Compared first with the model's own outline and MedSAM 2; four rim variants compared on the 52 tumours."),
  bullet("**Measurements:** long axis = longest diameter on the slice where it is largest; short axis = longest perpendicular on that slice; volume from the 3D outline; lobe = majority lobe."),
  bullet("**Matching:** affine lung registration (SimpleITK) + Hungarian pairing, gate max(10 mm, 0.75 × long axis)."),
  bullet("**Expert yardstick:** median absolute difference between the expert's manual outlines on the two scans of each patient (28 patients)."),
  bullet("**\"AI unsure about the edges\":** mean model probability over the outline below 0.6, or the rim would grow the long axis by 4 mm or more."),
  H3("Appendix D · Raw data and reproduction"),
  P("All in the engine repository, results/: finding_exam_all59.csv, finding_exam_matching.csv, halo_variants_found52.csv (shipped setting = scaled_*), small_nodule_repeatability.csv, expert_baseline.csv, central_check_blob_all59.csv, faint_flag_candidates.csv, daniel_steps.csv, time_log.csv. python results/make_figures.py rebuilds every figure and prints every number in this report. Data: RIDER Lung CT (Zhao et al., 2015) and RIDER-LungCT-Seg (Wee et al., 2020), The Cancer Imaging Archive.", { size: 17 }),
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
    children: [...page1, ...page2, ...page3, ...page4, ...page5, ...appendix],
  }],
});

Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(OUT, buf); console.log(OUT); });
