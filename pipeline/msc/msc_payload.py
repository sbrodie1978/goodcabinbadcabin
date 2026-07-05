#!/usr/bin/env python3
"""Build the MSC web payload: app/public/msc/data/ship-<id>.json + fleet_meta_msc.json

Adapts pipeline/make_payload.py. Emits the same row schema the shared frontend
reads, INCLUDING the core cabin `type` at index 18 (so MSC gets working
category filtering + per-type ranking):

  [num, deck, side, b, quiet, stab, conv, cat, conf, above, below, notes,
   sqft, berths, catname, space, colour, surround, type]

sqft (12) and berths (13) are null for MSC (no such source data). `surround`
(17) is the four-cell cross-section [above, below, fore, aft], each cell
[label, colour, kind]. Stdlib only.
"""
import json
import os
from collections import defaultdict

import sys
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
from msc_categories import MSC_META, SHIP_ORDER, CLASS_DISPLAY

_ROOT = os.path.dirname(os.path.dirname(_HERE))
_DATA = os.path.join(_ROOT, "app", "public", "msc", "data")
SCORED = os.path.join(_HERE, "msc_scored.json")

ZONE_VIS = {
    "venue_entertainment": ("#b0446a", "Entertainment venue"),
    "galley_buffet": ("#c98a2b", "Buffet / galley"),
    "pool_deck": ("#3a8fc4", "Pool deck"),
    "kids_play": ("#7bad3a", "Kids / play area"),
    "dining": ("#c46a3a", "Dining"),
    "public_general": ("#8a8f9a", "Public area"),
    "open_deck": ("#6fae62", "Open deck / air"),
    "crew_service": ("#7a6f5a", "Service area"),
    "unknown_noncabin": ("#9aa0a8", "Non-cabin space"),
    "cabins": ("#cfd6cf", "Other cabins"),
}


def surround(rows):
    idx = {r["cabin"]: r for r in rows}
    lanes = defaultdict(list)
    for r in rows:
        lanes[(r["deck"], r["side"])].append(r)
    for k in lanes:
        lanes[k].sort(key=lambda r: r["b"])
    out = {}
    for r in rows:
        lane = lanes[(r["deck"], r["side"])]
        i = lane.index(r)
        fwd = lane[i - 1] if i > 0 else None
        aft = lane[i + 1] if i < len(lane) - 1 else None

        def cell_updown(is_cabin, desc, zclass):
            if is_cabin:
                nb = desc.split(" (")[0]
                col = "#" + (idx[nb]["category_color"] if nb in idx else "cfd6cf")
                return [nb, col, "cabin"]
            col, _ = ZONE_VIS.get(zclass or "unknown_noncabin", ZONE_VIS["unknown_noncabin"])
            return [desc, col, "venue"]

        def side_cell(nb):
            if nb:
                return [nb["cabin"], "#" + nb["category_color"], "cabin"]
            return ["end of row", "#e8e4dc", "end"]

        out[r["cabin"]] = [
            cell_updown(r["cabin_above"], r["above_desc"], r["above_class"]),
            cell_updown(r["cabin_below"], r["below_desc"], r["below_class"]),
            side_cell(fwd), side_cell(aft)]
    return out


def main():
    fleet = json.load(open(SCORED))
    os.makedirs(_DATA, exist_ok=True)
    slim = []
    for sid, slug in enumerate(SHIP_ORDER, 1):
        rows = fleet[slug]
        disp, gt, cls = MSC_META[slug]
        decks = sorted(set(r["deck"] for r in rows), key=int, reverse=True)
        sur = surround(rows)
        data = []
        for r in rows:
            data.append([
                r["cabin"], r["deck"], r["side"], r["b"], r["quiet"],
                r["stability"], r["convenience"], r["category"],
                r["category_confidence"], r["above_desc"], r["below_desc"],
                r["quiet_notes"], None, None, r["category_name"], r["space"],
                "#" + r["category_color"], sur[r["cabin"]], r["type"]])
        slim.append({
            "id": sid, "line": f"MSC Cruises · {CLASS_DISPLAY[cls]} class",
            "name": disp,
            "spec": f"{gt:,} GT · {len(rows):,} STATEROOMS · OFFICIAL DATA",
            "decks": decks, "numstyle": "sphere", "data": data, "cls": cls})

    meta = []
    for s in slim:
        json.dump(s["data"], open(os.path.join(_DATA, f"ship-{s['id']}.json"), "w"))
        meta.append({k: v for k, v in s.items() if k != "data"})
    json.dump(meta, open(os.path.join(_HERE, "fleet_meta_msc.json"), "w"))
    biggest = max(os.path.getsize(os.path.join(_DATA, f"ship-{s['id']}.json")) for s in slim)
    total = sum(len(s["data"]) for s in slim)
    print("MSC payloads written:", len(slim), "ships,", f"{total:,}", "cabins")
    print("largest ship file:", biggest // 1024, "KB ->", os.path.relpath(_DATA))


if __name__ == "__main__":
    main()
