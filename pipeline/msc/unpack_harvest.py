#!/usr/bin/env python3
"""Unpack msc-harvest__*.json.gz bundles (browser harvest) into data-source/msc/.

Run from the repo root:   python3 pipeline/msc/unpack_harvest.py [downloads_dir]

Scans ~/Downloads (or the given dir) for files named
    msc-harvest__<slug>__YYYYMMDD[-vN][-suffix].json.gz
For each slug it applies bundles in version order (v1 first, later versions
overwrite/extend), writes per-ship folders and a fleet manifest:

    data-source/msc/<slug>/page.html          latest ship page HTML (legend source)
    data-source/msc/<slug>/svg/<file>.svg     one per deck
    data-source/msc/<slug>/meta.json          urls, versions, harvest timestamps
    data-source/msc/manifest.json             fleet summary

Stdlib only. Does not delete anything from Downloads.
"""
import glob
import gzip
import json
import os
import re
import sys

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data-source", "msc")
CABIN_RE = re.compile(r'id="cabin(\w+)"')
NAME_RE = re.compile(r"msc-harvest__(?P<slug>[a-z0-9-]+)__(?P<date>\d{8})(?:-v(?P<v>\d+))?(?:-(?P<sfx>[\w-]+))?\.json\.gz$")


def bundles(downloads):
    found = {}
    for p in glob.glob(os.path.join(downloads, "msc-harvest__*.json.gz")):
        m = NAME_RE.search(os.path.basename(p))
        if not m:
            continue
        slug = m.group("slug")
        ver = int(m.group("v") or 1)
        found.setdefault(slug, []).append((ver, p))
    for slug in found:
        found[slug].sort()
    return found


def main():
    downloads = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/Downloads")
    per_slug = bundles(downloads)
    if not per_slug:
        sys.exit("no msc-harvest__*.json.gz files found in " + downloads)
    manifest = {"unpacked_from": downloads, "ships": []}
    for slug in sorted(per_slug):
        ship_dir = os.path.join(OUT, slug)
        svg_dir = os.path.join(ship_dir, "svg")
        os.makedirs(svg_dir, exist_ok=True)
        meta = {"slug": slug, "bundles": [], "urls": []}
        for ver, path in per_slug[slug]:
            data = json.loads(gzip.open(path, "rt", encoding="utf-8").read())
            meta["bundles"].append({"file": os.path.basename(path), "version": ver,
                                    "harvested": data.get("harvested")})
            if data.get("page_html"):
                open(os.path.join(ship_dir, "page.html"), "w").write(data["page_html"])
            for u in data.get("urls", []):
                if u not in meta["urls"]:
                    meta["urls"].append(u)
            for fname, content in data.get("svgs", {}).items():
                if isinstance(content, str) and content.startswith("__HTTP"):
                    continue  # recorded fetch failure, skip
                open(os.path.join(svg_dir, fname), "w").write(content)
        # count
        decks, cabins = 0, set()
        for f in sorted(os.listdir(svg_dir)):
            text = open(os.path.join(svg_dir, f), encoding="utf-8", errors="replace").read()
            ids = set(CABIN_RE.findall(text))
            if ids:
                decks += 1
            cabins |= {f + ":" + i for i in ids}  # unique per deck file
        row = {"slug": slug, "deck_files": len(os.listdir(svg_dir)), "cabin_decks": decks,
               "cabins": len(cabins), "bundles": len(per_slug[slug])}
        meta.update(row)
        json.dump(meta, open(os.path.join(ship_dir, "meta.json"), "w"), indent=1)
        manifest["ships"].append(row)
        print("%-22s files:%-3s cabin-decks:%-3s cabins:%-5s (from %s bundle%s)" % (
            slug, row["deck_files"], decks, row["cabins"],
            row["bundles"], "" if row["bundles"] == 1 else "s"))
    total = sum(s["cabins"] for s in manifest["ships"])
    manifest["total_cabins"] = total
    json.dump(manifest, open(os.path.join(OUT, "manifest.json"), "w"), indent=1)
    print("\n%d ships, %d cabins -> data-source/msc/ (+ manifest.json)" % (len(manifest["ships"]), total))


if __name__ == "__main__":
    main()
