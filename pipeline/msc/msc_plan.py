#!/usr/bin/env python3
"""Generate MSC deck-plan geometry: app/public/msc/data/ship-<id>-plan.json

The shared frontend's "Deck plan" view fetches a per-ship plan file separate
from the score payload:

    {decks: {"<deck>": {w, h, cab: {"<num>": [x0,y0,x1,y1,x2,y2,x3,y3]}}}}

Each cabin is a polygon (here a rectangle from its SVG bounding box) in a
per-ship plan frame: forward at the LEFT, port at the TOP (matching the view's
PORT ▲ / FORWARD ◀ labels). In the raw SVGs bow is at high x and port (odd
numbers) at low y, so we flip x and keep y. Ship-wide extents are used for
every deck so scale is consistent when flipping decks. Run from repo root:

    python3 pipeline/msc/msc_plan.py
Stdlib only.
"""
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
from msc_categories import MSC_META, SHIP_ORDER

_ROOT = os.path.dirname(os.path.dirname(_HERE))
_DATA = os.path.join(_ROOT, "app", "public", "msc", "data")
EXTRACT = os.path.join(_HERE, "msc_extracted.json")


def build_plan(ship):
    cabs = [c for c in ship["cabins"] if c.get("b") is not None]
    xs = [c["x"] for c in cabs] + [c["x"] + c["w"] for c in cabs]
    ys = [c["y"] for c in cabs] + [c["y"] + c["h"] for c in cabs]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    W = round(xmax - xmin, 1)
    H = round(ymax - ymin, 1)
    decks = {}
    for c in cabs:
        d = str(c["deck"])
        x, y, w, h = c["x"], c["y"], c["w"], c["h"]
        # flip x (bow high-x -> forward left), keep y (port low-y -> top)
        xl = round(xmax - (x + w), 1)   # left edge after flip
        xr = round(xmax - x, 1)         # right edge after flip
        yt = round(y - ymin, 1)
        yb = round(y + h - ymin, 1)
        poly = [xl, yt, xr, yt, xr, yb, xl, yb]
        decks.setdefault(d, {"w": W, "h": H, "cab": {}})["cab"][c["num"]] = poly
    return {"decks": decks}


def main():
    ext = json.load(open(EXTRACT))
    os.makedirs(_DATA, exist_ok=True)
    biggest = 0
    for sid, slug in enumerate(SHIP_ORDER, 1):
        plan = build_plan(ext[slug])
        path = os.path.join(_DATA, f"ship-{sid}-plan.json")
        json.dump(plan, open(path, "w"))
        biggest = max(biggest, os.path.getsize(path))
        ndecks = len(plan["decks"])
        ncab = sum(len(d["cab"]) for d in plan["decks"].values())
        if sid <= 2 or sid == len(SHIP_ORDER):
            print(f"  ship-{sid} {MSC_META[slug][0]:22s} {ndecks} decks, {ncab} cabins")
    print(f"\n{len(SHIP_ORDER)} plan files -> {os.path.relpath(_DATA)}"
          f" (largest {biggest // 1024} KB)")


if __name__ == "__main__":
    main()
