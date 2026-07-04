"""Arvia (P&O) pipeline — extraction, auto-gazetteer, geometry, scoring.
Deck columns are pre-aligned per page; page 2 is offset +26pt to page 1's frame."""
import pdfplumber, re, json, statistics
from collections import defaultdict, Counter

PAGE2_OFFSET = 553 - 527   # align page-2 frame to page-1 via stacked launderettes
CABIN_DECKS = ["4","5","8","9","10","11","12","14","15","16","17"]
PHYS = ["3","4","5","6","7","8","9","10","11","12","14","15","16","17","18","19"]

pdf = pdfplumber.open("/mnt/user-data/uploads/Arvia-Deck-Plan-W26-27.pdf")

cabins = []       # {num, deck, x, y(shipframe)}
labels = []       # {text, x, y, page}
for pno, page in enumerate(pdf.pages):
    dy = PAGE2_OFFSET if pno == 1 else 0
    words = page.extract_words()
    # join orphan "NN." + "NNN" pairs
    orphA = [w for w in words if re.fullmatch(r"\d{1,2}\.", w["text"].strip())]
    orphB = [w for w in words if re.fullmatch(r"\d{3}", w["text"].strip())]
    used = set()
    joined = []
    for a in orphA:
        ay = (a["top"]+a["bottom"])/2
        best = None
        for b in orphB:
            if id(b) in used: continue
            by = (b["top"]+b["bottom"])/2
            dx = b["x0"] - a["x1"]; dyy = abs(by - ay)
            if -4 <= dx <= 22 and dyy < 7:
                if best is None or dx < best[0]: best = (dx, b)
        if best:
            used.add(id(best[1]))
            joined.append((a["text"].strip()+best[1]["text"].strip(),
                           (a["x0"]+best[1]["x1"])/2, ( (a["top"]+a["bottom"])/2 + (best[1]["top"]+best[1]["bottom"])/2 )/2))
    for w in words:
        t = w["text"].strip()
        m = re.fullmatch(r"(\d{1,2})\.\s?(\d{3})", t)
        cx, cy = (w["x0"]+w["x1"])/2, (w["top"]+w["bottom"])/2
        if m and m.group(1) in CABIN_DECKS:
            cabins.append({"num": f"{m.group(1)}.{m.group(2)}", "deck": m.group(1), "x": cx, "y": cy+dy, "page": pno})
        elif re.fullmatch(r"[A-Z][A-Z'’&é0-9]{2,}", t) or t in ("Launderette","Whirlpool"):
            labels.append({"t": t, "x": cx, "y": cy+dy, "page": pno})
    for t, x, y in joined:
        m = re.fullmatch(r"(\d{1,2})\.(\d{3})", t)
        if m and m.group(1) in CABIN_DECKS:
            cabins.append({"num": f"{m.group(1)}.{m.group(2)}", "deck": m.group(1), "x": x, "y": y+dy, "page": pno})

# drop notes-text stragglers: keep the page where each deck has most tokens
page_of = {}
cnt = Counter((c["deck"], c["page"]) for c in cabins)
for d in CABIN_DECKS:
    page_of[d] = max((p for dd,p in cnt if dd==d), key=lambda p: cnt[(d,p)])
cabins = [c for c in cabins if c["page"] == page_of[c["deck"]]]
# dedupe identical numbers keeping first
seen = {}
dupes = []
for c in cabins:
    if c["num"] in seen: dupes.append(c["num"])
    else: seen[c["num"]] = c
cabins = list(seen.values())
print("cabins:", len(cabins), " dupes dropped:", Counter(dupes))
per = Counter(c["deck"] for c in cabins)
print("per deck:", dict(sorted(per.items(), key=lambda x:int(x[0]))))

# deck column x-windows (from cabins; wider for venue capture)
cols = {}
for d in CABIN_DECKS:
    xs = [c["x"] for c in cabins if c["deck"]==d]
    cols[d] = {"x0": min(xs)-38, "x1": max(xs)+38, "cx": statistics.median(xs), "page": page_of[d]}
# public decks share the page-frame; find their columns from "Deck N" title labels
title_cols = {}
for pno, page in enumerate(pdf.pages):
    ws = page.extract_words()
    for i,w in enumerate(ws):
        if w["text"]=="Deck" and i+1<len(ws) and re.fullmatch(r"\d{1,2}", ws[i+1]["text"]):
            d = ws[i+1]["text"]
            title_cols.setdefault(d, {"x": (w["x0"]+ws[i+1]["x1"])/2, "page": pno})
print("deck title labels found:", sorted(title_cols, key=int))

# orientation: are .1xx cabins at low y (top) or high y?
y1 = statistics.mean(c["y"] for c in cabins if c["num"].split(".")[1].startswith("1"))
y7 = statistics.mean(c["y"] for c in cabins if c["num"].split(".")[1].startswith("7"))
bow_at_top = y1 < y7
print(f"mean y of .1xx={y1:.0f}  .7xx={y7:.0f}  -> bow at {'top' if bow_at_top else 'bottom'}")

ys = [c["y"] for c in cabins]
ymin, ymax = min(ys), max(ys)
for c in cabins:
    b = (c["y"]-ymin)/(ymax-ymin)
    c["b"] = round(b if bow_at_top else 1-b, 4)
    # bow-up plan: left = port; bow-down: left = starboard
    left = c["x"] < cols[c["deck"]]["cx"]
    c["side"] = ("P" if left else "S") if bow_at_top else ("S" if left else "P")

oddP = sum(1 for c in cabins if int(c["num"].split(".")[1])%2==1 and c["side"]=="P")
oddS = sum(1 for c in cabins if int(c["num"].split(".")[1])%2==1 and c["side"]=="S")
print(f"odd cabins: port={oddP} starboard={oddS}")

# ---- venue labels -> zones per deck ----
KEYWORDS = [
 (("POOL","SPLASH","LIDO","INFINITY","BEACHCOMBER","PANORAMA"), "pool_deck"),
 (("HORIZON",), "galley_buffet"),   # buffet
 (("THEATRE","CASINO","CLUB","BAR","STAGE","SCENE","LIMELIGHT","HEADLINERS","BRODIE","710","SKY"), "venue_entertainment"),
 (("RESTAURANT","DINER","DINING","CAFÉ","CAFE","GRILL","EPICUREAN","SINDHU","OLIVE","ZENITH","MERIDIAN","QUAYS","KEEL","GREEN","BEACH","TASTE","SUNDAES","RIPPLES","GLASS","VISTAS","MIZUHANA"), "dining"),
 (("SHOP","SHOPPING","GALLERY","RECEPTION","ATRIUM","PHOTO","LOYALTY","EXPERIENCES","MISSION","STUDIOS","AVENUE","ART"), "public_general"),
 (("GYM","SPA","THERMAL","TREATMENT","STUDIO","CHANGING","OASIS"), "public_general"),
 (("NURSERY","REEF","SCUBAS","SPLASHERS","SURFERS"), "public_general"),
 (("SUNBATHING","SUN","SPORTS","ARENA","GOLF","JOGGING","SKYWALK","GAMES","RETREAT","ALTITUDE","CROW","NEST"), "open_deck"),
 (("MEDICAL","CONTROL","BOARDING","EXIT"), "crew_service"),
 (("LAUNDERETTE",), "launderette"),
 (("WHIRLPOOL",), "pool_deck"),
]
def classify(t):
    T = t.upper().replace("’","'")
    for keys, cls in KEYWORDS:
        if any(k in T for k in keys): return cls
    return None

# assign labels to a deck: page + x-window (cabin decks) or nearest title column (public decks)
PUBLIC = [d for d in PHYS if d not in CABIN_DECKS]
zone_labels = defaultdict(list)
for L in labels:
    cls = classify(L["t"])
    if not cls: continue
    hit = None
    for d, w in cols.items():
        if w["page"]==L["page"] and w["x0"]<=L["x"]<=w["x1"]: hit=d; break
    if hit is None:
        # public deck columns: nearest title on same page within 90pt
        best=None
        for d,tc in title_cols.items():
            if d in CABIN_DECKS: continue
            if tc["page"]==L["page"]:
                dist=abs(tc["x"]-L["x"])
                if dist<90 and (best is None or dist<best[0]): best=(dist,d)
        if best: hit=best[1]
    if hit:
        zone_labels[hit].append({"name":L["t"],"cls":cls,"b":round(((L["y"]-ymin)/(ymax-ymin)) if bow_at_top else 1-((L["y"]-ymin)/(ymax-ymin)),4)})

# launderette positions per deck (b coords)
laund = {d:[z["b"] for z in zs if z["cls"]=="launderette"] for d,zs in zone_labels.items()}
print("launderettes:", {d:[round(b,3) for b in v] for d,v in sorted(laund.items(), key=lambda kv:int(kv[0])) if v})

# phrase-join raw uppercase words per deck column before zoning
phrases = defaultdict(list)
for L in labels:
    hit=None
    for d,w in cols.items():
        if w["page"]==L["page"] and w["x0"]<=L["x"]<=w["x1"]: hit=d; break
    if hit is None:
        best=None
        for d,tc in title_cols.items():
            if d in CABIN_DECKS: continue
            if tc["page"]==L["page"]:
                dist=abs(tc["x"]-L["x"])
                if dist<90 and (best is None or dist<best[0]): best=(dist,d)
        if best: hit=best[1]
    if hit and re.fullmatch(r"[A-Z0-9][A-Z0-9'’&é]{1,}|Launderette|Whirlpool", L["t"]):
        phrases[hit].append(L)
joined = defaultdict(list)
for d, ls in phrases.items():
    ls.sort(key=lambda l:(round(l["y"]/6), l["x"]))
    cur=[ls[0]]
    for l in ls[1:]:
        if abs(l["y"]-cur[-1]["y"])<5 and 0<l["x"]-cur[-1]["x"]<70:
            cur.append(l)
        else:
            joined[d].append(cur); cur=[l]
    joined[d].append(cur)

GOOD = re.compile(r"^[A-Z0-9'’&é\. ]+$")
zones = defaultdict(list)
for d, groups in joined.items():
    for g in groups:
        name = " ".join(x["t"] for x in g)
        cls = classify(name)
        if not cls or cls=="launderette": continue
        b = round(sum((((x["y"]-ymin)/(ymax-ymin)) if bow_at_top else 1-((x["y"]-ymin)/(ymax-ymin))) for x in g)/len(g),4)
        # garble guard: token with no vowels or >14 chars single word -> generic name
        disp = name.title().replace("’","'")
        if any(len(w)>=13 or not re.search(r"[AEIOU]", w) for w in name.split()):
            disp = {"pool_deck":"Pool/bar area","galley_buffet":"Buffet/galley area",
                    "venue_entertainment":"Bar/venue","dining":"Restaurant/bar",
                    "public_general":"Public area","open_deck":"Open deck",
                    "crew_service":"Service area"}[cls]
        zones[d].append({"b0":b-0.022,"b1":b+0.022,"cls":cls,"name":disp})
# launderette blocks are non-cabin on every deck at the same b: name them for above/below lookups
for d, bs2 in laund.items():
    for b in bs2:
        zones[d].append({"b0":b-0.02,"b1":b+0.02,"cls":"public_general","name":"Launderette / lift lobby block"})
# ---- recover any numbers present in raw text but not extracted: interpolate from numeric neighbours ----
alltext = " ".join(p.extract_text() for p in pdf.pages)
found = set()
for m in re.finditer(r"(\d{1,2})\.\s*(\d{3})", alltext):
    if m.group(1) in CABIN_DECKS: found.add(f"{m.group(1)}.{m.group(2)}")
have = {c["num"] for c in cabins}
bynum = {c["num"]: c for c in cabins}
recovered = []
for _pass in range(4):
  progress=False
  for num in sorted(found - {c["num"] for c in cabins}):
    d, tail = num.split("."); n = int(tail)
    cands = []
    for off in (2,-2,4,-4,6,-6):
        nb = bynum.get(f"{d}.{n+off:03d}")
        if nb: cands.append((abs(off), nb, off))
    if len(cands) >= 1:
        cands.sort(key=lambda t: t[0])
        if len(cands) >= 2 and cands[0][2]*cands[1][2] < 0:
            a,b2 = cands[0][1], cands[1][1]
            wa = cands[1][0]/(cands[0][0]+cands[1][0])
            x = a["x"]*wa + b2["x"]*(1-wa); y = a["y"]*wa + b2["y"]*(1-wa)
        else:
            nb, off = cands[0][1], cands[0][2]
            step = 9 if off>0 else -9   # approx one cabin pitch in pts
            x, y = nb["x"], nb["y"] + step*(abs(off)//2)*(1 if off>0 else -1)
        b = (y-ymin)/(ymax-ymin); b = b if bow_at_top else 1-b
        c = {"num":num,"deck":d,"x":x,"y":y,"b":round(b,4),
             "side":"S" if n%2==1 else "P","estimated":True,"page":page_of[d]}
        cabins.append(c); bynum[num]=c; recovered.append(num); progress=True
  if not progress: break
print("recovered by interpolation:", len(recovered))
json.dump({"zones":zones,"launderettes":laund}, open("arvia_zones.json","w"), indent=1)
json.dump(cabins, open("arvia_cabins_raw.json","w"), indent=1)
print("zones per deck:", {d:len(z) for d,z in sorted(zones.items(), key=lambda kv:int(kv[0]))})
