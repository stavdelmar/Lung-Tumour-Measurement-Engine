"""Build the short results PDF (5 pages + appendix) from results/report/report.html.

RESULTS.md stays the full version in the repo; this PDF is the short, readable one.
Usage (from the repo root):
    python results/make_figures.py          # refresh figures first
    python results/build_pdf.py             # writes results/LungMarker_Results.pdf
Needs: pip install playwright (with a Chromium).
"""
import pathlib
import sys

from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
SRC = HERE / "report" / "report.html"
OUT = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else HERE / "LungMarker_Results.pdf"

FOOTER = ("<div style='font-size:7pt;color:#777;width:100%;text-align:center'>"
          "LungMarker results · research use only · <span class='pageNumber'></span>/<span class='totalPages'></span></div>")

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(SRC.as_uri())
    page.wait_for_load_state("networkidle")
    page.pdf(path=str(OUT), format="A4", print_background=True,
             margin={"top": "14mm", "bottom": "16mm", "left": "14mm", "right": "14mm"},
             display_header_footer=True, header_template="<span></span>", footer_template=FOOTER)
    browser.close()
print(OUT)
