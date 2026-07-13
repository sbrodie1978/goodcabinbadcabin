#!/usr/bin/env python3
"""Generate MSC deck-plan geometry: app/public/msc/data/ship-<id>-plan.json

The shared frontend's "Deck plan" view fetches a per-ship plan file separate
from the score payload:

    {decks: {"<deck>": {w, h, cab: {"<num>": [x0,y0,x1,y1,x2,y2,x3,y3]}}}}

Each cabin is a rectangle (from its SVG bounding box) in a per-DECK frame set
by that deck's hull outline (#ship / #ingombro), so every deck maps to a
consistent canvas at true ship proportions regardless of the deck SVG's native
scale -- and any cabin whose geometry falls outside the hull is clipped rather
than blowing up the canvas. Orientation matches the view's labels: forward at
the LEFT (bow is high-x in the SVG, so x is flipped), port at the TOP (port =
odd numbers = low y, so y is kept). Run from repo root:

    python3 pipeline/msc/msc_plan.py
Stdlib only.
"""
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
from msc_categories import MSC_META, SHIP_ORDER

_ROOT = os.path.dirname(os.path.dirname(_HERE))
_DATA = os.path.join(_ROOT, "app", "public", "msc", "data")
_SRC = os.path.join(_ROOT, "data-source", "msc")
EXTRACT = os.path.join(_HERE, "msc_extracted.json")
NUM = re.compile(r'-?\d+(?:\.\d+)?')


def _ln(t):
    return t.rsplit("}", 1)[-1]


def hull_bbox(path):
    root = ET.parse(path).getroot()
    hull = None
    for e in root.iter():
        if e.get("id") in ("ship", "ingombro"):
            hull = e
            break
    if hull is None:
        return None
    xs, ys = [], []
    for e in hull.iter():
        if _ln(e.tag) == "rect":
            x, y = float(e.get("x", 0)), float(e.get("y", 0))
            w, h = float(e.get("width", 0)), float(e.get("height", 0))
            xs += [x, x + w]; ys += [y, y + h]
        if _ln(e.tag) == "line":
            xs += [float(e.get("x1", 0)), float(e.get("x2", 0))]
            ys += [float(e.get("y1", 0)), float(e.get("y2", 0))]
        for a in ("points", "d"):
            if e.get(a):
                n = [float(v) for v in NUM.findall(e.get(a))]
                xs += n[0::2]; ys += n[1::2]
    return (min(xs), max(xs), min(ys), max(ys)) if xs else None


def build_plan(slug, ship):
    cabs = [c for c in ship["cabins"] if c.get("b") is not None]
    by_deck = {}
    for c in cabs:
        by_deck.setdefault(str(c["deck"]), []).append(c)
    decks = {}
    for d, dcabs in by_deck.items():
        fname = ship["decks"].get(d) or dcabs[0]["file"]
        hb = hull_bbox(os.path.join(_SRC, slug, "svg", fname))
        if hb is None:
            xs = [c["x"] for c in dcabs] + [c["x"] + c["w"] for c in dcabs]
            ys = [c["y"] for c in dcabs] + [c["y"] + c["h"] for c in dcabs]
            hb = (min(xs), max(xs), min(ys), max(ys))
        hx0, hx1, hy0, hy1 = hb
        W = round(hx1 - hx0, 1)
        H = round(hy1 - hy0, 1)
        cab = {}
        for c in dcabs:
            x, y, w, h = c["x"], c["y"], c["w"], c["h"]
            cx0, cx1 = max(x, hx0), min(x + w, hx1)
            cy0, cy1 = max(y, hy0), min(y + h, hy1)
            if cx1 <= cx0 or cy1 <= cy0:
                continue
            xl = round(hx1 - cx1, 1)
            xr = round(hx1 - cx0, 1)
            yt = round(cy0 - hy0, 1)
            yb = round(cy1 - hy0, 1)
            cab[c["num"]] = [xl, yt, xr, yt, xr, yb, xl, yb]
        decks[d] = {"w": W, "h": H, "cab": cab}
    return {"decks": decks}


def main():
    ext = json.load(open(EXTRACT))
    os.makedirs(_DATA, exist_ok=True)
    biggest = 0
    for sid, slug in enumerate(SHIP_ORDER, 1):
        plan = build_plan(slug, ext[slug])
        path = os.path.join(_DATA, f"ship-{sid}-plan.json")
        json.dump(plan, open(path, "w"))
        biggest = max(biggest, os.path.getsize(path))
        if sid <= 2 or sid == len(SHIP_ORDER):
            ncab = sum(len(d["cab"]) for d in plan["decks"].values())
            print(f"  ship-{sid} {MSC_META[slug][0]:22s} {len(plan['decks'])} decks, {ncab} cabins")
    print(f"\n{len(SHIP_ORDER)} plan files -> {os.path.relpath(_DATA)}"
          f" (largest {biggest // 1024} KB)")


if __name__ == "__main__":
    main()
