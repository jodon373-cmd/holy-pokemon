# AI Grader — full training and inference specification

**This is a required first-class product component, not a plugin or optional future idea.** Codex must implement training, evaluation, inference and integration into the deal review. The reference code under `reference/legacy_scanner/scanner/photo_grader.py` is only a deterministic image-quality/inspection baseline. It contains no trained Holy Pokémon grading weights.

## Inputs and training labels
- User-supplied local source ZIPs contain 250 case records across 16 detailed packs (including **20 One Piece**; monthly/public cross-video overlaps possible). Two other packs contain aggregates/trends. Not every record has useful before/after card closeups, exact variant or independently verified grading metadata. Count usable *specimens*, not CSV rows or repeated frames.
- Build `evidence_assets`, `card_copies`, `grading_events`, `grade_targets`, `source_permission`, `image_pairs`, `inspection_annotations`. Preserve the source ZIP and cropped/video frames exactly; generate derived training inputs separately and with transform metadata.
- Treat a grade as a **grader-specific observed outcome**, not an objective condition truth. Keep CGC numeric Mint/Gem, CGC Pristine 10, BGS 9.5/subgrades and PSA numeric grades distinct.
- Multiple photos from the same specimen and all its regrades must share one train/validation/test split. Deduplicate multiple publication episodes and recapture frames. Exclude post-result photos/grades from any prediction supposed to represent a buyer's **pre-purchase** decision; post-crack observations are retrospective diagnostics, not pre-listing features.
- Use source-rights/consent manifests. Do not upload private creator images to third-party model APIs or rehost public original footage without authorization; support local/offline pipeline. Analyzing user-provided research for personal use is different from assuming the right to redistribute training images.
- Historical aggregate distributions (546 PSA→CGC, two-year gem rates) may be used for **separate statistical context**, never fabricated into 546 image/grade pairs.

## Dataset preparation (must be executable, resumable and auditable)
1. Load original ZIPs and metadata by SHA-256 and verify archives safely (path traversal/zip bomb limits). Extract indexed images into an isolated local data cache; preserve original file bytes and save transformations' config and SHA.
2. Identify front/back, card art region vs slab/label, rotation, perspective, glare, resolution, obstruction and proxy annotations. Never crop or mask a flaw to improve its apparent condition; preserve an unedited original image for reviewer comparison.
3. The **learning input must not see grade text, cert barcode, holder logo, later-result spreadsheet overlays, file paths indicating grade, colored grader labels or any annotations that leak the target**. Model must receive a card-only view or strictly masked label areas, and note residual slab artifacts. Do not use the outcome name as a class token.
4. Build a defect annotation schema: front/back centering ratios with error bars; whitening location/severity, chipping, corner damage, edge wear, print lines, foil scratching, gloss/surface wear, dents, creases, stains, ink/size concerns, grading obstructions and missing surface visibility. Support `seen`, `not_visible`, `unknown` distinctly. Record original reviewer/source and whether observed before or after crack.
5. Produce an exploratory report showing sample coverage by game, era, grader, target grade, photo completeness, seller vs creator origin and train/test overlap. Do not silently drop difficult cards.

## Training implementation and realistic small-data plan
- Include deterministic non-ML baseline using reference `photo_grader` image-quality/centering features + manual defect screen. Include a **real supervised training command** that fits model weights using available, rights-cleared labeled specimens and saves a versioned checkpoint; also implement prediction from saved weights.
- With modest data, favor transfer-learning/small capacity visual encoder and calibrated lightweight heads over training a large foundation model from scratch. Choice of framework (PyTorch/ONNX) must be justified; operate on Mac CPU/Apple Silicon where supported. Default deterministic seed, no paid external model calls. Clearly state when pretrained weights would have to be downloaded and license checked. If no authorized weights, allow CPU-based feature baseline and training from supplied licensed weights.
- Multi-task targets: `P(grade band | target grader, visible condition)` as **experimental** only with enough independent labels; ordinal grade prediction, inspection defects, uncertainty, data sufficiency and likely risk factors. Make model output grade bands/ranges rather than a fake cert. Do not infer exact PSA10 probability from selected Fredy regrades without independent validation/calibration. Keep abstain/manual-review as a first-class inference output.
- Stage A: trained proof-of-concept on usable Pokémon subset (if sufficient for train/holdout) with conspicuous experimental status; Stage B: add authorized user-graded examples and cross-validate, calibrate out-of-video; Stage C: replace experimental probabilities only after representative held-out performance confirms them. Keep One Piece separate model/domain or secondary transfer study, never pool outcome statistics blindly.
- Train/validation/test split by physical specimen + related video/submission + content fingerprint, preferably held-out videos and eras; no random frame-level splits. Compare against naive grader/era conditional baseline. Support cross-domain evaluation and distribution-shift flags (era, Japanese vs English, modern textured vs WOTC holo, lighting, glare, slab type).
- Report accuracy by target grade and grading company, per-class recall, confusion matrix, grade MAE where numerical, interval coverage, calibration/Brier where probabilities justified, subgroup performance, known defects, uncertainty/abstention rate. Include high-impact error tests: predicted PSA10 but actual PSA8/9, hidden dents, severe backs, bad centering.
- Save `model_card.json`, `training_manifest.json`, feature config, rights provenance, split IDs, checkpoint hash, metrics, environment/seed, and clear “experimental vs validated” status. Do not commit large checkpoints to Git.

## Inference inside Holy Pokémon
- Operator supplies front/back photos or allowed API URLs; downloads only after provider/image permissions verified. Keep original source images and display them side-by-side with non-destructive annotations.
- `inspect listing` emits image QA, identity, grader/label ambiguity, deterministic quality hints, trained model result (if installed), uncertainty, grade-route scenario distribution or `insufficient_evidence`; never fill absent back with a fabricated inspection.
- Combine with exact variant and BGS/CGC legacy subgrades, label era, photo availability and conservative downside branches. Market scoring must not confuse a CV grade estimate with an observed third-party grading result.
- Human override/correction log should be append-only; reviewer feedback can form a future training set only with source/time provenance; no automatic continual learning that changes deployed scores silently.

## Acceptance tests
- Label/cert watermark leakage trap: if visible numeric grades are masked or scrambled, model training/evaluation must not depend on them.
- Same physical card across multiple videos and two CGC regrades cannot appear across data splits.
- Missing/blurred back forces lower confidence or abstention.
- CGC Pristine 10 remains distinct from Gem Mint 10; BGS 9.5 never automatically equals CGC 10.
- The One Piece 17/20 PSA10 study must not inflate Pokémon hit rates.
- Training can run from a small labeled fixture, write a checkpoint, reload it, and reproduce inference exactly. With no real permission/usable data it produces a useful QA report, not fabricated metrics.
