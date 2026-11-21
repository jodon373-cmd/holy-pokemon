"""Audit graded-card image datasets before they enter a Holy Pokémon model.

All dataset imagery stays on the owner's machine. This tool NEVER downloads,
rewrites, or uploads images and NEVER trains a model. Labels from unknown
sources, expected (not observed) grades, and post-result slab photographs
must not silently become pre-buy grading ground truth.

Run:
  python -m holy_pokemon.dataset_intake inventory-paco --csv path/to/grades.csv --out inventory.json
  python -m holy_pokemon.dataset_intake inventory-jyesr --csv path/to/metadata.csv --out inventory.json
  python -m holy_pokemon.dataset_intake audit --manifest path/to/reviewed.csv --out audit.json
"""
from __future__ import annotations

import argparse
import collections
import csv as _csv
import csv
import hashlib
import json
from pathlib import Path

ALLOWED_RIGHTS = {"self_photographed", "explicit_permission", "verified_permissive_license"}
GRADES = {"8", "9", "10"}
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
VINTAGE_MIN, VINTAGE_MAX = 1996, 2007


def truth(value):
    return str(value or "").strip().lower() in {"true", "yes", "1"}


def digest_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _inventory_paco(csv_path):
    """Paco data includes PSA, BGS, CGC and ACE, and inferred decimal subgrades.

    Filename grade/source is a dataset CLAIM, not independently verified PSA
    grading. Source page gives no training redistribution license.
    """
    with open(csv_path, encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    summary = collections.Counter()
    candidates = []
    for row in rows:
        filename = (row.get("filename") or "").strip()
        source = (row.get("source") or "").strip().lower()
        grade = (row.get("overall_grade") or "").strip()
        grade_number = None
        try:
            grade_number = float(grade)
        except ValueError:
            pass
        is_psa = source == "ebay_psa"
        is_target = grade_number in {8.0, 9.0, 10.0}
        summary["all_metadata_rows"] += 1
        summary["source_" + (source or "unknown")] += 1
        if is_psa:
            summary["psa_claim_rows"] += 1
        if is_psa and is_target:
            summary["psa_8_9_10_claim_rows"] += 1
            summary["psa_" + str(int(grade_number)) + "_claim_rows"] += 1
            candidates.append({"filename": filename, "grade_claim": int(grade_number),
                               "source": source, "authorization": "UNVERIFIED",
                               "grade_verification": "UNVERIFIED",
                               "front_back_pair": "UNVERIFIED",
                               "actual_subgrades": "NOT_ESTABLISHED"})
    return {
        "source": "pacoalberola/Poke-Grader-Dataset-Images-PSA",
        "kind": "third_party_metadata_inventory",
        "source_csv_sha256": digest_file(csv_path),
        "counts": dict(sorted(summary.items())),
        "candidate_metadata_only": candidates,
        "eligible_training_rows": 0,
        "blocked_reasons": [
            "NO_DATASET_LICENSE_OR_ITEM_LEVEL_PERMISSION_VERIFIED",
            "NO_VERIFIED_CERT_SPECIMEN_ID_OR_SAME_CARD_FRONT_BACK",
            "NO_VERIFIED_CARD_ONLY_NO_LABEL_LEAKAGE",
            "NO_INDEPENDENT_PSA_OUTCOME_VALIDATION",
            "DECIMAL_SUBGRADES_NOT_VERIFIED_GRADER_OUTCOMES",
            "NO_ERA_OR_EXACT_CARD_IDENTITY_METADATA",
        ],
    }


def _inventory_jyesr(csv_path):
    """jyesr describes grades as EXPECTED PSA grades, not observed labels."""
    with open(csv_path, encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = reader.fieldnames or []
        count = 0
        head = []
        for row in reader:
            count += 1
            if len(head) < 3:
                head.append({key: str(value)[:100] for key, value in row.items()})
    return {
        "source": "jyesr/pokemon-tcg-grading",
        "kind": "third_party_metadata_inventory",
        "source_csv_sha256": digest_file(csv_path),
        "columns": columns,
        "rows": count,
        "example_metadata": head,
        "eligible_training_rows": 0,
        "blocked_reasons": [
            "EXPECTED_PSA_GRADES_ARE_NOT_OBSERVED_PSA_OUTCOMES",
            "RIGHTS_AND_ITEM_LEVEL_PERMISSION_NOT_VERIFIED",
            "PAIRING_SPECIMEN_ERA_AND_NO_LABEL_LEAKAGE_NOT_AUDITED",
            "MODERN_CARD_DISTRIBUTION_BIAS",
        ],
        "allowed_use_if_authorized": "unlabeled_visual_pretraining_or_exploratory_quality_diagnostics",
    }


def inventory(source, csv_path):
    csv_path = Path(csv_path)
    if not csv_path.is_file():
        raise FileNotFoundError(str(csv_path))
    if source == "paco":
        return _inventory_paco(csv_path)
    if source == "jyesr":
        return _inventory_jyesr(csv_path)
    raise ValueError("Unknown inventory source")


def _image_info(path):
    from PIL import Image, UnidentifiedImageError
    try:
        with Image.open(path) as im:
            im.verify()
        with Image.open(path) as im:
            return im.size
    except (UnidentifiedImageError, OSError, ValueError):
        return None


def _local_image(root, relative):
    """Do not let external manifest paths escape the explicitly selected root."""
    if not relative or Path(relative).is_absolute():
        return None
    root = root.resolve()
    resolved = (root / relative).resolve()
    if resolved != root and root not in resolved.parents:
        return None
    return resolved


def _row_category(row):
    try:
        year = int(row.get("year") or 0)
    except ValueError:
        year = 0
    if VINTAGE_MIN <= year <= VINTAGE_MAX:
        return "primary_vintage"
    return "secondary_or_unknown"


def audit(manifest, images_root, min_side=500):
    """Produce training-ready manifest only after explicit metadata + pixel review.

    Required columns: specimen_id,grader,grade,label_kind,outcome_verified,
    outcome_evidence,year,front_path,back_path,card_only_verified,
    same_specimen_pair_verified,pre_buy_visible,rights_basis,rights_evidence,
    source_id,exact_card_identity_verified,game.

    Post-grade slab photos can be kept in a separate diagnostic dataset, but
    cannot be fed to the prospective pre-buy trainer by this command.
    """
    images_root = Path(images_root)
    with open(manifest, encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    usable, blocked, source_hash_to_specimen = [], [], {}
    seen_specimens = set()
    summary = collections.Counter()
    for index, row in enumerate(rows, 2):
        reasons = []
        specimen = (row.get("specimen_id") or "").strip()
        grader = (row.get("grader") or "").strip().upper()
        grade = (row.get("grade") or "").strip()
        if row.get("game", "").strip().lower() != "pokemon":
            reasons.append("NOT_POKEMON")
        if grader != "PSA" or grade not in GRADES:
            reasons.append("NOT_TARGET_PSA_8_9_10")
        if (row.get("label_kind") or "").strip() != "observed_professional_grade":
            reasons.append("EXPECTED_OR_UNVERIFIED_GRADE")
        if not truth(row.get("outcome_verified")) or not row.get("outcome_evidence"):
            reasons.append("OUTCOME_NOT_VERIFIED")
        if (row.get("rights_basis") or "").strip() not in ALLOWED_RIGHTS or not row.get("rights_evidence"):
            reasons.append("TRAINING_RIGHTS_NOT_VERIFIED")
        if not truth(row.get("card_only_verified")):
            reasons.append("GRADE_LABEL_OR_SLAB_LEAKAGE_NOT_REVIEWED")
        if not truth(row.get("same_specimen_pair_verified")):
            reasons.append("FRONT_BACK_SPECIMEN_PAIR_NOT_VERIFIED")
        if not truth(row.get("pre_buy_visible")):
            reasons.append("POST_GRADE_OR_NOT_PREBUY_VISIBLE")
        if not truth(row.get("exact_card_identity_verified")):
            reasons.append("EXACT_CARD_IDENTITY_NOT_VERIFIED")
        if not specimen or not (row.get("source_id") or "").strip():
            reasons.append("MISSING_SPECIMEN_OR_SOURCE_ID")
        if specimen in seen_specimens:
            reasons.append("DUPLICATE_SPECIMEN")
        seen_specimens.add(specimen)
        images = {}
        for side in ("front", "back"):
            path = _local_image(images_root, row.get(side + "_path"))
            if path is None or not path.is_file() or path.suffix.lower() not in ALLOWED_EXTENSIONS:
                reasons.append("MISSING_OR_UNSAFE_" + side.upper() + "_FILE")
                continue
            dimensions = _image_info(path)
            if dimensions is None:
                reasons.append("INVALID_" + side.upper() + "_IMAGE")
                continue
            if min(dimensions) < min_side:
                reasons.append("LOW_RESOLUTION_" + side.upper())
            sha = digest_file(path)
            if sha in source_hash_to_specimen:
                reasons.append("DUPLICATE_IMAGE_ACROSS_SPECIMENS_OR_SIDES")
            source_hash_to_specimen[sha] = specimen
            images[side] = {"local_relative_path": row[side + "_path"],
                            "sha256": sha, "width": dimensions[0], "height": dimensions[1]}
        category = _row_category(row)
        summary["submitted_rows"] += 1
        summary["category_" + category] += 1
        if reasons:
            blocked.append({"row": index, "specimen_id": specimen,
                            "reasons": sorted(set(reasons)), "category": category})
            summary["blocked_rows"] += 1
            for reason in set(reasons):
                summary["reason_" + reason] += 1
            continue
        summary["eligible_rows"] += 1
        summary["eligible_grade_" + grade] += 1
        summary["eligible_category_" + category] += 1
        usable.append({
            "specimen_id": specimen, "source_id": row["source_id"],
            "grader": grader, "observed_grade": grade, "year": row.get("year") or None,
            "category": category, "image_pair": images,
            "outcome_evidence": row["outcome_evidence"],
            "rights_basis": row["rights_basis"], "rights_evidence": row["rights_evidence"],
            "pre_buy_visible": True, "no_visible_grade_labels_confirmed": True,
        })
    return {
        "schema": "holy_pokemon_dataset_intake_v1",
        "status": "AUDITED_ONLY_NOT_TRAINED",
        "manifest_sha256": digest_file(manifest),
        "images_root": str(images_root.resolve()),
        "counts": dict(sorted(summary.items())),
        "eligible": usable,
        "blocked": blocked,
        "notes": [
            "No training, image modification or external transfer occurred.",
            "Physical specimen and source-group separation must be verified before splitting.",
            "Post-grade slabs require a SEPARATE diagnostic domain, not pre-buy training.",
            "Passing this metadata audit does not certify all surface defects are visible.",
        ],
    }


def write_report(destination, payload):
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def export_training_manifest(audit_report, destination):
    """Bridge only VERIFIED pre-buy specimens to vision_training.read_manifest.

    The existing trainer uses individual images as examples; two images per
    specimen are exported with one shared ID. Splitting remains grouped by
    source_video_id, and mixed-source specimens must be resolved first.
    """
    if audit_report.get("status") != "AUDITED_ONLY_NOT_TRAINED":
        raise ValueError("Expected audited data, not an arbitrary JSON manifest")
    eligible = audit_report.get("eligible", [])
    root = Path(audit_report["images_root"])
    fields = ("grader", "grade", "rights_basis", "rights_evidence",
              "card_only_verified", "pre_decision_visible",
              "physical_specimen_id", "source_video_id", "image_path")
    dest = Path(destination)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "w", encoding="utf-8", newline="") as handle:
        writer = _csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for specimen in eligible:
            for side in ("front", "back"):
                writer.writerow({
                    "grader": specimen["grader"], "grade": specimen["observed_grade"],
                    "rights_basis": specimen["rights_basis"],
                    "rights_evidence": specimen["rights_evidence"],
                    "card_only_verified": "true", "pre_decision_visible": "true",
                    "physical_specimen_id": specimen["specimen_id"],
                    "source_video_id": specimen["source_id"],
                    "image_path": str((root / specimen["image_pair"][side]["local_relative_path"]).resolve()),
                })
    return {"file": str(dest), "verified_specimens": len(eligible),
            "image_rows": 2 * len(eligible), "model_trained": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("inventory-paco", "inventory-jyesr"):
        p = commands.add_parser(name)
        p.add_argument("--csv", required=True)
        p.add_argument("--out", required=True)
    p = commands.add_parser("audit")
    p.add_argument("--manifest", required=True)
    p.add_argument("--images-root", required=True)
    p.add_argument("--min-side", type=int, default=500)
    p.add_argument("--out", required=True)
    p.add_argument("--training-manifest-out", help="Export only fully audited pairs for existing vision_training trainer")
    args = parser.parse_args(argv)
    if args.command == "audit":
        payload = audit(args.manifest, args.images_root, args.min_side)
    else:
        payload = inventory(args.command.split("-")[1], args.csv)
    dest = write_report(args.out, payload)
    if args.command == "audit" and args.training_manifest_out:
        export_training_manifest(payload, args.training_manifest_out)
    print(json.dumps({"report": str(dest), "counts": payload.get("counts"),
                      "eligible_training_rows": len(payload.get("eligible", []))}))


if __name__ == "__main__":
    main()
