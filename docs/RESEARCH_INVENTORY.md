# Research inventory and source-of-truth rules

## Verified source collection
**18 canonical ZIP archives, 18 passed local ZIP integrity checks**, inventoried in [../research/manifest.csv](../research/manifest.csv). These are references to local research, not files committed to GitHub. The ZIP's SHA-256 identifies an exact byte version and supports deduplication of repeat uploads (including files suffixed `(1)` or `(2)`).

The 18 canonical archives include:
- **8 monthly financial packs:** February, March, April, May V2 recapture, June, July, August, September. The February archive records 9 case rows; later months have variable schemas, types of sales and incomplete costs.
- **8 Pokémon individual/submission case packs:** PSA9→PSA clean $12,174 (22 rows: 20 primary + 2 bonus), PSA9→PSA second experiment (20 primary), CGC consistency 13, CGC harsher 20, Community Challenge 20 (lightweight), PSA→CGC $7,246 (20), PSA→CGC $7,999 (20), plus grading-route/bonus records inside packs. **Do not sum overlapping individual cases as a unique sample.**
- **2 aggregate studies:** 546 original PSA→CGC submissions and a PSA-vs-CGC two-year gem-rate study. The 546 cohort is **not** an additional 546 newly itemized physical card rows; keep distributions and curated examples separate.
- **1 extra cross-game One Piece pack:** BGS9.5→PSA, 20 physical cards, 17 PSA10s, isolated in its own domain.

> Counts above are grouped semantically; the canonical manifest is authoritative for exactly which 18 ZIP files belong to the intake. Detailed cases may overlap monthly reports or the 546 cohort.

## Other research assets available outside the 18-archive canonical list
- Community Challenge full evidence ZIP: `Fredy_Community_20_Regrades_Research_Pack.zip` (large; same 20 cases as light pack).
- Earlier noncanonical PSA9→PSA capture archive; May pre-recapture monthly archive; early recorder artifacts. These are archival sources or alternates, **not extra outcomes**.
- Original transcript / metadata / WebM files, screenshots, condition exemplars and certain extra evidence reports not yet consolidated in the local 14-ZIP user folder. These remain offline and are not assumed synchronized to the repo.
- Older `pokemon-market-scanner` GitHub repository is available as read-only engineering reference, with listing discovery and grading experiments; don't import its historical data without provenance review.

## Known video result anchors to verify when ingesting
- PSA9→PSA $12,174 V2: 20 primary PSA9 regrades (11 → PSA10), 2 bonus, $15,359 all-in, $27,533 displayed valuation, difference $12,174. Not verified total realized profit.
- PSA9→PSA second experiment: 5/20 → PSA10; $7,377 cost, $10,895 displayed value.
- CGC consistency: 13 physical cards, 9 same / 3 up / 1 down on repeat assessment; $7,963 cost and $12,170 value.
- 546 original PSA→CGC: 62 PSA7s, 306 PSA8s, 178 PSA9s; 162 CGC10s including 18 Pristines. Possible aggregate outlier classification and CGC Pristine average scoring require explicit handling.
- CGC harsher? 20 physical cards, $11,333 total all-in / $15,425 new displayed value; baseline value for keeping PSA slabs $13,885.
- Community: 20 cards; 11 CGC10 or Pristine 10; $2,719 all-in / $6,235 displayed value.
- PSA→CGC $7,246: 14 PSA8 / 5 PSA9 / 1 PSA7 despite video title; $12,469 / $19,715.
- PSA→CGC $7,999: 20 physical cards, 22 CGC grading events; $11,161 / $19,160, and market appreciation acknowledged as a key driver.
- One Piece BGS9.5→PSA: 17/20 PSA10, $6,328 / $12,370; **only for One Piece**.
- PSA-vs-CGC two-year historical cohort: ≈51.6% vs 51.3% overall gem rates in source analysis; do not confuse with crossover odds.

These are **research check values** to compare against the source files, not independent verification of realized sale proceeds or current market worth.

## Next source-inventory actions for Codex, once commissioned
1. User locates ZIP collection on their Mac; inspect actual paths and hashes and enumerate missing optional files.
2. Read `card_cases.csv`, `financial_metrics.csv`, other JSON/CSV and the reports within each ZIP. Maintain native originals; normalize into staged audited records, never silently rewrite.
3. Preserve *source evidence* (video + timestamp + slide/frame + speech + creator guesses), *physical copy*, *grading events*, and *economic events* separately.
4. Maintain an unresolved overlap report for physical card cross-video matches and transcript recapture duplicates.
5. Emit a complete coverage matrix: imported, parsed, unknown fields, conflicts and verified refs.
