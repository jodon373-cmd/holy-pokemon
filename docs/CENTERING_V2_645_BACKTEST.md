# Holy Pokémon — centering v2, $500 default, and replay of 645 saved eBay cards

**Effective owner direction:** 2026-10-29. **Not a new Codex prompt or separate repository.** This is a tested, additive component of the existing Holy Pokémon build. The newer Mac checkout must be preserved. Do not replace its centering/image/audit modules blindly. Use existing immutable originals and resume cache.

## What was implemented on GitHub

- \`holy_pokemon/centering_v2.py\`: strict local OpenCV detector for card rectangle, perspective correction, independent physical-card and interior printed-frame borders, LAB color transitions from five cross-sections per side, median/dispersion-based boundary agreement, separate horizontal and vertical ratios. Returns \`MEASURED_NEEDS_VALIDATION\` or \`ABSTAIN\` with reason; no fake 50/50 or grade prediction. Supports human-provided \`outer_quad\` where slab/card auto-detection is ambiguous. Classic yellow-border front and blue back are implemented; unsupported layouts abstain pending separate calibrated references. Never silently loosen tests just to increase the passing count.
- \`holy_pokemon/centering_backtest.py\`: offline command for the owner's **existing** 645 saved IDs; inspects every saved native photo with an available local side/path mapping, supports manual human corner annotations, preserves originals with SHA-256, caches unchanged evidence, writes new \`audit-v2.csv\` and \`report.json\` in a separate output directory. Does not make eBay, CompSniper, PSA, or GPT API calls.
- \`tests/test_centering_v2.py\`: synthetic known border ratios, bad/missing image abstention, repeatability, duplicate-ID checks, original-image byte integrity, no invented financial rank and file traversal protection. Synthetic pass **does NOT** prove accuracy on the actual 645.
- The GitHub Actions offline test workflow installs OpenCV/NumPy to run these tests on every commit.

### Source baseline from owner's completed Mac audit

The **Mac-local** report—not GitHub's preexisting data—contained:
- 645 unique eBay listings (19 searches; no reason to repeat them).
- 483 PSA 9 title-screen candidates, 1,314 analyzed photographs, 162 rejected by saved title screen.
- 399 listings with at least one numeric centering result.
- 211 proposed front/back pairs. Revised validated both-face baseline: **12 / 211**, leaving **199** needing geometry review.
- Breakdown of 199: front review **99**, back review **14**, both **84**, front layout reference **2**; **136** pairs had front-bottom boundary disagreement.
- 18 both-face GPT inspected (not 18 proven PSA 10 prospects), 465 deferred from GPT, $0.288087 total accounted vision cost within $0.30 daily cap. **Do not rerun paid vision.**
- No individually verified purchase-grade sale comps / complete cost quotes at end of that run, so financial rankings remain NULL.

The saved audit is at the owner's **Mac path**:
\`outputs/arbitrage-2026-10-29/all-listings/audit.csv\`
in its active checkout. Its photo cache, database and existing audit HTML/JSON stay there; **they are not committed or available inside this GitHub repository**. Never claim the 645 were already physically rerun under v2 on GitHub.

## Replay the saved universe locally, with ZERO provider calls

From the **newer Mac checkout**, add only the new modules/tests without overwriting its local app code. The command assumes \`audit.csv\` has \`listing_id\` plus optional \`recorded_ask\`, \`front_path\`, \`back_path\` columns. The actual Mac audit schema may differ. In that case export a deterministic photo manifest from the existing offline database/photo ledger:

\`\`\`json
{"listing_id":"ebay|SAVED_ITEM_ID","side":"front","path":"photos/FRONT_ORIGINAL.jpg","layout":"yellow_border"}
{"listing_id":"ebay|SAVED_ITEM_ID","side":"back","path":"photos/BACK_ORIGINAL.jpg","layout":"blue_back"}
\`\`\`

One JSON object per line in \`outputs/arbitrage-2026-10-29/all-listings/centering-source-photos.jsonl\`. A listing may have multiple photos per side. The IDs must match \`audit.csv\` **exactly**. \`path\` must be relative to \`--image-root\`, or an absolute path within it. Only supply an explicit \`outer_quad\` after a qualified human reviewer or validated geometry model has identified the four card corners, ordered TL TR BR BL; never pretend candidate rectangles are certified.

Run with installed local NumPy + OpenCV (\`python3 -m pip install numpy opencv-python-headless\`) in the existing Mac virtual environment. Set the image root to the **already cached original image directory**, not a remote URL. Typical command (replace the root with the actual verified original cache location):

\`\`\`bash
python3 -m holy_pokemon.centering_backtest \
  --audit-csv outputs/arbitrage-2026-10-29/all-listings/audit.csv \
  --image-root outputs/arbitrage-2026-10-29 \
  --photo-manifest outputs/arbitrage-2026-10-29/all-listings/centering-source-photos.jsonl \
  --output outputs/arbitrage-2026-10-29/all-listings/centering-v2 \
  --expected 645 \
  --max-default-ask 500
\`\`\`

This outputs \`centering-v2/audit-v2.csv\` and \`centering-v2/report.json\`. It does **not** replace or overwrite the previous centering score, originals, model predictions or purchased slabs. The runner fails if 645 unique IDs are not present, rather than silently dropping records. Missing original faces or unsuitable layouts produce explicit abstentions. Repeated runs reuse source-hash-verified results.

**No misleading result reporting:** This replays 645 listing records, but the count of faces *actually measured* depends on existing local photo/side paths, sufficient resolutions, layout support, and boundary quality. Do not claim 645 dual-face measurements.

## Human-labeled regression & acceptance metrics

Without manually annotated independent reference boundaries, a new v2 number cannot be declared better than the old one simply because more cards pass. Build a fixed review sample across old failures, including:
- At least 30 front-bottom failures from the 136 cases, plus examples of front-only, back-only, dual-side failures.
- Borderline left-heavy modern Pikachu SWSH020 from owner screenshot; do not use earlier uncorrected \`50/50\` guess as truth.
- Classic WOTC yellow-border, card backs, reverse foils, oblique slabs, thick holder edges, glare, low-res, and full-art unsupported designs.
- Manually identify outer physical corners AND printed frame transitions, preferably blinded and independently reviewed. Convert annotated widths to \`left_pct\` and \`top_pct\` for the comparison CSV; resolve disagreements.
- Include both clean and flawed cards. Do not claim true PSA10 labels from appearance.

For independent ratio evaluation create CSV:

\`\`\`csv
listing_id,side,left_pct,top_pct
ebay|SAVED_ITEM_ID,front,54.8,50.4
\`\`\`

Then add \`--manual-truth /path/to/independent-boundary-truth.csv\` to the replay command. The report calculates human-annotation coverage, mean absolute centering error in percentage points, and how many measured faces fall within 3 percentage points in both axes. It does **not** calculate true grade accuracy or conversion likelihood. Track abstentions on the labeled set, not just successes, and report old-versus-new on the same fixed specimens. Any algorithm tuned against labeled examples needs a **separate held-out set** to claim generalization.

**Success criterion:** Lower independently measured boundary error with explicit abstentions, especially fewer wrongful front-bottom identifications; all 645 listings still accounted for, original SHA unchanged, no new API usage and zero new paid vision calls. Passing more geometry checks is a secondary metric, not proof of correctness.

## Purchase priority changes: $500 base + strict premium exceptions

- The user wants the main discovery/research lane to prioritize **PSA 9 asks at or below $500**. Retain speculative high-priced cards in a separate **Premium Exceptions** queue, NOT deleted by price alone.
- \`centering_backtest\` labels \`BUDGET_UNDER_500\`, \`PREMIUM_EXCEPTION_REQUIRES_INDEPENDENT_EVIDENCE\` and \`ASK_UNKNOWN\`. A $650 example is merely deferred, **not approved**.
- To promote an above-$500 exception: manually verified exact variant/PSA9 slab, high-confidence approximately **52/48 or better front and 55/45 or better back on both axes**, independently checked excellent surface/corners/edges, reliable exact-variant dated PSA10 comps, plausible liquidity and complete fees/downside. These are project **screening preferences**, not PSA standards or calibrated upgrade probabilities. If geometry is unvalidated, surface obscured or comps missing: exception remains *pending*.
- Below $500 does NOT imply buy-ready. A $150 Entei remains research until validated photos, grade possibilities, grading service/review quote, conservative sold comps, fallback/downside and purchase tax/shipping are confirmed.
- First run's $2,000 all-in pilot allocation and protected $5,000 reserve remain unchanged; no auto-buy, automatic paid API calls or guaranteed PSA10 outcome.
- Vision AI should only score the **automatically ranked** top candidates after every eligible listing has deterministic centering evidence or a recorded abstention. Use an explicitly approved spending cap and never presume unknown ROI is positive.

## Important limitations

1. The new geometric detector is a **safe baseline**, not a fully calibrated universal fix; full-art and uncertain slab/card rectangles abstain. Accurate geometry must be proven on source photographs before it replaces the latest Mac detector.
2. The owner Mac checkout has newer production files not present on GitHub. Merge modules incrementally; compare native versions and preserve local user edits. This document isn't a competing build order.
3. Today's 645-image replay **has not been executed here** because the actual saved Mac audit/photo assets have not been transferred to GitHub; this is designed to be run there. The automated unit tests use only synthetic fixtures.
4. Validating a ratio is not verifying grade, transaction comps or ROI. No live marketplace or paid vision required for this replay.
