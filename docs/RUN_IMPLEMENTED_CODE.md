# Run what's actually implemented now

This repo currently includes an **offline local functional foundation**, not the full live eBay/PSA Vault/trained-grade product. It requires no credentials, paid API or external marketplace access.

From the repository root, on a Mac with Python 3.12+:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 -m holy_pokemon monthly
python3 -m holy_pokemon rules
python3 -m holy_pokemon.dashboard --port 8765
```

Open **http://127.0.0.1:8765** in your browser. It shows eight-month source-ledger figures, route comparison and PSA Vault withdrawal what-ifs. Double-click Mac launcher after one-time `chmod +x mac/Start_Holy_Pokemon.command` from a cloned checkout. The app binds only to 127.0.0.1 and cannot buy/sell cards.

If the full transcript transport has been downloaded, audit the *nested canonical 18-source ZIP*:

```bash
python3 -m holy_pokemon inspect-transport --zip '/path/to/HolyPokemon_Research_Data_for_Codex.zip'
```

The newer full source bundle `HolyPokemon_Full_Fredy_Business_Source_Transport.zip` has the canonical ZIP inside it and the overlapping 28-video transcripts. Extract the nested canonical ZIP before calling the simple transport audit, or implement the full nested ZIP intake per the master Codex task.

For actual model training (requires installed PyTorch, torchvision, Pillow and a rights-verified card-only image manifest with at least five independent source videos):

```bash
python3 -m holy_pokemon.vision_training train --manifest /path/to/approved_images.csv --grader PSA --out local_models/psa_experimental.pt
python3 -m holy_pokemon.vision_training predict --checkpoint local_models/psa_experimental.pt --image /path/to/verified_card_only.jpg
```

Important: **no trained real-data weights are included**. The model is experimental until valid image data are supplied and independent holdout evaluation is complete. The manifest must include grader, grade, image_path, physical_specimen_id, source_video_id, rights_basis, rights_evidence, card_only_verified, pre_decision_visible. Original source images must not be modified to conceal flaws.

Current limitations: dashboard is an offline research/what-if console, not yet the finished scanner; eBay OAuth production adapter, Vault owner inventory import, actual sales reconciliation UI, image annotation UX, local source ingest and trained weights are tasks for Codex. Full execution requirements: docs/CODEX_MASTER_BUILD.md, docs/FREDY_BUSINESS_REVERSE_ENGINEERING.md and docs/PSA_VAULT_END_TO_END.md.

**Codex launch blocker** as of 2026-10-28: issue #1 has an explicit @codex request, but the Codex bot responded that a [Codex Cloud environment must be created for this repo](https://chatgpt.com/codex/cloud/settings/environments). A bot mention is NOT proof of a running task.
