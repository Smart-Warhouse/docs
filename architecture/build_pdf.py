"""README.md -> system-architecture.pdf via Edge headless. Diagrams are the SVGs from figures.py (run it first);
photos are in img/photos. No network needed."""
import re
import subprocess
import sys
from pathlib import Path

import markdown

HERE = Path(__file__).resolve().parent
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

src = (HERE / "README.md").read_text(encoding="utf-8")
body = markdown.markdown(src, extensions=["tables", "fenced_code"])
body = body.replace('src="img/', f'src="{HERE.as_uri()}/img/')
body = body.replace('<a href="system-architecture.pdf">system-architecture.pdf</a>', "this document")
for h in ("<h2>3. ", "<h2>5. ", "<h2>6. ", "<h2>7. ", "<h2>9. ", "<h2>10. ", "<h2>11. "):
    body = body.replace(h, h.replace("<h2>", '<h2 class="pb">'), 1)

css = """
@page { size: A4; margin: 14mm 13mm 15mm; }
body { font-family: 'Segoe UI', Arial, sans-serif; font-size: 10.2pt; color: #1d2b33; line-height: 1.5; }
h1 { color: #124A5A; font-size: 20pt; margin: 0 0 8px; border-bottom: 3px solid #F2B33D; padding-bottom: 8px; }
h2 { color: #124A5A; font-size: 14.5pt; margin: 18px 0 6px; break-after: avoid; }
h3 { color: #124A5A; font-size: 12pt; margin: 12px 0 4px; break-after: avoid; }
table { border-collapse: collapse; width: 100%; margin: 8px 0 12px; font-size: 9pt; }
th { background: #124A5A; color: #fff; text-align: left; padding: 5px 7px; }
td { border-bottom: 1px solid #DCE3E6; padding: 4px 7px; vertical-align: top; }
tr { break-inside: avoid; }
tr:nth-child(even) td { background: #F4F7F9; }
img { max-width: 100%; display: block; margin: 8px auto; break-inside: avoid; }
p[align="center"] { text-align: center; margin: 8px 0 2px; break-inside: avoid; }
p[align="center"] img { display: inline-block; box-sizing: border-box; margin: 3px 0.4%; border: 1px solid #DCE3E6; border-radius: 6px; vertical-align: top; }
img[alt="ROS 2 node graph"] { width: 88%; }
.cap { text-align: center; color: #5B6B73; font-size: 8.8pt; margin: 2px 6% 12px; break-before: avoid; }
code { background: #F4F7F9; padding: 1px 4px; border-radius: 3px; font-size: 8.8pt; }
hr { border: 0; border-top: 1px solid #DCE3E6; margin: 14px 0; }
a { color: #124A5A; }
.pb { break-before: page; }
.foot { margin-top: 16px; color: #5B6B73; font-size: 8.5pt; }
"""
page = (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>System architecture</title>'
        f'<style>{css}</style>'
        f'</head><body>{body}'
        '</body></html>')
tmp = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE
(tmp / "architecture.html").write_text(page, encoding="utf-8")
pdf = HERE / "system-architecture.pdf"
subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--allow-file-access-from-files", "--no-pdf-header-footer",
                "--virtual-time-budget=5000",
                f"--print-to-pdf={pdf}", (tmp / "architecture.html").as_uri()], check=True, capture_output=True)
print(pdf, pdf.stat().st_size)
