# Holy Pokémon — CompSniper sold comps + PSA SecureScan integration

**Owner instruction:** 2026-10-29. **State:** first-party Holy Pokémon GitHub baseline now includes a read-only, opt-in CompSniper adapter and mocked tests. **Not** an authenticated live CompSniper check. GitHub \`main\` != current, newer Mac checkout. Preserve Mac app and its existing eBay adapter when merging. **This supplements the ONE authoritative execution contract:** \`docs/CODEX_ONE_SHOT_EXECUTION.md\`.

## 0. Critical discovery and PSA support blocker

**CompSniper documents no professional-quality front/back slab-photo or PSA SecureScan endpoint on its PSA API.** Its PSA API provides catalog identity, prices by grade, population, and recent transactions. The eBay sold endpoints may return marketplace \`thumbnailUrl\`, \`fullResThumbnailUrl\` or historical \`imageUrl\`; those are NOT PSA SecureScans, not proof of surface grade, and may be missing/low resolution. Images must remain unmodified and source-linked.

**PSA Public API approval pending:** Owner tried \`GET https://api.psacard.com/publicapi/cert/GetByCertNumber/138267599\` with a generated token and documented bearer header on **2026-10-28** and received **HTTP 403: "Access to this API is limited to approved customers."** Owner sent an email to PSA's collectors-apis contact **2026-10-28 20:39 EDT** asking how to get access and whether a licensed Auction Prices data feed exists. No approval or response has been reported. Do NOT say PSA's API works, treat token creation as entitlement, repeatedly hammer the 403 endpoint, or embed any token in GitHub. PSA's user-facing \`https://www.psacard.com/cert/<CERT>\` pages can be opened manually for card details/available SecureScan images. High-resolution photos for certs with available scans may be inspected via user-authorized imports/exports or a separately documented authorized image interface **only when actually permitted**; otherwise mark \`PSA_IMAGE_UNAVAILABLE\`.

## 1. Data architecture

| Need | Preferred source | Strength / guardrail |
|---|---|---|
| Buy candidates, price, listing links, listing photos | Existing authorized eBay Browse adapter in owner's Mac checkout | Current ask is NOT sale, image defects may be obscured |
| PSA-9 and PSA-10 recent sold comps | CompSniper \`GET /v1/psa/search\` -> exact \`specId\` -> \`GET /v1/psa/card?specId=...&grade=...\` | Third-party-reported individual dated sales; verify exact company+grade and exact variant; API may return ungraded sales even filtered |
| Card universe/pops | CompSniper \`/v1/psa/sets?game=pokemon\` -> \`/v1/psa/set?headingId=...\` | Population ratios describe graded populations, **NOT** probability a PSA9 regrades to 10 |
| Rare/older comps, up to 3 years | CompSniper \`GET /v1/research/sold\` | Up to 50 listing-level rows/page, not a transaction feed. Filter \`recordType=single_unit_listing\` and \`soldUnits=1\`, then match variant manually/strictly. \`listing_aggregate\` is NOT one sale. Long exact queries omit real sales! |
| Recent sold comps (~90 days) | CompSniper \`GET /v1/scrape?keyword=...&count=240&bestOfferPrice=true\` | The API may provide thumbnails and eBay IDs; filter by exact grade/variant and exclude non-card, raw and unrelated results |
| Accepted offer, if one exists | \`acceptedOfferPrice\` only if \`acceptedOfferPriceStatus=found\`; check saved later via free \`GET /v1/best-offer-prices?itemIds=...\` | \`pending\` and \`not_available\` do not prove accepted cash. Never pass nominal sale price as a verified accepted offer |
| PSA cert confirmation/official front+back scans | PSA manual \`/cert/<CERT>\`, owner-supplied images | Actual PSA Public API access currently blocked by 403. Missing images may NOT be fabricated. Comps API does NOT provide SecureScan. |
| PSA Sales History / Auction Prices Realized | Owner-accessible PSA research pages / licensed feed if approved | Official public sold-history or Vault API **NOT** established. No scraping restricted pages or undocumented internal endpoints. |
| ALT, eBay Seller Hub Product Research, PriceCharting | Owner-provided screens, authorized exports, other verified permitted feeds | Cross-check and dedup transactions by source item ID + sale date; never use source UI's aggregate median as a sale |

**Separation of concerns:** \`market_data.py\` or a source-specific market adapter obtains prices; \`psa_cert\` obtains card/cert identity only when authorized; \`image_review\`/image grader receives the exact original scan/photo pixels plus quality warnings. Do not conflate PSA Vault custody, PSA Sales History, and PSA Public Cert API.

## 2. Verified CompSniper documentation, access and quota

1. PSA catalog + pricing: https://api.compsniper.com/docs/psa
2. Full API and field definitions: https://api.compsniper.com/docs/api-reference
3. 3-year eBay Product Research data: https://api.compsniper.com/docs/sold-history
4. Accepted Best Offer prices + *free* subsequent status checks: https://api.compsniper.com/docs/best-offer-prices
5. Plan pricing dated 2026-10-27: https://api.compsniper.com/pricing
6. Official PSA API docs (registration does not guarantee entitlement): https://www.psacard.com/publicapi/documentation
7. PSA research: https://www.psacard.com/auctionprices

As advertised 2026-10-29: **free = 100 requests/month, $9/month = 2,000, $29/month = 10,000, $79/month = 50,000**. PSA requests count like eBay requests; provider docs say failed requests do not charge; accepted-offer follow-up lookup is free, under the normal minute rate limit. Do not buy or upgrade without owner action. One history page = one request; per-minute history cap 20; free plan general cap 30/min. Bulk batch charges per card, NOT automatically a cheap single request for hundreds of cards. Use \`GET /v1/account/usage\` for usage; cache cards by exact verified \`specId\`, route, grade, observation window. Provider docs indicate search pace around one request/second and occasional 502/503.

**Data license:** CompSniper advertises commercial use; its upstream provenance, completeness, right to store/reproduce images, and PSA affiliation or license are NOT independently established. Treat prices as third-party observations until corroborated. Never assume that documented endpoints imply permission to bypass terms elsewhere.

## 3. Plug and play (NO paid API calls or uploaded secrets)

1. Owner creates **free** account/key via https://api.compsniper.com/dashboard and keeps key private. Do not post in chat, GitHub, app logs, screenshots or Codex prompt.
2. On Mac terminal, supply key in **process environment** (prefer shell keychain/secure local .env with \`.gitignore\`; no keys in committed files). Example:
   \`\`\`bash
   read -rs COMPSNIPER_API_KEY; echo
   export COMPSNIPER_API_KEY
   # Paste key into read prompt; never commit it.
   \`\`\`
3. From Holy Pokémon checkout, dry-run before spending the provider quota:
   \`\`\`bash
   PYTHONPATH=. python3 -m holy_pokemon.compsniper --search "Entei 34"
   \`\`\`
4. First approved live call, operator-controlled:
   \`\`\`bash
   PYTHONPATH=. python3 -m holy_pokemon.compsniper --search "Entei 34" --live --max-calls 1 --output work/compsniper_entei_search.json
   \`\`\`
   **Human verifies exact ENTEI #34 2001 WOTC promo / Game Movie reverse foil; PSA catalog naming aliases exist.** Do not pick first string match by default. Note actual numeric \`specId\` from search result; ignore any example IDs from unrelated cards.
5. Get grade 10 (and separately grade 9) after verifying identity:
   \`\`\`bash
   PYTHONPATH=. python3 -m holy_pokemon.compsniper --spec-id VERIFIED_NUMERIC_ID --grade 10 --live --max-calls 1 --output work/compsniper_entei_psa10.json
   PYTHONPATH=. python3 -m holy_pokemon.compsniper --spec-id VERIFIED_NUMERIC_ID --grade 9 --live --max-calls 1 --output work/compsniper_entei_psa9.json
   \`\`\`
6. Optional rare 3-year comps (avoid too-long keyword; start narrower then filter exact variants):
   \`\`\`bash
   PYTHONPATH=. python3 -m holy_pokemon.compsniper --history "Entei 34 PSA 10" --start 2023-10-29 --end 2026-10-29 --live --max-calls 1
   \`\`\`
7. Audit provider quota usage and specific output, compare against the **Entei ground-truth UI comparison** in \`research/strategy_discovery/psa_entei_34_comp_provider_benchmark_2026-10-29.json\`. **Only then** promote provider to broadly preferred comps source. Keep source provenance for failures and no matches.

The adapter is read-only and \`--live\` is required; an offline dry run makes no requests. Caching is under \`work/compsniper_cache\` (do not commit cache or secret files). Current \`--max-calls\` is a **per-process** cap, not a durable daily/monthly ledger; before high-volume runs Codex must add a persistent account quota ledger and atomic budget lock, use provider remaining-usage headers, track failures/cached hits, and monitor rate limits across jobs. A local desktop integration needs a credential status/validation UI without ever echoing the token.

## 4. Entei benchmark: exact known UI figures, not guessed profits

Canonical target: 2001 Pokémon 3 Movie Promo / WOTC Black Star Promo **Entei #34 reverse foil**, PSA 9 source specimen **cert 108755543** (user-provided slab photos, SecureScan not yet verified). Distinct from Neo Revelation Entei and movie promo non-reverse foil. PSA's catalog aliases include "Pokemon Game Movie Entei-Reverse Foil #034" and "Pokemon Wizards of the Coast Black Star Promos Entei #34". **Confirm same edition/finish explicitly** before merging.

PSA Sales History **PSA 10** owner-observed 2026-10-29:
- 2026-10-21 eBay auction $1,825.00, lot/item 307228435607
- 2026-10-21 eBay auction $1,725.00, item 800795877708
- 2026-10-20 eBay fixed $1,995.60, item 327406749204
- 2026-10-17 eBay auction $1,697.43, item 206616977459
- 2026-10-08 eBay Best Offer $1,700.00, item 298729654263
- PSA UI historical/selected average $1,474.02, last sold $1,825, low $940, high $2,099.26. **Median of these five most recent user-shown sales: $1,725**, arithmetic mean $1,788.61; neither represents after-fee net or a guaranteed exit.
- ALT owner view: 2026-10-21 1,825 and 1,725, 2026-10-20 ~1,989, 2026-10-17 ~1,697. Different displayed price vs PSA; match item IDs and sale status.
- Owner's exact long-keyword eBay Seller Hub Product Research showed **only** Oct 2 $1,125 and Oct 3 $1,500 in its last-30-day search: this is incomplete coverage for the query, **not** proof PSA/ALT sales didn't happen. Shorten keywords rather than automatically discount the later records.

The goal is to retrieve at least 3/5 PSA UI lot IDs with exact amounts/dates in a CompSniper response before relying on it as an Entei comps provider. If 0/5, keep it as supplemental. Consider eBay source-ID existence, sale reversal/relist, grading qualifier, price basis and source lag. **Do not invent PSA9→PSA10 conditional success odds**: two selected FredyCards PSA9→PSA experiments (11/20 and 5/20 upgrades) are selected, different cohorts and not calibrated to this Entei.

## 5. Codex integration tasks, **implement rather than re-plan**

The repo's **main** currently contains \`holy_pokemon/compsniper.py\`, \`tests/test_compsniper.py\`, this handoff and benchmark. Codex's Mac checkout is newer, and may already have different modules. Merge carefully, do not replace local code, and read/update \`docs/IMPLEMENTATION_STATUS.md\` and \`outputs/run_state.json\` if present.

1. Merge adapter into production provider registry and **settings panel** with \`COMPSNIPER_API_KEY\` as env/secret-store input, **one-time Validate** that reports key validity/remaining quota without displaying secrets, and a manual refresh/cancel action. Disable by default and no auto-paid charges.
2. Build two-tier market-data cache: (a) exact normalized card identity, PSA \`specId\`, grader/grade, variant and sale source; (b) sale ID, amount basis, dates, status, original URLs and retrieval timestamp. Keep fresh research separate from validated marketplace receipts.
3. Add robust API handling: 400 input errors, 401/403 invalid key, 429 distinguish rate-limited vs quota exhausted, 502/503 backoff, timeouts, retries with a **finite total**, stale cache visibility, idempotent persistence and durable cross-process quota accounting. Avoid logging Authorization. Use public OpenAPI schema https://api.compsniper.com/openapi.json.
4. Implement optional short-keyword query expansion for low-hit cards (no restrictive whitelists), relevant grade and variant filters, exact source ID dedup, comparative PSA9 vs PSA10 lookback, matched median/quantile/volume and conservative exit range. Treat provisional Research listing aggregates differently.
5. Build **image side:** prefer available *official* PSA SecureScan when user supplies a permitted file, verified approved feed or official user-facing viewing; add optional cert hyperlink. When cert API returns 403, show "PSA approval pending" and do not retry storm. Marketplace original scans are fallback and quality downgrade; image quality and damage visibility must be shown. No image alteration or fake defects, no promises of grade-10 chance without held-out calibration.
6. Connect high-quality comps to ranking and risk models (expected downside, no upgrade case, original PSA9 resale, all fees, time, break-even). Do not auto-buy; approval requires exact-card evidence and operator review.
7. Add reproducible integration tests with mocked HTTP and no secrets, Entei known-sale regression and wrong-card/grade/edition rejection, accepted-offer pending vs found, no-images cases, 403 PSA case, 429/503 handling, unit-vs-aggregate distinction, dedup and budget. Run full suite and report observed results.
8. **Scale opportunistically** across all sets/eras/variants/strategies specified by the owner, not just this Entei; batch/caching can preserve Codex credits. The owner separately controls spending, run limits and query budget.

**Every statement of "data verified" must name the verifying source.** Before CompSniper live key test, status is **documented but NOT confirmed live.** The owner makes purchases and approves any paid service or credential connection. Avoid calling a third-party CompSniper price "PSA official API data."

## 6. Sources of truth: grading and financial boundaries

Read \`AGENTS.md\`, \`docs/OPEN_ENDED_ARBITRAGE_DISCOVERY.md\`, \`docs/CODEX_ONE_SHOT_EXECUTION.md\`, \`docs/MARKET_DATA_SOURCES.md\`, \`research/strategy_discovery/evidence_manifest.json\`. For CompSniper documentation, favor vendor schema over guesses. For PSA, **actual 403 owner-test overrides claims that generating a token is enough**. Don't introduce a second build contract or run another expensive dataset-wide research import before incremental implementation.
