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

## Reviewed centering v3 and offline search upgrade

The additive `centering_v3`, `title_parser`, `comp_index`, `roi_scorer`,
`query_planner`, and `scan_pipeline` modules support experimental image geometry
and offline research ranking. eBay CLI imports now have the required network,
SQLite, and CSV helpers. Existing v2 and dashboard flows remain available.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install 'Pillow>=10,<13' 'numpy>=1.26,<3' 'opencv-python-headless>=4.8,<5'
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m holy_pokemon.scan_pipeline --input listings.json --output-json outputs/leads.json --output-csv outputs/leads.csv
```

Input is a JSON list (or an object with `listings`), with `title`, `card`,
`number`, `set_name`, `edition`, `asking_price`, and `shipping` fields. Explicit
zero shipping means free shipping; missing shipping remains unknown. Currency
defaults to USD for manual files; explicit other currencies require conversion
outside this scanner. Titles must identify finish for scoring. Incomplete leads
remain visible with an explanatory status. The CLI reads local input only; it
neither searches live nor automatically measures photos. A previously computed
`centering` result may be supplied per listing.

Comp summaries preserve source-reported status and reject ambiguous variant
pools. Default fee/tax assumptions are illustrative, configurable through the
Python `FeeSchedule`, and reported alongside results. Downside uses target-grader
9 comps, never the destroyed original holder; it is a scenario rather than a
worst-case bound. Break-even rate is sensitivity, not an upgrade probability.
All leads have `trade_approved: false`.

Centering v3 thresholds are **unverified experimental screening heuristics**,
not certified current grader standards. Synthetic image tests do not establish
accuracy on real cards. No independent real-photo benchmark or 645-listing v3
replay has been run; v3 is not substituted for v2 in the saved-listing backtest.
The initial 100-test local suite includes all three supplied v3 image tests and 11 review
regressions, with no skips (Python 3.14 on this Mac; CI uses Python 3.12).

Upgrade source: owner-provided `holy-pokemon-upgraded.zip`, SHA-256
`d1081e905ebafd250891177b533dcb5d04d363490753df633d9cacdac4e37021`.
Both supplied archives passed ZIP CRC integrity checks; original archives and
Desktop source folders were preserved.


## Run automatic centering

Double-click `mac/Centering_Tool.command`, or run:

```sh
.venv/bin/python -m holy_pokemon.centering_tool
```

Choose or drop a photo. Side detection, physical card detection, perspective
correction and printed-border measurement run automatically. The page overlays
the detected boundaries and displays left/right and top/bottom ratios. Upload
both sides of the same specimen for a combined centering screening check.
There is no manual corner or border placement in this flow. Export saves JSON.

For unattended local batches:

```sh
.venv/bin/python -m holy_pokemon.centering_tool --image /path/front.jpg --image /path/back.jpg --output outputs/automatic-centering.json
```

V3.2 uses supported physical border color plus straight-edge evidence to avoid
slab/frame confusion. Rounded tips no longer pull physical corners inward.
Front sampling uses the outer border color and rejects deeper artwork edges.
Blue backs and observable yellow-border fronts are supported. Full-art, silver,
e-reader and obscured borders can abstain; this is not universal design coverage.
Original photos are never changed or uploaded.

The reproducible known-PSA10 diagnostic is in `research/centering_v3/`:
six photos of four specimens, **three automatically measured and within their
side's screening band, three abstentions**. The measured photos are Houndoom
back (51.43/48.57 L/R, 54.32/45.68 T/B), Tyranitar back (49.28/50.72,
46.43/53.57), and Jolteon front (48.98/51.02, 54/46). Front/back counts must
not be presented as three completely evaluated specimens. Labels come from
owner records or visible holders, not a fresh certificate API check. These are
known-label diagnostics, not blind accuracy or final-grade predictions.

```sh
.venv/bin/python -m holy_pokemon.centering_benchmark --manifest research/centering_v3/known_psa10_manifest.json --image-root /path/to/existing/holy-pokemon --output outputs/psa10-replay.json
```

The manifest pins immutable original hashes and references local photos without
publishing them. Geometry helpers were reviewed and adapted from the owner's
newer local `centering_v3.py`; that checkout was preserved unchanged.
