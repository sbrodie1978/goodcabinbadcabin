#!/usr/bin/env python3
"""Unpack msc-pdfs-all__*.json.gz (browser PDF grab) -> data-source/msc/pdf/<slug>.pdf

Run from the repo root:   python3 pipeline/msc/unpack_pdfs.py [downloads_dir]
PDFs are kept out of git (see .gitignore) — the committed artefact is the
extracted text produced by extract_pdftext.py. Stdlib only.
"""
import base64
import glob
import gzip
import json
import os
import sys

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data-source", "msc", "pdf")

downloads = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/Downloads")
bundles = sorted(glob.glob(os.path.join(downloads, "msc-pdfs-all__*.json.gz")))
if not bundles:
    sys.exit("no msc-pdfs-all__*.json.gz in " + downloads)
data = json.loads(gzip.open(bundles[-1], "rt", encoding="utf-8").read())
os.makedirs(OUT, exist_ok=True)
for slug, b64 in sorted(data["pdfs"].items()):
    path = os.path.join(OUT, slug + ".pdf")
    raw = base64.b64decode(b64)
    open(path, "wb").write(raw)
    print("%-22s %6.2f MB" % (slug, len(raw) / 1048576))
print("\n%d PDFs -> %s (gitignored)" % (len(data["pdfs"]), os.path.relpath(OUT)))
