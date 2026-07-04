# Harvesting Princess deck-plan data

Data is pulled from Princess's public deck-plan JSON API:

    https://www.princess.com/getDeckJSON.do?&shipCode=XX&version=N&deck=D

returned per deck as `{ "cabins": [ ... ] }` with, for each cabin: number, deck,
zone, category code/name/colour, square footage, balcony area, berths, bath type,
connecting rooms, accessibility, and vector `path` + label position.

## Ship codes and versions (as of July 2026)

| Ship       | code | version |
|------------|------|---------|
| Sun        | SU   | 3       |
| Star       | ST   | 1       |
| Royal      | RP   | 6       |
| Regal      | GP   | 9       |
| Majestic   | MJ   | 5       |
| Sky        | YP   | 4       |
| Enchanted  | EX   | 3       |
| Discovery  | XP   | 3       |
| Caribbean  | CB   | 4       |
| Crown      | KP   | 9       |
| Emerald    | EP   | 8       |
| Ruby       | RU   | 8       |
| Grand      | AP   | 5       |
| Diamond    | DI   | 8       |
| Sapphire   | SA   | 9       |
| Coral      | CO   | 7       |
| Island     | IP   | 0       |

Codes come from Princess's own ship-page URLs (`/ships/xx-name-princess`). The
version corresponds to a deck-plan revision (before/after a refit); read the current
value from the ship's deck-plan page "when are you sailing" links. Versions change
after refits — re-check before a refresh.

`princess_fleet_all.json` is a dict keyed by ship name:
`{ "Sun": {code, version, cabins:[...]}, ... }`.
