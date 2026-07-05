#!/usr/bin/env python3
"""MSC category classification + ship metadata for the GCBC scorer.

MSC's public data gives us a legend slug per cabin (e.g. 'deluxe-balcony',
'yc-grand-suite') plus its category group, but no square footage, berth counts
or official display names. This module turns a slug+group into:
  - type:  one of interior / oceanview / balcony / suite  (the app's filter +
           per-type ranking vocabulary; MSC has no Princess-style mini-suite)
  - base:  a space-score base (0-100) by finer tier
  - yc:    True for MSC Yacht Club cabins (self-contained enclave -> conv floor)
  - aurea: True for Aurea experience cabins (spa-adjacency bonus)
  - name:  a human display name derived from the slug
"""
import re

# --- Yacht Club / Aurea group detection ---------------------------------
YC_GROUPS = {"msc-yacht-club", "msc-yc", "yacht-club"}


def is_yc(slug, groups):
    return (any(g in YC_GROUPS for g in groups)
            or slug.startswith("yc-") or "yacht-club" in slug)


def is_aurea(slug, groups):
    return "aurea" in groups or "aurea" in slug or slug in ("psa", "gsa-tw")


# --- type (4-way, matches the app's TYPE_ORDER minus mini-suite) ---------
_SUITE_HINTS = ("suite", "duplex", "owner", "royal", "two-bedroom", "psa",
                "gsa", "-family", "executive")
_BALC_HINTS = ("balcony", "-pv")
_OV_HINTS = ("ocean-view", "oceanview", "-ov", "dov", "pov", "sea-view")
_INT_HINTS = ("interior", "studio-interior", "si-", "di-", "-interior")


def cabin_type(slug, groups):
    s = slug.lower()
    if is_yc(s, groups):
        return "suite"                       # every Yacht Club room is a suite grade
    if any(h in s for h in _SUITE_HINTS):
        return "suite"
    if "balcony" in s or s.endswith("-pv") or "promenade-view" in s \
       or any(g in ("balcony", "balcony-sum25") for g in groups):
        return "balcony"
    if any(h in s for h in _OV_HINTS) or "infinite-ocean-view" in s \
       or "ocean-view" in groups:
        return "oceanview"
    if any(h in s for h in _INT_HINTS) or "interior" in groups:
        return "interior"
    # group fallback
    for g in groups:
        if "suite" in g:
            return "suite"
        if "balcony" in g:
            return "balcony"
        if "ocean" in g:
            return "oceanview"
    return "interior"


# --- space base by finer tier ------------------------------------------
def space_base(slug, groups):
    s = slug.lower()
    yc = is_yc(s, groups)
    top = ("royal", "owner", "duplex", "grand", "executive", "-family",
           "two-bedroom")
    if any(h in s for h in top):
        return 92 if yc else 88
    if "suite" in s or s in ("psa", "gsa-tw"):
        if "junior" in s or "interior-suite" in s:
            return 70
        return 86 if yc else 84
    if "balcony" in s or "promenade-view" in s or s.endswith("-pv"):
        if "junior" in s or "studio" in s:
            return 52
        if "aurea" in s:
            return 62                         # Aurea balconies are larger + spa access
        return 58
    if "ocean-view" in s or s.endswith("-ov") or s in ("dov", "pov") \
       or "infinite-ocean-view" in s:
        if "obstructed" in s:
            return 36
        if "junior" in s or "studio" in s:
            return 40
        return 44
    # interior
    if "junior" in s or "studio" in s:
        return 26
    return 30


def display_name(slug):
    """'yc-grand-suite-two-room' -> 'YC Grand Suite Two Room'."""
    words = []
    for w in slug.replace("_", "-").split("-"):
        if not w:
            continue
        if w in ("yc",):
            words.append("YC")
        elif w in ("ov", "pv", "tw"):
            words.append(w.upper())
        elif re.fullmatch(r"\d+", w):
            words.append(w)
        else:
            words.append(w.capitalize())
    return " ".join(words) or "Stateroom"


# --- ship metadata: (display name, gross tonnage, class) ----------------
# GT from MSC published specifications.
MSC_META = {
    # World class
    "msc-world-europa":  ("MSC World Europa",  215863, "world"),
    "msc-world-america": ("MSC World America", 216638, "world"),
    "msc-world-asia":    ("MSC World Asia",    216638, "world"),
    # Seaside EVO
    "msc-seascape":      ("MSC Seascape",      170412, "seaside-evo"),
    "msc-seashore":      ("MSC Seashore",      169380, "seaside-evo"),
    # Seaside
    "msc-seaview":       ("MSC Seaview",       153516, "seaside"),
    "msc-seaside":       ("MSC Seaside",       153516, "seaside"),
    # Meraviglia
    "msc-euribia":       ("MSC Euribia",       184011, "meraviglia"),
    "msc-virtuosa":      ("MSC Virtuosa",      181541, "meraviglia"),
    "msc-grandiosa":     ("MSC Grandiosa",     181541, "meraviglia"),
    "msc-bellissima":    ("MSC Bellissima",    171598, "meraviglia"),
    "msc-meraviglia":    ("MSC Meraviglia",    171598, "meraviglia"),
    # Fantasia
    "msc-preziosa":      ("MSC Preziosa",      139072, "fantasia"),
    "msc-divina":        ("MSC Divina",        139072, "fantasia"),
    "msc-splendida":     ("MSC Splendida",     137936, "fantasia"),
    "msc-fantasia":      ("MSC Fantasia",      137936, "fantasia"),
    # Musica
    "msc-magnifica":     ("MSC Magnifica",      95128, "musica"),
    "msc-poesia":        ("MSC Poesia",         92627, "musica"),
    "msc-orchestra":     ("MSC Orchestra",      92409, "musica"),
    "msc-musica":        ("MSC Musica",         92409, "musica"),
    # Lirica
    "msc-sinfonia":      ("MSC Sinfonia",       65542, "lirica"),
    "msc-opera":         ("MSC Opera",          65591, "lirica"),
    "msc-lirica":        ("MSC Lirica",         65591, "lirica"),
    "msc-armonia":       ("MSC Armonia",        65542, "lirica"),
}

# Picker build order: newest class first, newest ship first within class.
SHIP_ORDER = [
    "msc-world-europa", "msc-world-america", "msc-world-asia",
    "msc-seascape", "msc-seashore",
    "msc-seaview", "msc-seaside",
    "msc-euribia", "msc-virtuosa", "msc-grandiosa", "msc-bellissima", "msc-meraviglia",
    "msc-preziosa", "msc-divina", "msc-splendida", "msc-fantasia",
    "msc-magnifica", "msc-poesia", "msc-orchestra", "msc-musica",
    "msc-sinfonia", "msc-opera", "msc-lirica", "msc-armonia",
]

CLASS_DISPLAY = {
    "world": "World", "seaside-evo": "Seaside EVO", "seaside": "Seaside",
    "meraviglia": "Meraviglia", "fantasia": "Fantasia", "musica": "Musica",
    "lirica": "Lirica",
}
