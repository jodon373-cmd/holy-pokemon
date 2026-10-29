# HOLY POKÉMON — OPEN-ENDED ARBITRAGE DISCOVERY, EVIDENCE, AND IMPLEMENTATION PLAYBOOK

**Owner direction recorded 2026-10-29:** Discover excellent grade/resale arbitrage opportunities across **ALL Pokémon cards**, NOT just the first shortlist or specific Jungle/Fossil/Rocket/Gym cards. The owner will independently provide the workload, credit/compute and search constraints for a given Codex run. **Do not invent those limits or interpret existing example query queues as a maximum scope.**

This is an **addendum to the existing authoritative** [one-shot execution contract](CODEX_ONE_SHOT_EXECUTION.md), **not a replacement or a new competing prompt**. Implement into the already running, newer Mac checkout after inspecting the local code. GitHub `main` may be older than the local Mac. Preserve original assets, local operator notes, model checkpoints, databases, permissions, app flows and tests; don't reset the Mac workspace to the older GitHub state.

## The opportunity we're after

Find a *specific, authentic, reasonably priced card copy* whose currently underpriced slab has a strong observable condition case for a higher-value grading exit **or profitable same-grade marketplace exit**, with robust real sold transactions and a survivable loss if the grade fails.

The user's especially desired niche is **PSA 9 → CGC Gem Mint 10**, including *some* PSA 8 → CGC 10 cases where deeply undervalued. But the system **must search beyond those routes** to discover materially better opportunities, including a path not previously enumerated. No owner requirement to limit discovery to one set, a fixed 16-card ranking, top 5, era, language, or source.

### Discover from hypotheses, not from a frozen watchlist

Possible opportunity families (examples, NOT limits):
- PSA 9 → CGC Gem Mint 10, PSA 8 → CGC Gem Mint 10, carefully differentiated CGC Pristine 10;
- PSA 9 → PSA 10 (review/crack/regrade policy varies); BGS 9.5 → PSA 10 or CGC Gem 10;
- old CGC blue-label 9.5 → PSA 10 or CGC Gem 10, distinguishing legacy and newer grade definitions;
- same-company grading discrepancies, high BGS subgrades with overlooked defects, old cert/photo listings;
- same-grade resale/venue differences (no grade improvement necessary);
- PSA Vault/consignment/Partner Offer vs direct sale where custody/fee/tax/effective dates are evidenced;
- undervalued raw copies with approved high-resolution photo/physical inspection, authentic print variants;
- underresearched set, obscure promo, staff/prerelease, 1st Edition, unlimited, No Symbol, reverse holo, error, Japanese/English, e-reader/EX, low-print-run 2010s cards;
- overlooked modern promo, illustration rare, trophy/prize/promotional variant, unrecognized category combinations;
- negative controls: cards with high population differential but low CGC premium, insufficient sold depth, downgrades, weak liquidity.

**Open strategy discovery means searching for new, evidence-backed hypotheses**, not claiming every scheme makes money. Expand the universe when evidence reveals a new set, print-era, grade route, marketplace, slab generation, or price anomaly. Do not make novelty an excuse to skip authentication, source rights or observed price verification.

## Key evidence already in the repository

These are historical research snapshots, **not current listings or trade approvals**. File-specific instructions and provenance are preserved in each folder.

| Cohort | Files | Role |
|---|---|---|
| **Jungle** | [Jungle full report](../research/jungle_2026/README.md), [64-card 152-variant index](../research/jungle_2026/all_64_cards_and_special_variants.csv), [48 holo/variant population rows](../research/jungle_2026/holo_variant_population_and_reference_prices.csv), [60 dated reported comps](../research/jungle_2026/dated_reported_sold_comps.csv) | Holo, 1st edition, unlimited, error discovery; multiple CGC Gem Mint 10 transactions. Includes poor exits too |
| **Jungle economics** | [13 conditional sensitivity examples](../research/jungle_2026/illustrative_two_outcome_sensitivity_NOT_QUOTES.csv), [listing-review queue](../research/jungle_2026/historical_listing_inspection_queue.csv), [39 search patterns](../research/jungle_2026/authorized_discovery_searches.json), [offline ranker](../holy_pokemon/jungle_research.py) | No fake live inventory, no sale-price extrapolation from peak single trade |
| **Cross-set G-GAP** | [Cross-set research](../research/cross_set_gap_2026/README.md), [12 set/card population rows](../research/cross_set_gap_2026/populations_and_guide_references.csv), [38 dated source-reported sale rows](../research/cross_set_gap_2026/dated_source_reported_sales.csv), [10 bounded example searches](../research/cross_set_gap_2026/bounded_exact_card_search_queue.json), [offline ranker](../holy_pokemon/gem_gap_research.py) | Fossil, Rocket, Base Set 2, Gym Heroes, Neo and **negative control** examples across 2010s |
| **Promos** | [Promo reference/category source](https://www.pricecharting.com/console/pokemon-promo), [high-priority source/query registry](../research/pokemon_promo_priority.json), [12 source-reported sold comps](../research/pokemon_promo_reported_sold_comps_2026-10-29.csv), [promo read-only adapter](../holy_pokemon/promo_priority.py) | Black Star Promo and any new promotional subseries/variants |
| **Fredy original case studies** | [Source transport](../research/FULL_SOURCE_TRANSPORT.md), [18-pack research manifest](../research/manifest.csv), [Fredy business reverse-engineering](FREDY_BUSINESS_REVERSE_ENGINEERING.md), [market evidence policy](MARKET_DATA_SOURCES.md) | Aggregate/case/outcome research; original records may be on Mac only; creator grade outcomes are not sold comps |
| **Open-ended exploration** | [Route registry](../research/strategy_discovery/routes.json), [open-universe query generator](../holy_pokemon/open_strategy_discovery.py), [discovery test suite](../tests/test_open_strategy_discovery.py) | **New sets, cards, grades, eras and variants can be supplied without changing hardcoded rankings** |

**Source dates matter.** The snapshot is 2026-10-29, not a real-time quote. Always keep original source URI, exact set/number/variant/grade, last retrieved timestamp and evidence type. Where a CSV contains PriceCharting-reported sales, verify the completed-sale transaction and exact price/variant at approval time; source-reported does not equal independently confirmed cash received. Sales of different physical copies are not same-card grading conversions.

## FredyCards: observations versus our added hypothesis

Source: [Fredy 546-card PSA→CGC reveal](https://www.youtube.com/watch?v=00qFtZz6eZU) and [his PSA-vs-CGC two-year GemRate breakdown](https://www.youtube.com/watch?v=XmaISDa55DM).

Fredy's narrated retrospective: **178 selected PSA 9s → 86 CGC 10 or better (48.3%); 14 of 178 Pristine (~7.9%)**. **306 selected PSA 8s → 72 CGC 10 or better (23.5%); 4 Pristine (~1.3%)**. All grades combined **546 submissions → 162 CGC 10 or better; 18 Pristine**. These are *selected creator submissions*, mixed cards/eras, potentially repeat attempts and partially unrealized profit; do not assign 48.3% to a random PSA 9 listing or add overlapping videos as independent observations.

Fredy separately examined `gemrate.com` PSA versus CGC two-year submission gem rates: **51.6% CGC / 51.3% PSA overall**; greater CGC advantage around **2010–2019** (up to ~20 percentage points at times), some advantage in **2000–2009**, less decisive **1990s** and **2020+**. His video presents era-level aggregate patterns, **not proof that any single 2010s card has easier CGC 10 outcomes**. Flashfire Charizard EX #100 and Plasma Storm Lugia EX #134 are included as counterexamples in our existing cross-set dataset.

**What is NOT established:** Fredy does not explicitly document a rigorous *per-card PSA gem-pop vs CGC gem-pop ratio combined with exact-market exit and failure price* as his own selection formula. That is **our proposed G-GAP strategy**, informed by his outcomes and research, not an attributed Fredy secret.

## Starting discoveries, not a whitelist

- **Fossil Lapras holo #10 Unlimited**: 51 PSA10 / 12,740 total (**0.40%**) vs CGC 10-inclusive 113 / 4,917 (**2.30%**); Grade 9 *blended* guide ~$171, **CGC Gem 10 source-reported** $489–$809. **PSA9 purchase and CGC9 failure prices not verified**.
- **Base Set 2 Chansey holo #3 Unlimited**: PSA10 29 / 5,211 (**0.56%**) vs CGC 10-inclusive 31 / 1,937 (**1.60%**). Only three historical CGC Gem 10 observations at ~$510/$699/$1,150; thin volatile resale.
- **Fossil Dragonite #4 Unlimited holo**: PSA 10 60/14,946 (**0.40%**) vs CGC10-inclusive 72/3,866 (**1.86%**); cited CGC Gem10 sales from ~$975 to $1,999. Capital-intensive; inspect production issues and verified seller comps.
- **Team Rocket Dark Charizard holo #4 Unlimited**: PSA10 176/18,186 (**0.97%**) vs CGC10-inclusive 74/3,279 (**2.26%**); source-reported PSA9 ~$920–$984 and CGC Gem10 ~$1,375–$1,999. NOT nonholo #21.
- **Gym Heroes Sabrina's Gengar holo #14 Unlimited**: PSA10 34/7,946 (**0.43%**) vs CGC10-inclusive 117/1,697 (**6.89%**); CGC Gem10 sold reports ~$2,101–$3,195. High capital/risk, huge descriptive population mismatch.
- **Jungle Vaporeon #12 Unlimited holo**: PSA10 population ~0.21%; CGC 10 population ~1.7%; actual source-reported PSA9 transactions ~$275–$400 and Gem10 ~$510–$1,225. Favor low-quartile exit and inspect holo scratches rather than cherry-picking the $1,225 sale.
- **Jungle Kangaskhan holo #5**, **1st Edition Scyther holo #10**, **Jungle Snorlax holo #11**, **Promo Mewtwo #14**, **Promo Entei #34**, **Promo Snorlax #051** remain source-linked cohorts; see folders.
- **Negative controls**: Gym Heroes Blaine's Moltres, Rocket's Scyther, Pidgeot Jungle where population advantage does not create strong fee-adjusted resale; 2010s examples where CGC counts are actually less favorable.

Every numerical comparison is **historical snapshot and descriptive**. “CGC 10 population” may combine ordinary Gem Mint 10 and Pristine; CGC Gem Mint 10 **sales** must not combine Pristine, Pristine sells differently. No claim of real-time live PSA9 availability or 100+ listings from a PSA population count.

## What to do in each exploration / implementation cycle

### A. Build or extend the entire search universe

Start with all known card identities from the fixed seed folders but **DO NOT STOP THERE**.

Sources to examine where authorized: official Pokémon card databases and collector-checklists, PSA and CGC census/cert reports, GemRate time-series, PriceCharting category and set pages, completed sales from eBay Seller Hub/Product Research exports or approved interfaces, official Fanatics/PSA Vault records where accessible, owned exports, authenticated marketplace listings, and user-reported Fredy result examples. Sources must be tagged with access mode and license; no unauthorized scraping, guessing a private API or CAPTCHA avoidance.

Expand recursively: identify previously unexamined full sets/eras, common cards and rarer promos, 1st-edition vs unlimited, graded slab generations, language and holo patterns, no-symbol and distinct error variants, reholder/regrade/marketplace routes. A hypothesis can begin with high resale potential **without having verified comps yet**—tag it RESEARCH_UNVERIFIED and retain it. When a source is inaccessible, record the gap and do other work.

### B. Prospect grader-population gaps correctly

For exact card identity + edition + time window, record **PSA 10, PSA 9, PSA total, CGC Gem 10 if separable, CGC Pristine 10 if separable, CGC total, census snapshot date, source and population minimum**. Historical all-time cohorts differ from recent grading-month cohorts. Do not infer conditional PSA9→CGC10 from ratios. A 10-pop rarity could come from poor centering, holo scratches, production cuts or submission selection—evaluate evidence not just rarity.

Use wide **hypothesis bands, not exclusions**: example PSA gem rate <2%, CGC gem rate higher and PSA9 supply >100, but *do not silently throw out a good trade outside these bands*. Rank a CGC/PSA contrast with confidence intervals, cohort size and age, and compare to actual completed sale depth.

### C. Establish money-making spreads without invented comps

For a given exact card/variant and proposed route:
1. Separate **observed completed PSA9 sale prices** from a cross-grader Grade9 guide number, from **seller active asking**, from **creator-projected** value. Require dates/links, accepted-offer basis and certification/variant matching.
2. Independently establish **ordinary CGC GEM MINT 10** completed sales and separately **Pristine 10**. Prefer multiple recent sales; preserve low/median/high, thin-market and trending changes.
3. Model actual acquisition tax, shipping/insurance, CGC tier/handling/upcharge, venue selling fee, potential time to sale and holding/market impact.
4. Evaluate **fallback** CGC 9/9.5, 8.5, authentic-altered/rejected and lost-original-slab outcome; a cracked PSA9 no longer retains a PSA9 slab resale fallback. Intact crossover eligibility/grade minimum terms must be provider-verified.
5. Separate `conditional-success-spread` from true `expected profit`. The latter requires a **validated conditional route outcome probability** and all downside scenarios. If missing, show break-even probability *sensitivity only* and mark probability UNKNOWN. No auto-buying.

### D. Hand-pick condition with actual native photos

No flattening 256×384 of full card as the only grading evidence. Keep **original resolution** and inspect native crops of front/back corners, edges, holo, borders and centering, preserving source and no fabricated detail. Verify front L/R and T/B, back L/R and T/B, check rectification/skew uncertainty. **PSA 10 and CGC Gem Mint 10 both publish roughly 55/45 front centering criteria**; a numerical 59/41 can be a real obstacle. Do not assert CGC is looser on front centering. Some PSA 9s are held back by factory defects, marks, gloss, print lines invisible to sellers. Get tilted light if possible; abstain with inadequate images.

The simple experimental grader previously scored a confirmed PSA10 Moltres as ~8.19 and a PSA8 Nidoking ~8.13; it cannot independently distinguish vintage 8 vs 10 or justify grading odds yet. Any new model should be held out by **physical specimen**, not merely certificate ID; keep blind results and failure gallery, condition-subgrade evidence and era calibration.

### E. Innovate: discover **new strategies** beyond this playbook

Codex may research a completely new hypothesis or asset family. For each proposed route document:
- hypothesis and physical/market causal mechanism;
- prior sources and unknowns; anti-examples that would falsify it;
- how to search across **unseen sets/cards**, not just targeted example IDs;
- how actual same-specimen outcomes, seller offers and completed exits could test it;
- worst-case capital loss and sample selection bias;
- evidence tiers: `DISCOVERED` → `CONDITION_INSPECTION` → `SOLD_COMPS_CONFIRMED` → `MANUAL_OWNER_APPROVAL`; promotion depends on evidence, not a compelling narrative.

Compare opportunities with and without grading. The **best arbitrage might be selling the current slab directly** if regrading destroys value. The next successful set might be Neo Revelation, EX-era, Diamond & Pearl, Japanese promos, Sun & Moon or an unknown future set. None should be dropped solely because the current seed files don't list it.

### F. Practical software workflow, without a separate lengthy prompt

In the checked-out local Mac repo, inspect the running implementation for existing discovery/provider modules and avoid duplicate rewrites. Register the new source categories and strategy registry as data, not hardcoded card lists. Use caches/source timestamps and an audit of exact searches executed. Prefer existing approved provider adapters. **Only the owner decides the specific scope / token / credit / runtime limits for a Codex assignment.** Any historical file saying “four queries per batch” is an example of a conservative manual seed, not an overriding max of four queries across all research. Respect actual provider rate limits.

Offline demonstration (no live calls or purchased services):
```sh
python3 -m holy_pokemon.open_strategy_discovery --output outputs/all_seed_queries.json
python3 -m holy_pokemon.open_strategy_discovery --universe research/local/new_cards.csv --output outputs/expanded_queries.json
python3 -m holy_pokemon.open_strategy_discovery --no-builtins --universe research/local/new_cards.csv
python3 -m holy_pokemon.gem_gap_research --top 25
python3 -m holy_pokemon.jungle_research --top 25
python3 -m unittest discover -s tests -v
```

Any `--universe` CSV may cover **ANY** set and must have:
```csv
set,card,number,edition,year,language
EX Deoxys,Rayquaza ex,107,gold star holo,2005,English
Neo Revelation,Shining Gyarados,65,unlimited holo,2001,English
```
These are **query-generation examples, not real for-sale records or value predictions**. Omit or revise examples as needed. The command accepts unlimited rows and defaults to all defined routes; `--route`/ `--limit` are explicit owner-selectable flags. It deliberately returns `UNEXECUTED_RESEARCH_QUERY`, null listing counts, null profitability and no conversion odds.

### G. Acceptance and reporting

Evidence:
- structured source registry for every claim, URL, read/retrieved date, cert/photo if applicable;
- verified comps independently traced to individual distinct sale events (not guide/index), negative cases, exact variants;
- no synthetic market sales, no invented submissions, no false live inventory counts and no label-leakage models.

Functionality:
- broad/open universe and strategy families, data-importable new cards, real authorized search and sold-comp workflows where credentials exist; durable status and notes;
- ranked **research** leads including unknowns; distinct owner **trade-approval** flow and full downside/fee math;
- tests proving that new sets/grades/routes work and falsifying cases remain in view;
- local Mac UI integration ONLY after inspecting its newer code, with provenance and state migration safety;
- concise honest report of completed/tested functionality and missing access; never invent results.

**Do not execute a purchase, seller message, slab cracking, grading submission or paid data call** without explicit owner approval. The owner determines eventual execution scope and budget.
