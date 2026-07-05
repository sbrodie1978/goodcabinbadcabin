#!/usr/bin/env python3
"""MSC fleet scorer. Reads pipeline/msc/msc_extracted.json (per-cabin geometry
+ category, ship-normalised b and side) and the class zone maps, and produces
pipeline/msc/msc_scored.json — quiet / stability / convenience / space per
cabin, plus above/below descriptions and a surround cross-section.

Mirrors the Princess pipeline/fleet_build.py model, with MSC adaptations:
  * b and side already normalised per ship in extraction (no deck registration)
  * lift positions come from CLASS_VENUE_DECKS[cls]['lift_b'] (MSC numbering
    doesn't encode lift blocks the way Princess's does)
  * MSC has no self-service launderettes -> convenience is lift + venues only
  * no square-footage data -> space uses category tier + within-ship SVG
    footprint area as a relative size proxy
  * house rules: Yacht Club convenience floor, Aurea spa bonus, promenade-view
    quiet note (all from msc_classes.py, agreed with Stuart)
Stdlib only.
"""
import json
import os
import statistics
from collections import defaultdict

import sys
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
from msc_classes import (CLASSES, CLASS_VENUE_DECKS, CLASS_ZONES, ZONE_PEN,
                         YC_CONV_FLOOR, AUREA_SPA_BONUS)
from msc_categories import (MSC_META, cabin_type, space_base, is_yc, is_aurea,
                            display_name)

EXTRACT = os.path.join(_HERE, "msc_extracted.json")
OUT = os.path.join(_HERE, "msc_scored.json")

# Zone overlap resolution: when two zones cover the same b, the louder wins.
PRIORITY = {"pool_deck": 7, "venue_entertainment": 6, "galley_buffet": 5,
            "kids_play": 4, "crew_service": 3, "dining": 2, "open_deck": 1,
            "public_general": 0, "unknown_noncabin": -1, "cabins": -2}

# mild default for deck regions with no mapped zone (interstitial non-cabin space)
PEN = dict(ZONE_PEN)
PEN["unknown_noncabin"] = {"above": 6, "below": 4}

SHIP_BY_CLASS = {}
for cls, ships in CLASSES.items():
    for s in ships:
        SHIP_BY_CLASS[s] = cls


def build_ship(slug, ship):
    cls = SHIP_BY_CLASS[slug]
    zones = CLASS_ZONES[cls]
    vdecks = CLASS_VENUE_DECKS[cls]
    lift_b = vdecks.get("lift_b", [0.3, 0.6])

    cabs = [dict(c) for c in ship["cabins"] if c.get("b") is not None]
    PHYS = sorted(int(d) for d in ship["all_decks"])
    PIDX = {d: i for i, d in enumerate(PHYS)}
    cabin_decks = sorted(set(c["deck"] for c in cabs))
    HEIGHT = {d: i for i, d in enumerate(cabin_decks)}
    lowest = cabin_decks[0]

    # relative footprint area -> percentile within ship (space size proxy)
    areas = sorted(c["w"] * c["h"] for c in cabs)
    def area_pct(a):
        # fraction of cabins with a smaller footprint (0..1)
        lo, hi = 0, len(areas)
        while lo < hi:
            mid = (lo + hi) // 2
            if areas[mid] < a: lo = mid + 1
            else: hi = mid
        return lo / len(areas) if areas else 0.5

    by_ds = defaultdict(list)
    for c in cabs:
        by_ds[(c["deck"], c["side"])].append(c)

    # pitch/tolerance from the most-populous cabin deck
    ref_deck = max(cabin_decks, key=lambda d: sum(1 for c in cabs if c["deck"] == d))
    bref = sorted(c["b"] for c in cabs if c["deck"] == ref_deck)
    gaps = [y - x for x, y in zip(bref, bref[1:]) if 0.0004 < y - x < 0.03]
    pitch = statistics.median(gaps) if gaps else 0.012
    TOL = pitch * 1.5

    def cabin_at(deck, side, b):
        best, bd = None, TOL
        for c in by_ds.get((deck, side), []):
            d = abs(c["b"] - b)
            if d < bd:
                bd, best = d, c
        return best

    def ndeck(deck, up):
        i = PIDX.get(deck)
        if i is None:
            return None
        i += 1 if up else -1
        return PHYS[i] if 0 <= i < len(PHYS) else None

    def zone_for(deck, b):
        if deck is None:
            return {"cls": "open_deck", "name": "Open air"}
        best = None
        for z0, z1, zc, zn in zones.get(deck, []):
            if z0 <= b <= z1 and (best is None or PRIORITY[zc] > PRIORITY[best[2]]):
                best = (z0, z1, zc, zn)
        if best:
            return {"cls": best[2], "name": best[3]}
        return {"cls": "unknown_noncabin", "name": f"Deck {deck} non-cabin space"}

    rows = []
    for c in cabs:
        dk = c["deck"]
        slug_c = c["cats"][0] if c["cats"] else ""
        grp = c["grp"]
        ctype = cabin_type(slug_c, grp)
        yc = is_yc(slug_c, grp)
        aurea = is_aurea(slug_c, grp)
        up, dn = ndeck(dk, True), ndeck(dk, False)
        ca = cabin_at(up, c["side"], c["b"]) if up in cabin_decks else None
        cb = cabin_at(dn, c["side"], c["b"]) if dn in cabin_decks else None

        # ---- QUIET ----
        q = 100
        notes = []
        above_desc = below_desc = "cabins"
        above_class = "cabins" if ca else None
        below_class = "cabins" if cb else None
        if not ca:
            z = zone_for(up, c["b"]); pen = PEN[z["cls"]]["above"]; q += pen
            above_desc = z["name"]; above_class = z["cls"]
            if pen: notes.append(f"above: {z['name']} ({pen})")
        else:
            above_desc = f"{ca['num']} ({display_name(ca['cats'][0]) if ca['cats'] else 'cabin'})"
        if not cb:
            z = zone_for(dn, c["b"]); pen = PEN[z["cls"]]["below"]; q += pen
            below_desc = z["name"]; below_class = z["cls"]
            if pen: notes.append(f"below: {z['name']} ({pen})")
        else:
            below_desc = f"{cb['num']} ({display_name(cb['cats'][0]) if cb['cats'] else 'cabin'})"
        dlift = min(abs(c["b"] - L) for L in lift_b)
        if dlift < 0.014: q -= 10; notes.append("beside lift lobby (-10)")
        elif dlift < 0.028: q -= 5; notes.append("near lift lobby (-5)")
        if c["b"] < 0.07 and dk == lowest: q -= 10; notes.append("far forward, lowest cabin deck (-10)")
        if c["b"] > 0.93 and dk == lowest: q -= 8; notes.append("far aft, low deck: prop vibration (-8)")
        promenade = ("promenade-view" in slug_c) or c.get("fill") == "#003891"
        if promenade: q -= 8; notes.append("promenade-view balcony: faces indoor promenade (-8)")
        quiet = max(0, min(100, q))

        # ---- STABILITY (bow worst, ideal slightly aft of midship, height penalty) ----
        IDEAL = 0.55
        d_fore = c["b"] - IDEAL
        if d_fore < 0:
            longit = 100 - (abs(d_fore) / IDEAL) * 70
        else:
            longit = 100 - (d_fore / (1 - IDEAL)) * 32
        stab = max(0, min(100, longit - HEIGHT[dk] * 1.6))

        # ---- CONVENIENCE (lifts + venue decks; no launderettes on MSC) ----
        lift_s = max(0, 100 - dlift * 300)
        dks = [abs(PIDX[dk] - PIDX[v]) for k, v in vdecks.items()
               if k != "lift_b" and v in PIDX]
        ven_s = max(0, 100 - (sum(dks) / len(dks)) * 9) if dks else 50
        conv = max(0, min(100, .55 * lift_s + .45 * ven_s))
        if yc:
            conv = max(conv, YC_CONV_FLOOR)          # self-contained enclave
        elif aurea:
            conv = min(100, conv + AUREA_SPA_BONUS)  # spa adjacency
        if ctype == "suite" and not yc:
            conv = conv * 0.6 + 30                    # suite priority services

        # ---- SPACE (category tier + within-ship footprint percentile) ----
        base = space_base(slug_c, grp)
        space = max(0, min(100, base + (area_pct(c["w"] * c["h"]) - 0.5) * 16))

        rows.append({
            "cabin": c["num"], "deck": str(dk), "side": c["side"], "b": c["b"],
            "type": ctype, "category": slug_c, "category_confidence": "official",
            "category_name": display_name(slug_c) if slug_c else "Stateroom",
            "category_color": (c.get("fill") or "#cfd6cf").lstrip("#"),
            "yc": yc, "aurea": aurea,
            "cabin_above": bool(ca), "cabin_below": bool(cb),
            "above_desc": above_desc, "below_desc": below_desc,
            "above_class": above_class, "below_class": below_class,
            "quiet": round(quiet, 1), "stability": round(stab, 1),
            "convenience": round(conv, 1), "space": round(space, 1),
            "quiet_notes": "; ".join(notes) if notes else "cabins above and below"})
    return rows


def main():
    ext = json.load(open(EXTRACT))
    fleet = {}
    for slug in MSC_META:
        rows = build_ship(slug, ext[slug])
        fleet[slug] = rows
        qs = [r["quiet"] for r in rows]
        cvs = [r["convenience"] for r in rows]
        print("%-20s %5d cabins  Q[%d-%d] C[%d-%d] perfectQ=%d"
              % (slug, len(rows), min(qs), max(qs), min(cvs), max(cvs),
                 sum(1 for q in qs if q == 100)))
    json.dump(fleet, open(OUT, "w"))
    print("\nTOTAL:", sum(len(v) for v in fleet.values()), "cabins across",
          len(fleet), "ships ->", os.path.relpath(OUT))


if __name__ == "__main__":
    main()
