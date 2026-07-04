"""Majestic Princess — rebuild from official Princess API data.
Uses textX/textY label anchors (clean 2-lane layout) for position, real category
codes/colours, and geometry-based above/below via shared coordinate frame."""
import json, re, statistics
from collections import defaultdict

d = json.load(open("/mnt/user-data/uploads/majestic_princess_api.json"))

# ---- shared frame: all decks use same x,y coordinate system (label anchors) ----
# normalise y across ship extent -> b (0 forward .. 1 aft); x -> side + s
CABIN_DECKS = [8,9,10,11,12,14,15,16]
PHYS = [4,5,6,7,8,9,10,11,12,14,15,16,17,18,19]
HEIGHT = {dk:i for i,dk in enumerate(CABIN_DECKS)}
PIDX = {dk:i for i,dk in enumerate(PHYS)}

# y-extent for b-normalisation: use full cabin-bearing span across all decks
ys = [c["textY"] for c in d]
YMIN, YMAX = min(ys), max(ys)
xs = [c["textX"] for c in d]
XMID = statistics.median(xs)
XMIN, XMAX = min(xs), max(xs)

for c in d:
    c["b0"] = (c["textY"]-YMIN)/(YMAX-YMIN)
    c["side"] = "P" if c["textX"] < XMID else "S"
    half = (XMAX-XMID) if c["side"]=="S" else (XMID-XMIN)
    c["s"] = round((c["textX"]-XMID)/half, 3)

# register each deck to deck-10 frame via shared cabin numbers (true vertical alignment)
def _suf(n): return n[1:] if n[1:].isdigit() else None
_ref = {_suf(c["number"]): c["b0"] for c in d if c["deck"]==10 and _suf(c["number"])}
_tf = {}
for _dk in CABIN_DECKS:
    _p = [(c["b0"], _ref[_suf(c["number"])]) for c in d if c["deck"]==_dk and _suf(c["number"]) in _ref]
    _n=len(_p); _sx=sum(p[0] for p in _p); _sy=sum(p[1] for p in _p)
    _sxx=sum(p[0]**2 for p in _p); _sxy=sum(p[0]*p[1] for p in _p)
    _a=(_n*_sxy-_sx*_sy)/(_n*_sxx-_sx*_sx); _b=(_sy-_a*_sx)/_n
    _tf[_dk]=(_a,_b)
for c in d:
    _a,_b = _tf[c["deck"]]
    c["b"] = round(_a*c["b0"]+_b, 4)

# ---- category class from metaCode ----
META = {"S":"suite","M":"mini-suite","D":"balcony","B":"balcony","O":"oceanview","I":"interior"}
for c in d:
    c["category_class"] = META.get(c["metaCode"], "interior")

# ---- above/below via geometry (same frame => compare b within side) ----
by_ds = defaultdict(list)
for c in d: by_ds[(c["deck"],c["side"])].append(c)
# pitch tolerance from deck 10
b10 = sorted(c["b"] for c in d if c["deck"]==10)
pitch = statistics.median([y-x for x,y in zip(b10,b10[1:]) if 0.0004<y-x<0.02])
TOL = pitch*1.4

def cabin_at(deck, side, b):
    best=None; bd=TOL
    for c in by_ds[(deck,side)]:
        dd=abs(c["b"]-b)
        if dd<bd: bd=dd; best=c
    return best
def neighbour_deck(deck, up):
    i=PIDX[deck]+(1 if up else -1)
    return PHYS[i] if 0<=i<len(PHYS) else None

# ---- venue zones (Royal-class canon, b-frame) + laundry/lift from data ----
# lifts: 3 shafts. Fwd = boundary of x1/x2 blocks, mid = 4xx internal gap, aft = 6xx/7xx
def block_boundary(lo, hi):
    v=[]
    for dk in CABIN_DECKS:
        L=[c["b"] for c in d if c["deck"]==dk and c["number"][0].isalpha() and c["number"][1:].isdigit() and int(c["number"][1:])//100==lo]
        H=[c["b"] for c in d if c["deck"]==dk and c["number"][0].isalpha() and c["number"][1:].isdigit() and int(c["number"][1:])//100==hi]
        if L and H: v.append((max(L)+min(H))/2)
    return statistics.median(v)
LIFT_FWD=block_boundary(1,2)
LIFT_AFT=block_boundary(6,7)
mids=[]
for dk in CABIN_DECKS:
    bs=sorted(c["b"] for c in d if c["deck"]==dk and c["number"][1:].isdigit() and int(c["number"][1:])//100==4)
    if len(bs)>6:
        g=max(zip(bs,bs[1:]),key=lambda p:p[1]-p[0])
        if g[1]-g[0]>0.010: mids.append((g[0]+g[1])/2)
LIFT_MID=statistics.median(mids)
LIFTS=[LIFT_FWD,LIFT_MID,LIFT_AFT]

# laundry: block 618-628
laund=defaultdict(list)
for dk in CABIN_DECKS:
    v=[c["b"] for c in d if c["deck"]==dk and c["number"][1:].isdigit() and 616<=int(c["number"][1:])<=628]
    if v: laund[dk]=[statistics.mean(v)]

CANON={
 7:[(0.0,0.20,"venue_entertainment","Princess Theater (upper)"),
    (0.20,0.42,"public_general","Shops of Princess / atrium"),
    (0.42,0.55,"dining","Ocean Terrace / Catch by Rudi"),
    (0.55,0.72,"venue_entertainment","Princess Live! & Crown Grill"),
    (0.72,0.86,"public_general","Photo gallery"),
    (0.86,1.0,"venue_entertainment","Vista Lounge")],
 6:[(0.0,0.20,"venue_entertainment","Princess Theater (lower)"),
    (0.20,0.40,"venue_entertainment","Grand Casino / bars"),
    (0.40,0.62,"dining","Bellini's / Alfredo's"),
    (0.62,0.82,"dining","Concerto Dining Room"),
    (0.82,1.0,"dining","Allegro Dining Room")],
 5:[(0.15,0.35,"public_general","Lotus Spa & Enclave"),
    (0.35,0.62,"public_general","The Piazza / guest services"),
    (0.62,1.0,"dining","Symphony Dining Room")],
 17:[(0.0,0.22,"pool_deck","Hollywood Conservatory"),
     (0.22,0.40,"pool_deck","Hollywood Pool Club"),
     (0.40,0.75,"open_deck","Sun deck / Movies Under the Stars"),
     (0.75,1.0,"open_deck","Sports terraces")],
 16:[(0.30,0.56,"pool_deck","Fountain & main pools"),
     (0.56,0.62,"public_general","Panoramic lift lobby"),
     (0.62,0.86,"galley_buffet","World Fresh Marketplace & Bakery"),
     (0.86,1.0,"open_deck","Wake View Bar terrace")],
 18:[(0.0,1.0,"open_deck","Sports Central / jogging track")],
}
zones=defaultdict(list)
for dk,zl in CANON.items():
    for b0,b1,cls,name in zl: zones[dk].append({"b0":b0,"b1":b1,"cls":cls,"name":name})

ZONE_PEN={"pool_deck":{"above":-25,"below":-12},"galley_buffet":{"above":-18,"below":-20},
 "venue_entertainment":{"above":-20,"below":-20},"dining":{"above":-14,"below":-16},
 "public_general":{"above":-12,"below":-12},"open_deck":{"above":-8,"below":0},
 "crew_service":{"above":-8,"below":-8},"unknown_noncabin":{"above":-12,"below":-12}}
PRIORITY={"pool_deck":5,"galley_buffet":4,"venue_entertainment":3,"dining":2,
          "public_general":1,"open_deck":1,"crew_service":0,"unknown_noncabin":0}
def zone_for(deck,b):
    if deck is None: return {"cls":"open_deck","name":"Open air"}
    best=None
    for z in zones.get(deck,[]):
        if z["b0"]<=b<=z["b1"]:
            if best is None or PRIORITY[z["cls"]]>PRIORITY[best["cls"]]: best=z
    return best or {"cls":"unknown_noncabin","name":f"Deck {deck} non-cabin space"}

VENUE_DECKS={"buffet":16,"pool":16,"hub":5}
rows=[]
for c in d:
    dk=c["deck"]; up,dn=neighbour_deck(dk,True),neighbour_deck(dk,False)
    ca=cabin_at(up,c["side"],c["b"]) if up in CABIN_DECKS else None
    cb=cabin_at(dn,c["side"],c["b"]) if dn in CABIN_DECKS else None
    q=100; notes=[]; above_desc=below_desc="cabins"
    above_class="cabins" if ca else None; below_class="cabins" if cb else None
    if not ca:
        z=zone_for(up,c["b"]); pen=ZONE_PEN[z["cls"]]["above"]; q+=pen
        above_desc=z["name"]; above_class=z["cls"]; notes.append(f"above: {z['name']} ({pen})")
    else: above_desc=f"{ca['number']} ({ca['categoryName']})"
    if not cb:
        z=zone_for(dn,c["b"]); pen=ZONE_PEN[z["cls"]]["below"]; q+=pen
        below_desc=z["name"]; below_class=z["cls"]; notes.append(f"below: {z['name']} ({pen})")
    else: below_desc=f"{cb['number']} ({cb['categoryName']})"
    dlift=min(abs(c["b"]-L) for L in LIFTS)
    dl=min((abs(c["b"]-l) for l in laund.get(dk,[])),default=None)
    if dlift<0.014: q-=10; notes.append("beside lift lobby (-10)")
    elif dlift<0.028: q-=5; notes.append("near lift lobby (-5)")
    if dl is not None:
        if dl<0.018: q-=8; notes.append("beside laundromat (-8)")
        elif dl<0.036: q-=4; notes.append("near laundromat (-4)")
    if c["b"]<0.07 and dk==8: q-=10; notes.append("far forward, lowest cabin deck (-10)")
    if c["b"]>0.93 and dk==8: q-=8; notes.append("far aft, low deck: prop vibration (-8)")
    quiet=max(0,min(100,q))
    stab=max(0,min(100,(100-abs(c["b"]-0.5)*100)-HEIGHT[dk]*2.2))
    lift_s=max(0,100-dlift*300)
    laun_s=max(0,100-dl*600) if dl is not None else 40
    dks=[abs(PIDX[dk]-PIDX[v]) for v in VENUE_DECKS.values()]
    ven_s=max(0,100-(sum(dks)/len(dks))*9)
    conv=max(0,min(100,.45*lift_s+.15*laun_s+.40*ven_s))
    rows.append({"cabin":c["number"],"deck":str(dk),"side":c["side"],"s":c["s"],"b":c["b"],
      "category":c["categoryCode"],"category_class":c["category_class"],"category_confidence":"official",
      "category_name":c["categoryName"],"category_color":c["categoryColor"],
      "area_sqft":c["areaInSqft"],"balcony_sqft":c["balconyAreaInSqft"],"berths":c["berths"],
      "bath":c["bathType"],"connecting":c["connecting"],"accessible":c["accessible"],
      "dist_lift":round(dlift,4),"dist_laundry":round(dl,4) if dl is not None else None,
      "cabin_above":bool(ca),"cabin_below":bool(cb),"above_desc":above_desc,"below_desc":below_desc,
      "above_class":above_class,"below_class":below_class,
      "quiet":round(quiet,1),"stability":round(stab,1),"convenience":round(conv,1),
      "quiet_notes":"; ".join(notes) if notes else "cabins above and below"})

json.dump(rows,open("majestic2/majestic_api_scored.json","w"),indent=1)
print("scored:",len(rows))
print("lifts b:",[round(x,3) for x in LIFTS])
for dim in ("quiet","stability","convenience"):
    v=sorted(r[dim] for r in rows)
    print(f"  {dim:12s} min {v[0]:5.1f} med {v[len(v)//2]:5.1f} max {v[-1]:5.1f}")
worst=sorted(rows,key=lambda r:r["quiet"])[:4]
for r in worst: print(f"   {r['cabin']} d{r['deck']} Q{r['quiet']}: {r['quiet_notes'][:80]}")
print("perfect-quiet:",sum(1 for r in rows if r['quiet']==100))

