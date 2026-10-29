# Holy Pokémon

**New private home for the Pokémon grading-arbitrage bot.** This project is separate from `jodon373-cmd/pokemon-market-scanner`; the old repository is an optional source of reviewed implementation ideas, **not** the source of truth.

**START CODEX LOCALLY:** **[ONE-SHOT ALL-IN-ONE EXECUTION](docs/CODEX_ONE_SHOT_EXECUTION.md)** is now the single most recent and authoritative build order. It covers full Fredy images + held-out training, all sourced arbitrage rules, eBay/PSA Vault/other venue adapters, portfolio cash cycle, backtesting, and premium blue/red Pokémon-inspired dashboard. Older [master build](docs/CODEX_MASTER_BUILD.md) and [grader-first](docs/CODEX_GRADER_FIRST_LAUNCH.md) documents are supporting technical references, not competing prompts. **The code is a starting foundation, not a trained grader or completed live scanner.**

## Open-ended arbitrage strategy research — 2026-10-29

**[READ THE COMPLETE NEW STRATEGY PLAYBOOK](docs/OPEN_ENDED_ARBITRAGE_DISCOVERY.md)** · **[ALL SOURCE/UNCERTAINTY RECORDS](research/strategy_discovery/evidence_manifest.json)** · **[13 EXTENSIBLE ROUTES](research/strategy_discovery/routes.json)**.

Includes Jungle (all 64 base cards and 152 search variants), Pokémon Promos, cross-set Fossil/Base Set 2/Team Rocket/Gym Heroes/Neo/2010s comparisons, source-reported completed sales, FredyCards' 546-card PSA→CGC cohort, two-year grading-era trends and counterexamples. **The current shortlists are discovery seeds, not restrictions.** Codex can investigate wholly new sets/cards/strategies or import an arbitrary card universe with `python3 -m holy_pokemon.open_strategy_discovery --universe path/to/new_cards.csv`. This merely generates research queries; no live APIs are called, no current prices or grade-conversion odds are invented. **Owner sets Codex execution/credit/query limits in the next assignment**, not this repository. Preserve conservative research vs manual trade-approval separation. GitHub additions are not guaranteed to be integrated into the newer running Mac app.

## CompSniper sold comps + PSA high-resolution condition images (2026-10-29)

**[Full API/image integration handoff](docs/COMPSNIPER_COMPS_AND_PSA_IMAGE_INTEGRATION.md)** covers CompSniper PSA prices, sets, populations, recent sales, three-year eBay history, accepted Best Offer statuses, and the Entei #34 PSA9→PSA10 owner-supplied October 2026 sale benchmark. An opt-in read-only Python adapter with dry run and mocked tests is committed as `holy_pokemon/compsniper.py`. It needs an owner-created API key for the first live test and integration into the newer Mac app. **No verified live CompSniper calls have run.** CompSniper does **not** document PSA SecureScan-quality scans; those must come from separate legitimately available PSA cert records or user-provided images. Official PSA API is currently blocked by HTTP 403 pending customer approval.

## Centering v2 + saved 645-listing backtest (2026-10-29)

**[Centering implementation and Mac replay guide](docs/CENTERING_V2_645_BACKTEST.md)** · [Detector](holy_pokemon/centering_v2.py) · [Local replay tool](holy_pokemon/centering_backtest.py) · [Offline tests](tests/test_centering_v2.py).

Project now includes separate outer-card vs. printed-border geometry, perspective correction, multi-sample border consensus, honest abstentions, hash-checked resume cache, and an auditable replay for all **645 existing Mac-local** IDs. Default research target: **PSA 9 asks ≤$500**; higher-priced cards only enter a pending premium-exception lane until exceptional centering, condition, exact sales and costs are verified. Local full-universe centering precedes any paid AI grading of financially ranked favorites. **No real 645-photo v2 backtest has yet been executed on GitHub**; its source assets remain in the owner's newer Mac checkout. No expensive image API or eBay calls required for replay.

## North star
Discover overlooked listings across Pokémon eras, grades, languages and slab companies; evaluate the actual card condition and regrading pathways; compare expected resale outcomes with real current sold-price evidence; and show research leads and verified trade opportunities separately.

**Status (2026-10-28):** implementation has started. Executable read-only Python modules include the 8-month business audit, local transport audit, multi-route pricing, PSA Vault fee/custody/payout logic, specimen/event cash ledger and experimental PyTorch train/infer code. GitHub CI unit tests validate the currently implemented modules. **The complete all-in-one UI, live authorized marketplace adapters and genuinely trained real-data grading weights are still not finished.** Codex must finish the [master build order](docs/CODEX_MASTER_BUILD.md) and [Fredy business reconstruction](docs/FREDY_BUSINESS_REVERSE_ENGINEERING.md). A separate assistant-produced V1 starter ZIP is not installed or authoritative. The owner launches the build by instructing Codex to execute the committed build order.

## Research evidence
We have 18 canonical source archives inventoried in [research/manifest.csv](research/manifest.csv), including:
- Eight Fredy Cards monthly financial research packs (February–September).
- Detailed PSA→CGC, PSA→PSA and CGC→CGC card case studies.
- 546-PSA→CGC historical **aggregate** study and two-year PSA-vs-CGC gem-rate **aggregate** study.
- Community Challenge (20 cards, lightweight version; full-resolution evidence retained separately).
- One Piece BGS 9.5→PSA outcomes, **isolated from Pokémon estimates**.

The original files stay **locally stored and immutable**; they are deliberately **not committed to GitHub**. The manifest lists canonical names, ZIP hashes and content types so Codex can discover, verify and ingest them efficiently. Older monthly financial cases can overlap with public-video cases, and some recaptures duplicate videos. See [docs/RESEARCH_INVENTORY.md](docs/RESEARCH_INVENTORY.md) and [docs/DATA_INTEGRITY.md](docs/DATA_INTEGRITY.md).

## Required product boundaries
1. **Discovery lane:** broad interesting opportunities, including speculative high-upside and expensive cards; missing data makes a lead *unverified*, not invisible.
2. **Trade-approval lane:** strict dated sold comps, exact variant matching, condition risks, full all-in costs, realistic downsides, liquidity and manual approval.
3. **Research-driven grade analysis:** inspect unmodified listing photos plus subgrades/era/holder information; estimate ranges and uncertainty, not guaranteed grading results.
4. **Market connections:** approved eBay APIs when actually authorized; PSA Vault listings/other legitimate providers where permitted; manual CSV, screenshots and user-provided exports as offline fallback.
5. **Portfolio protection:** initial shared **$2,000 all-in test cap**, remaining **$5,000 untouched**, no automatic purchases or unapproved paid services.

**PSA Vault is a required full workflow**: vaulted vs eligible discovery, collection and custody, tax/fee/withdrawal analysis, PSA eBay consignment and Partner Offers, withdraw-to-regrade, owner-initiated transfer tracking and payout reconciliation. See [docs/PSA_VAULT_END_TO_END.md](docs/PSA_VAULT_END_TO_END.md). It is not a promised undocumented API.

**Codex start:** read [AGENTS.md](AGENTS.md), then execute [docs/CODEX_MASTER_BUILD.md](docs/CODEX_MASTER_BUILD.md). Engineering source references and prior tests are quarantined under [reference/legacy_scanner](reference/legacy_scanner/README.md). Complete data/vision design: [docs/PROJECT_SCOPE.md](docs/PROJECT_SCOPE.md), [docs/AI_GRADER_TRAINING.md](docs/AI_GRADER_TRAINING.md), [docs/MARKET_DATA_SOURCES.md](docs/MARKET_DATA_SOURCES.md). For primary 18-source records and the additional overlapping 28-video transcript corpus, see [research/FULL_SOURCE_TRANSPORT.md](research/FULL_SOURCE_TRANSPORT.md) and [research/DATA_TRANSPORT.md](research/DATA_TRANSPORT.md).
