"""Generate slim_fleet.json + per-ship data files + meta, including per-cabin
'surround' visual context (above/below/fore/aft neighbours with category colours)."""
import json, os
from collections import defaultdict
import os
_HERE=os.path.dirname(os.path.abspath(__file__))
_ROOT=os.path.dirname(_HERE)
_DATA=os.path.join(_ROOT,"app","public","princess","data")
from fleet_classes import SHIP_CLASS, SHIP_META

fleet=json.load(open("fleet_scored.json"))
ORDER=["Sun","Star","Royal","Regal","Majestic","Sky","Enchanted","Discovery",
       "Caribbean","Crown","Emerald","Ruby","Grand","Diamond","Sapphire","Coral","Island"]

# zone -> soft colour + short label for non-cabin neighbours
ZONE_VIS={
 "venue_entertainment":("#b0446a","Entertainment venue"),
 "galley_buffet":("#c98a2b","Buffet / galley"),
 "pool_deck":("#3a8fc4","Pool deck"),
 "dining":("#c46a3a","Dining"),
 "public_general":("#8a8f9a","Public area"),
 "open_deck":("#6fae62","Open deck / air"),
 "crew_service":("#7a6f5a","Service area"),
 "unknown_noncabin":("#9aa0a8","Non-cabin space"),
 "cabins":("#cfd6cf","Other cabins"),
}

def surround(rows):
    idx={r["cabin"]:r for r in rows}
    lanes=defaultdict(list)
    for r in rows: lanes[(r["deck"],r["side"])].append(r)
    for k in lanes: lanes[k].sort(key=lambda r:r["b"])
    out={}
    for r in rows:
        lane=lanes[(r["deck"],r["side"])]; i=lane.index(r)
        fwd=lane[i-1] if i>0 else None
        aft=lane[i+1] if i<len(lane)-1 else None
        def av():   # above cell
            if r["cabin_above"]:
                nb=r["above_desc"].split(" (")[0]
                return [nb, "#"+ (idx[nb]["category_color"] if nb in idx else "cfd6cf"), "cabin"]
            col,lab=ZONE_VIS.get(r["above_class"] or "unknown_noncabin",ZONE_VIS["unknown_noncabin"])
            return [r["above_desc"], col, "venue"]
        def bl():
            if r["cabin_below"]:
                nb=r["below_desc"].split(" (")[0]
                return [nb, "#"+ (idx[nb]["category_color"] if nb in idx else "cfd6cf"), "cabin"]
            col,lab=ZONE_VIS.get(r["below_class"] or "unknown_noncabin",ZONE_VIS["unknown_noncabin"])
            return [r["below_desc"], col, "venue"]
        def side(nb):
            if nb: return [nb["cabin"], "#"+nb["category_color"], "cabin"]
            return ["end of row", "#e8e4dc", "end"]
        out[r["cabin"]]=[av(), bl(), side(fwd), side(aft)]
    return out

slim=[]
for sid,name in enumerate(ORDER,1):
    rows=fleet[name]; cls=SHIP_CLASS[name]; disp,gt=SHIP_META[name]
    decks=sorted(set(r["deck"] for r in rows),key=int,reverse=True)
    sur=surround(rows)
    data=[]
    for r in rows:
        s=sur[r["cabin"]]
        data.append([r["cabin"],r["deck"],r["side"],r["b"],r["quiet"],r["stability"],
          r["convenience"],r["category"],r["category_confidence"],r["above_desc"],r["below_desc"],
          r["quiet_notes"],r["area_sqft"],r["berths"],r["category_name"],r.get("space",50),
          "#"+r["category_color"], s, r.get("category_class","interior")])   # 16 colour, 17 surround, 18 type
    slim.append({"id":sid,"line":f"Princess Cruises · {cls} class","name":disp,
     "spec":f"{gt} GT · {len(rows):,} STATEROOMS · OFFICIAL DATA","decks":decks,
     "numstyle":"prefix" if not rows[0]["cabin"][0].isdigit() else "sphere","data":data,"cls":cls})

json.dump(slim,open("slim_fleet.json","w"))
os.makedirs(_DATA,exist_ok=True)
meta=[]
for s in slim:
    json.dump(s["data"],open(os.path.join(_DATA,f"ship-{s['id']}.json"),"w"))
    meta.append({k:v for k,v in s.items() if k!="data"})
json.dump(meta,open("fleet_meta.json","w"))
biggest=max(os.path.getsize(os.path.join(_DATA,f"ship-{s['id']}.json")) for s in slim)
print("payloads regenerated with surround data. largest ship file:",biggest//1024,"KB")
