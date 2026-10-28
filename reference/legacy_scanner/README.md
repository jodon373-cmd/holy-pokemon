# Reused code from the earlier scanner — quarantined reference

These files are **exact copies** of selected modules and matching tests from the user's existing private repository `jodon373-cmd/pokemon-market-scanner`, as read 2026-10-28. They are not imported into any production `holy_pokemon` package. Some modules use relative imports into an older `scanner` package and **will not run standalone in this directory**. Do not assume tests have passed in this new project; port, refactor and test each choice intentionally.

## Why these were selected

| Source file | Proposed reusable behavior | Risks / required changes |
| --- | --- | --- |
| `scanner/grade_image_dataset.py` | Image manifest, SHA-based duplicate filtering, rights/consent checks, class-balance audit | Current hard-coded grade classes 8/9/10 and 1,000-image readiness floor don't match multi-grader/few-shot research; replace with graded event labels, all valid scores, subject-level splits and actual learning pipeline |
| `scanner/photo_grader.py` | Image validity, EXIF orientation, blur/glare/quality checks, candidate card border detection, optional ONNX inference | Not a trained model; slab-vs-card ambiguity, lighting, edges and centering estimation must be measured and validated; preserve originals; never use label as grade |
| `scanner/pregrade.py` | Human-verified centering, photo evidence, defect checklist, uncertainty flags | Approximate 55/45 and 75/25 are screening guidance not exact automatic 10/no-10 rules; should support different grader/era policies |
| `scanner/costs.py` | Deterministic Decimal-valued grade branch net P&L | Extend to keep-as-is comparison, tax/shipping coverage, PSA value surcharges, time/capital lock-up, fees, actual vs estimated proceeds |
| `scanner/discovery_queue.py` | Broad title/lead staging and reverse-search queries | Do not perpetuate low-value completeness-first ordering; discovery must not require comps/photos to show candidates |
| `scanner/ebay_browse.py` (+ `scanner/ingestion.py`) | Read-only official OAuth Browse API handling, scoped host, rate limits, caching and missing fields | Old code requires review before network calls; never interpret live asks as sold comps; verify new account eligibility and test with mocked HTTP first |
| `scanner/strategy_common.py` | Exact variant tuple, Decimal money, single shared budget | Expand identity schema to error/edition/foil/stamp; update when bringing into production |
| `scanner/subgrades.py` | CGC/BGS four-factor inspection checklist, uncertainty and cohort-audit conventions | Separate graders/label eras; heuristic score is NOT a probability |
| `scanner/crossover.py` | Distinct CGC blue 9 / 9.5 outcomes, fallback and administrative-reholder paths | Strict validation must only govern approvals, not suppress early leads; verify current grading service rules and costs |

Original historical `AGENTS.md`, previous Codex task files and strict Top50 settings are **not transplanted**: they were task-specific and at times caused discovery to over-filter. Source tests are retained as *reference regression tests*, not automatically run from the new repo.

## Original blob SHA-1 (GitHub blob identities)
```text
scanner/grade_image_dataset.py 9b606055b56cad0bfe7763d91febb33f28e1567a
scanner/photo_grader.py      abf762618ff27d15d0d6906abacd2e3ceb90e844
scanner/pregrade.py          2eb75238444bf60a29e491f3b180448923cd1110
scanner/costs.py             7f48a8194045bd745b50c1f6697ee74aa2cd7427
scanner/discovery_queue.py   ad0e87a505fcc7cc6a2463d766f997f8197caa17
scanner/ebay_browse.py       9d74b01944a76b5d4131ba3fc0915abb180d047f
scanner/ingestion.py         642fa1bcac5a22c0785c64dd370f1655a79422ab
scanner/strategy_common.py   c28b43b44cd8079619c9ce74d318b33898449df9
scanner/subgrades.py         7a14244f4eb99a6d1c10e7f17f7e0a13c0e82a55
scanner/crossover.py         8ce4e5b9f15fdfb956969a51bc3207c10c28c835
tests/test_photo_grader.py   a21c2fb645ff761317fad6b2b8efaf9c335c56f8
tests/test_pregrade.py       959abd869fc5ca82ca4ab4a543ac822af04b6e97
tests/test_ebay_browse.py    bfd86c5f53a5c2b2c3f3d658554fea427de45a10
tests/test_crossover.py      20000c9da07958d1ffc52f5fd3cd7c50eb70abe2
tests/test_discovery_queue.py 1afcaf492039dbbdd12ccebf4cb99d744f2c37f5
```

## Useful original design / research, without copying broken assumptions
- [Issue #2](https://github.com/jodon373-cmd/pokemon-market-scanner/issues/2): blue label 9 vs 9.5 crossover distinctions.
- [Issue #3](https://github.com/jodon373-cmd/pokemon-market-scanner/issues/3): verified subgrades, no invented odds, PSA10 photo screen.
- [Issue #4](https://github.com/jodon373-cmd/pokemon-market-scanner/issues/4): point-in-time grade-lag falsification/backtesting.
- [Issue #5](https://github.com/jodon373-cmd/pokemon-market-scanner/issues/5): integrated validation, all-in shared risk budget.
- [Issue #6](https://github.com/jodon373-cmd/pokemon-market-scanner/issues/6): high-upside-first, retain candidate discovery even when incomplete; premium grades, WOTC/EX and Japanese 1996–2007.
- `docs/REPRODUCIBLE_DISCOVERY.md`: **Expedition Rapidash #62 non-holo vs reverse vs holo #26** and dated variant-specific PSA sales; original $82.95 listing is unverified.
- `docs/PHOTO_PREGRADING_V2.md`, `docs/PREGRADE_SCREEN.md`: CV heuristics, ONNX adapter, 1,000-image aspirational goal, rights evidence, leakage avoidance.
- `docs/EBAY_BROWSE_SETUP.md`, `docs/POKEMON_PRICE_TRACKER_API.md`: eBay approval-first and strict provider licensing/spend control; initial real Top50 enrichment was unconfirmed.
- `docs/HIGH_UPSIDE.md`: separate safe and speculative tiers and preference for $500+ exit opportunities.
