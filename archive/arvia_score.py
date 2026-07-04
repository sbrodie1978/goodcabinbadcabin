"""Arvia scoring — same three-dimension model, per-ship config, auto zones."""
import json, statistics
from collections import defaultdict

cabins = json.load(open("arvia_cabins_raw.json"))
Z = json.load(open("arvia_zones.json"))
zones, laund = Z["zones"], Z["launderettes"]
GRADES = json.load(open("arvia_grades.json"))
LIFTS = json.load(open("arvia_lifts.json"))
def grade_class(g):
    if not g: return None
    return {"B":"suite","C":"mini-suite","E":"balcony","G":"balcony","L":"oceanview",
            "O":"interior","P":"interior","Q":"balcony","S":"interior"}[g[0]]

CABIN_DECKS = ["4","5","8","9","10","11","12","14","15","16","17"]
PHYS = ["3","4","5","6","7","8","9","10","11","12","14","15","16","17","18","19"]
HEIGHT = {d:i for i,d in enumerate(CABIN_DECKS)}          # 4=0 ... 17=10
PIDX = {d:i for i,d in enumerate(PHYS)}
VENUE_DECKS = {"buffet":"16","pool":"16","hub":"7"}

ZONE_PEN = {"pool_deck":{"above":-25,"below":-12},"galley_buffet":{"above":-18,"below":-20},
 "venue_entertainment":{"above":-20,"below":-20},"dining":{"above":-14,"below":-16},
 "public_general":{"above":-12,"below":-12},"open_deck":{"above":-8,"below":0},
 "crew_service":{"above":-8,"below":-8},"unknown_noncabin":{"above":-12,"below":-12}}
PRIORITY = {"pool_deck":5,"galley_buffet":4,"venue_entertainment":3,"dining":2,"public_general":1,"open_deck":1,"crew_service":0,"unknown_noncabin":0}

# side by parity (98% rule; centreline singles get their true booking side)
for c in cabins:
    c["side"] = "S" if int(c["num"].split(".")[1])%2==1 else "P"

# pitch/tolerance from deck 11
bs = sorted(c["b"] for c in cabins if c["deck"]=="11")
gaps = [y-x for x,y in zip(bs,bs[1:]) if 0.0003<y-x<0.03]
pitch = statistics.median(gaps); TOL = pitch*1.5

by_ds = defaultdict(list)
for c in cabins: by_ds[(c["deck"],c["side"])].append(c["b"])
def has_cabin(d, s, b):
    return d in CABIN_DECKS and any(abs(b-z)<=TOL for z in by_ds[(d,s)])
def neighbour(d, up=True):
    i = PIDX[d] + (1 if up else -1)
    return PHYS[i] if 0<=i<len(PHYS) else None

def zone_for(deck, b):
    if deck is None: return {"cls":"open_deck","name":f"Open air"}
    best=None
    for z in zones.get(deck, []):
        if z["b0"]<=b<=z["b1"]:
            if best is None or PRIORITY[z["cls"]]>PRIORITY[best["cls"]]: best=z
    if best: return best
    return {"cls":"unknown_noncabin","name":f"Deck {deck} non-cabin space"}

rows=[]
for c in cabins:
    d=c["deck"]; up,dn = neighbour(d,True), neighbour(d,False)
    ca, cb = has_cabin(up,c["side"],c["b"]), has_cabin(dn,c["side"],c["b"])
    # QUIET
    q=100; notes=[]
    above_desc=below_desc="cabins"
    if not ca:
        z=zone_for(up,c["b"]); pen=ZONE_PEN[z["cls"]]["above"]; q+=pen
        above_desc=z["name"]; notes.append(f"above: {z['name']} ({pen})")
    if not cb:
        z=zone_for(dn,c["b"]); pen=ZONE_PEN[z["cls"]]["below"]; q+=pen
        below_desc=z["name"]; notes.append(f"below: {z['name']} ({pen})")
    ls=laund.get(d,[])
    dl=min((abs(c["b"]-l) for l in ls), default=None)
    dlift=min(abs(c["b"]-L) for L in LIFTS)
    if dlift<0.014: q-=10; notes.append("beside lift lobby (-10)")
    elif dlift<0.028: q-=5; notes.append("near lift lobby (-5)")
    if dl is not None:
        if dl<0.018: q-=8; notes.append("beside launderette (-8)")
        elif dl<0.036: q-=4; notes.append("near launderette (-4)")
    if c["b"]<0.07 and d in ("4","5"): q-=10; notes.append("far forward, low deck: anchor/thruster noise (-10)")
    if c["b"]>0.93 and d in ("4","5"): q-=8; notes.append("far aft, low deck: engine vibration (-8)")
    quiet=max(0,min(100,q))
    # MOTION (stored as stability)
    longit=100-abs(c["b"]-0.5)*2*50
    stab=max(0,min(100, longit - HEIGHT[d]*2.2))
    # CONVENIENCE (no lift data on this plan -> neutral 60)
    lift_s=max(0,100-dlift*300)
    laun_s=max(0,100-(dl*600)) if dl is not None else 40
    dks=[abs(PIDX[d]-PIDX[v]) for v in VENUE_DECKS.values()]
    ven_s=max(0,100-(sum(dks)/len(dks))*9)
    conv=max(0,min(100, .45*lift_s+.15*laun_s+.40*ven_s))
    rows.append({"cabin":c["num"],"deck":d,"side":c["side"],"s":c["b"],"b":c["b"],
      "category":GRADES.get(c["num"]),"category_class":grade_class(GRADES.get(c["num"])),
      "category_confidence":"high" if GRADES.get(c["num"]) else None,
      "dist_lift":round(dlift,4),"dist_laundry":round(dl,4) if dl is not None else None,
      "cabin_above":ca,"cabin_below":cb,"above_desc":above_desc,"below_desc":below_desc,
      "above_class":"cabins" if ca else zone_for(up,c["b"])["cls"],
      "below_class":"cabins" if cb else zone_for(dn,c["b"])["cls"],
      "quiet":round(quiet,1),"stability":round(stab,1),"convenience":round(conv,1),
      "quiet_notes":"; ".join(notes) if notes else "cabins above and below"})

json.dump(rows, open("arvia_scored.json","w"), indent=1)
from collections import Counter
print("scored:", len(rows))
for dim in ("quiet","stability","convenience"):
    v=sorted(r[dim] for r in rows)
    print(f"{dim:12s} min {v[0]:5.1f} med {v[len(v)//2]:5.1f} max {v[-1]:5.1f}")
print("\nabove-desc samples for deck 8 (promenade cabins):")
d8=[r for r in rows if r["deck"]=="8"][:1]
worst=sorted(rows,key=lambda r:r["quiet"])[:6]
for r in worst: print(f"  {r['cabin']} deck {r['deck']} Q{r['quiet']}: {r['quiet_notes'][:95]}")
best=[r for r in rows if r["quiet"]==100]
print("perfect-quiet cabins:", len(best))
