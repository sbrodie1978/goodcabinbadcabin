"""CabinIntel scoring engine — reads cabins_geo.json + scoring_config.json +
gazetteer.json, computes the three dimension scores and profile rankings,
writes sunprincess.db (D1-compatible schema) and cabins_scored.csv."""
import json, sqlite3, csv
from collections import defaultdict

cfg = json.load(open("scoring_config.json"))
gaz = json.load(open("gazetteer.json"))["zones"]
rows = json.load(open("cabins_geo.json"))

def zone_for(deck, s):
    for z in gaz:
        if z["deck"] == deck and z["s0"] <= s <= z["s1"]:
            return z
    return {"class": "unknown_noncabin", "name": f"deck {deck} non-cabin space", "confidence": "guess"}

def clamp(v): return max(0, min(100, round(v, 1)))

q, st, cv = cfg["quiet"], cfg["stability"], cfg["convenience"]

for r in rows:
    # ---------- QUIET ----------
    score = q["base"]; notes = []
    if not r["cabin_above"]:
        z = zone_for(r["deck_above"], r["s"])
        pen = cfg["zone_classes"][z["class"]]["above"]
        score += pen
        notes.append(f"above: {z['name']} ({pen})")
        r["above_desc"] = z["name"]; r["above_class"] = z["class"]
    else:
        r["above_desc"] = "cabins"; r["above_class"] = "cabins"
    if not r["cabin_below"]:
        z = zone_for(r["deck_below"], r["s"])
        pen = cfg["zone_classes"][z["class"]]["below"]
        score += pen
        notes.append(f"below: {z['name']} ({pen})")
        r["below_desc"] = z["name"]; r["below_class"] = z["class"]
    else:
        r["below_desc"] = "cabins"; r["below_class"] = "cabins"

    if r["dist_lift"] < q["lift_adjacent_dist"]:
        score += q["lift_adjacent_pen"]; notes.append(f"beside lift lobby ({q['lift_adjacent_pen']})")
    elif r["dist_lift"] < q["lift_near_dist"]:
        score += q["lift_near_pen"]; notes.append(f"near lift lobby ({q['lift_near_pen']})")
    if r["dist_laundry"] is not None:
        if r["dist_laundry"] < q["laundry_adjacent_dist"]:
            score += q["laundry_adjacent_pen"]; notes.append(f"beside launderette ({q['laundry_adjacent_pen']})")
        elif r["dist_laundry"] < q["laundry_near_dist"]:
            score += q["laundry_near_pen"]; notes.append(f"near launderette ({q['laundry_near_pen']})")
    if r["b"] < q["bow_zone_b"] and r["deck"] in q["bow_low_decks"]:
        score += q["bow_pen"]; notes.append(f"far forward, low deck: anchor/thruster noise ({q['bow_pen']})")
    if r["b"] > q["stern_zone_b"] and r["deck"] in q["stern_low_decks"]:
        score += q["stern_pen"]; notes.append(f"far aft, low deck: engine vibration ({q['stern_pen']})")
    r["quiet"] = clamp(score); r["quiet_notes"] = "; ".join(notes) if notes else "cabins above and below, away from lifts"

    # ---------- STABILITY ----------
    longit = 100 - abs(r["b"] - 0.5) * 2 * st["longitudinal_max_pen"]
    height = st["deck_height_index"][r["deck"]] * st["height_pen_per_deck"]
    r["stability"] = clamp(longit - height)

    # ---------- CONVENIENCE ----------
    lift_s = max(0, 100 - r["dist_lift"] * cv["lift_slope"])
    if r["dist_laundry"] is not None:
        laun_s = max(0, 100 - r["dist_laundry"] * cv["laundry_slope"])
    else:
        laun_s = cv["no_laundry_on_deck_score"]
    pi = cv["physical_index"]
    dks = [abs(pi[r["deck"]] - pi[vd]) for vd in cv["venue_decks"].values()]
    ven_s = max(0, 100 - (sum(dks)/len(dks)) * cv["venue_pen_per_deck"])
    w = cv["weights"]
    r["convenience"] = clamp(w["lift"]*lift_s + w["laundry"]*laun_s + w["venues"]*ven_s)

# ---------- PROFILES ----------
for name, w in cfg["profiles"].items():
    for r in rows:
        r[f"score_{name}"] = round(w["quiet"]*r["quiet"] + w["stability"]*r["stability"]
                                   + w["convenience"]*r["convenience"], 1)
# ranks
for name in cfg["profiles"]:
    order = sorted(rows, key=lambda r: -r[f"score_{name}"])
    for i, r in enumerate(order, 1):
        r[f"rank_{name}"] = i

# ---------- OUTPUTS ----------
fields = ["cabin","deck","side","s","b","dist_lift","dist_laundry",
          "cabin_above","cabin_below","above_desc","below_desc",
          "quiet","stability","convenience","quiet_notes"] + \
         [f"score_{p}" for p in cfg["profiles"]] + [f"rank_{p}" for p in cfg["profiles"]]

with open("cabins_scored.csv","w",newline="") as f:
    wtr = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
    wtr.writeheader()
    for r in sorted(rows, key=lambda r: r["cabin"]):
        wtr.writerow(r)

con = sqlite3.connect("sunprincess.db")
con.executescript("""
DROP TABLE IF EXISTS cabins; DROP TABLE IF EXISTS scores; DROP TABLE IF EXISTS ships;
CREATE TABLE ships (id INTEGER PRIMARY KEY, name TEXT, line TEXT, plan_version TEXT);
CREATE TABLE cabins (
  cabin TEXT PRIMARY KEY, ship_id INTEGER, deck TEXT, side TEXT,
  s REAL, b REAL, dist_lift REAL, dist_laundry REAL,
  cabin_above INTEGER, cabin_below INTEGER,
  above_desc TEXT, below_desc TEXT, above_class TEXT, below_class TEXT,
  quiet REAL, stability REAL, convenience REAL, quiet_notes TEXT
);
CREATE TABLE scores (
  cabin TEXT, profile TEXT, score REAL, rank INTEGER,
  PRIMARY KEY (cabin, profile)
);
CREATE INDEX idx_scores_profile ON scores(profile, rank);
""")
con.execute("INSERT INTO ships VALUES (1,'Sun Princess','Princess Cruises','2023-05 Pure Holidays plan')")
for r in rows:
    con.execute("INSERT OR REPLACE INTO cabins VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (r["cabin"],1,r["deck"],r["side"],r["s"],r["b"],r["dist_lift"],r["dist_laundry"],
         int(r["cabin_above"]),int(r["cabin_below"]),r["above_desc"],r["below_desc"],
         r["above_class"],r["below_class"],r["quiet"],r["stability"],r["convenience"],r["quiet_notes"]))
    for p in cfg["profiles"]:
        con.execute("INSERT OR REPLACE INTO scores VALUES (?,?,?,?)",
                    (r["cabin"], p, r[f"score_{p}"], r[f"rank_{p}"]))
con.commit()

# ---------- REPORT ----------
print("=== score distribution ===")
for dim in ["quiet","stability","convenience"]:
    vs = sorted(r[dim] for r in rows)
    print(f"{dim:12s} min {vs[0]:5.1f}  p25 {vs[len(vs)//4]:5.1f}  median {vs[len(vs)//2]:5.1f}  p75 {vs[3*len(vs)//4]:5.1f}  max {vs[-1]:5.1f}")

for p in ["balanced","light_sleeper","motion_sensitive","everything_nearby"]:
    top = sorted(rows, key=lambda r: r[f"rank_{p}"])[:5]
    bot = sorted(rows, key=lambda r: -r[f"rank_{p}"])[:3]
    print(f"\n=== {p} — top 5 ===")
    for r in top:
        print(f"  #{r[f'rank_{p}']:4d} {r['cabin']} (deck {r['deck']}{r['side']})  {r[f'score_{p}']:5.1f}  Q{r['quiet']:.0f}/S{r['stability']:.0f}/C{r['convenience']:.0f}  above:{r['above_desc'][:34]} below:{r['below_desc'][:34]}")
    print(f"  --- bottom 3 ---")
    for r in reversed(bot):
        print(f"  #{r[f'rank_{p}']:4d} {r['cabin']} (deck {r['deck']}{r['side']})  {r[f'score_{p}']:5.1f}  Q{r['quiet']:.0f}/S{r['stability']:.0f}/C{r['convenience']:.0f}  {r['quiet_notes'][:80]}")
print(f"\nwrote sunprincess.db + cabins_scored.csv ({len(rows)} cabins)")
