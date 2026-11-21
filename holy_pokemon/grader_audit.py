"""Decode unique original images once; cache descriptive QA and duplicate candidates."""

import json
from collections import Counter
from .store import Store, ROOT, stable, now
from .image_review import quality
from .app_service import images, asset_path


def audit_images():
    report = {
        "generated_at": now(),
        "decoded": 0,
        "unreadable": [],
        "near_duplicate_candidates": [],
        "side_counts": {"unknown": 0},
        "stage_counts": {"unknown": 0},
        "verified_pre_buy_photo_outcome_pairs": 0,
    }
    with Store() as store:
        records = []
        for asset in images(store):
            key = stable("qa", asset.get("sha256") or asset["id"])
            prior = store.get("review", key)
            if prior:
                qa = prior["qa"]
            else:
                try:
                    qa = quality(asset_path(store, asset["id"]))
                except Exception as exc:
                    report["unreadable"].append(
                        {"id": asset["id"], "reason": type(exc).__name__}
                    )
                    continue
                store.put(
                    "review",
                    key,
                    {
                        "type": "photo_qa",
                        "asset_id": asset["id"],
                        "qa": qa,
                        "at": now(),
                    },
                )
            records.append(
                {
                    "id": asset["id"],
                    "name": asset["name"],
                    "qa": qa,
                    "side": "unknown",
                    "stage": "unknown",
                    "actual_outcome_link": None,
                    "eligible": False,
                    "exclusion": "REQUIRES_PHYSICAL_COPY_STAGE_OUTCOME_AND_CROP_REVIEW",
                }
            )
        hashes = [(r["id"], int(r["qa"]["dhash"], 16)) for r in records]
        for i, (a, ha) in enumerate(hashes):
            for b, hb in hashes[i + 1 :]:
                distance = (ha ^ hb).bit_count()
                if distance <= 3:
                    report["near_duplicate_candidates"].append(
                        {
                            "a": a,
                            "b": b,
                            "distance": distance,
                            "status": "CANDIDATE_NOT_PHYSICAL_MATCH",
                        }
                    )
        report["decoded"] = len(records)
        report["side_counts"]["unknown"] = len(records)
        report["stage_counts"]["unknown"] = len(records)
        report["quality_warnings"] = dict(
            Counter(w for r in records for w in r["qa"]["warnings"])
        )
        report["images"] = records
        report["curated_labels"] = len(
            [r for r in store.rows("review") if r.get("type") == "training_label"]
        )
    directory = ROOT / "outputs/grader"
    (directory / "image_audit.json").write_text(json.dumps(report, indent=2))
    (directory / "excluded_images.json").write_text(json.dumps(records, indent=2))
    (directory / "model_card.md").write_text(
        "# Real grader status: NO MODEL\n\nNo verified buyer-visible photograph pair has been linked to an actual later result with reviewed card-only crops. Real-data accuracy, PSA10 false-positive rate and economic backtest are unavailable.\n\nOriginal QA proxies are descriptive, not validated defect detectors. Synthetic pipeline validation is separate and does not establish grading accuracy.\n"
    )
    return {
        k: v
        for k, v in report.items()
        if k not in ("images", "near_duplicate_candidates")
    }


if __name__ == "__main__":
    print(json.dumps(audit_images(), indent=2))
