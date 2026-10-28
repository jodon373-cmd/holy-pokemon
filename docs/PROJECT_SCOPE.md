# Product scope — design contract (NOT yet a Codex master prompt)

## Goal
New practical Pokémon arbitrage assistant for Mac that systematically surfaces overlooked graded cards and evaluates actual regrade/resale paths. Research is sufficient to begin coding. Continue incorporating additional evidence later without restarting architecture.

## Core workflows
**A. Discover:** Browse authorized listings and manual exports, bulk-import eBay titles, approved sold research, seller-supplied photos, and PSA Vault listings where access permits. Monitor vintage 1996–2007 (English/Japanese), EX era and stamped reverses, modern standout cards and legacy CGC blue-label; allow researched expansion. Never quietly limit the lead universe to cheap commons.

**B. Resolve:** Normalize game, set/year, card name, number, edition, 1st edition, finish, holo/reverse, stamp, promo, Japanese/English, label/cert, BGS subgrades. Block materially ambiguous variants from verified profit calculations.

**C. Inspect:** Preserve original full-size front/back photos; identify centering, corner whitening, wear, edge chips, holo scratches, textured/foil defects, stains/indentations, slab glare and missing image surfaces. Make confidence and reason codes visible; support human annotation. BGS subgrade pathways must reflect era and category, not simplistic averages.

**D. Price:** Current sold-price evidence via **authorized eBay API** if the account has required access; separately support manual exports from eBay Product Research or user-submitted sold screenshots, and other authorized market data including PSA Vault listing sales when legitimately available. Don't claim PSA Vault is a universally available API. Respect marketplace terms. Dated exact comps, sale format, condition and sales fees matter. Asks are not sales.

**E. Evaluate:** Multiple strategy pathways—hold original slab, sell as-is, legacy CGC reholder, CGC→PSA, BGS9.5→PSA, PSA8/9→CGC, PSA9→PSA, CGC→CGC. Scenarios for realistic grades (not only optimistic 10), turnaround time, shipping/tax/insurance/grading/premium, liquidity, fee friction and worst-case outcomes. Value-over-cost != realized profit. Do not quote precise predictive success probabilities until substantiated by held-out evidence; start with transparent empirically informed scenarios.

**F. Rank:** Separate wide high-upside/watchlist **research discovery** from conservative strict **trade-ready approval**. User manually approves any trade. Track changing sales/comps and source freshness. Show summary, source links, expected upside range, likely reasons, risks and what needs verification.

## PSA Vault — first-class end-to-end workflow
Read [PSA_VAULT_END_TO_END.md](PSA_VAULT_END_TO_END.md). Product must support permitted discovery of vaulted and vault-eligible eBay listings, collection/custody import, actual PSA Partner Offers, PSA auctions/Buy It Now consignment, withdraw vs sell vs regrade net P&L, dated insurance/withdrawal fees, optional vault-to-vault transfer tracking (manual irreversible action only) and owner payout reconciliation. PSA's single-cert public API does NOT provide a public personal Vault inventory endpoint. Implement a complete user-operable flow with manual/authenticated permitted inputs and clearly label absent automated sync. These are required for the initial integrated product, not later enhancements.

## Engineering north star
- Python core with SQLite or comparable auditable store; modular adapters for marketplace and image inspection; CLI first, then streamlined desktop/web UX.
- Deterministic identity and math, incremental resumable ingestion, local-first caching, structured provenance and reproducible tests. No unnecessary AI call per listing and no forced premium subscriptions.
- No live order placement, automatic purchases, paid provider plans or high-volume prohibited scraping.
- Shared $2,000 test budget; $5,000 preserved. User chooses actual acquisition and risk level.
- Use read-only `pokemon-market-scanner` to borrow reviewed reusable code, not to migrate or overwrite old data.
- Avoid bloating GitHub with hundreds of megabytes of evidence and videos. Store a file manifest and hashes in Git; user retains raw ZIPs offline.

## Development sequence when authorized
1. Verify available ZIPs against hashes, parse all 18 source types and surface coverage/conflicts.
2. Build canonical entities and audits for physical card identity, creator predictions, event histories and price observations.
3. Build actionable listing discovery and authorized eBay/manual import provider abstractions.
4. Build visual condition screening and transparent grade-scenario calculations.
5. Add strict approval scoring, evaluation/backtests, usable review interface, tests and deployment guide.

**The master Codex build order has now been written** at [CODEX_MASTER_BUILD.md](CODEX_MASTER_BUILD.md). It has not yet been executed; actual implementation will begin when the owner launches it.
