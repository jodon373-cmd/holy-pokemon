# Holy Pokémon

**New private home for the Pokémon grading-arbitrage bot.** This project is separate from `jodon373-cmd/pokemon-market-scanner`; the old repository is an optional source of reviewed implementation ideas, **not** the source of truth.

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
