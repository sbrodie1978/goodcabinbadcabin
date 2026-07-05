#!/usr/bin/env python3
"""Generate the MSC app HTML from the SHARED frontend template.

Imports the HTML template constant from pipeline/build_frontend.py (the single
source of truth for the GCBC app design) and re-skins the line-specific tokens
for MSC, then writes app/public/msc/index.html. Design edits live in
build_frontend.py and flow to both lines; this file only swaps MSC strings +
the picker's class ordering. Run from the repo root:

    python3 pipeline/msc/msc_frontend.py
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_PIPE = os.path.dirname(_HERE)
_ROOT = os.path.dirname(_PIPE)
sys.path.insert(0, _PIPE)
from build_frontend import HTML

DATA = open(os.path.join(_HERE, "fleet_meta_msc.json")).read()

# MSC class ordering for the picker (most specific substrings first so
# "Seaside EVO" resolves before "Seaside").
MSC_CLASSORDER = '["World","Seaside EVO","Seaside","Meraviglia","Fantasia","Musica","Lirica"]'

html = HTML.replace("__DATA__", DATA)
html = html.replace(
    "Good Cabin Bad Cabin — Princess Cruises cabin ratings",
    "Good Cabin Bad Cabin — MSC Cruises cabin ratings")
html = html.replace(
    "<span>PRINCESS CRUISES</span>", "<span>MSC CRUISES</span>")
html = html.replace(
    "not affiliated with or endorsed by Princess Cruises or any cruise line",
    "not affiliated with or endorsed by MSC Cruises or any cruise line")
html = html.replace(
    'const CLASSORDER=["Sphere","Royal","Grand","Coral"];',
    f'const CLASSORDER={MSC_CLASSORDER};')

_OUT = os.path.join(_ROOT, "app", "public", "msc", "index.html")
os.makedirs(os.path.dirname(_OUT), exist_ok=True)
open(_OUT, "w").write(html)
# sanity: no Princess strings leaked into the MSC build
leaks = [t for t in ("Princess Cruises", "PRINCESS CRUISES",
                     '"Sphere","Royal"') if t in html]
print("written:", os.path.getsize(_OUT) // 1024, "KB ->", _OUT)
print("leak check:", "CLEAN" if not leaks else "LEAKS: " + ", ".join(leaks))
