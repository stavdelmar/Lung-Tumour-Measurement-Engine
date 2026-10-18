"""Build RESULTS.pdf from RESULTS.md (same text and figures).
Usage: python results/build_pdf.py . RESULTS.pdf   (needs: pip install markdown playwright; a Chromium)
"""
import sys, re, markdown, pathlib
from playwright.sync_api import sync_playwright
repo = pathlib.Path(sys.argv[1]); out = pathlib.Path(sys.argv[2])
md = (repo / "RESULTS.md").read_text()
# Python-Markdown needs a blank line before a list; GitHub doesn't. Add one where a list follows a text line.
lines, fixed = md.split("\n"), []
for i, ln in enumerate(lines):
    is_item = re.match(r"^\s*([-*]|\d+\.)\s", ln)
    prev = fixed[-1] if fixed else ""
    if is_item and prev.strip() and not re.match(r"^\s*([-*]|\d+\.)\s", prev):
        fixed.append("")
    fixed.append(ln)
md = "\n".join(fixed)
# in-page anchors only; image paths absolute
html_body = markdown.markdown(md, extensions=["tables", "toc", "sane_lists"])
html_body = html_body.replace('<h2 id="why-this-differs-from-last-years-tool">', '<h2 id="why-this-differs-from-last-years-tool" style="break-before: page">')
html_body = html_body.replace('src="results/', f'src="file://{repo}/results/')
css = """

body { font-family: 'Inter','Helvetica Neue',Arial,sans-serif; font-size: 9.6pt; line-height: 1.45; color: #0b0b0b; }
h1 { font-size: 20pt; margin: 0 0 4pt; }
h2 { break-before: auto; font-size: 13.5pt; margin: 16pt 0 6pt; padding-bottom: 3pt; border-bottom: 1px solid #e6e5e1; page-break-after: avoid; }
h3 { font-size: 11pt; margin: 12pt 0 4pt; page-break-after: avoid; }
p, li { orphans: 3; widows: 3; }
blockquote { margin: 6pt 0 8pt; padding: 6pt 10pt; background: #eef4fc; border-left: 3px solid #2a78d6; }
blockquote p { margin: 0; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0 10pt; font-size: 8.3pt; page-break-inside: auto; }
tr { page-break-inside: avoid; }
th, td { border: 1px solid #dddcd7; padding: 3pt 5pt; vertical-align: top; text-align: left; }
th { background: #f3f2ef; }
img { max-width: 100%; margin: 6pt 0; page-break-inside: avoid; }
hr { border: 0; border-top: 1px solid #e6e5e1; margin: 12pt 0; }
code { font-size: 8.3pt; background: #f3f2ef; padding: 0 2pt; border-radius: 2px; }
a { color: #1c5cab; text-decoration: none; }
"""
html = f"<!doctype html><html><head><meta charset='utf-8'><style>{css}</style></head><body>{html_body}</body></html>"
tmp = out.with_suffix(".html"); tmp.write_text(html)
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page()
    pg.goto(f"file://{tmp}")
    pg.wait_for_load_state("networkidle")
    pg.pdf(path=str(out), format="A4", print_background=True,
           margin={"top": "16mm", "bottom": "18mm", "left": "14mm", "right": "14mm"},
           display_header_footer=True, header_template="<span></span>",
           footer_template="<div style='font-size:7pt;color:#777;width:100%;text-align:center'>LungMarker results · research use only · <span class='pageNumber'></span>/<span class='totalPages'></span></div>")
    b.close()
print(out)
