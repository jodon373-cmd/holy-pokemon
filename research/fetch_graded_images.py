"""Fetch pinned Hugging Face image archives for Holy Pokémon's local graded-card audit.

Run from any directory:
  python3 -m pip install 'huggingface_hub[hf_xet]>=0.34'
  python3 research/fetch_graded_images.py --dry-run
  python3 research/fetch_graded_images.py --dataset both

Downloading is not permission to train. Never commit or alter original images.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "research" / "graded_image_sources.json"
LOCAL = ROOT / "research" / "local" / "graded"

SOURCES = {
    "paco": {
        "id": "pacoalberola_poke_grader_images",
        "repo": "pacoalberola/Poke-Grader-Dataset-Images-PSA",
        "patterns": ["grades.csv", "images/**", "README.md"],
        "min_free_gib": 2,
    },
    "jyesr": {
        "id": "jyesr_pokemon_tcg_grading",
        "repo": "jyesr/pokemon-tcg-grading",
        "patterns": ["metadata.csv", "data_shard_*.tar", "README.md"],
        "min_free_gib": 25,
    },
}


def source_plan(selection, output):
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    entries = {row["id"]: row for row in registry["sources"]}
    names = ("paco", "jyesr") if selection == "both" else (selection,)
    result = []
    for name in names:
        spec = SOURCES[name]
        entry = entries[spec["id"]]
        revision = entry.get("snapshot", "")
        expected_url = "https://huggingface.co/datasets/" + spec["repo"]
        if entry.get("url", "").rstrip("/") != expected_url:
            raise ValueError("Unexpected source URL for " + name)
        if len(revision) != 40 or any(c not in "0123456789abcdef" for c in revision):
            raise ValueError("Unpinned or malformed source revision for " + name)
        result.append({
            "name": name, "repo_id": spec["repo"],
            "revision": revision,
            "local_dir": str(output / name),
            "allow_patterns": spec["patterns"],
            "min_free_gib": spec["min_free_gib"],
            "training_status": "NOT_APPROVED_UNVERIFIED",
        })
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=["paco", "jyesr", "both"], default="both")
    parser.add_argument("--out", type=Path, default=LOCAL)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-workers", type=int, default=4)
    args = parser.parse_args(argv)
    if not 1 <= args.max_workers <= 16:
        parser.error("--max-workers must be between 1 and 16")
    jobs = source_plan(args.dataset, args.out)
    print(json.dumps({
        "status": "DRY_RUN" if args.dry_run else "FETCHING_UNVERIFIED_ORIGINALS",
        "sources": jobs,
    }, indent=2))
    if args.dry_run:
        return 0
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        parser.error("Install: python3 -m pip install 'huggingface_hub[hf_xet]>=0.34'")
    for job in jobs:
        dest = Path(job["local_dir"])
        dest.mkdir(parents=True, exist_ok=True)
        free = shutil.disk_usage(dest).free / 1024**3
        if free < job["min_free_gib"]:
            raise RuntimeError(
                f"{job['name']} needs at least {job['min_free_gib']} GiB free; "
                f"only {free:.1f} GiB available. No download started."
            )
        print(f"Fetching original snapshot for {job['name']}...", flush=True)
        snapshot_download(
            repo_id=job["repo_id"], repo_type="dataset",
            revision=job["revision"],
            allow_patterns=job["allow_patterns"],
            local_dir=dest, max_workers=args.max_workers,
        )
        print(f"Fetched {job['name']}; training eligibility still unverified.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
