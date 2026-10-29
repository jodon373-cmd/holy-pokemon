# Holy Pokémon: fetch the two original image collections

This repository now has a **pinned full-media download command** for the two
external graded-card datasets in `research/graded_image_sources.json`.

From the Holy Pokémon checkout on the owner's Mac:

```bash
python3 -m pip install 'huggingface_hub[hf_xet]>=0.34'
python3 research/fetch_graded_images.py --dry-run
python3 research/fetch_graded_images.py --dataset both
```

The downloader retrieves:

- **paco**: all available `images/**` and `grades.csv`, source
  `pacoalberola/Poke-Grader-Dataset-Images-PSA` (~282 MB, 3,156 images).
- **jyesr**: all `data_shard_*.tar` images and `metadata.csv`, source
  `jyesr/pokemon-tcg-grading` (~17 GB, 20K+ front/back scans).

It pins each source to the revision already recorded in the repository,
stores files under the existing Git-ignored `research/local/graded/`,
checks available disk space, and supports resumable downloads. No resizing,
image editing, labeling, model promotion or Git commits are performed.

**Codex continuation:** Download the originals on the Mac, preserve all source
bytes, inventory and safely index the shards, run
`holy_pokemon.dataset_intake`, verify rights and grade evidence, and only
then pass eligible verified front/back specimens into the current trainer.
In particular, jyesr's **expected PSA grade** is not an observed professional
grade, and paco's image grades are source claims until independently checked.

**Storage and rights limitation:** The raw third-party media have not been
uploaded to GitHub itself. The public dataset cards do not establish clear
redistribution/training rights, and the larger original is 17 GB. This private
repo tracks the exact sources and the downloader; the original image files
remain at the source and in the owner's local checkout after download.
