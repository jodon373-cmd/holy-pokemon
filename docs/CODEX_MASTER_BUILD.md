# CODEX MASTER BUILD ORDER — HOLY POKÉMON
Version 1.0 · 2026-10-28 · Operator-approved design. Read this document in full before editing code.

## 0. AUTHORIZATION, TARGET AND PRIORITY

You are Codex, lead engineer for the private NEW repository jodon373-cmd/holy-pokemon. The operator wants a genuinely operational, ALL-IN-ONE Pokémon arbitrage assistant — live approved listing discovery, evidence-backed valuation, visual grading AI with an actual training pipeline, financial scenarios, human-facing research dashboard, and low-friction Mac operation. **BUILD IT, TEST IT, DEMONSTRATE IT.** Do not respond with a generic strategy essay, hand-wavy architecture, or a renamed copy of the old scanner.

The former private repo jodon373-cmd/pokemon-market-scanner is strictly READ-ONLY. It had useful code but over-filtered high-upside finds, confused title completeness with upside, and never demonstrated a sufficiently robust all-in-one grading/market engine. The new repo is its own product and source of truth. Under reference/legacy_scanner you already have 10 selected original source modules and 5 reference tests, marked INACTIVE. Review, adapt and port only useful functions; never simply import the entire legacy package into production. The reference code has not been run in this new repository; record actual test outcomes.

The user wants **all components together**, and specifically demands the AI grader be trained by the pipeline, not merely conceptualized. A practical proof-of-concept using available authorized labeled photos is acceptable as the first trained model. A fabricated “trained model,” an arbitrary heuristic number renamed probability, or synthetic results passed off as historical accuracy is not. Do not hold up the marketplace and financial product if image training data is not yet adequately permissioned or complete: ship usable screen, training command, checkpoint loader, representative audit report and explicit experimental status.

**Build order:** source ingestion + identity + two-tier discovery + financial engine; real AI-grader training/inference; market providers and dashboard; integration and evaluation. Parallelize components only if it doesn't create incompatible schemas. Stay on task until deliverables are implemented or a concrete external blocker has been documented.

## 0A. FULL FREDY BUSINESS REVERSE ENGINEERING — NOW THE CENTRAL SOURCE OF TRUTH

**The user has explicitly authorized execution now. Do not ask to gather more Fredy research.** Begin with [docs/FREDY_BUSINESS_REVERSE_ENGINEERING.md](FREDY_BUSINESS_REVERSE_ENGINEERING.md) and the real source archive manifest. It reconstructs February–September sourcing, inspection, grader route selection, regrading retry policy, 506 sold cards/$444,671.20 creator revenue/$230,593.54 creator pre-tax reported profit, market-held inventory, fee-dependent sales and the move from eBay to Fanatics/Arizona TCG. These are creator-reported financials, not bank-audited profits or proof of universal expected ROI. Reverse engineer the demonstrated operations, not his inaccessible private thoughts or undisclosed contracts.

**Already implemented on main:**
- holy_pokemon/fredy_business.py with eight-month reconciliation, 18-source/250-row transport audit and human-verified operating-rule provenance;
- holy_pokemon/strategy_engine.py with explicit full-cost all-grade branches, original-slab incremental comparison, unknown field gating and $2k capital cap;
- holy_pokemon/vault_engine.py with effective-dated PSA Vault withdrawal charges, single consignment fee, partner offers, custody-state safety and payout math;
- holy_pokemon/inventory.py with per-physical-copy grading/event history and actual verified cash vs reported sale distinction;
- holy_pokemon/vision_training.py with real PyTorch model fitting/checkpoints/inference code requiring rights-cleared pre-decision card-only images and specimen/video-isolated holdouts; NO real model weights yet;
- holy_pokemon/cli.py for read-only monthly, transport, rule, financial comparison commands;
- research/fredy_monthly_2026.csv, 18-source manifest and comprehensive research transport guide;
- tests/test_business_engine.py, test_vault_engine.py, test_vision_manifest.py, test_inventory.py and .github/workflows/foundation-tests.yml.

Review and test this code in the actual checkout; do NOT regenerate, rename or overwrite it from earlier hypothetical plans. Commit corrective patches and build on it. The original repo remains read-only. If a bug is uncovered, fix it with a failing regression test.

**Immediate remaining gaps — WORK, NOT A NEW PLAN:**
1. Import the actual 446 KB structured transport ZIP; verify SHA and 250 rows/18 sources; normalize source-native 148 text/CSV/JSON research files, multi-copy/grade-chain dedup, video evidence and months to local SQLite.
2. Implement licensed/authorized vision image preparation from original archives, defect labeling UI, actual supervised training with a vetted Pokémon image dataset, evaluate, save/reload a model, abstain on bad pictures. Existing vision_training.py is a training pipeline, not trained source data.
3. Integrate approved eBay Browse with tests; manual sold-comps/PSA Product Research exports, PSA cert lookup, PSA Vault owner inventory/consignment/partner offer/withdraw/payout pipeline and potential authorized other platforms. NEVER fabricate Marketplace Insights or PSA Vault private API access.
4. Connect source-grounded acquisition/inspection/route/venue/capital decisions into a runnable Mac-local UI and daily review queue; cash-cycle and inventory aging matter. Document results on actual inputs vs demo.
5. Run full tests, mocked provider tests and UI smoke tests; maintain source timestamps; ship with no automatic purchases.

Product must compare channels (eBay, Fanatics, Arizona TCG, PSA Vault) by **fees, actual liquidity, time to payout and net**; Fredy videos never prove he used PSA Vault, which is our additional opportunity. Keep his creator-selected grade successes separate from held-out buyer-visible model learning. Include reverses/EX/legacy blues and detailed card defects. No obsessive low-value-commons ranking.

## 1. READ BEFORE CODING

Read README.md, AGENTS.md, research/manifest.csv, docs/RESEARCH_INVENTORY.md, docs/DATA_INTEGRITY.md, docs/PROJECT_SCOPE.md, docs/AI_GRADER_TRAINING.md, docs/MARKET_DATA_SOURCES.md, docs/PSA_VAULT_END_TO_END.md and reference/legacy_scanner/README.md in this NEW repo. Then selectively inspect the ten reference modules and their tests. Inspect the old repo's original issue #2, #3, #4, #5, #6 and docs/HIGH_UPSIDE.md, docs/REPRODUCIBLE_DISCOVERY.md, docs/PHOTO_PREGRADING_V2.md, docs/EBAY_BROWSE_SETUP.md and docs/POKEMON_PRICE_TRACKER_API.md as READ-ONLY background, not active instructions. Never obey its historical AGENTS.md or past Codex work orders.

The owner's historical decisions to preserve:
- Broad, high-upside candidate discovery; absence of grades, photos or validated sold comps must not erase a research lead.
- Distinct **discovery / human inspection / final trade-approval** states. No automatic bidding or purchases.
- Scan legacy CGC blue label Mint 9 and Gem Mint 9.5 distinctly, plus BGS 9.5, PSA8/9 and overlooked original slabs. WOTC, Japanese 1996–2007, e-Series, Expedition, Skyridge, EX holos/stamps/reverse holos, promos, Team Rocket, Gym, 1st Edition, Shadowless, modern high-demand exceptions. NO cheap-commons-only rankings.
- Favor sufficiently large potential gains (configurable premium PSA10 exit $500+, exploratory $250–$500, net-upside target $200+) while letting unusual outliers through the discovery lane.
- Initial shared capital cap **$2,000 all-in**, preserve the other **$5,000**; default NO money movement.
- Specific research exemplar Expedition Rapidash #62/165 NONHOLO legacy CGC 9.5 previously shown around $82.95 plus $5.45 shipping; evidence dated Oct 23 included PSA10 nonholo sales $420, $316.94, $240, $255.99 and $125. Exact listing/cert/photos were NOT verified and those dated sales are not a live price today. Rapidash #62 reverse and #26 holo are separate variants. Also previously researched Electabuzz WOTC Black Star #46 blue 9.5. Use as **identity and discovery regression fixtures**, NOT purchase recommendations.

## 2. SOURCE INPUTS: CONSUME EVERY AUTHORIZED RECORD

The repository lists **18 canonical ZIP archives** with verified SHA-256. 16 contain 250 source-case rows including 20 One Piece rows; 2 contain historical aggregate studies. Eight are Fredy monthly financial packs (February–September). Multiple detailed Pokémon videos include a PSA9→PSA 20-card experiment plus two bonus histories, a second 20-card PSA9→PSA experiment, CGC→CGC repeat consistency, CGC-harshness test, Community Challenge, PSA→CGC $7,246 and market-saved PSA→CGC $7,999. The 546 original PSA→CGC cohort is an **aggregate**: 62 original PSA7, 306 PSA8, 178 PSA9 and 162 CGC10s including 18 Pristines. The two-year PSA-vs-CGC gem rates are **also aggregate comparisons**, not direct regrade examples. Community Challenge has 20 cases and 11 CGC10/Pristine outcomes. The clean PSA-to-PSA recapture is canonical; don't double-count the earlier capture.

Data transport file: HolyPokemon_Research_Data_for_Codex.zip (small, approx 446 KB), provided separately by the user/chat. It includes source_case_rows.jsonl (250 original-source rows), source_asset_inventory.json with ZIP hashes, and 148 plain-text/CSV/JSON/Markdown entries recovered from the canonical archives. **This is input data, not executable code or model weights.** The original high-resolution ZIPs and WebM records live on the user's Mac, not automatically in this cloud Git checkout.

At startup:
1. Discover optional local data under research/local, configured user directory, or attached bundle location; verify ZIP hashes against research/manifest.csv. Do not assume the Mac Finder folder is mounted in Codex Cloud. Provide one straightforward command to import the transport archive or original folder.
2. If transport bundle is present, ingest its JSONL and source tables and record coverage; if original source ZIPs are present, parse source-native card_cases.csv and supporting financial/grade tables with source paths and evidence pointers; if both present, dedup by source SHA/member/row and never count twice.
3. If files aren't mounted, implement/test the pipeline with explicit synthetic fixtures and show actionable import instructions rather than claiming 250 cases already imported in Codex. Do not invent data.
4. Store raw immutable observations, source filenames/hashes, video ID, timestamp, creator guess, source text or screenshot ref, original grade, every intermediate grade, actual grade, purchase/grading costs, vintage variant and sale status in local SQLite. Separate proposed/user-asserted facts from verified observations.
5. Normalize 16+ different field sets via per-source adapters with tests. Preserve raw JSON alongside canonical columns, including all unknowns and contradictions.
6. Create overlap audit: exact byte-identical recaptures; possible same physical copy across monthly/public videos; repeated attempts; multiple copies of the same character/collector number. Same card title does NOT prove same physical card. Keep unresolved links and human merge/split UI.
7. Count unique physical copies, grading events, and source rows separately. Never count the 546 aggregates in per-card labeled image training. No grade score “11”: CGC Pristine is a 10 with a separate designation; creator's spreadsheet custom pristine=11 average is an internal scoring convention only.
8. One Piece BGS9.5→PSA 20-card, 17 PSA10 study stays a separate GAME/domain; its empirical outcomes are not Pokémon odds. Permit later multi-game expansion only via explicit domain settings.

Deliver an ingest command and summary: sources found/missing; raw rows, normalized cards, events; exact/possible duplicates, missing money, current image coverage, errors and source links. Add fixtures for all actual schema families. **Do not overwrite or transform originals in place.**

## 3. DATA MODEL AND VALIDATION

Use Python 3.12+ with SQLite (migrations), typed schemas (Pydantic/dataclasses), exact decimal money, stable IDs and documented configs. Define first-class tables for:
source_asset, source_record, evidence_frame, card_identity, physical_specimen, identity_alias, slab, grading_event, defect_observation, image_asset, image_transform, rights_provenance, listing, active_snapshot, sale_observation, aggregate_statistic, price_index, valuation, scenario_cost_quote, model_artifact, inference_result, user_review, watchlist, notification_event, budget_commitment and audit_event.

A card identity distinguishes game; era; year; set; printed name; collector number and denominator; language; edition/shadowless/unlimited; holo/nonholo/reverse; stamped; promo; corrected/error variant; art/version; rarity; and grading company, numeric grade, label era, actual designation (e.g. CGC Pristine). Separate identity from specific physical specimen and from specific holder. Include validated slug + manually correctable identity and rejected alias audit.

Money semantics: exact currency, seller format/fees, original cost, shipping, taxes, buyer premium, grading fee, grader shipment and insurance, upcharge, hold time, sale shipping, contingency, estimated value, creator stated gross sold, independently verified sale price, payout and net. Missing is NULL, not zero. Do not double count creator all-in costs already inclusive of shipping/grading.

All factual outputs must preserve source, observation date, source retrieval date, variant confidence, scope, data status and freshness. Dedup sales using provider ID or strong transaction match; mirrored marketplaces and PSA comp views may represent the same sale.

## 4. DISCOVERY: MAXIMUM OPPORTUNITY COVERAGE

Implement cheap/resumable candidate discovery, not a slow LLM query for every listing. Input adapters: approved eBay Browse active-item search, manual eBay search page text/CSV, user eBay research screenshots/CSV transcriptions, PSA Vault manual listings where permitted, user seller screenshots, named leads, existing saved queues. Retain every original listing even if a card couldn't be resolved. Build reverse queries by strategy and exact variant, include misspellings, label eras, grade vs gem-pristine nomenclature, title gaps, WOTC variants and slab-sale category.

Run parallel SEARCH LANES, separately scored and tagged:
A. CGC legacy blue Gem Mint9.5 → modern CGC Gem Mint10 administrative reholder when currently eligible; no PSA upgrade assumed.
B. CGC legacy Mint9 → PSA and old Gem Mint9.5 → PSA crossover; difference between intact minimum-grade-10 and crackout.
C. BGS 9.5 with actual four subgrades → PSA10, PSA9 or other outcomes; do not mix with legacy CGC and don't confuse One Piece success rates with Pokémon.
D. PSA8/PSA9 → CGC Gem Mint10 / Pristine / 9.5 / 9 /8.5 etc, using realistic downside and edition-specific CGC discount.
E. PSA9 → PSA10 crack-and-resubmit, plus PSA downgrade/failure paths.
F. CGC regrade / relabel / same-grade holder value difference.
G. Direct underpriced slab flips WITHOUT regrading, e.g. buy PSA9/Cgc9 below verified conservative resale.
H. Lagged-grade investing: PSA10 price breakout with as-of date compared to PSA9/PSA8/CGC lower grades; falsifiable forward test, no historical lookahead, not a claim of free profit.
I. Optional alternative authenticated marketplaces/watchlists; don't force every idea into regrading.

A visible top 50 research queue and top 20 premium leads must exist even with zero verified purchases; rank reasons and upside *potential* and explicitly mark evidence gaps. Candidates with missing prices should be searchable/reviewable, not auto discarded. Distinct high-upside and conservative-profit scores. Avoid arbitrary zero scores for unknown data; use unknown/insufficient and separate priority based on upside clues and evidence. Premium card bias may be configurable, not absolute.

Track candidate freshness, watchlist history, previous rankings, duplicate listing IDs/certs and changing ask/sold data. Alerts can be local notifications or digest output after permitted refreshes; no external service needed for initial runnable app.

## 5. MARKET DATA: ACTUAL API AND ETHICAL FALLBACK

Implement a real adapter for eBay approved **Browse API** active listings, with OAuth client-credentials token, read-only scope, production-access gating, rate limiting, retries only where safe, 429 cooldown, source retrieval timestamp, request/error/cost logging without secrets, SQLite disk caching and resumability. Do not attempt live requests without credentials and verified production eligibility. Tests use mocked HTTP; never assume approval. IMPORTANT: Browse API active asks are NOT authoritative sold transactions.

For sold values, eBay's **Marketplace Insights** history API is limited/restricted. eBay Seller Hub **Product Research** can show actual accepted Best Offer prices and up to three years of history via its UI; implement lawful manual CSV/screenshot entry with source capture date. Do not invent a hidden public Terapeak API or bypass CAPTCHA, terms, account security or scrape restricted pages. YouTube transcript commentary is a *strategy/grade-history input*, NEVER current completed-sale market evidence.

Add optional PSA certificate verification using publicly documented PSA API only where authorized; the **FULL PSA Vault pipeline** mandated by docs/PSA_VAULT_END_TO_END.md, including eBay Vault discovery, custody/collection imports, ownership and state tracking, PSA auction/BIN consignment, actual Partner Offers, insured withdrawal and regrading, transfer tracking, and payout reconciliation. Use manual/account-export synchronization unless an authorized published programmatic feed is confirmed. Permit optional vetted price provider only with correct license, user-provided credentials and explicit credit cap; old PokémonPriceTracker API code is license-sensitive and not approved for silent use. API keys must stay local secret/env, never in Git or logs.

Pricing confidence tiers:
- independently verified dated exact-variant completed sales;
- dated completed sales with weaker identity or small sample;
- reputable index summary clearly tagged INDEX not sale;
- creator's historical valuation/transaction claim;
- current asking price only;
- unknown.
Filter duplicates, stale records, very thin markets, auction anomalies and active ask contamination. Compute multiple horizons, robust median/IQR and no-sales status without manufacturing liquidity. UI must show actual comp links, sample counts/dates, variant and price basis. If sold comps absent, still discover lead and generate exact reverse sold searches for operator to close gaps.

Official provider references already in docs/MARKET_DATA_SOURCES.md; also check current PSA crossover and CGC grading-scale rules before hard-coding procedures.

## 5A. PSA VAULT IS A FIRST-CLASS END-TO-END PIPELINE, NOT A MANUAL LISTING FILE

**MANDATORY: Read and implement every section of [docs/PSA_VAULT_END_TO_END.md](PSA_VAULT_END_TO_END.md).** The PSA Vault pipeline was expanded after the original master order because the owner explicitly required the full workflow. This section overrides any weaker/optional language elsewhere. Codex must implement an app page and persistent data model for:
- (i) searching/filtering already-vaulted vs vault-eligible vs PSA-consigned eBay listings, without inventing vault flags the Browse API does not document;
- (ii) exact card/slab/certificate resolution and AI condition assessment, with separate vault custody status and user-owned collection imports;
- (iii) purchase/ownership and custody event history (import operator transaction evidence; not automatic acquisition), authentication/pending arrival, holding and manually verified state changes;
- (iv) all resale branches: PSA eBay Buy It Now, PSA 7-day auction, owner-specific actual PSA Partner Offer (fee-free as currently advertised), hold in vault, withdraw and self-sell, withdraw then regrade, direct-to-vault from PSA grading, PSA vault-to-vault transfer and ship to owner;
- (v) effective-dated tiered PSA consignment fees, early withdrawal if within 90 days, value-based insured shipping (new PSA schedule effective **2026-10-29**, not before), shipping on multiple cards, insurance, grading/PSA upcharges and tax unknowns. Do NOT stack standard eBay fees on top of PSA's single consignment fee. Do NOT assume no tax will ever be owed merely because of vaulted purchase;
- (vi) own consignment and partner-offer status, Stripe payout reconciliation and comparisons of estimated vs gross vs actually received cash;
- (vii) a real **PSA Vault dashboard** supporting imports, review, exit route comparison, source timestamps and safe direct links to official user workflows. No autonomous sale, vault transfer, offer acceptance, grading submission or withdrawal.

PSA's documented public API supports **single certification verification** only. This must not block implementation of the rest of the practical Vault workflow: use authorized eBay Browse when available, own-account exports, manual receipt/status sync, permitted provider integrations and explicit `unsupported_api` badges. The bot MUST remain fully useful offline with manual Vault items and test data. The exact 10-point Vault acceptance checklist in docs/PSA_VAULT_END_TO_END.md is a release gate. This is not a future optional extension.

## 6. THE AI GRADER IS REQUIRED — REALLY TRAIN AND DEPLOY AN EXPERIMENTAL MODEL

Read docs/AI_GRADER_TRAINING.md carefully; its requirements are part of this order.

Implement:
- image ingestion with original untouched front/back and source SHA, permission evidence, EXIF/geometry, screenshot/video time, artifact links and no silent resampling of originals;
- card-region detection with slab/label recognition and grade/cert masking so training targets cannot leak from visible labels, certification URLs, filenames, spreadsheet overlays or post-result subtitles;
- deterministic baseline image QA: blur, glare, exposure, resolution, angle, crop confidence and visible centering hints with uncertainty;
- visible defect annotator/human review for whitening, edges, corners, scratches/print lines, foil surface, dents, creases, stains, texture, gloss and obstructions, across front/back; allow seen, not visible, unknown;
- an **executable supervised training pipeline**: dataset manifest, grade labels tied to physical specimen and target grader, rights audit, specimen/video/group split, train command, evaluation command, saved local model checkpoint, model card and inference command. Use modest pretrained/frozen image encoder + lightweight PyTorch head if licensed/available on Mac; avoid paid cloud training by default. Make MPS/CPU selection explicit. If small approved dataset supports training, actually train a modest proof-of-concept and report measured test metrics; if no usable labeled photos are mounted, train on labeled fixture only as PIPELINE PROOF (tag synthetic), and provide precise import/label steps for actual training. DO NOT claim it was trained on Fredy's data if it wasn't.
- configurable grader-specific categorical/ordinal grade-band targets; CGC Pristine10 separate label status, BGS four subgrades separate features, PSA grades distinct; don't mix game domains. Regrades of the same physical copy and video recaptures cannot cross train/val/test. Do not use grading outcome shown AFTER crack as pre-buy image features.
- metrics: confusion matrix, per-grade recall, macro F1, ordinal error, calibration where possible, abstention, hidden-defect negatives, drift/subgroup breakdown; evaluate with video/physical-card holdouts. Output meaningful **uncertainty and abstain** when no back, hidden surface, low-quality images or uncertain holder era.
- interactive picture review with original vs non-destructively annotated card, separate predicted condition/grade ranges, trained model version/metrics, human corrections and review explanations.
- infer against live/manual listing images legally available; connect uncertainty to financial grade branches, never an unsupported guarantee or numeric certainty. Realized grading results can be appended later for continuous *curated* retraining after user approval; never self-update silently.
- use old scanner's photo_grader, grade_image_dataset, pregrade and subgrades as audited reference building blocks only; those modules were not previously trained AI.

An all-in-one product that merely offers photo-upload heuristic warnings without actual model fitting/reload is INCOMPLETE. A trained toy dataset that claims real PSA10 accuracy is equally INCOMPLETE.

## 7. MONEY/DECISION ENGINE: EVERY BRANCH, NOT JUST THE HERO 10

For any listing show acquisition ask plus buyer taxes/shipping/premium, and compare:
(1) keep original slab, sell immediately;
(2) CGC administrative legacy 9.5 reholder, eligible + verified;
(3) PSA intact crossover with minimum grade, including failed-attempt full fee and returned original slab;
(4) crack and resubmit to PSA or CGC with PSA8, PSA9, PSA10, CGC8, CGC8.5, CGC9, 9.5, Gem10 and Pristine10 where valid;
(5) hold original slab for a research-defined period, with scenario risk and fees;
(6) two-step resubmission only when independently justified, with cumulative fees, capital lock, damage and downgrade downside.

Decimal arithmetic, service-tier value caps/upcharges, insurance, reverse and outbound shipping, card purchase tax, selling venue commission, payment fees, buyer premium, return allowance, holding time and contingency. Avoid double-charging included expenses. Break-even bid and maximum all-in purchase price for each route; worst-case downside including fully paid crossover failure; success case and failure case. Define confidence/range for exits and liquidity; scenario p-threshold sensitivity is NOT measured success probability. When model calibration is demonstrably adequate, optional measured p-based EV may be enabled separately with uncertainty intervals.

Crucially compare **regrade incremental value vs keeping slab**, not simply new value minus acquisition. An original slab may have appreciated. Fredy's $7,999 market-saved video illustrates this, as does his CGC-harsher experiment where all-in cost $11,333, new value $15,425 but keeping the original PSA slabs gave hypothetical $13,885. Many nominal upgrades are financially worse because of CGC discount. Never call estimated spread realized net profit.

Shared **$2,000** first trial cap, **$5,000 untouched reserve**, adjustable per-card loss budget and stage labeling. Trades never execute automatically. Show REVIEW, PASS, NOT-READY or manually APPROVABLE based on evidence; never fabricate permission, grading outcomes or prices.

## 8. PRODUCT UX: ONE MAC-FIRST APP

Ship a Mac-startable local app, not only CSV outputs. Suggested architecture: Python 3.12+ core, SQLite, FastAPI web app with a lightweight modern UI (Jinja/HTMX acceptable; avoid costly unnecessary frontend complexity), responsive dark/light theme and easy drilldown. Streamlit may be considered if it demonstrably supports all interactions and persistent provenance.

Minimum pages:
1. HOME: data-source readiness, API status, research archive coverage, last refresh, model version/training status, budget and candidate counts.
2. DISCOVER: top 50 live/manual research leads with multiple strategy tags; priority by upside and separate confidence; saved searches and direct eBay/PSA links; filters by company/grade/year/language/era/label/price.
3. DEAL DETAIL: original listing, identity/variant confidence, original photos, observed defects, four BGS/CGC subgrades, model assessment, all regrading routes with costs and conservative comps, breakeven offers, worst-case loss and evidence TODOs.
4. AI GRADER: drag/drop one or two images; inspect blur/glare/missing back; annotate; infer; show model vs rules and abstention; initiate actual training and evaluation from configured authorized dataset with logs and results.
5. RESEARCH: 18-source manifest, 250 raw source rows, aggregate cohorts, 20-case video tables, creator outcome summaries, cross-video duplicate review and drill-down to video timestamps/frames where local files exist.
6. MARKET: verified dated sold comps, indexes clearly separated, manual import and exact searches, no seller-data contamination.
7. WATCHLIST/ALERTS: history, notes, sort, last-seen, manual update queue.
8. SETTINGS/SAFETY: credentials status without showing secrets, read-only provider permissions, grading fee quotes, target premium thresholds, budget and data-path configuration, offline mode.

Include copyable research summaries, CSV/JSON export, precise source hyperlinks and a simple macOS .command launcher. On boot with no APIs show an OFFLINE working demo with real research data if mounted, not a blank page. No fake “live” badges.

## 9. QUALITY, SECURITY AND TESTING

- pytest tests for 16 detailed source schema adapters, 2 aggregate-only packs, 250 source rows (when bundled), SHA dedup, zip traversal/zip bomb handling, repeated grading, duplicate copies, dollars, Pristine labels, One Piece domain isolation, title variant ambiguity, duplicate sales, missing comps, no-lookahead, and broken/blurred images.
- Golden financial fixtures from the actual packs: PSA→PSA $15,359 total all-in/$27,533 displayed = $12,174; community $2,719/$6,235=$3,516; PSA→CGC $12,469/$19,715=$7,246; market-saved $11,161/$19,160=$7,999; CGC-harshness $11,333/$15,425=$4,092; CGC consistency $7,963/$12,170=$4,207; One Piece $6,328/$12,370=$6,042, distinct game. Creator valuations do not become verified sold comps or outcome-only profit.
- Image leakage traps, group split test, checkpoint train/save/reload, missing-back abstention, MPS/CPU fallback, deterministic outputs, no marker text inside model input.
- Mock eBay OAuth, API 401/403, 429 and cooldown, quota, absent secrets, field mapping and no sold-price claims from asks.
- Tests that unverified high-upside leads are VISIBLE in research but NOT trade-approved; test original CGC9 / legacy blue Gem9.5 / Mint+ / Pristine split; BGS9.5 with 9 surface subgrade remains inspection concern and does not guarantee PSA10. Explicit no-buy transaction code paths.
- Test portfolio $2,000 cap and reserve. Synthetic demos labeled SYNTHETIC everywhere. Test Mac launcher and package installation commands on available platforms; do not claim to run on Mac if only Linux environment exists.
- Offline tests never require network or paid API. Static typing/lint optional after functional tests, secrets scan, licenses/source review, reproducible database migrations.

## 10. DELIVERABLES & EXECUTION MILESTONES — DO NOT STOP AT A PLAN

Commit coherent working increments to the NEW repo (feature branch and PR preferred if Codex environment supports) with tests and short docs. Leave old repo untouched. Suggested milestones:
M1. Repo package scaffolding, config, database migrations and archive ingest including transport bundle.
M2. All listing/grade identity and 2-tier candidate engine with imported and synthetic fixtures.
M3. Full grade/exit cost scenario calculator and buyer-budget safety.
M4. Grader dataset audit + QA + train/evaluate/save/reload CLI + genuinely trained experimental checkpoint when right-cleared data present.
M5. eBay approved API adapter plus offline/manual sold import, PSA cert verification when authorized, and FULL PSA VAULT end-to-end module (owned collection/custody, eBay consignment, Partner Offers, withdrawal/regrade, dated fees and payout reconciliation per docs/PSA_VAULT_END_TO_END.md).
M6. Working local dashboard, history, human review, images and evidence.
M7. Integrated tests, end-to-end dry run, performance improvements, actual runbook, Mac launcher, explanatory source coverage.

Keep a MILESTONES.md checklist with completed, failed and blocked status; provide actual test results and commands. If a credential or data folder is missing, implement and test the adapter with mocks and continue. No unnecessary clarification questions. Prefer low-cost deterministic batch processing/caches over repeated LLM/model calls or rewatching video. Fix runtime/test defects instead of leaving TODO placeholders in core paths.

Actual acceptance for FIRST BUILD:
- clean clone installs and launches from documented commands;
- optional 446KB transport bundle imports reproducibly and reports 18 sources/250 raw rows (if supplied), preserving two aggregates and separate One Piece;
- app shows non-empty research opportunities from supplied listings even without paid APIs and shows no fabricated approvals;
- finances include every grade route and original-slab benchmark with tests;
- image QA and annotation work on actual supplied user images;
- real training/eval/inference command writes and loads a model checkpoint when usable licensed images are supplied; no false calibration claims;
- eBay Browse connector is real but off by default without approved access; manual sold evidence works;
- FULL PSA Vault module demonstrates end-to-end manual/authorized discovery → collection/custody → buy vs keep vs withdraw+regrade vs PSA consignment/partner offer exit → fee-adjusted comparison → actual payout reconciliation, including effective-dated 2026-10-29 insured withdrawal rates and 90-day early withdrawal conditions; no fake Vault API;
- PSA Vault's ten required tests from docs/PSA_VAULT_END_TO_END.md pass;
- visible source provenance and duplicate flags, working Mac startup guide, no modifications to previous repo, no automatic orders and no exposed secrets.

## 11. THE RESPONSE YOU MUST GIVE AT END

Deliver exact commits/PR, screenshots of UI if available, install/run/test commands, source counts, model training state (actual real / only fixture / not trained and why), provider status (credential present? production approved? live calls made?), financial golden-test results, tests pass/fail count, notable risks and **one clear next operator action**. A status message alone is not a deliverable. No invented numbers. Make reasonable implementation choices and ship substantial working code.

Begin by inspecting the new repo and implementing M1, not by copying the old repo or requesting more Fredy research.
