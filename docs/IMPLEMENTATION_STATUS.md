# Implementation status — 2026-10-28

Version 0.2 is a working private Mac-local research/business application. **The full one-shot acceptance contract remains PARTIAL. No real Fredy condition model has been trained, and no real held-out grading accuracy or economic edge is claimed.**

| Component | Implemented and verified | Remaining limitation |
|---|---|---|
| Original source audit | 524 files / 4,774,208,067 bytes, 289 unique hashes; 3 compact ZIPs match extracted members; originals untouched | File inventory and sampled evidence do not constitute complete physical-card annotation |
| Canonical research | Four SHA-matched packs, 46 raw source observations; source-native raw dictionaries retained | 14 canonical packs and full transport absent locally; not all 16 schema families independently exercised |
| Specimen/event provenance | 16 source-reported cert-linked specimens, 20 source-reported grading observations; 23 caption versions across 18 video IDs | These are conditional source facts, not independent certificate verification or a complete cross-video physical-copy graph |
| Photographs | 333 indexed image assets decoded in the first QA audit; original gallery, uploads, zoom, reviewed full-card crops and append-only defects work | No automatic validated card geometry, centering or trained defect detector; no verified pre-buy/later-outcome training pairs |
| Raw video | All 18 logical source videos sampled into 543 quarantined previews using recorder clocks; resumable sampling, contact sheets and full-resolution decode | Sampling is not exhaustive; clock timestamps require review; original/after-crack/after-result stage and actual physical-copy linkage remain unfinished |
| Training/evaluation | Paired 256px CNN, rights/stage/outcome gates, connected video/specimen/cert/exact/perceptual grouping, immutable frozen-test mapping, MPS/CPU, checkpoint/evaluate/infer commands | No real-data fitting, calibration, subgroup accuracy or financial replay. Small CNN is a baseline, not a high-fidelity grader |
| Executed training proof | Explicitly SYNTHETIC 6 train / 2 validation / 2 test specimens; MPS fit, checkpoint, frozen evaluation and exact reload; modified frozen target rejected | Synthetic results are never real accuracy and the synthetic checkpoint is refused during real-card inference |
| Discovery and approval | Manual/authorized lead imports, latest listing snapshots, Top50/Top20 filtering, watches, exact sold searches, evidence-based manual-readiness gate | No live leads or verified buy-ready opportunities seeded; freshness and quotations require operator/provider evidence |
| Market adapters | Official Browse OAuth/search/detail, pagination/cache/quota/429 cooldown/no automatic retries; optional PSA single-cert adapter; manual sold/Fanatics/Arizona imports | eBay and PSA credentials absent; zero live marketplace/cert calls; PSA endpoint/account compatibility not live-verified; no private Vault API |
| Financial/inventory | Decimal route costs, original-slab benchmark, max bid, downside, shared $2k cap/$5k reserve, venue cash time/carry costs, stop/retry sensitivity, owned-copy grading history | No point-in-time real sold dataset for independent strategy backtesting; tax and unknown fees remain unknown |
| PSA Vault | Separate custody/eligibility/consignment evidence, owned collection, status timeline, all nine exit/scenario categories, dated withdrawal and offer checks, single-fee payout math, receipt dedup/reconciliation, grade-attempt records | Manual account synchronization and execution; unquoted fee tiers and hypothetical outcomes remain unknown; combined payout receipts require explicit per-card allocation |
| UI/startup | Nine responsive navy/blue/red screens; original-source review, functional forms, exports, light/dark mode; classic fallback; Mac launcher tested | Setup is a readiness checklist, not an account-connection wizard; sophisticated identity merge/split and annotation coaching remain incomplete |
| Verification | 103 local tests passed, Ruff checks passed, Python/JS/shell syntax checked, dependency audit found no known vulnerabilities at execution | GitHub CI is separately reported by the PR; local results do not imply remote CI passed |

## Actual local evidence

Private, ignored outputs: `outputs/grader/dataset_audit.json`, `image_audit.json`, `excluded_images.json`, `model_card.md`; `outputs/video_review/video_audit.json` and contact sheets; `outputs/synthetic_pipeline/execution_summary.json`; `outputs/tests-final.log`; `outputs/dependency-audit.json`; `outputs/run_state.json`.

The real-data grading metrics (accuracy, MAE, PSA10 false positives, uncertainty calibration and financial consequences) are **unavailable**, not zero. No source-caption guesses or original slab grades have been repurposed as later grading labels. Original-source images, raw videos, local SQLite, private receipts and trained checkpoints are ignored by Git.

## Next operator action

Open Grade Photos in the local app and review one original front/back pair with its independently traced later grading result and permission evidence. This starts the curated review queue; actual training requires at least five independent connected source groups. The larger remaining engineering task is completing the physical-copy/stage/outcome graph across the recordings, not merely pressing Train.


## PR #2 local integration

The additive automated-research discovery changeset from PR #2 (`9122c93a1d7ccfcac8c83e393586622420778b18`) is reconciled with this Store, existing Browse adapter and the nine-screen dashboard. Research Lab displays the feed and supports CSV intake, synchronization and explicitly authorized one-shot scans. Native Store integration, snapshot history, unknown-currency handling, shared quota/cache storage, matching PSA cert semantics and the browser queue flow are tested. The owner confirmed no API keys are currently available; no real-provider listing or PSA lookup was attempted. See `AUTOMATED_DISCOVERY.md` for the single-query command after secure key configuration.


## Arbitrage engine integration — 2026-11-21

Integrated the existing application branch into main in a separate worktree to preserve the running Mac checkout and its uncommitted work. Extended Browse, CompSniper, planner, scorer, inventory, scan pipeline and dashboard rather than replacing the application.

- Four lanes: high-spread BIN, ending auctions with at least three target comps, typo/poor-title discovery and merged promo priority. Search requests use separate buying options, exact aspects, EXTENDED fields and a local USD price ceiling.
- Full-URL search cache lasts five hours. Atomic daily quota reservations include OAuth and failed calls; per-run caps and Retry-After cooldowns stop requests without retries.
- Condition IDs and category aspects use documented wire filters. Grader/grade/cert condition descriptors are checked locally against returned structured evidence; absent evidence is unresolved. No undocumented descriptor query parameter was invented.
- Fredy's ten rule IDs accompany routes and economics. Each grading attempt pays its own costs; max offers include original-slab fallback, target P25, taxes, channel fees, margins, capital cost and BGS reserve. Gem Mint is the baseline; Pristine is upside only. A sell-original benchmark is not a floor after cracking.
- Cross-query and persistent listing/item/cert deduplication preserves alternative grading routes. Optional bounded CompSniper enrichment excludes unresolved Best Offers. Saved dashboard leads load through read-only SQLite and are marked as needing availability refresh.
- Local v3.3 geometry remains intact. Image-role uncertainty, blur, skew and a conservative glare heuristic cause review/abstention. Unlabeled images do not become verified front/back pairs. This is not a validated defect detector or grade predictor. Search thumbnails may be too small; official PSA scan retrieval has not been newly validated here.
- `/search-engine` shows ranked cached leads, ceiling/bid, route comparisons, original-slab increment, warnings and comp provenance. All outputs retain `trade_approved=False`; population ratios never become upgrade probabilities.

Validation: all 204 tests passed with NumPy/OpenCV installed; full Ruff checks passed. Offline synthetic acceptance exported JSON/CSV with all required fields, and browser testing loaded 98 real saved leads. These cached leads were not refreshed or declared buys. No live eBay, PSA or CompSniper calls, paid grading calls, or marketplace purchases were performed. The separate running checkout's earlier 544-test baseline had two failures and was left untouched; the 204-test result applies to this integrated main worktree.

Private validation artifacts live in ignored `outputs/search_engine_validation/`; the browser proof is `outputs/search-engine-proof.jpg`. They are not committed to the public repository. Remote CI results must be checked separately.
