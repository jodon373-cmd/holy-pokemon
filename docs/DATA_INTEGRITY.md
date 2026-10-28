# Provenance, preservation and data quality

## Immutability
Never edit, rename destructively, recompress or crop the source ZIPs or video/frame files in place. SHA-256 the entire ZIP before ingestion. Separate derived copies, normalized rows and visual annotations from the originals; reference exact source path and timestamp.

## Entity graph
`source_asset` (ZIP/video/caption/recapture) → `evidence_observation` (on-screen row/frame or creator statement with time) → `physical_card_copy` → `grading_event` (one event per grading/resubmission) → `value_observation` / `sale_transaction` (independent, with evidence strength).

Do not identify a physical copy solely by matching set/name/grades. Keep grade chains explicit. Dedup exact file SHA, exact verified cert/event IDs, then cautiously reviewed cross-video matches. Claims like "already sold" remain creator-reported unless actual sale price and after-fee payout evidence are available.

## Price semantics
Retain: acquisition_price, buyer shipping, taxes, grading and submission fees, insurance, displayed grade value, listed asking price, dated gross realized sale, seller fees, payout, calculated net. Any unknown economic component is null with reason; "all-in creator cost" may already include fees so don't double subtract.

## Bias / evaluation
Fredy intentionally picks cards he believes can upgrade. The outcomes are evidence on *his selected inventory*, not all PSA 8s, PSA 9s or BGS 9.5s. Prevent optimistic training leakage: deduplicate by physical copy, evaluate by source date/video and overlapping cohorts, segregate creator-predicted grades revealed only **after cracking** from information visible at the time of a buyer's decision. Still use all provided research for features and hypothesis testing.

## Dataset and UI confidence
Separate `verified_source_record`, `creator_claim`, `derived_calculation`, `market_verified_observation`, `user_hypothesis`. Track identity uncertainty, stale prices, hidden surface issues, photos missing, and in-slab obstructions. Never make unsupported ROI/profit certainty claims.

## External access and expenses
No credentials or downloaded session data committed. Authorized provider API only. No bypassing seller limits, required permissions or rate limits. Do not buy cards or sign up for paid services without user's explicit approval.
