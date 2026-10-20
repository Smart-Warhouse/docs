"""README.md (Arabic, RTL) -> warehouse-map-design.pdf, via Edge headless. Run build_figures.py first."""
import subprocess
import sys
from pathlib import Path

import markdown

HERE = Path(__file__).resolve().parent
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

body = markdown.markdown((HERE / "README.md").read_text(encoding="utf-8"), extensions=["tables", "fenced_code"])
base = HERE.as_uri() + "/"
body = body.replace('src="', f'src="{base}')
body = body.replace('<a href="warehouse-map-design.pdf">warehouse-map-design.pdf</a>', "هذا الملف")
css = """
@page { size: A4; margin: 14mm 12mm 15mm; }
body { font-family: 'Segoe UI', Tahoma, Arial, sans-serif; font-size: 10.6pt; color: #1d2b33; line-height: 1.6; direction: rtl; }
h1 { color: #124A5A; font-size: 19pt; margin: 0 0 8px; border-bottom: 3px solid #F2B33D; padding-bottom: 8px; }
h2 { color: #124A5A; font-size: 14.5pt; margin: 18px 0 6px; break-after: avoid; }
h3 { color: #124A5A; font-size: 12pt; margin: 12px 0 4px; break-after: avoid; }
table { border-collapse: collapse; width: 100%; margin: 8px 0 12px; font-size: 9.4pt; }
th { background: #124A5A; color: #fff; text-align: right; padding: 5px 7px; }
td { border-bottom: 1px solid #DCE3E6; padding: 4px 7px; vertical-align: top; }
tr { break-inside: avoid; }
tr:nth-child(even) td { background: #F4F7F9; }
img { max-width: 100%; display: block; margin: 8px auto; border: 1px solid #DCE3E6; border-radius: 6px; break-inside: avoid; }
p:has(img) { break-inside: avoid; }
blockquote { margin: 10px 0; padding: 8px 12px; background: #FFF7E0; border-right: 4px solid #F2B33D; border-left: 0; }
blockquote p { margin: 0; }
code { background: #F4F7F9; padding: 1px 4px; border-radius: 3px; font-size: 9pt; direction: ltr; unicode-bidi: embed; }
hr { border: 0; border-top: 1px solid #DCE3E6; margin: 14px 0; }
a { color: #124A5A; }
.pb { break-before: page; }
.keep { break-inside: avoid; }
.foot { margin-top: 16px; color: #5B6B73; font-size: 8.5pt; }
"""
# page breaks before the big sections so figures do not split awkwardly
import re

# keep a heading, its short intro paragraph and its figure on one page
body = re.sub(r'(<h[23][^>]*>[^<]*</h[23]>\s*(?:<p>[^<]*(?:<(?!img|/p)[^>]*>[^<]*)*</p>\s*)?(?:<p>)?<img[^>]*>(?:</p>)?)',
              r'<div class="keep">\1</div>', body)
for h in ("<h2>4. ", "<h2>6. "):
    body = body.replace(h, h.replace("<h2>", '<h2 class="pb">'), 1)
html = (f'<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><title>خارطة المخزن</title>'
        f"<style>{css}</style></head><body>{body}"
        '<p class="foot">SW·Fleet — مشروع المخزن الذكي · github.com/Smart-Warhouse/docs/warehouse-map</p></body></html>')
tmp = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE
(tmp / "warehouse-map.html").write_text(html, encoding="utf-8")
pdf = HERE / "warehouse-map-design.pdf"
subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--allow-file-access-from-files", "--no-pdf-header-footer",
                f"--print-to-pdf={pdf}", (tmp / "warehouse-map.html").as_uri()], check=True, capture_output=True)
print(pdf, pdf.stat().st_size)
