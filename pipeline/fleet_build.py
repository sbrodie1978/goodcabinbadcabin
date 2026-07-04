"""Universal Princess fleet builder. For each ship: registration, geometry-based
above/below, lifts/laundry from numbering, class venue zones, three-dimension
scoring. Outputs fleet_scored.json (all ships) + loads DB + builds slim payload."""
import json, re, statistics
from collections import defaultdict
from fleet_classes import (CLASS_DECKS, CLASS_VENUE_DECKS, CLASS_ZONES,
    ZONE_PEN, PRIORITY, SHIP_CLASS, SHIP_META)

import os
_HERE=os.path.dirname(os.path.abspath(__file__))
_ROOT=os.path.dirname(_HERE)
FLEET = json.load(open(os.path.join(_ROOT,"data-source","princess_fleet_all.json")))
META = {"S":"suite","M":"mini-suite","D":"balcony","B":"balcony","O":"oceanview","I":"interior"}
PROFILES={"balanced":(.40,.30,.30),"light_sleeper":(.55,.20,.25),
          "motion_sensitive":(.20,.55,.25),"everything_nearby":(.15,.15,.70)}

def num_int(n):
    m=re.search(r'\d+', n); return int(m.group()) if m else None

def build_ship(name, info):
    cls = SHIP_CLASS[name]
    cabs = [dict(c) for c in info["cabins"] if c.get("textY") is not None]
    PHYS = CLASS_DECKS[cls]
    PIDX = {d:i for i,d in enumerate(PHYS)}
    cabin_decks = sorted(set(c["deck"] for c in cabs))
    HEIGHT = {d:i for i,d in enumerate(cabin_decks)}
    zones = CLASS_ZONES[cls]
    vdecks = CLASS_VENUE_DECKS[cls]

    ys=[c["textY"] for c in cabs]; YMIN,YMAX=min(ys),max(ys)
    xs=[c["textX"] for c in cabs]; XMID=statistics.median(xs); XMIN,XMAX=min(xs),max(xs)
    for c in cabs:
        c["b0"]=(c["textY"]-YMIN)/(YMAX-YMIN)
        c["side"]="P" if c["textX"]<XMID else "S"
        half=(XMAX-XMID) if c["side"]=="S" else (XMID-XMIN)
        c["s"]=round((c["textX"]-XMID)/half,3) if half else 0
        c["category_class"]=META.get(c["metaCode"],"interior")

    # register decks to the most-populous cabin deck via shared cabin-number suffix
    ref_deck=max(cabin_decks,key=lambda d:sum(1 for c in cabs if c["deck"]==d))
    def suf(n):
        m=re.search(r'(\d{2,3})$', n); return m.group(1) if m else None
    ref={suf(c["number"]):c["b0"] for c in cabs if c["deck"]==ref_deck and suf(c["number"])}
    for dk in cabin_decks:
        pts=[(c["b0"],ref[suf(c["number"])]) for c in cabs if c["deck"]==dk and suf(c["number"]) in ref]
        if len(pts)>=8:
            n=len(pts); sx=sum(p[0] for p in pts); sy=sum(p[1] for p in pts)
            sxx=sum(p[0]**2 for p in pts); sxy=sum(p[0]*p[1] for p in pts)
            den=(n*sxx-sx*sx)
            a=(n*sxy-sx*sy)/den if den else 1; b=(sy-a*sx)/n
        else: a,b=1,0
        for c in cabs:
            if c["deck"]==dk: c["b"]=round(a*c["b0"]+b,4)

    by_ds=defaultdict(list)
    for c in cabs: by_ds[(c["deck"],c["side"])].append(c)
    bref=sorted(c["b"] for c in cabs if c["deck"]==ref_deck)
    gaps=[y-x for x,y in zip(bref,bref[1:]) if 0.0004<y-x<0.02]
    pitch=statistics.median(gaps) if gaps else 0.01
    TOL=pitch*1.4

    def cabin_at(deck,side,b):
        best=None; bd=TOL
        for c in by_ds[(deck,side)]:
            dd=abs(c["b"]-b)
            if dd<bd: bd=dd; best=c
        return best
    def ndeck(deck,up):
        i=PIDX.get(deck)
        if i is None: return None
        i+=(1 if up else -1)
        return PHYS[i] if 0<=i<len(PHYS) else None
    def zone_for(deck,b):
        if deck is None: return {"cls":"open_deck","name":"Open air"}
        best=None
        for z0,z1,zc,zn in zones.get(deck,[]):
            if z0<=b<=z1 and (best is None or PRIORITY[zc]>PRIORITY[best[2]]): best=(z0,z1,zc,zn)
        if best: return {"cls":best[2],"name":best[3]}
        return {"cls":"unknown_noncabin","name":f"Deck {deck} non-cabin space"}

    # lifts: forward/aft from hundreds-block boundaries; mid from 4xx internal gap
    def boundary(lo,hi):
        v=[]
        for dk in cabin_decks:
            L=[c["b"] for c in cabs if c["deck"]==dk and num_int(c["number"]) and num_int(c["number"])//100==lo]
            H=[c["b"] for c in cabs if c["deck"]==dk and num_int(c["number"]) and num_int(c["number"])//100==hi]
            if L and H: v.append((max(L)+min(H))/2)
        return statistics.median(v) if v else None
    lifts=[x for x in (boundary(1,2),boundary(2,3),boundary(6,7)) if x is not None]
    mids=[]
    for dk in cabin_decks:
        bs=sorted(c["b"] for c in cabs if c["deck"]==dk and num_int(c["number"]) and num_int(c["number"])//100==4)
        if len(bs)>6:
            g=max(zip(bs,bs[1:]),key=lambda p:p[1]-p[0])
            if g[1]-g[0]>0.01: mids.append((g[0]+g[1])/2)
    if mids: lifts.append(statistics.median(mids))
    if not lifts: lifts=[0.2,0.5,0.85]

    laund=defaultdict(list)
    for dk in cabin_decks:
        v=[c["b"] for c in cabs if c["deck"]==dk and num_int(c["number"]) and 616<=num_int(c["number"])<=628]
        if v: laund[dk]=[statistics.mean(v)]

    lowest=cabin_decks[0]
    rows=[]
    for c in cabs:
        dk=c["deck"]; up,dn=ndeck(dk,True),ndeck(dk,False)
        ca=cabin_at(up,c["side"],c["b"]) if up in cabin_decks else None
        cb=cabin_at(dn,c["side"],c["b"]) if dn in cabin_decks else None
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
        dlift=min(abs(c["b"]-L) for L in lifts)
        dl=min((abs(c["b"]-l) for l in laund.get(dk,[])),default=None)
        if dlift<0.014: q-=10; notes.append("beside lift lobby (-10)")
        elif dlift<0.028: q-=5; notes.append("near lift lobby (-5)")
        if dl is not None:
            if dl<0.018: q-=8; notes.append("beside laundromat (-8)")
            elif dl<0.036: q-=4; notes.append("near laundromat (-4)")
        if c["b"]<0.07 and dk==lowest: q-=10; notes.append("far forward, lowest cabin deck (-10)")
        if c["b"]>0.93 and dk==lowest: q-=8; notes.append("far aft, low deck: prop vibration (-8)")
        quiet=max(0,min(100,q))

        # ---- MOTION (honest, but asymmetric: aft calmer than bow for pitch) ----
        # fore-aft: bow (b->0) worst, midship (0.5) best, aft (b->1) middling-good.
        # map b to a "distance-from-ideal" where ideal sits slightly aft of midship.
        IDEAL=0.55
        d_fore = c["b"] - IDEAL
        if d_fore < 0:            # forward of ideal: pitch builds quickly toward bow
            longit = 100 - (abs(d_fore)/IDEAL)*70
        else:                      # aft of ideal: gentler falloff, aft never as bad as bow
            longit = 100 - (d_fore/(1-IDEAL))*32
        stab=max(0,min(100, longit - HEIGHT[dk]*1.6))

        # ---- CONVENIENCE (walking distance to lifts/venues; softened for suites) ----
        lift_s=max(0,100-dlift*300)
        laun_s=max(0,100-dl*600) if dl is not None else 40
        dks=[abs(PIDX[dk]-PIDX[v]) for v in vdecks.values() if v in PIDX]
        ven_s=max(0,100-(sum(dks)/len(dks))*9) if dks else 50
        conv_raw=max(0,min(100,.45*lift_s+.15*laun_s+.40*ven_s))
        # suites get priority everything + private lounges: distance matters far less.
        cls=c["category_class"]
        if cls=="suite":       conv=conv_raw*0.4+60      # floor ~60, distance barely counts
        elif cls=="mini-suite":conv=conv_raw*0.7+30
        else:                  conv=conv_raw

        # ---- SPACE & COMFORT (new dimension from real category + sqft data) ----
        base={"suite":88,"mini-suite":72,"balcony":58,"oceanview":42,"interior":30}.get(cls,30)
        sq=c["areaInSqft"] or 0
        sq_bonus=min(20,(sq-160)/720*20) if sq>160 else 0   # 160sqft=0, 880sqft=+20
        bal=c["balconyAreaInSqft"] or 0
        bal_bonus=min(8, bal/250*8) if bal>0 else 0
        space=max(0,min(100, base+sq_bonus+bal_bonus))
        if c["category_class"]=="suite" and c["b"]>0.9:
            notes.append("premium aft suite: large wraparound balcony, secluded")
        rows.append({"cabin":c["number"],"deck":str(dk),"side":c["side"],"s":c["s"],"b":c["b"],
          "category":c["categoryCode"],"category_class":c["category_class"],"category_confidence":"official",
          "category_name":c["categoryName"],"category_color":c["categoryColor"],
          "area_sqft":c["areaInSqft"],"balcony_sqft":c["balconyAreaInSqft"],"berths":c["berths"],
          "bath":c["bathType"],"connecting":c["connecting"],"accessible":c["accessible"],
          "dist_lift":round(dlift,4),"dist_laundry":round(dl,4) if dl is not None else None,
          "cabin_above":bool(ca),"cabin_below":bool(cb),"above_desc":above_desc,"below_desc":below_desc,
          "above_class":above_class,"below_class":below_class,
          "quiet":round(quiet,1),"stability":round(stab,1),"convenience":round(conv,1),"space":round(space,1),
          "quiet_notes":"; ".join(notes) if notes else "cabins above and below"})
    return rows

fleet={}
for name,info in FLEET.items():
    rows=build_ship(name,info)
    fleet[name]=rows
    qs=[r["quiet"] for r in rows]
    print(f"{name:11s} {len(rows):5d} cabins  Q[{min(qs):.0f}-{max(qs):.0f}] "
          f"perfect={sum(1 for q in qs if q==100)}")
json.dump(fleet, open("fleet_scored.json","w"))
print("\nTOTAL:",sum(len(v) for v in fleet.values()),"cabins across",len(fleet),"ships")
