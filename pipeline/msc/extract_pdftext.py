#!/usr/bin/env python3
"""Extract positioned text from the MSC deck-plan PDFs.

Run from the repo root:   python3 pipeline/msc/extract_pdftext.py

Requires PyMuPDF (the one non-stdlib dev dependency in this pipeline):
    pip3 install pymupdf --break-system-packages    # or: pip3 install --user pymupdf

Reads data-source/msc/pdf/<slug>.pdf (from unpack_pdfs.py) and writes
pipeline/msc/msc_pdftext.json.gz — per ship, per page: every word with its
centre coordinates. This is the committed artefact feeding venue-zone
drafting, category identification (e.g. the World-class #003891), and cabin
count reconciliation; the PDFs themselves stay out of git.
"""
import gzip
import json
import os
import sys

try:
    import fitz  # PyMuPDF
except ImportError:
    sys.exit("PyMuPDF missing — run: pip3 install pymupdf --break-system-packages")

HERE = os.path.dirname(os.path.abspath(__file__))
PDF_DIR = os.path.join(HERE, "..", "..", "data-source", "msc", "pdf")
OUT = os.path.join(HERE, "msc_pdftext.json.gz")

fleet = {}
for fname in sorted(os.listdir(PDF_DIR)):
    if not fname.endswith(".pdf"):
        continue
    slug = fname[:-4]
    doc = fitz.open(os.path.join(PDF_DIR, fname))
    pages = []
    nwords = 0
    for page in doc:
        words = []
        for x0, y0, x1, y1, w, *_ in page.get_text("words"):
            words.append([round((x0 + x1) / 2, 1), round((y0 + y1) / 2, 1), w])
        pages.append({"n": page.number, "wpx": round(page.rect.width, 1),
                      "hpx": round(page.rect.height, 1), "words": words})
        nwords += len(words)
    fleet[slug] = {"pages": pages}
    print("%-22s pages:%-3d words:%d" % (slug, len(pages), nwords))
    doc.close()

with gzip.open(OUT, "wt", encoding="utf-8") as f:
    json.dump(fleet, f)
print("\n-> %s (%.1f MB)" % (os.path.relpath(OUT), os.path.getsize(OUT) / 1048576))
