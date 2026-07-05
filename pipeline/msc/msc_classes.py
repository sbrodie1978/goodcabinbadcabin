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
    "seaside":    {"buffet": 8, "pool": 16, "hub": 6,    # hub = Piazza/atrium
                   "theatre": 6, "casino": 7, "spa": 8,
                   "lift_b": [0.34, 0.64]},
    "seaside-evo": {"buffet": 16, "pool": 18, "hub": 6,  # hub = Times Square
                   "theatre": 6, "casino": 7, "spa": 8,
                   "lift_b": [0.34, 0.64]},
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
    "seaside": {
        4:  [(0.25, 0.35, "public_general", "Medical Centre"),
             (0.35, 0.40, "public_general", "Passenger embarkation (fwd)"),
             (0.65, 0.72, "public_general", "Passenger embarkation (aft)"),
             (0.00, 1.00, "crew_service", "Crew / service deck")],
        5:  [(0.44, 0.62, "public_general", "Art Gallery / Emotions Immersive Gallery"),
             (0.62, 0.68, "public_general", "Atrium: reception, guest services, Seaside Bar"),
             (0.70, 0.81, "dining", "Seashore Restaurant"),
             (0.82, 1.00, "crew_service", "Galley / crew (aft)")],
        6:  [(0.10, 0.27, "crew_service", "Fwd service / theatre understage"),
             (0.28, 0.37, "venue_entertainment", "Metropolitan Theater"),
             (0.40, 0.52, "public_general", "Piazza Grande: shops, Venchi, Mini Mall"),
             (0.58, 0.66, "public_general", "Atrium / Shine Bar / MSC Excursions"),
             (0.70, 0.79, "dining", "Ipanema Restaurant"),
             (0.80, 1.00, "crew_service", "Galley (aft)")],
        7:  [(0.28, 0.36, "venue_entertainment", "Metropolitan Theater (upper)"),
             (0.40, 0.51, "venue_entertainment", "Miami Casino"),
             (0.58, 0.67, "public_general", "Atrium / Champagne Bar"),
             (0.67, 0.80, "venue_entertainment", "XD Cinema / Formula Racer / Arcade & Bowling / Haven Lounge"),
             (0.80, 0.88, "venue_entertainment", "Garage Club / Billiard Room"),
             (0.88, 0.97, "pool_deck", "South Beach Bar & Pool (aft)")],
        8:  [(0.14, 0.36, "public_general", "MSC Aurea Spa complex (thalasso, salon, gym area)"),
             (0.44, 0.56, "public_general", "The Gallery / Sports Bar / The Piazza"),
             (0.56, 0.68, "public_general", "Shops / Atrium / Bistrot La Boheme / Infinity Bridges"),
             (0.68, 0.95, "venue_entertainment", "Waterfront Boardwalk (outdoor, both sides)"),
             (0.70, 0.82, "galley_buffet", "Marketplace Buffet & Bar")],
        # 9-15 cabin decks
        16: [(0.16, 0.21, "public_general", "Top Sail Lounge (Yacht Club, quiet)"),
             (0.32, 0.37, "public_general", "Yacht Club concierge"),
             (0.44, 0.56, "dining", "Ocean Cay / Butcher's Cut / Asian Market Kitchen / Wine & Cocktails"),
             (0.57, 0.67, "galley_buffet", "Biscayne Bay Restaurant & Buffet"),
             (0.68, 0.87, "pool_deck", "Miami Beach Bar, Pool & Sun Deck"),
             (0.87, 0.92, "public_general", "Panoramic lift / Bridge of Sighs")],
        18: [(0.14, 0.19, "dining", "MSC Yacht Club Restaurant"),
             (0.42, 0.56, "pool_deck", "Jungle Pool (Magnodome), Lounge & Bar"),
             (0.58, 0.74, "venue_entertainment", "Forest Aquaventure Park + kids clubs (Doremi, Teen, Young)")],
        19: [(0.14, 0.33, "pool_deck", "Yacht Club Sundeck, Grill & Bar, Pool, whirlpools"),
             (0.33, 0.38, "public_general", "Aurea Bar"),
             (0.38, 0.56, "open_deck", "Top 19 Exclusive Solarium / sun deck"),
             (0.56, 0.70, "venue_entertainment", "Zip line / Aquaventure (upper)"),
             (0.70, 0.74, "public_general", "Miramar Bar")],
        20: [(0.20, 0.36, "open_deck", "Sun deck (fwd)"),
             (0.60, 0.76, "venue_entertainment", "Adventure Trail / MSC Sports Arena / waterslides")],
    },
    "seaside-evo": {
        4:  [(0.25, 0.35, "public_general", "Medical Centre"),
             (0.35, 0.40, "public_general", "Passenger embarkation (fwd)"),
             (0.65, 0.72, "public_general", "Passenger embarkation (aft)"),
             (0.00, 1.00, "crew_service", "Crew / service deck")],
        5:  [(0.50, 0.62, "public_general", "MSC Foundation / Hub / Emotions Immersive Gallery"),
             (0.63, 0.68, "public_general", "Atrium: reception, Seashore Bar"),
             (0.70, 0.82, "dining", "Central Park Restaurant"),
             (0.83, 1.00, "crew_service", "Galley / crew (aft)")],
        6:  [(0.10, 0.26, "crew_service", "Fwd service / theatre understage"),
             (0.27, 0.36, "venue_entertainment", "Madison Theater"),
             (0.42, 0.53, "public_general", "Times Square: shops, Venchi, duty free"),
             (0.58, 0.67, "public_general", "Atrium / Shine Bar / MSC Excursions"),
             (0.70, 0.80, "dining", "Main restaurant"),
             (0.88, 0.97, "venue_entertainment", "Le Cabaret Rouge")],
        7:  [(0.27, 0.35, "venue_entertainment", "Madison Theater (upper)"),
             (0.42, 0.56, "venue_entertainment", "MSC Signature Casino"),
             (0.64, 0.70, "public_general", "Wine bar / atrium"),
             (0.70, 0.80, "dining", "5th Avenue Restaurant / Manhattan"),
             (0.80, 0.88, "venue_entertainment", "Boulevard du Cabaret"),
             (0.88, 0.97, "venue_entertainment", "Le Cabaret Rouge (upper)")],
        8:  [(0.14, 0.35, "public_general", "MSC Aurea Spa + Gym complex"),
             (0.42, 0.62, "public_general", "Liberty Plaza / Sports Bar / shops / Waterfront Promenade"),
             (0.62, 0.68, "public_general", "HOLA! / Art Gallery / Infinity Bridges"),
             (0.68, 0.82, "dining", "Chef's Court: Kaito, Ocean Cay, Butcher's Cut / Wine Cellar / Cocktail Bar"),
             (0.84, 0.90, "venue_entertainment", "Uptown Lounge"),
             (0.90, 0.97, "pool_deck", "Infinity Pool & Bar (aft)")],
        # 9-15 cabin decks
        16: [(0.16, 0.20, "public_general", "Top Sail Lounge (Yacht Club, quiet)"),
             (0.41, 0.53, "pool_deck", "Jungle Pool Lounge & Beach Bar (Magnodome)"),
             (0.55, 0.72, "galley_buffet", "Marketplace Buffet & Restaurant"),
             (0.76, 0.82, "public_general", "Sky Bar / Bridge of Sighs")],
        18: [(0.15, 0.20, "dining", "MSC Yacht Club Restaurant"),
             (0.43, 0.52, "pool_deck", "Jungle Pool Lounge (upper)"),
             (0.52, 0.64, "venue_entertainment", "Kids clubs: Doremi, Mini, Junior, Teen / The Studio"),
             (0.64, 0.75, "venue_entertainment", "Pirates Cove Aquapark / Hall of Games"),
             (0.82, 0.90, "pool_deck", "Long Island Pool (aft)")],
        19: [(0.12, 0.17, "pool_deck", "Yacht Club sundeck / whirlpools (VERIFY extent)"),
             (0.62, 0.66, "public_general", "MSC Aurea Bar"),
             (0.66, 0.76, "open_deck", "Top 19 Exclusive Solarium"),
             (0.76, 0.84, "venue_entertainment", "Adventure Trail"),
             (0.84, 0.88, "public_general", "Horizon Bar")],
        20: [(0.20, 0.35, "open_deck", "Sun deck (fwd)"),
             (0.60, 0.76, "venue_entertainment", "Sports court / waterslides")],
    },
    # lirica / musica / fantasia / world: to be read from their PDFs with
    # the same render-and-ruler method.
}

# MSC house rules (applied by the scorer; agreed with Stuart)
# - yacht_club_floor: YC-group cabins get a strong convenience floor — the
#   enclave is self-contained (restaurant, lounge, pool, concierge), so
#   distance to main venues barely matters.
# - aurea_spa_bonus: Aurea-group cabins gain convenience from spa proximity.
# - promenade_view: cabins overlooking indoor promenades (World PR*,
#   Meraviglia Galleria-adjacent) take an evening-noise penalty at the
#   quiet axis, flagged in the cabin note.
