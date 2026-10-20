"""README.md -> motor-measurements.pdf via Edge headless. Run build_figures.py first."""
import re
import subprocess
import sys
from pathlib import Path

import markdown

HERE = Path(__file__).resolve().parent
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

body = markdown.markdown((HERE / "README.md").read_text(encoding="utf-8"), extensions=["tables", "fenced_code"])
body = body.replace('src="img/', f'src="{HERE.as_uri()}/img/')
body = body.replace('<a href="motor-measurements.pdf">motor-measurements.pdf</a>', "this document")
# keep each step heading with its text and figure
body = re.sub(r'(<h2>Step [^<]*</h2>\s*<p>[^<]*(?:<(?!img|/p)[^>]*>[^<]*)*</p>\s*(?:<p>)?<img[^>]*>(?:</p>)?)',
              r'<div class="keep">\1</div>', body)
body = body.replace("<h2>Results form</h2>", '<h2 class="pb">Results form</h2>')
css = """
@page { size: A4; margin: 14mm 13mm 15mm; }
body { font-family: 'Segoe UI', Arial, sans-serif; font-size: 10.4pt; color: #1d2b33; line-height: 1.5; }
h1 { color: #124A5A; font-size: 20pt; margin: 0 0 8px; border-bottom: 3px solid #F2B33D; padding-bottom: 8px; }
h2 { color: #124A5A; font-size: 14pt; margin: 16px 0 6px; break-after: avoid; }
table { border-collapse: collapse; width: 100%; margin: 8px 0 12px; font-size: 9.4pt; }
th { background: #124A5A; color: #fff; text-align: left; padding: 5px 7px; }
td { border-bottom: 1px solid #DCE3E6; padding: 4px 7px; vertical-align: top; }
tr { break-inside: avoid; }
tr:nth-child(even) td { background: #F4F7F9; }
img { width: 100%; display: block; margin: 8px 0; border: 1px solid #DCE3E6; border-radius: 6px; break-inside: avoid; }
.keep { break-inside: avoid; }
ol, ul { margin: 4px 0 8px; }
code { background: #F4F7F9; padding: 1px 4px; border-radius: 3px; font-size: 9pt; }
pre { background: #F4F7F9; border: 1px solid #DCE3E6; border-radius: 6px; padding: 10px; font-size: 8.4pt; line-height: 1.65; white-space: pre-wrap; }
pre code { background: none; padding: 0; }
hr { border: 0; border-top: 1px solid #DCE3E6; margin: 12px 0; }
.pb { break-before: page; }
"""
html = (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Motor measurements</title>'
        f"<style>{css}</style></head><body>{body}</body></html>")
tmp = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE
(tmp / "motor-tests.html").write_text(html, encoding="utf-8")
pdf = HERE / "motor-measurements.pdf"
subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--allow-file-access-from-files", "--no-pdf-header-footer",
                f"--print-to-pdf={pdf}", (tmp / "motor-tests.html").as_uri()], check=True, capture_output=True)
print(pdf, pdf.stat().st_size)
