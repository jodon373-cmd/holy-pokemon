> **SUPERSEDED AS LAUNCH ENTRYPOINT.** For any new Codex execution, start from [CODEX_ONE_SHOT_EXECUTION.md](CODEX_ONE_SHOT_EXECUTION.md). This file remains a supporting requirements reference and must not be launched as a separate coding task.

# CODEX GRADER-FIRST LAUNCH — ALL-IN-ONE HOLY POKÉMON
Version 2026-10-28. This document is the operator-approved concrete execution order for the cloned local Mac repository. It **supplements** (does not replace) docs/CODEX_MASTER_BUILD.md, docs/AI_GRADER_TRAINING.md, docs/FREDY_BUSINESS_REVERSE_ENGINEERING.md, docs/PSA_VAULT_END_TO_END.md and research/FULL_SOURCE_TRANSPORT.md.

## 0. START CODING IMMEDIATELY, IN THE RIGHT PLACE
Work inside the existing local clone of jodon373-cmd/holy-pokemon on the user's Mac, with GitHub main as origin; use a feature branch. The user has already linked a Fredy Results folder at research/local/fredy_results. This is a symlink, NOT a Git file. Check whether it resolves with:
- pwd; git status --short; git branch --show-current
- ls -ld research/local/fredy_results
- test -d research/local/fredy_results && echo DATASET_LINK_OK || echo DATASET_LINK_BROKEN
- find research/local/fredy_results -maxdepth 3 -type f | head -40 (use -L for find if needed to traverse symbolic links)
If broken, report exact issue and continue building with other mounted evidence. Do not falsely report files seen in another ChatGPT session are in this local checkout. Never upload, duplicate, move, rename, delete, re-encode in place or push the 4.7 GB original data to Git. The Mac's actual resolved path may be ~/Downloads/Fredy_Results copy 2, but verify it rather than assuming.

Read AGENTS.md, full master build, AI training, business, Vault and market-data docs once. Read existing working modules and tests: holy_pokemon/vision_training.py, fredy_business.py, strategy_engine.py, vault_engine.py, inventory.py, ebay_browse.py, dashboard.py and their test files. Preserve tests and the read-only old scanner. Work as an engineer implementing code, not writing another 30-page plan. The GitHub foundation tests previously passed; re-run them locally before/after changes.

## 1. AUDIT EVERY AVAILABLE REAL IMAGE / RESEARCH SOURCE BEFORE MODEL FITTING
Search the linked 4.7 GB source folder recursively, including nested results, frame captures, card fronts/backs, label files, training/validation scripts, old model artifacts, metadata and RUN_SUMMARY.json. Discover whether the three Fredy Evidence ZIP parts (roughly 48/48/26 MB) are duplicate subsets of the folder. Search configured local research folders for Fredy 18-source archive packs, 28-video transcripts, reports, full-resolution photo ZIPs and the earlier 135-pre-result image evidence index (Master_Index.csv); the index may or may not actually be mounted. Do not assume the 135 images or the 4.7 GB are already linked to grade outcomes until verified. Inspect files through their manifest/index first, not by repeatedly decoding all 4.7 GB into memory.

Produce a reproducible dataset audit at outputs/grader/dataset_audit.json and outputs/grader/dataset_audit.md with:
- total source files; unique SHA-256 and perceptual-duplicate groups; per-game, video, era, set, grader, holder era, label designation, BGS subgrade and original vs target grade counts;
- number of FRONT-only, BACK-only, paired, macro/center/edge, pre-submission, post-crack, after-grade, ambiguous, low-resolution, damaged/unreadable, and unusable/leakage images;
- physical-specimen matches, source observation IDs, grading-event chains and apparent cross-video repeats; an ambiguous pair is NOT forcibly merged;
- training rights/permissions and source provenance status; source labels verified vs creator estimates;
- exact count with buyer-visible original photos AND actual independent grading outcome and holder designation. Report the count, not a promised number.
Keep 546-case aggregate stats and two-year PSA-vs-CGC gem-rate aggregate outside the independent image-training sample. Keep 20 One Piece BGS-to-PSA cards in an isolated game/domain; do not use their 17/20 outcomes as Pokémon odds. The monthly finance and 28-video transcript archives may overlap the 18 packs: never inflate labels from duplicate mentions.

Use original bytes only as source; generate a separate derived/cache area under ignored research/local or outputs. Create a SQLite evidence index and append-only raw-label audit; no destructive originals.

## 2. PAIR REAL CARD PHOTOS WITH REAL GRADING OUTCOMES, NOT VIDEO CLAIMS ALONE
Unit of independence = PHYSICAL CARD COPY, not screenshot, frame, grade event, CSV row or video mention. For each copy: canonical set/name/number/finish/edition/language/era/game; original grader+grade+cert and holder generation; optional four BGS/legacy CGC subgrades; exact BEFORE front/back images with capture timestamp and grade labels hidden or outside crop; actual subsequent company/grade/designation with verified evidence pointer; all repeat submission events, date and fees; unknown outcomes remain NULL.

Correct causal order is BEFORE photos -> first AFTER grading outcome. Images captured after cracking or after final grading cannot be used for a pre-purchase prediction; may only support post-result condition/error analysis. Predictions visible on creator screens are not ground-truth defect labels. A grade (e.g. PSA9) is an ordinal outcome from a grading company, NOT a supervised annotation that the card has particular whitening/scratches. Collect explicit defect/location labels via manual review or inspectable image evidence.

Special outcome rules:
- CGC Gem Mint 10 vs CGC Pristine 10 are distinct real designations; never create fictitious CGC grade 11 from creator custom scoring.
- PSA minimum 10 intact crossover failure is NOT a PSA9/8 grade label: the slab was returned unchanged. Grade-transition / rejected attempt is separately labeled.
- Repeat CGC/PSA grading of the same physical card remains one group in all splits.
- Blue-label legacy CGC Gem Mint9.5, modern Mint+9.5, BGS9.5, CGC Mint9, PSA9 and actual Gem/Pristine10 must remain separate.
- Different physical copies of identical Charizard, Reshiram or Umbreon must stay distinct unless a cert or evidence establishes match.
- Fredy's selection favors cards he thought could upgrade. Optimize for buyable listing risk and evaluate prospectively on unseen sources, never announce universal success odds from this selected sample.

## 3. TRAIN THE BEST REALISTIC CARD-CONDITION MODEL THE EVIDENCE SUPPORTS
Build/refactor full supervised local training with a multi-view front+back model plus optional high-resolution corner, edge and surface crops. The current simple 128x128 single-photo CNN in holy_pokemon/vision_training.py is an executable starting point, NOT an adequate final high-fidelity grader. Upgrade it rather than claiming it is already fully trained.

System A — IMAGE QUALITY AND NONDESTRUCTIVE GEOMETRY:
- detect physical-card outline, distinguish plastic holder/labels, preserve full original pixels and generate documented card-only views;
- hard-mask grade text/certs, label colors/brand and source subtitles/overlays/file-name hints from model input. Confirm masking/segmentation with leakage tests and sampled original-vs-derived review gallery; retaining slab artifacts should be an explicit domain-shift warning;
- check front/back completeness, resolution/focus, lighting/reflection/foil glare, perspective, occlusion and possible post-crack mismatch;
- measure left/right and top/bottom border centering (front and back) with uncertainty ranges; use actual card boundaries, not slab border. Uncertain measurements are reported unknown.

System B — VISIBLE DEFECTS AND CONDITION:
- human-assisted image annotations of whitening, corner wear, chipping, ink/print dot, dent/crease, holo scratches, print lines, surface streak, gloss loss, stains, foil/texture and abnormal dimensions. Label seen / not visible / unknown, severity, approximate image region and reviewer + evidence.
- A blurred back, hidden holo surface, cropped corner, slab glare, lack of macro photos or missing card side is a legitimate INSUFFICIENT_EVIDENCE reason. Never infer hidden dents are absent; no generative retouching/defect removal/enhancement to boost predicted condition.
- With no directly observed defect labels, do not claim a trained scratch detector based only on grader's numeric grade. Allow auditable image QA+manual review while collecting labels.

System C — GRADER-SPECIFIC OUTCOME ESTIMATION:
- target labels conditional on grader/route and visible pre-decision condition; distinct PSA, CGC (Gem/Pristine separately), BGS and graded-era/English-vs-Japanese domains.
- Prefer locally available licensed pretrained image encoders, shallow/frozen-backbone or fine-tuned compact networks plus structured photo quality, centering and verified subgrades, with trainable multi-view heads. Benchmark simpler logistic/gradient boosting/rule baseline on exactly same folds. Avoid giant from-scratch neural training on a small, selected dataset; avoid costly remote model calls.
- Train from actually rights-eligible real photos, save model checkpoint, feature transforms, model card, labels, sample IDs, seed, training command, source SHA, split indices, git commit and environment versions.
- If no legitimate real photos/labels pass checks, do NOT say trained. Provide functioning training/eval/infer command and exact missing-data audit; any synthetic smoke test must be marked SYNTHETIC and excluded from measured real accuracy. Do not silently relax permissions or leak post-result images.
- Local hardware: Apple Silicon MPS when available, CPU fallback. Train via runnable script the user can launch and close Codex while training; cache embeddings/patches so future runs are incremental. Never require Codex to manually scroll thousands of photos; sample uncertain cases for human annotation.

## 4. BACKTEST STRICTLY ON UNSEEN CARDS AND UNSEEN VIDEOS
Create deterministic frozen train/validation/test partitions by connected physical-specimen, video/episode/recapture group, repeated cert and perceptual near-duplicate group (including same card mentioned in monthly and public video). If a specimen appears across two videos, connected-group them or exclude pending resolution. Favor leave-video-out and chronological holdouts; no random frame splits. Split and leakage check must be committed as reproducible code and persisted to output, not implicit randomness.

Measure and save:
- per-grader and era sample counts, confusion matrices, macro F1, per-class precision/recall, grade MAE, one-grade-off error, severe-overgrade rate;
- critical PSA10 vs non10 precision/recall and false-positive inspection samples, CGC Pristine vs Gem confusion, BGS subgrade conditional performance;
- score calibration / Brier / confidence interval coverage IF sufficient labels, else display uncalibrated or abstain; mean confidence alone is not grade probability;
- missing-back, glare, poor-scan and out-of-domain tests; test-time abstention and error as a function of photo quality;
- compare against naive original-grade predictor, simple condition-heuristic and other local baseline, rather than printing an uncontextualized accuracy;
- complete per-specimen held-out prediction ledger with original image ref, true result, predicted range, confidence status, route, failure reason and optional PNG review sheet. No hidden failure examples.

Then conduct finance-aware holdout replay: only decisions available BEFORE the grade outcome and only sales/comps available as of decision date; show fraction of candidates missed, predicted success failures, hypothetical net outcome vs selling original slab and actual realized cash when documented. The 546 aggregate cannot be replayed as 546 image predictions. Labels from creator's post-crack predictions cannot be backtested as buyer decisions.

Publish outputs/grader/model_card.md, metrics.json, confusion matrices, failure_gallery index, dataset_audit.md, heldout_predictions.csv, leak_check.json and real trained checkpoint under ignored local_models/ (NOT Git). If true performance is poor or insufficient, say so and keep human-review gates.

## 5. GRADER EXPERIENCE INSIDE THE ACTUAL HOLY POKÉMON APP
Replace placeholder grader page with upload/paste two or more source photos, original-side-by-side with unaltered pixels, zoom/magnifier, corner/edge crops, measured border overlays, visible defects, ambiguous region flags, user edits and provenance. Show:
- photographic quality status, specific observed defects and missing evidence;
- grade RANGE / possible outcomes for each company and regrade route, model version, holdout metrics, abstain state;
- explanation by condition and old slab/subgrades; separate image-observed fact from AI guess;
- buyer-visible photo before outcome; hold-out outcome explanation when testing, never expose target grade in pre-result model input;
- incremental net sell/regrade options for PSA/CGC/BGS, current authorized sold comps, grading/shipping/insurance fees, downside, seller fees and original-slab baseline. No fake precision, fabricated market price or implied PSA guarantee.
Use user feedback to save append-only corrections; future offline retraining only after review.

## 6. COMPLETE THE ALL-IN-ONE BOT (DON'T STOP AT TRAINING)
Continue and integrate the already-committed modules:
- high-upside research leads + strict separate manual trade-approval queue, every relevant vintage/EX/Japanese/legacy blue CGC/BGS/PSA pathway; interesting missing-comp candidates remain visible;
- authorized eBay Browse live listings and manual eBay Product Research sold comps, exact variant resolution, optional PSA cert verification. Without credentials, official provider is clearly offline and simulated fixtures are clearly marked; no unauthorized marketplace scraping or invented sold API;
- full PSA Vault workflow per docs/PSA_VAULT_END_TO_END.md: vaulted vs vault-eligible vs consignment distinctions, user holdings, owner-manual transfers, auction/BIN, actual Partner Offers, withdrawal and then regrading cost, dated consignment/withdrawal fees and cash payout reconciliation. No phantom private PSA Vault API;
- Fredy business routing and capital cycle: source card, inspect, select submission route, regrade retry stopping condition, manage submitted/ready inventory, compare eBay/Fanatics/Arizona TCG/PSA Vault net exits and time to cash, realized vs paper profit; $2k all-in initial limit and untouched $5k reserve. Existing Fredy monthly reports are reference business examples, not present-day sales comps.
- polished Mac-local UI and launcher: Pokémon-inspired but original design, NAVY BLUE base, vibrant electric BLUE, restrained POKÉBALL-RED action accents, GOLD success/high-upside indicators, clear typography, responsive cards, generous breathing room and keyboard-accessible controls. Pages: Dashboard / Discover / Grade Photos / Trade Detail / Evidence & Backtests / Portfolio & Cash / PSA Vault / Settings. No copyrighted Pokémon-branded artwork required; use user's permitted card images privately. Make UI usable, not just decorative. Provider/model status must accurately report live vs offline and real-trained vs synthetic.
- Preserve the working simple dashboard as a functional fallback; use tested UI/API integration and a first-run wizard for local dataset availability, model train status, image permission and eBay credentials.

## 7. COST/TIME/SAFETY AND FINISH CONDITIONS
- Work in staged commits, fix existing code/tests rather than restarting; do not edit the old pokemon-market-scanner repository or the 4.7 GB source folder.
- Avoid duplicating data or expensive repeated decoding/training: inventory filenames/metadata first, hash in batches, cached pHashes/embedding features and resumable checkpoints.
- No automatic bidding, buying, sale, card transfer, Vault withdrawal, paid subscriptions or credentials in Git. Strict local data, optional API credentials only when configured.
- Run actual unit tests, source ingestion tests, eBay mocked HTTP tests, Vault workflow tests, real photo-quality tests, actual train/eval/inference test, UI smoke tests and end-to-end Mac launcher smoke test. Record exact passed/failed counts and any unverified features.
- Don't claim “best market grader” without independent comparison metrics. Deliver the strongest source-grounded local grader available now, show honest limitations and a path for improving with newly graded outcomes.
- Finish with implemented commits/PR, exact local commands to launch, verified dataset counts and training status, independent backtest metrics and failure examples, eBay/PSA Vault connection status, working UI screenshot, and one concise operator action. Do not stop at a plan or ask for more Fredy research.

## ACCEPTANCE GATE
This task is NOT done merely because holy_pokemon/vision_training.py trains on random fixtures or because a “grader score” displays. Done means: the local source folder was actually audited, every eligible pre-result image correctly paired to an observed outcome with provenance, split/leakage checks passed, real-model training completed if rights-cleared usable examples exist, held-out metrics/failures saved, grader integrated into card-level financial decisions, the all-in-one user app launches with honest provider status, and tests pass. If source permissions or hardware block one milestone, implement all unblocked components and report precise blocker; never fabricate completion.
