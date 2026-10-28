# Getting the actual source research into a Codex checkout

**Important:** This private GitHub repo contains the manifest and instructions. It intentionally does NOT contain the original gigabytes of video evidence or 18 source ZIP archives. A Codex Cloud workspace cannot read your Mac's Finder folder unless you explicitly attach/sync the contents.

The owner has a compact research transport artifact: **HolyPokemon_Research_Data_for_Codex.zip** (445,620 bytes, ZIP integrity tested). It is an export from the **18 manifest-matched original ZIPs**. It includes:
- `source_case_rows.jsonl`: 250 raw case rows from 16 itemized source packs, with original source-native columns and provenance retained. **Not automatically 250 unique physical cards**.
- `source_asset_inventory.json`: all 18 exact ZIP hashes and extracted file mapping.
- `archive_tables/`: 148 plain-text/CSV/JSON/Markdown files, including the 546-card and gem-rate aggregate studies. No raw video or full-resolution card-condition imagery.
- `README.md`: readme inside the bundle.

## Local Mac quick setup
1. Clone the new GitHub repo to your Mac.
2. Download the compact transport bundle from the ChatGPT conversation.
3. Create directory `research/local` inside the cloned repo and extract the transport bundle there. The directory is intentionally ignored by Git.
4. For the full AI-grading dataset, also point the configured import path to the untouched original Fredy research ZIPs in your Finder folder. The compact transport bundle contains only text/data records; it does not replace full evidence images.

## Codex Cloud quick setup
If Codex runs in a cloud checkout, upload the compact transport bundle to its task or otherwise make it available in its cloud filesystem. **Merely mentioning the ZIP's name or having it in a separate ChatGPT chat does not mount it.** Codex must check the real files and not claim import if absent.

## No manual renaming
The canonical source names and SHA256s are in `research/manifest.csv`. Copies with `(1)` or `(2)` suffix are byte-duplicate uploads and should be checksum-matched, not re-counted as new submissions. Alternate archival versions are distinct sources and cannot be silently substituted for canonical hashes.

## Training
The compact archive can populate card metadata and event labels. For the actual supervised computer-vision training run, use the permitted original before/after image evidence; require explicit data rights and group-by-card/video splits. Training data coverage will be audited and missing images honestly noted.
