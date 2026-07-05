#!/usr/bin/env python3
"""MSC deck-plan harvester — downloads official interactive-deckplan SVGs.

Run from the repo root:   python3 pipeline/msc/harvest.py [slugs...] [--force]

For each ship it fetches the msccruises.com ship page, saves the raw HTML,
extracts the per-deck SVG URLs (server-rendered into the page), downloads
them into data-source/msc/<slug>/<version>/, counts cabins per deck, and
writes data-source/msc/manifest.json. Stdlib only. Be polite: sequential,
1s delay between requests.

See HARVEST.md in this folder for the source documentation.
"""
import json
import os
import re
import sys
import time
import urllib.request

BASE = "https://www.msccruises.com"
SHIP_PAGE = BASE + "/int/our-cruises/ships/{slug}"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data-source", "msc")

SLUGS = [
    # Lirica class (may be PDF-only — expect possible gaps, see HARVEST.md)
    "msc-armonia", "msc-lirica", "msc-opera", "msc-sinfonia",
    # Musica class
    "msc-musica", "msc-orchestra", "msc-poesia", "msc-magnifica",
    # Fantasia class
    "msc-fantasia", "msc-splendida", "msc-divina", "msc-preziosa",
    # Meraviglia / Meraviglia-Plus
    "msc-meraviglia", "msc-bellissima", "msc-grandiosa", "msc-virtuosa", "msc-euribia",
    # Seaside / Seaside EVO
    "msc-seaside", "msc-seaview", "msc-seashore", "msc-seascape",
    # World class
    "msc-world-europa", "msc-world-america", "msc-world-asia",
]

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36"}
DELAY = 1.0

SVG_RE = re.compile(r'["\'(]([^"\'()]*?/interactive-deckplan/[^"\'()]*?\.svg)["\')]')
CABIN_RE = re.compile(r'id="cabin(\w+)"')


def get(url, binary=False):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read()
    time.sleep(DELAY)
    return data if binary else data.decode("utf-8", "replace")


def harvest_ship(slug, force=False):
    row = {"slug": slug, "status": "?", "version": None, "decks": 0, "cabins": 0, "files": []}
    ship_dir = os.path.join(OUT, slug)
    os.makedirs(ship_dir, exist_ok=True)
    try:
        html = get(SHIP_PAGE.format(slug=slug))
    except Exception as e:
        row["status"] = "page FAILED: %s" % e
        return row
    open(os.path.join(ship_dir, "page.html"), "w").write(html)

    urls = []
    for m in SVG_RE.finditer(html):
        u = m.group(1)
        if u.startswith("/"):
            u = BASE + u
        if u not in urls:
            urls.append(u)
    if not urls:
        row["status"] = "no interactive deckplan (PDF-only ship?)"
        return row

    versions = {re.search(r"interactive-deckplan/([^/]+)/", u).group(1) for u in urls}
    row["version"] = sorted(versions)[0] if len(versions) == 1 else "MIXED:" + ",".join(sorted(versions))

    total = 0
    for u in urls:
        ver = re.search(r"interactive-deckplan/([^/]+)/", u).group(1)
        fname = u.rsplit("/", 1)[-1]
        vdir = os.path.join(ship_dir, ver)
        os.makedirs(vdir, exist_ok=True)
        path = os.path.join(vdir, fname)
        if force or not os.path.exists(path):
            try:
                svg = get(u, binary=True)
            except Exception as e:
                row["files"].append({"file": fname, "error": str(e)})
                continue
            open(path, "wb").write(svg)
        text = open(path, encoding="utf-8", errors="replace").read()
        n = len(set(CABIN_RE.findall(text)))
        total += n
        row["files"].append({"file": fname, "cabins": n, "bytes": os.path.getsize(path)})
    row["decks"] = len([f for f in row["files"] if "cabins" in f])
    row["cabins"] = total
    row["status"] = "ok"
    return row


def main():
    args = [a for a in sys.argv[1:] if a != "--force"]
    force = "--force" in sys.argv
    slugs = args or SLUGS
    os.makedirs(OUT, exist_ok=True)
    manifest = {"harvested": time.strftime("%Y-%m-%d %H:%M"), "ships": []}
    for slug in slugs:
        row = harvest_ship(slug, force=force)
        manifest["ships"].append(row)
        print("%-22s %-34s decks:%-3s cabins:%-5s %s" % (
            slug, (row["version"] or "-"), row["decks"], row["cabins"], row["status"]))
    json.dump(manifest, open(os.path.join(OUT, "manifest.json"), "w"), indent=1)
    print("\nmanifest -> data-source/msc/manifest.json")


if __name__ == "__main__":
    main()
