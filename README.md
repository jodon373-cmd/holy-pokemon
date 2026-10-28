# Holy Pokémon

**New private home for the Pokémon grading-arbitrage bot.** This project is separate from `jodon373-cmd/pokemon-market-scanner`; the old repository is an optional source of reviewed implementation ideas, **not** the source of truth.

## North star
Discover overlooked listings across Pokémon eras, grades, languages and slab companies; evaluate the actual card condition and regrading pathways; compare expected resale outcomes with real current sold-price evidence; and show research leads and verified trade opportunities separately.

**Status (2026-10-28):** research and project foundation only. **No new bot implementation, trained predictor, live marketplace integration or automated buying exists in this repository yet.** A separate assistant-produced V1 starter ZIP must **not** be presumed installed or authoritative. The user will supply the final Codex build instruction after reviewing scope.

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

**Read [AGENTS.md](AGENTS.md) before any Codex work.** Architectural and functional requirements are in [docs/PROJECT_SCOPE.md](docs/PROJECT_SCOPE.md). No final Codex prompt has been written or approved.
