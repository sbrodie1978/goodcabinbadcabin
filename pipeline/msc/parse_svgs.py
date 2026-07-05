#!/usr/bin/env python3
"""MSC extraction: deck SVGs + page legends -> msc_extracted.json

Run from anywhere:   python3 pipeline/msc/parse_svgs.py

Reads data-source/msc/<slug>/{page.html,svg/*.svg}, emits
pipeline/msc/msc_extracted.json (gitignored transient) with, per ship:
  legend:  colour -> [{group, slug, name}, ...]
  decks:   deck number -> filename
  cabins:  [{num, deck, x, y, w, h, fill, cats:[slug,...]}, ...]
Prints a validation table (cabins, category resolution, unknown fills).
Stdlib only.
"""
import json
import os
import re
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "..", "data-source", "msc")
OUT = os.path.join(HERE, "msc_extracted.json")

LEGEND_LI_RE = re.compile(r'<li id="([^"]+\|[^"]+\|#[0-9A-Fa-f]{6})">\s*<span[^>]*></span>\s*([^<]+?)\s*</li>')
GUID_RE = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
HEX_RE = re.compile(r'^#[0-9A-Fa-f]{6}$')

SHIP_CLASS = {
    "msc-armonia": "lirica", "msc-lirica": "lirica", "msc-opera": "lirica", "msc-sinfonia": "lirica",
    "msc-musica": "musica", "msc-orchestra": "musica", "msc-poesia": "musica", "msc-magnifica": "musica",
    "msc-fantasia": "fantasia", "msc-splendida": "fantasia", "msc-divina": "fantasia", "msc-preziosa": "fantasia",
    "msc-meraviglia": "meraviglia", "msc-bellissima": "meraviglia", "msc-grandiosa": "meraviglia",
    "msc-virtuosa": "meraviglia", "msc-euribia": "meraviglia",
    "msc-seaside": "seaside", "msc-seaview": "seaside",
    "msc-seashore": "seaside-evo", "msc-seascape": "seaside-evo",
    "msc-world-europa": "world", "msc-world-america": "world", "msc-world-asia": "world",
}
DECKNUM_RE = re.compile(r'(?:^|_)(?:deck_)?(\d{1,2})(?:_|\.svg$)')
NUM_TOKEN = re.compile(r'-?\d+(?:\.\d+)?')


def localname(tag):
    return tag.rsplit("}", 1)[-1]


def parse_legend(html):
    legend = {}
    for raw_id, name in LEGEND_LI_RE.findall(html):
        parts = raw_id.split("|")
        if len(parts) != 3 or not HEX_RE.match(parts[2]):
            continue
        group = GUID_RE.sub("", parts[0])
        legend.setdefault(parts[2].upper(), []).append(
            {"group": group, "slug": parts[1], "name": name.strip()})
    # dedupe identical entries (legend repeats for mobile/desktop)
    for c in legend:
        seen, uniq = set(), []
        for e in legend[c]:
            k = e["group"] + "|" + e["slug"]
            if k not in seen:
                seen.add(k)
                uniq.append(e)
        legend[c] = uniq
    return legend


def bbox_of(el):
    k = localname(el.tag)
    if k == "rect":
        try:
            x, y = float(el.get("x", 0)), float(el.get("y", 0))
            w, h = float(el.get("width", 0)), float(el.get("height", 0))
            return x, y, w, h
        except (TypeError, ValueError):
            return None
    pts = el.get("points") if k == "polygon" else el.get("d") if k == "path" else None
    if not pts:
        return None
    nums = [float(n) for n in NUM_TOKEN.findall(pts)]
    if len(nums) < 4:
        return None
    xs, ys = nums[0::2], nums[1::2]
    return min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)


def fill_of(el):
    f = el.get("fill")
    if not f:
        m = re.search(r'fill:\s*(#[0-9A-Fa-f]{3,6})', el.get("style", ""))
        f = m.group(1) if m else None
    if f and re.match(r"^#[0-9A-Fa-f]{3}$", f):  # #abc -> #aabbcc
        f = "#" + "".join(c * 2 for c in f[1:])
    return f.upper() if f and HEX_RE.match(f) else None


def rgb(c):
    return int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)


def nearest_legend(fill, legend, maxdist=42):
    if not HEX_RE.match(fill or ""):
        return None
    fr = rgb(fill)
    best, bd = None, maxdist + 1
    for c in legend:
        cr = rgb(c)
        d = max(abs(fr[i] - cr[i]) for i in range(3))
        if d < bd:
            bd, best = d, c
    return best


def deck_number(fname):
    m = DECKNUM_RE.search(fname)
    return int(m.group(1)) if m else None


def parse_ship(slug, class_legend=None):
    ship_dir = os.path.join(SRC, slug)
    html = open(os.path.join(ship_dir, "page.html"), encoding="utf-8", errors="replace").read()
    legend = parse_legend(html)
    cabins, decks = [], {}
    unknown_fills = {}
    for fname in sorted(os.listdir(os.path.join(ship_dir, "svg"))):
        deck = deck_number(fname)
        try:
            root = ET.parse(os.path.join(ship_dir, "svg", fname)).getroot()
        except ET.ParseError as e:
            print("  ! %s/%s: XML parse error: %s" % (slug, fname, e))
            continue
        n_before = len(cabins)
        for el in root.iter():
            eid = el.get("id", "")
            if not eid.startswith("cabin") or localname(el.tag) == "g":
                continue
            num = eid[5:]
            bb = bbox_of(el)
            if bb is None:
                continue
            fill = fill_of(el)
            key = fill if fill in legend else nearest_legend(fill, legend) if fill else None
            entries = legend.get(key, [])
            if not entries and fill and class_legend:
                key = fill if fill in class_legend else nearest_legend(fill, class_legend)
                entries = class_legend.get(key, [])
            cats = [e["slug"] for e in entries]
            grps = sorted({e["group"] for e in entries})
            if fill and not cats:
                unknown_fills[fill] = unknown_fills.get(fill, 0) + 1
            cabins.append({"num": num, "deck": deck, "file": fname,
                           "x": round(bb[0], 2), "y": round(bb[1], 2),
                           "w": round(bb[2], 2), "h": round(bb[3], 2),
                           "fill": fill, "cats": cats, "grp": grps})
        if len(cabins) > n_before:
            decks[str(deck)] = fname
    return {"slug": slug, "legend": legend, "decks": decks,
            "cabins": cabins, "unknown_fills": unknown_fills}


def main():
    slugs = sorted(d for d in os.listdir(SRC) if os.path.isdir(os.path.join(SRC, d)))
    # first pass: every ship's own legend, pooled per class for fallback
    class_legend = {}
    for slug in slugs:
        html = open(os.path.join(SRC, slug, "page.html"), encoding="utf-8", errors="replace").read()
        cl = class_legend.setdefault(SHIP_CLASS.get(slug, "?"), {})
        for colour, entries in parse_legend(html).items():
            pool = cl.setdefault(colour, [])
            for e in entries:
                if not any(p["group"] == e["group"] and p["slug"] == e["slug"] for p in pool):
                    pool.append(e)
    fleet = {}
    print("%-22s %-6s %-7s %-9s %-9s %-6s %s" % (
        "ship", "decks", "cabins", "slug-ok", "grp-ok", "nocat", "unknown fills"))
    for slug in slugs:
        s = parse_ship(slug, class_legend.get(SHIP_CLASS.get(slug, "?")))
        fleet[slug] = s
        n = len(s["cabins"])
        res = sum(1 for c in s["cabins"] if len(c["cats"]) == 1)
        grp = sum(1 for c in s["cabins"] if c["grp"])
        noc = n - grp
        uf = ",".join("%s:%d" % kv for kv in sorted(s["unknown_fills"].items())) or "-"
        print("%-22s %-6d %-7d %-9s %-9s %-6d %s" % (
            slug, len(s["decks"]), n,
            "%d(%d%%)" % (res, round(100.0 * res / n) if n else 0),
            "%d(%d%%)" % (grp, round(100.0 * grp / n) if n else 0), noc, uf))
    json.dump(fleet, open(OUT, "w"))
    total = sum(len(s["cabins"]) for s in fleet.values())
    print("\n%d ships, %d cabins -> %s (%.1f MB)" % (
        len(fleet), total, os.path.relpath(OUT), os.path.getsize(OUT) / 1048576))


if __name__ == "__main__":
    main()
