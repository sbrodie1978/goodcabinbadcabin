# MSC Cruises — harvest notes

Recon done 5 Jul 2026 (Claude in Chrome session on msccruises.com, MSC Virtuosa).
This documents the MSC data source the way `../HARVEST.md` does for Princess.

## Source of truth: official interactive deck-plan SVGs

Each ship page on msccruises.com embeds an interactive deck plan viewer that
loads **one SVG per deck** from MSC's media store (Sitecore DAM):

    https://www.msccruises.com/int/-/media/global-contents/ships/fleet/
        <ship-slug>/interactive-deckplan/<version>/deck_<N>_<deckname>.svg

Confirmed example (Virtuosa, 15 decks):

    .../fleet/virtuosa/interactive-deckplan/a8---winter-21-22/deck_8_deck-8.svg

- `<version>` is MSC's refit gate (cf. Princess version numbers), e.g.
  `a8---winter-21-22`. It differs per ship and changes after refits.
- The ship page HTML is **server-rendered**: all deck SVG URLs and the cabin
  category legend appear in the raw HTML. Plain HTTP harvest, no browser needed.
- Ship pages: `https://www.msccruises.com/int/our-cruises/ships/<ship-slug>`.

## SVG anatomy (per deck)

Layer groups (`g` ids) and what they give us, from Virtuosa deck 8
(879 KB, 258 cabins):

| layer        | contents                                                        |
|--------------|-----------------------------------------------------------------|
| `#cabins`    | `rect#cabin<NUM>` — **fill colour = cabin category**            |
| `#strokes`   | `rect#stroke<NUM>` — outline; x/y/width/height = **geometry**   |
| `#numbers`   | cabin number glyphs (outlined paths, not text — ignore; the ID carries the number) |
| `#icons`     | per-cabin icons (accessible, bathtub, obstructed…), `icon*` ids |
| `#connected` / `#conncted` (sic) | connecting-cabin markers                    |
| `#names`     | venue names as outlined paths (NOT extractable text)            |
| `#ship`, `#ingombro` | hull outline / footprint                                |

So per cabin we get number (from the element id), exact position + size, and
category (via fill colour) — geometry comes native, unlike the Princess API.

## Colour → category mapping

The legend on each ship page pairs swatch colours with category names
(e.g. `#F2A9C5` = Deluxe Interior, `#68A4D8` = Junior Ocean View,
`#4CA66F` = Deluxe Balcony). Caveats:

- The mapping is per ship (and possibly per deck view) — always harvest the
  legend from the same page as the SVGs.
- One colour can cover sibling categories ("Deluxe Balcony" vs "Deluxe
  Balcony with partial view" were both `#4CA66F` on Virtuosa). Disambiguate
  with the official deck-plan PDF legend, which lists category codes with
  their deck ranges (see below).

## Backup / cross-check source: official deck-plan PDFs

    https://www.msccruises.co.uk/content/dam/msc-cruises/b2c-assets/fleet/
        msc-<ship>/MSC_<SHIP>_DECKPLAN.pdf

Vector PDFs with a full text layer: cabin numbers, deck names, venue names,
and the category legend incl. per-category deck ranges (e.g. `BR1 8-10`).
Useful for: venue names/positions (SVG venue names are outlined paths),
category disambiguation, and validating harvested cabin counts.

## Fleet (23 ships in service, Jul 2026)

Classes: Lirica (Armonia, Lirica, Opera, Sinfonia) · Musica (Musica,
Orchestra, Poesia, Magnifica) · Fantasia (Fantasia, Splendida, Divina,
Preziosa) · Meraviglia/+ (Meraviglia, Bellissima, Grandiosa, Virtuosa,
Euribia) · Seaside (Seaside, Seaview) · Seaside EVO (Seashore, Seascape) ·
World (World Europa, World America; World Asia due 2026, World Atlantic 2027).

Ship slugs used by the site are `msc-<lowercase-name>` with hyphens
(`msc-world-america`). `harvest.py` maintains the list.

## Harvest procedure (browser-based — direct HTTP is blocked)

msccruises.com sits behind Akamai bot protection: **all** direct requests
(curl, urllib) return 403, pages and DAM assets alike. `harvest.py` in this
folder therefore does NOT work as a direct harvester — kept for reference.
The working procedure (used 5 Jul 2026) is Claude driving Chrome via the
Claude in Chrome extension: in-page `fetch()` rides the browser's cookies and
fingerprint, bundles each ship's page HTML + deck SVGs into a gzipped JSON,
and downloads it as `msc-harvest__<slug>__YYYYMMDD[-vN].json.gz`.

Then, from the repo root:

    python3 pipeline/msc/unpack_harvest.py   # reads ~/Downloads, writes data-source/msc/

Later bundle versions (-v2, -v3…) overwrite earlier ones per ship.

## Quirks found during the 5 Jul 2026 harvest (READ BEFORE RE-HARVESTING)

- **Two path schemes**: most ships use `/interactive-deckplan/<version>/`;
  World class uses `/deckplans/` (no version folder, season suffixes
  like `_s25` instead).
- **Filename schemes vary**: `deck_<N>_<deckname>.svg` (most),
  `ma_<NN>_<name>[_v2].svg` (Magnifica, refit files), `am_deck_<NN>[_new].svg`
  + `am_<NN>_<name>_s25.svg` mixed (World America), `as_deck_<NN>.svg`
  (World Asia). `_v2` / `_new` / `_s25` mark refit/season revisions.
- **Query strings**: some pages emit SVG URLs with Sitecore media params and
  HTML-escaped `&amp;` — extractors must allow `\.svg?…` and unescape.
- **Lazy loading**: several pages (Poesia, World America) embed only a few
  deck URLs in raw HTML; the rest are constructed client-side. Deck tab
  names in the rendered DOM give the full list; missing URLs can usually be
  guessed from the schemes above, or captured from the rendered DOM/network.
- **World America deck 5** (`am_deck_05_new.svg`) was not directly fetchable
  even in-browser; it was captured from the rendered inline SVG in the DOM.

## Harvest results, 5 Jul 2026 (from live site; validate against PDFs)

24 ships, ~39,900 cabins. Complete except: **Magnifica deck 12
(Portovenere)** — mid Yacht-Club refit (launches summer 2026), plan not yet
published by MSC; re-check and re-harvest Magnifica when it appears.
Poesia RESOLVED 5 Jul 2026: the site viewer omits deck 11 (D'Annunzio)
entirely, but `deck_11_d-annunzio.svg` exists in the DAM (found by probing
poet names; 234 cabins, matching the PDF) — harvested as a v10 supplement
bundle. Lesson: a viewer's deck-tab list is not authoritative; reconcile
per-deck cabin counts against the PDF after any harvest.

## Extraction (parse_svgs.py)

`python3 pipeline/msc/parse_svgs.py` turns the harvested SVGs + page legends
into `pipeline/msc/msc_extracted.json` (gitignored transient): per cabin
number, deck, bbox geometry, fill, category slug(s) + group. Legend lis are
machine-readable (`<li id="<group><guid>|<slug>|#HEX">`); resolution order is
ship legend exact → ship nearest-colour (revision palette drift, e.g.
#4CA66F/#4CA770) → pooled class legend. Status 5 Jul 2026: 97–100% of cabins
resolve to a category group on every ship. Known residue: a handful of fill-less/white cabins per ship (likely
unsellable); within-group sibling ambiguity (deluxe-balcony vs partial-view;
YC suite variants) is benign for scoring. SOLVED 5 Jul 2026 via the PDF
legends: `#003891` = **Deluxe Balcony with Promenade View** (code PR1, decks
10-11, World class) — added as a MANUAL_LEGEND alias in parse_svgs.py. Note
the PR2/PR3 promenade-view tiers (decks 12-16) may currently resolve as
plain deluxe-balcony via nearest-colour; promenade-facing cabins are
geometrically identifiable (centreline-adjacent) — verify during scoring.

## Geometry frame (in parse_svgs.py)

All decks of a ship share ONE drawing frame (single viewBox + hull box per
ship, verified fleet-wide) — no per-deck alignment needed. Every file carries
a `#ship`/`#ingombro` hull layer; the ship-level hull box gives bow→stern
`b` (0=bow, 1=stern). **Bow = right in every file**: cabin numbers ascend
bow→stern with 100% per-deck consistency, and the Virtuosa deck-5 render
confirms it visually. Sides: odd cabin numbers sit in the top lane
everywhere; a bird's-eye plan with bow right puts port at the top, so
**odd = Port, even = Starboard** (geometric derivation — not yet verified
against a real onboard photo; flag if contradicted). Duplicate SVG ids
(`cabin10008_1_`, Illustrator suffixes on World ships) are one cabin drawn
as multiple shapes — canonicalised and merged by union bbox. The `#icons`
layer (per-cabin markers, id `icon<num>`) is captured with positions; icon
*type* decoding (accessible/whirlpool/obstructed) is still to do.

## Open questions / next steps

1. Legend extraction: finalise the colour→category parser against the saved
   page.html files (per ship; one colour can cover sibling categories —
   disambiguate via the PDF legend's deck ranges).
2. Venue zone maps per class → `fleet_classes.py`-style hand mapping,
   7 classes, PDF text layer as reference.
3. Validate cabin counts per ship against the official PDFs
   (msc_pdftext.json.gz makes this scriptable); re-harvest Magnifica
   post-refit (deck 12 Portovenere still unpublished).
4. **Permission**: Princess data is used with Princess's permission; the
   equivalent ask should go to MSC before `/msc/` is published. Deck plans
   are stated to be MSC's property.
