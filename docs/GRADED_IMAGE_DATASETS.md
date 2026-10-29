# Graded-card image intake — source-truth first

This repository now has an explicit, local-only path for auditing thousands of
card photographs **before** allowing any into the existing PyTorch grader.

**This is not 23K verified PSA training examples.** Both public collections
require more evidence than their advertised image counts provide.

## Target training distribution

Primary: **Pokémon vintage 1996–2007**, English and Japanese, holographics
and high-value promos, including Base, Jungle, Fossil, Rocket, Gym, Neo,
e-Series and EX-era. Prioritize **PSA 8, 9 and 10** with a target of **1,000+
unique verified physical specimens**, not 1,000 variants of the same photo or
one-sided scans. Keep grade 6–7 and known damaged cards for negative validation
and failure analysis.

All of the following remain different cohorts: (a) true verified grading
results; (b) expected/human-predicted grades; (c) single post-grade slab photos;
(d) paired pre-purchase original photos with later observed grading outcomes;
(e) creator-reported regrading results. They must **not** be trained together as
though they share identical labels, access rights, or buyer-visible photo quality.

## External source reality

- [jyesr/pokemon-tcg-grading](https://huggingface.co/datasets/jyesr/pokemon-tcg-grading):
  ~17 GB; claims >20K front/back images. Its dataset card explicitly calls
  grade fields **expected** PSA grades, not completed PSA outcomes. Modern-biased.
  No confirmed permissive training license. Appropriate only for exploratory
  or separately approved visual pretraining; **NOT** observed-grade labels.
- [pacoalberola/Poke-Grader-Dataset-Images-PSA](https://huggingface.co/datasets/pacoalberola/Poke-Grader-Dataset-Images-PSA):
  ~282 MB, **3,156 images**, `grades.csv`. Rows include PSA and other
  graders (BGS, CGC, ACE), estimated decimal component scores and no confirmed
  original specimen front/back relationship. The dataset page has **no dataset
  card or declared data license**. Treat the file grades as publisher claims
  until verified from actual source certificates. **Not** an automatic 3,156
  PSA-paired-card ground-truth dataset.
- Provenance/permission statuses are in
  [research/graded_image_sources.json](../research/graded_image_sources.json).

**No raw images were copied or committed.** This matches AGENTS.md's explicit
source-image and privacy policy, avoids rehosting third-party photographs, and
prevents a 17 GB addition to a small private Git repository.

## 1. Obtain/source metadata legally

Once the source's acceptable-use and copyright/training permission have been
verified, use [Hugging Face documented downloads](https://huggingface.co/docs/huggingface_hub/guides/download)
on the owner's Mac. Keep images under the ignored `research/local/` directory:

```bash
python3 -m pip install huggingface_hub pillow
hf download pacoalberola/Poke-Grader-Dataset-Images-PSA grades.csv \
  --repo-type dataset --local-dir research/local/graded/paco
hf download jyesr/pokemon-tcg-grading metadata.csv \
  --repo-type dataset --local-dir research/local/graded/jyesr
```

Metadata inspection is **not** permission to redistribute dataset images.
Download image binaries only after rights, dataset terms, source provenance
and storage capacity have been checked. Pinned source revisions are in the
registry; pin them for a reproducible full media download.

## 2. Run real metadata inventory

```bash
python3 -m holy_pokemon.dataset_intake inventory-paco \
  --csv research/local/graded/paco/grades.csv \
  --out outputs/graded_paco_inventory.json

python3 -m holy_pokemon.dataset_intake inventory-jyesr \
  --csv research/local/graded/jyesr/metadata.csv \
  --out outputs/graded_jyesr_inventory.json
```

These commands compute genuine local metadata counts. Neither command trains
the grader or declares any image eligible. No one should claim which exact
rows pass the eligibility audit until the source files have been downloaded,
reviewed and checked.

## 3. Approve only genuine paired, label-hidden specimens

Create `research/local/graded/reviewed.csv` with these exact columns:

```csv
specimen_id,source_id,grader,grade,label_kind,outcome_verified,outcome_evidence,year,game,front_path,back_path,card_only_verified,same_specimen_pair_verified,pre_buy_visible,rights_basis,rights_evidence,exact_card_identity_verified
```

Each row is **one physical copy**, both native front and native back relative
to a chosen local image root. Set `label_kind=observed_professional_grade`
only with actual independently verified grader outcome. Never promote
jyesr's expected grades by setting `outcome_verified=true` without real
professional evidence. Record real training rights; `public_website` is not
an allowed permission type. Check that the card itself (not holder label or
barcode) is visible without grade leakage. Verify that both images depict
the same copy and are available at the point a buyer would make a decision.

```bash
python3 -m holy_pokemon.dataset_intake audit \
  --manifest research/local/graded/reviewed.csv \
  --images-root research/local/graded/approved_images \
  --out outputs/graded_intake_audit.json \
  --training-manifest-out research/local/graded/approved_train.csv
```

The command checks:
- Actual PSA 8/9/10 observed grade and evidence, Pokémon, card identity.
- Explicit per-source image training permission.
- Same-copy front/back metadata, card-only images, pre-buy visibility.
- Minimum source image dimensions 500 px on the short side by default.
- Corrupt/unreadable images, untrusted paths, duplicate SHA-256s and specimens.
- Vintage 1996–2007 versus secondary/out-of-domain categories.

All rejected rows stay in the JSON audit with explanations. The exported CSV
has **only passing pairs** in the exact schema consumed by
`holy_pokemon.vision_training.read_manifest`. The exporter itself does not fit,
update or promote any model.

## 4. Train only after audit and frozen specimen splits

```bash
python3 -m holy_pokemon.vision_training train \
  --manifest research/local/graded/approved_train.csv \
  --grader PSA --out local_models/psa_verified_experimental.pt
```

The existing trainer is a small proof-of-concept and its source-group split
needs to be audited for near-duplicates, especially cross-source duplicates,
before interpreting any accuracy. Do not use post-grade photo holdout scores
as proof of prospective buyer-photo grading quality. No training on 20K
expected labels as though they are actual PSA grades.

### The Hitmonchan lesson

A blind prediction clamped to PSA 1 followed by an in-sample PSA 8 after
training **does not show generalized accuracy**. Freeze original predictions
and preserve failed cases. Train on many *other* cards, and test on untouched
specimens from the same era/photo domain. The primary deliverable is better
blind reliability, not perfect memorization of known examples.

### Required promotion criteria

For an independent, specimen-disjoint holdout show the class confusion matrix,
PSA 8/9/10 per-class precision and recall, grade MAE, false PSA 10 rate and
abstention rate. Grade predictions and regrade-to-CGC-10 outcomes are
**different targets**; no conversion probability is claimed without real
cross-grading outcomes. Preserve failed/downsized cards and unknown defects.
No user-facing "gem candidate" claim without image quality and independent
model evidence.

## Implementation status

- ✅ External datasets identified; sizes and label semantics documented.
- ✅ Programmatic CSV inventory/rights quarantine.
- ✅ Native image integrity and paired specimen audit.
- ✅ Verified pair export into existing local trainer schema.
- ✅ Isolated test fixtures for invalid permissions, expected grades, duplicates,
  traversal and mixed grader sources.
- ⛔ Downloaded/validated third-party media: **0 verified rows in this PR**.
- ⛔ Rights clearance for these datasets: **not established**.
- ⛔ 1,000 validated, vintage, card-only, true-PSA-result pairs: **not achieved**.
- ⛔ Newly trained or independently tested model: **not done in this PR**.

The local Mac checkout contains substantial newer code than the GitHub main
branch. Merge this through an ordinary PR/rebase and resolve overlap with its
newer `graded_photo_batch.py` before training; do not overwrite the local work.
