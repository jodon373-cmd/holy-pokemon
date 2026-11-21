# Run the actual local application

From the existing `holy-pokemon` checkout on macOS with Python 3.12+:

```sh
chmod +x mac/Start_Holy_Pokemon.command
./mac/Start_Holy_Pokemon.command
```

Open **http://127.0.0.1:8876**. The launcher creates a local virtual environment and installs core dependencies if needed. Port 8765 was already occupied on this Mac and was left untouched. The app binds only to localhost. `HOLY_PORT` overrides the port; `HOLY_NO_OPEN=1` suppresses opening a browser. `/classic` retains the original functional calculator.

For the optional local vision/video runtime:

```sh
.venv/bin/python -m pip install -e '.[vision]'
```

This installs code libraries, not pretrained image weights. Training uses a modest from-scratch paired CNN baseline. No provider is contacted and no paid service is used on startup.

## Research and video intake

```sh
.venv/bin/python -m holy_pokemon.ingest --dataset research/local/fredy_results --search-dir "$HOME/Downloads"
.venv/bin/python -m holy_pokemon.grader_audit
.venv/bin/python -m holy_pokemon.video_evidence --step 30 --max-frames 60
# Optional full structured transport, when actually mounted:
.venv/bin/python -m holy_pokemon.ingest --transport '/path/to/HolyPokemon_Full_Fredy_Business_Source_Transport.zip'
```

Hashes are cached by original path/size/mtime. Canonical packs must match the committed manifest. ZIP paths, symlinks and decompression sizes are checked. Original files remain in place. Cache, decoded previews and all private records stay in ignored local directories.

Video previews are not training images. In Research Lab, open a preview, decode its original full-resolution frame, then inspect full card boundaries. Recorder clock estimates do not establish causal stage or physical identity. Review before/after outcome provenance explicitly.

## Real image review and training

In Grade Photos, upload or select both original sides. Open each image, click two opposing full-card corners, and save a reviewed card-only crop. Exclude grade text, certs, subtitles and holder branding while retaining every card edge and defect. If this is impossible, exclude the image. Append defect observations as seen/not visible/unknown. Link an actual later grading result, stable specimen ID, original video, pre-decision stage and training-rights evidence.

Model Lab validates the curated dataset before launching local training. At least five independent connected source groups are required. It fails explicitly when no eligible labels exist. The current source audit has **zero curated eligible pairs and no real trained model**.

Equivalent commands for an approved manifest:

```sh
.venv/bin/python -m holy_pokemon.vision_training train --manifest /path/approved_pairs.csv --grader CGC --out local_models/cgc_experimental.pt --epochs 4
.venv/bin/python -m holy_pokemon.vision_training evaluate --manifest /path/approved_pairs.csv --checkpoint local_models/cgc_experimental.pt --out outputs/grader/frozen_evaluation.json
.venv/bin/python -m holy_pokemon.vision_training predict --checkpoint local_models/cgc_experimental.pt --image /path/reviewed_front.png --back /path/reviewed_back.png --card-only-verified
```

Required CSV fields: `grader`, `grade`, `game` (`pokemon`), `physical_specimen_id`, `source_video_id`, `image_path`, `back_image_path`, `rights_basis`, `rights_evidence`, `card_only_verified`, `back_card_only_verified`, `pre_decision_visible`, `outcome_verified`, `outcome_evidence`. Optional `cert`, `source_bundle`, `duplicate_group`, `original_grade` strengthen isolation/baselines. Rights bases are `self_photographed`, `explicit_permission`, or `verified_permissive_license`; no redistribution rights are assumed. Keep CGC `Pristine 10` distinct. Use one reviewed pair per physical card. Model fitting never silently updates from corrections.

The pipeline saves local weights, checkpoint hash, source manifest, environment, frozen splits, metrics, held-out predictions and failures. Scores are uncalibrated. Missing back/unsafe crops/poor images cause abstention. Numeric outcomes do not supervise a defect detector.

## Business operation

- Discover: add a real URL or import CSV; incomplete leads remain visible. Save watches; refresh is on demand.
- Market: import actual dated completed-sale evidence. Required: source URL, observation/sale date, transaction ID, price/currency, exact identity, grader/grade and evidence kind. Active asks/indexes never become sold comps. CGC/BGS designations and CGC legacy 9.5 era need explicit matching.
- Deal review: compare original slab, unchanged/downgrade/rejection and upside routes; require full costs, recent exact sold evidence and seller/photo review. `MANUAL_BUY_READY` is research readiness, never purchase permission.
- PSA Vault: import owned items, actual state evidence and receipt-linked payouts; compare hold, PSA auction/BIN, actual Partner Offer, withdraw/resell/regrade, grading-to-vault, transfer and ship-to-owner scenarios. Execute outside this app in the official account. Record repeated actual grading outcomes against the same owned copy. Enter only newly paid fees not already included in imported basis.
- Portfolio: distinguish imported basis, later paid costs, grading queue, actual receipts and estimated proceeds. All strategies share $2,000; $5,000 stays reserved.

Imports accept partial records and return row errors. Records are immutable; corrections/notes append a review. SQLite files are mode 0600. Do not import passwords, API credentials, full Vault IDs or cookies into evidence tables. Back up private outputs separately; they are intentionally not in Git.

## Optional authorized providers

Configure local environment variables, never commit secrets:

- `EBAY_CLIENT_ID`, `EBAY_CLIENT_SECRET`, `EBAY_ENABLED=true`, `EBAY_PRODUCTION_APPROVED=true` only with real approved production access. Search is operator initiated; Browse supplies active listings, not sold history.
- `PSA_API_TOKEN` for authorized single-cert verification. This does not connect private Vault management.
- Fanatics Collect, Arizona TCG and private Vault account information use manual authorized exports and owner entry. No undocumented endpoints are used.

## Verification

```sh
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m ruff check holy_pokemon tests tools
PYTHONPATH=. .venv/bin/python tools/synthetic_training_smoke.py
```

Last execution: 81 tests passed on this Apple Silicon Mac. The separate synthetic execution fitted 6 training, 2 validation and 2 frozen test specimens on MPS, saved/reloaded exact weights, rejected a changed frozen target, and refused synthetic inference on real cards. **It establishes pipeline execution, not Fredy grading performance.** See `IMPLEMENTATION_STATUS.md` for remaining acceptance gaps.


## Four-lane arbitrage engine — 2026-11-21

Install in a virtual environment, then run offline before enabling providers:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev,inspection]'
.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
.venv/bin/python -m ruff check holy_pokemon tests tools
.venv/bin/python -m holy_pokemon.scan_pipeline --help
.venv/bin/python -m holy_pokemon.scan_pipeline --plan --query-limit 12
.venv/bin/python -m holy_pokemon.scan_pipeline --input cached-listings.json --output-json outputs/ranked.json --output-csv outputs/ranked.csv
```

No input produces a valid empty offline report. JSON accepts cached listing arrays; preserve exact set, edition, language, grade and front/back image roles. Missing evidence stays unresolved. Use `--only-new --seen-db outputs/seen.sqlite3` for persistent delta tracking. `--no-inspect-images` disables local image inspection. Downloaded photos remain immutable; thumbnail-only or unlabeled photos cannot establish a pristine card.

Explicitly opted-in provider discovery uses `--discover --live --query-limit 12 --max-requests 30 --daily-limit 5000`; configure the existing approved eBay credentials locally first. Optional CompSniper enrichment uses the existing local key and `--comp-max-calls 3`. These are configurable caps, not promises about universe size. Failed provider calls stop discovery without retrying. No live validation was run for this release.

Open `/search-engine` on the local dashboard. **Load saved bot leads** reads the source database without changing it or refreshing marketplace availability. Set `HOLY_SOURCE_DATABASE` to an existing bot SQLite file when running the app against a separate `HOLY_DATABASE`. All decisions remain research-only; max-offer scenarios depend on the displayed cost assumptions and available exact comps.

Last integration validation: 204 tests passed, full Ruff passed, offline JSON/CSV exports verified, and the browser loaded 98 saved leads. The existing running Mac bot was preserved on port 8876; the isolated review instance uses port 8877.
