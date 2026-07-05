#!/usr/bin/env python3
"""MSC class deck-stack and venue-zone maps for the GCBC scorer.

Structure mirrors pipeline/fleet_classes.py (Princess). Zones were read
visually from the official deck-plan PDFs rendered per deck with a b-ruler
overlay calibrated against the SVG cabin frame (see HARVEST.md). b runs
0=bow to 1=stern. Venue-class vocabulary is identical to Princess ZONE_PEN
so the scorer transfers: pool_deck, galley_buffet, venue_entertainment,
dining, public_general, open_deck, crew_service.

STATUS: meraviglia complete (read from MSC Virtuosa, 5 Jul 2026) — pending
Stuart's judgement pass. Other six classes to be read the same way.
"""

# Ships per class (build order: class then ship)
CLASSES = {
    "lirica":      ["msc-armonia", "msc-lirica", "msc-opera", "msc-sinfonia"],
    "musica":      ["msc-musica", "msc-orchestra", "msc-poesia", "msc-magnifica"],
    "fantasia":    ["msc-fantasia", "msc-splendida", "msc-divina", "msc-preziosa"],
    "meraviglia":  ["msc-meraviglia", "msc-bellissima", "msc-grandiosa",
                    "msc-virtuosa", "msc-euribia"],
    "seaside":     ["msc-seaside", "msc-seaview"],
    "seaside-evo": ["msc-seashore", "msc-seascape"],
    "world":       ["msc-world-europa", "msc-world-america", "msc-world-asia"],
}

# Per class: key venue decks for convenience scoring
CLASS_VENUE_DECKS = {
    "meraviglia": {"buffet": 15, "pool": 15, "hub": 6,   # hub = Galleria level
                   "theatre": 6, "casino": 7, "spa": 7,
                   "lift_b": [0.28, 0.63]},              # lift-bank positions
}

# Per class, per public deck: list of (b0, b1, venue_class, name)
CLASS_ZONES = {
    "meraviglia": {
        4:  [(0.00, 1.00, "crew_service", "Medical / tender / crew")],
        5:  [(0.12, 0.22, "venue_entertainment", "Le Grand Théâtre (lower)"),
             (0.55, 0.66, "public_general", "Infinity Atrium & Reception"),
             (0.70, 0.80, "dining", "Blue Danube"),
             (0.80, 1.00, "crew_service", "Galley / crew (aft)")],
        6:  [(0.12, 0.24, "venue_entertainment", "Le Grand Théâtre"),
             (0.30, 0.65, "venue_entertainment", "Galleria promenade (bars, shops, shows)"),
             (0.66, 0.72, "public_general", "Photo gallery / lifts"),
             (0.72, 0.95, "dining", "The Opera / The Symphony / Minuetto MDRs")],
        7:  [(0.18, 0.28, "public_general", "MSC Aurea Spa"),
             (0.30, 0.36, "venue_entertainment", "Masters of the Sea / TV Studio & Bar"),
             (0.36, 0.60, "dining", "Galleria level: Kaito, Butcher's Cut, Il Campo, Champagne Bars"),
             (0.70, 0.86, "venue_entertainment", "Red Gem Casino"),
             (0.86, 0.96, "venue_entertainment", "Carousel Lounge")],
        # 8–14 are cabin decks (no public zones at cabin level)
        15: [(0.30, 0.60, "pool_deck", "Solarium / Tropical & Atmosphere pools + bars"),
             (0.60, 0.66, "public_general", "Atmosphere bars / lifts"),
             (0.70, 0.97, "galley_buffet", "Marketplace Buffet")],
        16: [(0.12, 0.30, "public_general", "MSC Yacht Club: Top Sail Lounge, concierge (quiet)"),
             (0.30, 0.40, "open_deck", "Solarium"),
             (0.60, 0.68, "public_general", "MSC Gym"),
             (0.68, 0.88, "venue_entertainment", "Arcade / Sportplex / Bowling / Sports Bar"),
             (0.88, 1.00, "pool_deck", "Horizon Amphitheatre & Pool")],
        18: [(0.13, 0.18, "dining", "MSC Yacht Club Restaurant"),
             (0.30, 0.42, "open_deck", "Sliding roof / open deck"),
             (0.58, 0.66, "venue_entertainment", "Sky Lounge"),
             (0.70, 0.88, "venue_entertainment", "Kids complex: Doremiland, clubs, Teens"),
             (0.88, 1.00, "open_deck", "Horizon Bar / Sun Deck")],
        19: [(0.13, 0.30, "pool_deck", "Yacht Club pool, grill, sundeck, whirlpool"),
             (0.58, 0.64, "open_deck", "Top 19 Exclusive Solarium"),
             (0.72, 0.90, "pool_deck", "Savannah Aquapark & Bar / Himalayan Bridge")],
    },
    # lirica / musica / fantasia / seaside / seaside-evo / world: to be read
    # from their PDFs with the same render-and-ruler method.
}

# MSC house rules (applied by the scorer; agreed with Stuart)
# - yacht_club_floor: YC-group cabins get a strong convenience floor — the
#   enclave is self-contained (restaurant, lounge, pool, concierge), so
#   distance to main venues barely matters.
# - aurea_spa_bonus: Aurea-group cabins gain convenience from spa proximity.
# - promenade_view: cabins overlooking indoor promenades (World PR*,
#   Meraviglia Galleria-adjacent) take an evening-noise penalty at the
#   quiet axis, flagged in the cabin note.
