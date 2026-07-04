"""CabinIntel pipeline v2 — global lift-shaft calibration.

All deck drawings share one scale (same source file). Four lift shafts
(A fwd, B mid, C aft, D aft-panoramic) run vertically through the ship.
Each deck is aligned to the ship frame by translation only, solved by
matching its detected lift banks to reference shaft offsets.

Ship coordinate s: 0.0 = shaft A (forward bank), 1.0 = shaft C (aft bank).
Bow < 0, stern > 1. We also compute b = normalised bow->stern 0..1 using
the full cabin envelope across all decks.
"""
import json, statistics, itertools
from collections import defaultdict

CABIN_DECKS = ["05","06","09","10","11","12","14","15","16","17"]
PHYSICAL_ORDER = ["04","05","06","07","08","09","10","11","12","14","15","16","17","18","19","20","21"]

raw = json.load(open("raw_words.json"))
feat = json.load(open("features_raw.json"))
cabins = json.load(open("extracted.json"))["cabins"]
cabins = [{"num": c["t"], "x": c["x"], "y": c["y"]} for c in cabins]

byd = defaultdict(list)
for c in cabins:
    byd[c["num"][:2]].append(c)
cols = {}
for d, cs in byd.items():
    xs = [c["x"] for c in cs]; ys = [c["y"] for c in cs]
    cols[d] = {"x0": min(xs)-25, "x1": max(xs)+25, "y0": min(ys)-60, "y1": max(ys)+60,
               "cx": statistics.median(xs)}

def assign_deck(x, y):
    best, bestdist = None, 1e9
    for d, w in cols.items():
        if w["y0"] <= y <= w["y1"]:
            dist = 0 if w["x0"] <= x <= w["x1"] else min(abs(x-w["x0"]), abs(x-w["x1"]))
            if dist < bestdist:
                best, bestdist = d, dist
    return best if bestdist < 30 else None

lifts_by_deck = defaultdict(list)
for L in feat["lifts"]:
    d = assign_deck(L["x"], L["y"])
    if d:
        lifts_by_deck[d].append(L)

def cluster_banks(lifts, gap=45):
    pts = sorted(lifts, key=lambda l: l["y"])
    banks, cur = [], [pts[0]]
    for p in pts[1:]:
        if p["y"] - cur[-1]["y"] > gap:
            banks.append(cur); cur = [p]
        else:
            cur.append(p)
    banks.append(cur)
    return [statistics.mean(p["y"] for p in b) for b in banks]

banks = {d: cluster_banks(ls) for d, ls in lifts_by_deck.items()}

# ---- reference shafts from deck 11 (has all four) ----
ref = banks["11"]                      # [A, B, C, D] page-y on deck 11
shaftA = ref[0]
SHAFTS = [b - shaftA for b in ref]     # offsets from A: [0, ~202, ~395, ~518]
print("reference shaft offsets from A:", [round(s,1) for s in SHAFTS])

# ---- solve per-deck translation by best bank->shaft matching ----
offsets = {}
for d, bs in banks.items():
    best_off, best_hits, best_res = None, -1, 1e9
    for b, sref in itertools.product(bs, SHAFTS):
        off = b - sref           # candidate: this bank IS this shaft
        hits, res = 0, 0.0
        for bb in bs:
            errs = [abs((bb - off) - s) for s in SHAFTS]
            e = min(errs)
            if e < 12:
                hits += 1; res += e
        if hits > best_hits or (hits == best_hits and res < best_res):
            best_off, best_hits, best_res = off, hits, res
    offsets[d] = best_off
    matched = sorted(round(bb - best_off,1) for bb in bs)
    print(f"deck {d}: offset {best_off:7.1f}  banks at ship-y {matched} ({best_hits}/{len(bs)} matched)")

SPAN = SHAFTS[2]   # A->C distance = s 0..1

def to_s(d, y):
    return (y - offsets[d] - shaftA + shaftA*0) / SPAN if False else ((y - offsets[d]) - 0) / SPAN
# clean version: ship_y = y - offset ; s = (ship_y - shaftA_ship) / SPAN where shaftA_ship = shaftA - offsets["11"]... 
# simplify: ship frame anchored so shaft A sits at ship_y = 0
def ship_y(d, y):
    return (y - offsets[d]) - shaftA + (offsets["11"] * 0)
# shaft A on deck 11 page-y = shaftA, its ship_y must be 0:
A_ship = shaftA - offsets["11"]
def s_coord(d, y):
    return ((y - offsets[d]) - A_ship) / SPAN

rows = []
for c in cabins:
    d = c["num"][:2]
    s = s_coord(d, c["y"])
    rows.append({"cabin": c["num"], "deck": d, "s": round(s,4),
                 "side": "P" if c["x"] < cols[d]["cx"] else "S",
                 "x": round(c["x"],1), "y": round(c["y"],1)})

# bow->stern normalisation from global cabin envelope
smin = min(r["s"] for r in rows); smax = max(r["s"] for r in rows)
for r in rows:
    r["b"] = round((r["s"] - smin) / (smax - smin), 4)
print(f"\ncabin envelope s: [{smin:.3f}, {smax:.3f}]")

# ---- consistency check: laundromats should now roughly stack ----
laund_by_deck = defaultdict(list)
for L in feat["laundries"]:
    d = assign_deck(L["x"], L["y"])
    if d:
        laund_by_deck[d].append(round(s_coord(d, L["y"]), 3))
print("laundromat s-positions:", dict(sorted(laund_by_deck.items())))

# ---- above/below ----
allS = sorted(r["s"] for r in rows if r["deck"] == "11")
gaps = [b-a for a,b in zip(allS, allS[1:]) if 0.0005 < b-a < 0.05]
pitch = statistics.median(gaps); TOL = pitch * 1.5
by_ds = defaultdict(list)
for r in rows:
    by_ds[(r["deck"], r["side"])].append(r["s"])

def has_cabin(deck, side, s):
    return deck in CABIN_DECKS and any(abs(s-z) <= TOL for z in by_ds[(deck, side)])

def neighbour(deck, up=True):
    i = PHYSICAL_ORDER.index(deck) + (1 if up else -1)
    return PHYSICAL_ORDER[i] if 0 <= i < len(PHYSICAL_ORDER) else None

for r in rows:
    ud, dd = neighbour(r["deck"], True), neighbour(r["deck"], False)
    r["deck_above"], r["deck_below"] = ud, dd
    r["cabin_above"] = has_cabin(ud, r["side"], r["s"])
    r["cabin_below"] = has_cabin(dd, r["side"], r["s"])

bank_s = {d: sorted(s_coord(d, y) for y in bs) for d, bs in banks.items()}
for r in rows:
    r["dist_lift"] = round(min(abs(r["s"]-b) for b in bank_s[r["deck"]]), 4)
    ls = laund_by_deck.get(r["deck"], [])
    r["dist_laundry"] = round(min(abs(r["s"]-l) for l in ls), 4) if ls else None

json.dump(rows, open("cabins_geo.json","w"), indent=1)

# ---- summary + coverage gaps (candidate venue voids for gazetteer) ----
counts = defaultdict(lambda: [0,0,0])
for r in rows:
    counts[r["deck"]][0]+=1; counts[r["deck"]][1]+=r["cabin_above"]; counts[r["deck"]][2]+=r["cabin_below"]
print("\ndeck  cabins  above-is-cabin  below-is-cabin")
for d in CABIN_DECKS:
    n,a,b = counts[d]
    print(f"  {d}    {n:4d}     {a:4d} ({a/n*100:3.0f}%)     {b:4d} ({b/n*100:3.0f}%)")

print("\nnon-cabin coverage gaps per deck (s ranges with no cabins, width > 3 pitches):")
gap_report = {}
for d in CABIN_DECKS:
    ss = sorted(set(round(r["s"],4) for r in rows if r["deck"]==d))
    gs = []
    for a,b in zip(ss, ss[1:]):
        if b-a > pitch*3:
            gs.append([round(a,3), round(b,3)])
    ext = [round(smin,3), round(ss[0],3), round(ss[-1],3), round(smax,3)]
    gap_report[d] = {"internal_gaps": gs, "covered": [round(ss[0],3), round(ss[-1],3)]}
    print(f"  deck {d}: covers s[{ss[0]:.3f},{ss[-1]:.3f}]  internal gaps: {gs}")
json.dump(gap_report, open("coverage_gaps.json","w"), indent=1)
