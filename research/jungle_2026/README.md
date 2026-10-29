# HOLY POKÉMON — 1999 JUNGLE GRADED-CARD ARBITRAGE LAB

**Research timestamp:** 2026-10-29. **Status:** high-priority *research*, never automatic trade approval.  
**Source anchor:** https://www.pricecharting.com/console/pokemon-jungle  
**Route of interest:** buy unusually clean **PSA 9** (sometimes PSA 8 at substantially lower cost), submit for **CGC Gem Mint 10** / exceptionally Pristine 10. Preserve old holder vs crack risk distinctly.  
**No Codex work or third-party paid data access was used to prepare this dataset.**

## Files and immediate usage

| File | Contents | What it does NOT claim |
|---|---|---|
| `all_64_cards_and_special_variants.csv` | All 64 numbered English cards, first-edition/unlimited and 16 no-symbol holo versions, plus 8 special/error searches; 152 explicit identity rows | All 152 variants have recent comps, or that rare errors are genuine |
| `holo_variant_population_and_reference_prices.csv` | 16 holos × 3 variants (48 rows), PSA 9 and PSA 10 population, CGC Gem10 census where available, price-guide/index reference, caveats | Conditional crossover probability, currently purchasable prices, verified sales |
| `dated_reported_sold_comps.csv` | 60 individually dated Grade 9 / CGC Gem 10 sale records, source link, original claimed grade/edition and provenance level | That PriceCharting eBay reports are authenticated final net proceeds or that all repeated titles are independent physical cards |
| `illustrative_two_outcome_sensitivity_NOT_QUOTES.csv` | 13 labeled, hypothetical success/failure outcomes derived from distinct source-reported sale prices; fee and cost sensitivity, including break-even success thresholds | These thresholds are NOT estimated grade-conversion odds, cost quotes or guaranteed profits |
| `historical_listing_inspection_queue.csv` | 6 historical real eBay listings with seller asks, exact URLs, variant and status warnings | Live availability, measured centering or purchase approval |
| `authorized_discovery_searches.json` | 39 exact-card search patterns (all 16 holos unlimited and 1st ed plus seven no-symbol), finite query budget | Those searches have been executed or 100+ active PSA9 listings exist |
| `holy_pokemon/jungle_research.py` | Zero-API-cost, sold-observation-only arithmetic and ranked comparison `python3 -m holy_pokemon.jungle_research` | An expected-profit or calibrated probability model |

Read-only analysis command:
```sh
python3 -m holy_pokemon.jungle_research --top 25 --fee-pct 13 --grading-cost 55
python3 -m unittest tests.test_jungle_research -v
```
No API calls, logins, purchases, synthetic transaction generation, grader training or large-file transfer. Existing Mac dashboard has newer local-only code; **these repo additions do not automatically inject themselves into that running dashboard**. Preserve its source/DB before integration.

## 1. True shortlist: upside that might survive fees

**The entries below are not equivalent to buying a PSA 9 and selling a CGC 10.** Price comparisons are observations from separate physical cards, different dates and sometimes separate venues. There is *no measured conditional upgrade rate for Jungle PSA9s*. Use the complete sale rows instead of cherry-picking peak transactions.

### Tier A — work these first

**A1 · Vaporeon #12 holo, unlimited (best combination of gross spread and actual CGC10 sale depth).**
- **PSA9 population** 964; PSA10 only **35 of 16,783 (0.21%)**. **CGC Gem10** 89 of 5,246 (1.70%).
- **Reported CGC Gem10 sales:** $1,225 (Oct 27); $1,000 (Oct 16); $799 (Sep 12); $757.90 (Sep 1); $555 (Jul 27); $574.99 (May 26); $510.01 (Mar 23).
- **Reported PSA9 transactions:** $400 (Oct 3), $379 (Oct 2), $360 (Sep 29), $329 (Sep 23), $320 (Sep 22), $275 (Sep 13).
- An example $255.55 PSA9 eBay listing **now says out of stock**; do not count as a current buy. A separate $395 listing was cached, with live status unconfirmed.
- *Key advantage:* meaningful exit evidence, extremely low PSA10 rate, plentiful PSA9 *population* (not verified active listing count). Biggest risks are holo/surface scratches not visible in straight-on photos, image resolution, printing defects and recapture/duplicate listing effects.
- Sources: https://www.pricecharting.com/game/pokemon-jungle/vaporeon-12 · https://better-pop.com/pop-report/jungle/ · https://cardprice.com/pop/cgc/jungle

**A2 · Kangaskhan #5 holo, unlimited (cheaper experimentation).**
- PSA9 pop 969; PSA10 only 29/10,482 (0.28%).
- Actual source-reported CGC Gem10 sales $450 (Oct 27), $450 (Oct 17), $350 (Sep 25 and Sep 22), $272 (Aug 31), $250 (Aug 19).
- PSA9 reported sales $163.43, $125, $110, **$89** on various 2026 dates.
- **CGC census value in this dataset is intentionally NULL:** CardPrice search appeared to conflate this Unlimited population with an edition cohort. Do not invent CGC gem-rate edge for the missing value.
- The $149 eBay lead literally says **“Cracked Slab”**. Never treat its title as proof of an intact PSA holder. Holo vs #21 nonholo MUST be exact.
- https://www.pricecharting.com/game/pokemon-jungle/kangaskhan-5

**A3 · 1st Edition Scyther #10 holo (underappreciated graded-label spread; smaller/less certain sample).**
- Fanatics direct sold: CGC Gem10 **$1,299 (Sep 21)**, **$999 (Jul 25)**, $840 (Jul 13), $1,080 (Jul 6). These are separate market sales; prior certificate IDs unknown.
- **PSA CardFacts** records a distinct **PSA9 $400 sale Feb 2 2026** (eBay lot 297971665377, cert 25657473). Price/time can differ greatly, so the gross $400→$1,299 ratio **3.25× is NOT a realizable conversion forecast**.
- PSA10 pop 142/4,146 (3.4%); CGC Gem10 34/735 (4.6%) in third-party dated snapshots.
- Complete docs: https://www.fanaticscollect.com/buy-now/ab36d58a-fe9e-42e9-96f2-c56c2bf88905/1999-pokemon-jungle-1st-edition-holo-scyther-10-cgc-10-gem-mint ; https://www.psacard.com/cardfacts/non-sports-cards/1999-nintendo-pokemon-jungle/scyther-holo-1st-edition-10/641314

**A4 · Snorlax #11 holo, unlimited (big dollar spread but capital-intensive).**
- PSA10 39/9,937 (0.39%) while CGC Gem10 61/2,520 (2.42%).
- CGC10 sold reports **$1,499 (Sep 11, Aug 28); $1,300 (Aug 20); $1,275 (Aug 16); $1,110 (Jun 21)**. PSA9 sales $810, $750, $740, $783, $760, $739. A gem might generate several hundred dollars before all costs; a CGC 9 outcome could incur severe loss.
- https://www.pricecharting.com/game/pokemon-jungle/snorlax-11

### Tier B — monitor, but beware guide-price mirages

- **Flareon #3 Unlimited:** CGC10 reported $599/$600/$575 (Oct–Jul 2026), recent PSA9 around $240/$270/$297/$310. Potential upside conditional on purchasing a visually outstanding cheap PSA9, but smaller spread than users assume from a PSA10 guide value.
- **Jolteon #4 Unlimited:** CGC10 $813 Heritage Oct15, $999 eBay Sep29 but **$450 Sep22 and $470 Sep1**. Extreme venue and sale-to-sale dispersion: never use just the $999 exit. PSA9 entry guide ~$471; downside risk significant.
- **Clefable #1 Unlimited:** reported CGC10 $325, $300, $750, $210, $202; the $750 sale is an outlier until corroborated. CGC and PSA gem rates differ, but the common lower exits may destroy the spread.
- **Venomoth #13, Vileplume #15, Nidoqueen #7 Unlimited:** provisional grade-guide ratios look interesting but recent *individually dated same-variant CGC10 transactions* were not assembled in this pass. **Thin evidence, no ranking by guide ratio alone.**
- **Pidgeot #8, Electrode #2, Mr. Mime #6**: psychologically appealing PSA10 scarcity but observed/guide **CGC10 sale value too close to PSA9** for an easy crossover profit. Keep as low-bid watch, not priority.
- **Wigglytuff #16, Pinsir #9, Victreebel #14**: mixed secondary/watch tier, exact holo/edition and dated sale gap checks outstanding.
- **No-Symbol 16 holos:** valid distinct Unlimited error variant, not equivalent to standard Unlimited. Exact grade-specific CGC10 comps largely unknown. A single striking sale must not anchor a forecast. Separate all no-symbol records.
- **Nonholo #17–32, common/uncommon #33–63 and trainer #64:** fully indexed for discovery, but price and grader-specific comparable coverage incomplete. High CGC10 index values on 1st Edition commons are not proof of PSA9→CGC10 profit after grading.

### Special editions and errors

Official PSA error guide confirms:
- **No Symbol:** all 16 Unlimited holofoils can lack Jungle flower set icon.
- **Butterfree #33 “d” Edition:** malformed 1st Edition mark.
- **Pinsir #9 1st Edition Scratch Error:** distinct holo printing variation.
- **Venonat #63 1st Edition Line Error:** distinct ink border line.
- PSA population tracker also displays Clefable prerelease and limited inverted-back / incomplete-holo designations; preserve **reported provenance**, verify exact physical copy and whether CGC recognizes the specific variant.

PSA error guide: https://www.psacard.com/info/tcg/pokemon-error-guide  
Complete 64: https://pokedream.com/pokemon/tcg/cardsets/jungle/index.php

## 2. Population gap is a screening statistic, NOT a grader transfer rate

Sources: BetterPop October 1 PSA 2026 (https://better-pop.com/pop-report/jungle/) and CardPrice September 28 CGC 2026 (https://cardprice.com/pop/cgc/jungle).

**Never do:** PSA gem 0.21%, CGC gem 1.70% ⇒ 8.1x odds of a PSA9 converting. That inference is invalid because the graded cohorts, years, selection incentives, source quality and census rules differ.

Fredy creator retrospective *across heterogeneous Pokémon cards*: 178 carefully selected PSA9→CGC yielded **86 CGC10+** (48.3%) and 14 Pristines (7.9%); 306 selected PSA8→CGC yielded 72 CGC10+ (23.5%) and 4 Pristines (1.3%). This **is not a Jungle-specific success probability**, and other Fredy video sample groups overlap the retrospective. Strictly separate CGC Gem10 from Pristine10, as well as PSA9→PSA10 from PSA9→CGC10.

CGC currently requires **approximately 55/45 front, up to 75/25 back for Gem Mint 10**, with strong corners and surface. **Pristine** centering is described as 50/50. Source: https://www.cgccards.com/card-grading/grading-scale/ . Meeting one centering metric does not guarantee any target grade; cards may have hidden scratches, indents, print lines, silvering, altered stock or factory defects. Note PSA also commonly specifies 55/45 front for PSA10, so **“CGC is simply more lenient on centering than PSA” is not supported by published standards**. Any grader edge must be proven on same-card before/after records, not deduced from population ratios.

## 3. Upside arithmetic, downside discipline

For a concrete hypothetical (not any live listing): buying a PSA9 for **$320**, paying **$30** tax+shipping and **$55** grading/shipping, at **13%** selling fee:
- All-in $405. If CGC10 sells $799, after selling fee $695.13, profit **+$290.13**.
- If the failed outcome realizes a gross $320, after selling fee $278.40, loss **–$126.60**.
- A **hypothetical** success rate of 30.4% would be needed to break even between only those two outcomes. This is **not** a measured probability. Lower CGC outcomes or alteration failures worsen economics.
- Selling at $1,225 creates larger upside; treating it as the normal CGC10 exit ignores the other documented sales. Use conservative percentiles; account for different grade fallback routes.

PSA→CGC holder-preserving crossover vs crack must be modeled separately, including feasibility and the real CGC product rules. Never assume an intact holder qualifies for a requested grade or that grading costs are refundable. Avoid bidding automatically.

## 4. Listing screening / native-image review

- Exact Jungle #1–16 **HOLO**, not same-named #17–32 nonholo; English, not Japanese “Jungle”; first-edition versus standard versus no-symbol.
- Front/back native high resolution, visible card corners, unmodified original pixels, PSA slab cert and label, no swapped photos. Confirm the same physical card, cert, holder and seller.
- Measure front left/right and top/bottom, back left/right and top/bottom with boundary overlays. Do not overstate a measurement from skewed slabs. A card centered 41/59 on front is concerning for Gem10 even if its back is 50/50; 47/53 / 46/54 is more promising on centering alone.
- Inspect all 8 corners/edges and holo with multiple incident-light angles; light scratches/print defects can be invisible in flat scans. Centering is a *gate*, not the entire condition grade.
- Document picture quality, confidence, grade evidence and fallback sale price before evaluating upside. The current image model's vintage 8 vs 10 discrimination is not proven reliable enough to approve a purchase.

## 5. Listing supply and proof status

**ZERO reliable exact-current 100+ PSA9 listing counts collected.** A PSA9 *population* of 964 Vaporeon is not 964 active eBay sellers. The historic eBay listing queue is **not** an active inventory feed. Existing authorized eBay Browse and its quota controls can provide bounded current discovery on the Mac, but execution wasn't available here. To protect credits, only four highest-value queries per manual batch; limit pagination, honor cache and quota; avoid irrelevant broadly pooled “Jungle PSA9” results.

Similarly, PriceCharting's guide value != a specific sold sale. Direct Fanatics completed sales are higher confidence; PriceCharting-reported eBay sales are **source-reported** until underlying transaction/variant confirmed. Do not fabricate comps for missing cards or live auctions. Dedup repeated reports/cert IDs, especially identical listing titles repeated at different dates.

## 6. Research gaps and versioning

Still unresolved: (a) exact active PSA9 listing counts; (b) large-scale close-up centering and holo review; (c) fully verified 1st Edition and No Symbol recent CGC Gem10 sale sets; (d) exact certificate-level paired PSA9→CGC10 Jungle results; (e) same-variant fallback CGC8/9.5 liquidity; (f) CGC census inconsistencies in Kangaskhan/Victreebel Unlimited; (g) 30/60/90-day weighted market trend; (h) taxes/upcharges and seller fees per venue.

**Do not silently fill any blank as zero.** Every derived score/guide spread means speculative upside, never a purchase authorization. The aim is a list of underpriced **specific physical cards** whose observed photos are mint-like enough to merit close review—not a fictitious arbitrage count.
