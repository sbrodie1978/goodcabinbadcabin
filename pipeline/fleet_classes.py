"""Princess fleet class definitions: physical deck stacks and venue zones.
Venue zones are in b-frame (0=forward .. 1=aft) per public deck, derived from each
class's documented public-area layout. Cabin decks come from the data itself."""

# Physical deck ordering (bottom->top) for height/neighbour logic, per class.
# Includes public decks so above/below can point at real venues.
CLASS_DECKS = {
 "Royal":  [4,5,6,7,8,9,10,11,12,14,15,16,17,18,19],
 "Sphere": [4,5,6,7,8,9,10,11,12,14,15,16,17,18,19,20,21],
 "Grand":  [4,5,6,7,8,9,10,11,12,14,15,16,17,18,19],
 "Coral":  [4,5,6,7,8,9,10,11,12,14,15,16,17],
}

# Venue decks used for the convenience metric (buffet / pool / main hub).
CLASS_VENUE_DECKS = {
 "Royal":  {"buffet":16,"pool":16,"hub":5},
 "Sphere": {"buffet":9, "pool":17,"hub":7},   # Sun/Star: Eatery buffet d9, pools d17/18, Piazza d7
 "Grand":  {"buffet":14,"pool":14,"hub":7},   # Horizon Court buffet d14/15, pools d14, Piazza d7
 "Coral":  {"buffet":14,"pool":14,"hub":7},   # Horizon Court d14, pools d14, Atrium d7
}

# Venue zones per public deck, in b-frame. cls in
# {pool_deck,galley_buffet,venue_entertainment,dining,public_general,open_deck,crew_service}
ZONE_PEN={"pool_deck":{"above":-25,"below":-12},"galley_buffet":{"above":-18,"below":-20},
 "venue_entertainment":{"above":-20,"below":-20},"dining":{"above":-14,"below":-16},
 "public_general":{"above":-12,"below":-12},"open_deck":{"above":-8,"below":0},
 "crew_service":{"above":-8,"below":-8},"unknown_noncabin":{"above":-12,"below":-12}}
PRIORITY={"pool_deck":5,"galley_buffet":4,"venue_entertainment":3,"dining":2,
          "public_general":1,"open_deck":1,"crew_service":0,"unknown_noncabin":0}

CLASS_ZONES = {
 # ---- ROYAL class (Royal/Regal/Majestic/Sky/Enchanted/Discovery) ----
 "Royal": {
   7:[(0.0,0.20,"venue_entertainment","Princess Theater (upper)"),
      (0.20,0.42,"public_general","Shops / atrium"),
      (0.42,0.55,"dining","Ocean Terrace / specialty dining"),
      (0.55,0.72,"venue_entertainment","Princess Live! & Crown Grill"),
      (0.72,0.86,"public_general","Photo gallery"),
      (0.86,1.0,"venue_entertainment","Vista Lounge")],
   6:[(0.0,0.20,"venue_entertainment","Princess Theater (lower)"),
      (0.20,0.40,"venue_entertainment","Casino / bars"),
      (0.40,0.62,"dining","Atrium dining (Alfredo's / Bellini's)"),
      (0.62,0.82,"dining","Main Dining Room (fwd)"),
      (0.82,1.0,"dining","Main Dining Room (aft)")],
   5:[(0.15,0.35,"public_general","Lotus Spa & fitness"),
      (0.35,0.62,"public_general","The Piazza / guest services"),
      (0.62,1.0,"dining","Main Dining Room")],
   17:[(0.0,0.22,"pool_deck","Conservatory / enclosed pool"),
       (0.22,0.42,"pool_deck","Retreat / adult pool"),
       (0.42,0.75,"open_deck","Sun deck / Movies Under the Stars"),
       (0.75,1.0,"open_deck","Sports terraces")],
   16:[(0.30,0.56,"pool_deck","Main pools & fountains"),
       (0.56,0.62,"public_general","Panoramic lift lobby"),
       (0.62,0.86,"galley_buffet","World Fresh Marketplace / buffet"),
       (0.86,1.0,"open_deck","Aft terrace")],
   18:[(0.0,1.0,"open_deck","Sports Central / jogging track")],
 },
 # ---- SPHERE class (Sun/Star) — Dome, Piazza spanning 6-8, Eatery buffet d9 ----
 "Sphere": {
   7:[(0.0,0.30,"venue_entertainment","Princess Arena (theatre)"),
      (0.30,0.55,"public_general","Piazza atrium & shops"),
      (0.55,0.78,"dining","Americana Diner / specialty"),
      (0.78,1.0,"venue_entertainment","Take Five / Crooners bars")],
   8:[(0.0,0.30,"venue_entertainment","Princess Arena (upper)"),
      (0.30,0.55,"public_general","Piazza (upper) / casino"),
      (0.55,0.80,"dining","Main dining rooms"),
      (0.80,1.0,"dining","Main dining (aft)")],
   9:[(0.0,0.30,"public_general","Signature suite lounge / fwd"),
      (0.30,0.72,"galley_buffet","The Eatery (buffet)"),
      (0.72,1.0,"dining","O'Malley's / aft dining")],
   17:[(0.0,0.28,"pool_deck","The Dome (pool/venue)"),
       (0.28,0.60,"pool_deck","Resort-style pools"),
       (0.60,1.0,"open_deck","Sun deck / sports")],
   18:[(0.0,0.35,"open_deck","Sanctuary / sun terraces"),
       (0.35,1.0,"open_deck","Sports deck")],
   16:[(0.0,1.0,"public_general","Reserve Collection lounge / spa")],
 },
 # ---- GRAND class (Caribbean/Crown/Emerald/Ruby/Grand/Diamond/Sapphire) ----
 # Piazza d5-7, theatre fwd, Horizon Court buffet d14 aft, pools d14 midship
 "Grand": {
   7:[(0.0,0.22,"venue_entertainment","Princess Theater (upper)"),
      (0.22,0.50,"public_general","Piazza / shops / casino"),
      (0.50,0.75,"dining","Specialty dining / bars"),
      (0.75,1.0,"venue_entertainment","Aft lounge (Vista/Explorers)")],
   6:[(0.0,0.22,"venue_entertainment","Princess Theater (lower)"),
      (0.22,0.50,"venue_entertainment","Casino / Piazza"),
      (0.50,1.0,"dining","Main Dining Rooms")],
   5:[(0.0,0.30,"public_general","Fwd public / medical"),
      (0.30,0.55,"public_general","Atrium / guest services"),
      (0.55,1.0,"dining","Michelangelo / Botticelli dining")],
   14:[(0.0,0.20,"open_deck","Fwd sun deck"),
       (0.20,0.55,"pool_deck","Neptune's Reef & pools"),
       (0.55,0.60,"public_general","Lift lobby"),
       (0.60,0.90,"galley_buffet","Horizon Court buffet"),
       (0.90,1.0,"open_deck","Terrace pool (aft)")],
   15:[(0.0,0.30,"public_general","Sanctuary / spa"),
       (0.30,0.70,"open_deck","Sun deck / Movies Under the Stars"),
       (0.70,1.0,"galley_buffet","Horizon Court (upper)")],
   16:[(0.0,1.0,"open_deck","Sports deck / Skywalkers")],
 },
 # ---- CORAL class (Coral/Island) — smaller; Universe Lounge, buffet d14 ----
 "Coral": {
   7:[(0.0,0.25,"venue_entertainment","Princess Theater"),
      (0.25,0.55,"public_general","Atrium / shops / casino"),
      (0.55,0.80,"dining","Bayou Cafe / specialty"),
      (0.80,1.0,"venue_entertainment","Explorers / Wheelhouse")],
   6:[(0.0,0.25,"venue_entertainment","Princess Theater (lower)"),
      (0.25,0.55,"venue_entertainment","Casino / lounges"),
      (0.55,1.0,"dining","Provence Dining Room")],
   5:[(0.0,0.35,"public_general","Fwd public / medical"),
      (0.35,0.60,"public_general","Atrium / guest services"),
      (0.60,1.0,"venue_entertainment","Universe Lounge / dining")],
   14:[(0.0,0.25,"open_deck","Fwd sun deck"),
       (0.25,0.58,"pool_deck","Calypso Reef & pools"),
       (0.58,0.63,"public_general","Lift lobby"),
       (0.63,0.92,"galley_buffet","Horizon Court buffet"),
       (0.92,1.0,"open_deck","Aft terrace")],
   15:[(0.0,0.40,"public_general","Spa / Lotus"),
       (0.40,1.0,"open_deck","Sun deck / sports")],
 },
}

SHIP_CLASS = {
 "Sun":"Sphere","Star":"Sphere",
 "Royal":"Royal","Regal":"Royal","Majestic":"Royal","Sky":"Royal","Enchanted":"Royal","Discovery":"Royal",
 "Caribbean":"Grand","Crown":"Grand","Emerald":"Grand","Ruby":"Grand","Grand":"Grand","Diamond":"Grand","Sapphire":"Grand",
 "Coral":"Coral","Island":"Coral",
}
SHIP_META = {  # (line display name, GT, marketing full name)
 "Sun":("Sun Princess","175,500"),"Star":("Star Princess","177,882"),
 "Royal":("Royal Princess","142,229"),"Regal":("Regal Princess","142,714"),
 "Majestic":("Majestic Princess","143,700"),"Sky":("Sky Princess","145,281"),
 "Enchanted":("Enchanted Princess","145,281"),"Discovery":("Discovery Princess","145,281"),
 "Caribbean":("Caribbean Princess","112,894"),"Crown":("Crown Princess","113,561"),
 "Emerald":("Emerald Princess","113,561"),"Ruby":("Ruby Princess","113,561"),
 "Grand":("Grand Princess","107,517"),"Diamond":("Diamond Princess","115,875"),
 "Sapphire":("Sapphire Princess","115,875"),"Coral":("Coral Princess","91,627"),
 "Island":("Island Princess","92,822"),
}
