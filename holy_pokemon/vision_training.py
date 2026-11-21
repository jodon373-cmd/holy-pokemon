"""Real, local PyTorch training/inference pipeline for user-approved card-only photos.

No weights are pretended to exist. No remote image downloads, credentials or AI API.
The model is experimental until holdout metrics validate it.
"""

from __future__ import annotations
import argparse
import csv
import hashlib
import json
import random
from pathlib import Path

ALLOWED_RIGHTS = {
    "self_photographed",
    "explicit_permission",
    "verified_permissive_license",
}
LABELS = {
    "PSA": ("6", "7", "8", "9", "10"),
    "CGC": ("7.5", "8", "8.5", "9", "9.5", "10", "Pristine 10"),
    "BGS": ("8", "8.5", "9", "9.5", "10"),
}


def read_manifest(path, grader):
    """Hard gate against label leakage and duplicate specimen/video split."""
    if grader not in LABELS:
        raise ValueError("Select supported target grader")
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    selected = []
    excluded = []
    seen = set()
    for i, row in enumerate(rows, 2):
        reasons = []
        if row.get("grader") != grader:
            continue
        if row.get("grade") not in LABELS[grader]:
            reasons.append("unknown_grader_grade")
        if row.get("rights_basis") not in ALLOWED_RIGHTS or not row.get(
            "rights_evidence"
        ):
            reasons.append("no_authorized_training_rights")
        if row.get("card_only_verified", "").lower() not in ("true", "1", "yes"):
            reasons.append("unverified_card_only_crop_label_leakage_risk")
        if row.get("pre_decision_visible", "").lower() not in ("true", "1", "yes"):
            reasons.append("post_outcome_image_not_buyer_visible")
        if not row.get("physical_specimen_id") or not row.get("source_video_id"):
            reasons.append("unidentified_group")
        image = Path(row.get("image_path", ""))
        if not image.is_file() or image.suffix.lower() not in (
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
        ):
            reasons.append("missing_local_supported_image")
        sha = ""
        if not reasons:
            sha = hashlib.sha256(image.read_bytes()).hexdigest()
            if sha in seen:
                reasons.append("duplicate_photo")
        if reasons:
            excluded.append({"row": i, "reasons": reasons})
            continue
        seen.add(sha)
        selected.append({**row, "sha256": sha})
    return selected, excluded


def split_by_video(rows, seed=73):
    """Keep all physical copies in one video/submission together to limit leakage."""
    if not rows:
        raise ValueError("No rights-verified image rows")
    groups = {}
    for row in rows:
        groups.setdefault(row["source_video_id"], []).append(row)
    vids = sorted(groups)
    if len(vids) < 5:
        raise ValueError(
            "At least five separate source videos/groups needed for a held-out experimental test"
        )
    random.Random(seed).shuffle(vids)
    test_count = max(1, round(len(vids) * 0.2))
    validation_count = max(1, round(len(vids) * 0.2))
    test = set(vids[:test_count])
    val = set(vids[test_count : test_count + validation_count])
    parts = {"train": [], "val": [], "test": []}
    for video_id, group in groups.items():
        target = "test" if video_id in test else "val" if video_id in val else "train"
        parts[target].extend(group)
    physical_assignment = {}
    for split, rr in parts.items():
        for row in rr:
            key = row["physical_specimen_id"]
            if key in physical_assignment and physical_assignment[key] != split:
                raise ValueError(
                    "Physical specimen across different videos/splits: resolve duplicate before training"
                )
            physical_assignment[key] = split
    if any(not rr for rr in parts.values()):
        raise ValueError("Empty data split")
    return parts


def _torch():
    try:
        import torch
        from torch import nn
        from torchvision import transforms
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError(
            "Install torch, torchvision and pillow locally before training"
        ) from exc
    return torch, nn, transforms, Image


def model_for(num_classes):
    torch, nn, _, _ = _torch()
    return nn.Sequential(
        nn.Conv2d(3, 12, 3, padding=1),
        nn.ReLU(),
        nn.MaxPool2d(2),
        nn.Conv2d(12, 24, 3, padding=1),
        nn.ReLU(),
        nn.MaxPool2d(2),
        nn.Conv2d(24, 32, 3, padding=1),
        nn.ReLU(),
        nn.AdaptiveAvgPool2d((1, 1)),
        nn.Flatten(),
        nn.Linear(32, num_classes),
    )


def _training_rows(manifest, grader):
    rows, rejected = read_manifest(manifest, grader)
    approved = []
    from .image_review import quality

    for r in rows:
        reasons = []
        if r.get("game") != "pokemon":
            reasons.append("pokemon_domain_required")
        if not r.get("outcome_evidence"):
            reasons.append("missing_observed_later_outcome_evidence")
        if r.get("outcome_verified", "").lower() not in ("yes", "true", "1"):
            reasons.append("unverified_outcome")
        if not r.get("back_image_path") or not Path(r["back_image_path"]).is_file():
            reasons.append("missing_back")
        if r.get("back_card_only_verified", "").lower() not in ("yes", "true", "1"):
            reasons.append("back_label_leakage_review_missing")
        if not reasons:
            r["back_sha256"] = hashlib.sha256(
                Path(r["back_image_path"]).read_bytes()
            ).hexdigest()
            for p in (r["image_path"], r["back_image_path"]):
                try:
                    qa = quality(p)
                    if min(qa["width"], qa["height"]) < 128:
                        reasons.append("low_resolution")
                except Exception:
                    reasons.append("unreadable_image")
        if reasons:
            rejected.append(
                {"specimen": r.get("physical_specimen_id"), "reasons": reasons}
            )
        else:
            approved.append(r)
    # Conservatively connect perceptually similar views; this does not assert card identity.
    fingerprints = []
    for r in approved:
        fingerprints.append(
            [int(quality(r[p])["dhash"], 16) for p in ("image_path", "back_image_path")]
        )
    parent = list(range(len(approved)))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(len(approved)):
        for j in range(i):
            if any(
                (a ^ b).bit_count() <= 3
                for a in fingerprints[i]
                for b in fingerprints[j]
            ):
                parent[root(i)] = root(j)
    for i, r in enumerate(approved):
        r["perceptual_group"] = "near_" + str(root(i))
    return approved, rejected


def _pair_model(classes):
    torch, nn, _, _ = _torch()
    return nn.Sequential(
        nn.Conv2d(6, 16, 3, padding=1),
        nn.ReLU(),
        nn.MaxPool2d(2),
        nn.Conv2d(16, 32, 3, padding=1),
        nn.ReLU(),
        nn.MaxPool2d(2),
        nn.Conv2d(32, 48, 3, padding=1),
        nn.ReLU(),
        nn.AdaptiveAvgPool2d((4, 4)),
        nn.Flatten(),
        nn.Linear(48 * 16, classes),
    )


def _pair_tensor(front, back):
    torch, _, T, Image = _torch()
    from .image_review import load_image

    transform = T.Compose([T.Resize((256, 256)), T.ToTensor()])
    return torch.cat([transform(load_image(front)), transform(load_image(back))], dim=0)


def _specimen_fingerprint(row):
    keys = (
        "physical_specimen_id",
        "source_video_id",
        "grader",
        "grade",
        "game",
        "sha256",
        "back_sha256",
        "outcome_evidence",
        "pre_decision_visible",
    )
    return hashlib.sha256(
        json.dumps({k: row.get(k) for k in keys}, sort_keys=True).encode()
    ).hexdigest()


def train(manifest, grader, output, epochs=4, seed=73):
    from .evaluation import connected_split, metrics as measure
    from .store import now
    import platform

    torch, nn, T, Image = _torch()
    if not 1 <= epochs <= 200:
        raise ValueError("epochs must be 1..200")
    rows, rejected = _training_rows(manifest, grader)
    parts = connected_split(rows, seed)
    # One sample is one physical specimen, rather than each frame receiving a vote.
    for part in parts.values():
        specimens = [r["physical_specimen_id"] for r in part]
        if len(specimens) != len(set(specimens)):
            raise ValueError("Use one reviewed front/back pair per physical specimen")
    labels = list(LABELS[grader])
    torch.manual_seed(seed)
    random.seed(seed)
    torch.set_num_threads(min(4, torch.get_num_threads()))
    model = _pair_model(len(labels))
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    model.to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    criterion = nn.CrossEntropyLoss()
    for epoch in range(epochs):
        model.train()
        batch = list(parts["train"])
        random.Random(seed + epoch).shuffle(batch)
        for offset in range(0, len(batch), 8):
            rr = batch[offset : offset + 8]
            x = torch.stack(
                [_pair_tensor(r["image_path"], r["back_image_path"]) for r in rr]
            ).to(device)
            y = torch.tensor([labels.index(r["grade"]) for r in rr], device=device)
            optimizer.zero_grad()
            loss = criterion(model(x), y)
            loss.backward()
            optimizer.step()
        import sys

        print(
            f"Epoch {epoch + 1}/{epochs}; final batch loss={float(loss.detach().cpu()):.6f}; device={device}",
            file=sys.stderr,
            flush=True,
        )
    results = {}
    predictions = []
    model.eval()
    majority = max(
        range(len(labels)),
        key=lambda i: sum(r["grade"] == labels[i] for r in parts["train"]),
    )
    with torch.no_grad():
        for split, rr in parts.items():
            truth = []
            pred = []
            for r in rr:
                scores = model(
                    _pair_tensor(r["image_path"], r["back_image_path"])[None].to(device)
                )
                t = labels.index(r["grade"])
                p = int(scores.argmax(1))
                truth.append(t)
                pred.append(p)
                if split == "test":
                    predictions.append(
                        {
                            "specimen": r["physical_specimen_id"],
                            "source_video": r["source_video_id"],
                            "actual": labels[t],
                            "predicted": labels[p],
                            "correct": t == p,
                            "image_path": r["image_path"],
                            "financial_consequence": None,
                            "status": "UNCALIBRATED",
                        }
                    )
            results[split] = measure(truth, pred, labels, grader)
            results[split]["majority_baseline_accuracy"] = sum(
                t == majority for t in truth
            ) / len(truth)
            baseline = [
                labels.index(r.get("original_grade"))
                if r.get("original_grade") in labels
                else None
                for r in rr
            ]
            results[split]["original_grade_baseline_accuracy"] = (
                sum(t == p for t, p in zip(truth, baseline)) / len(truth)
                if all(p is not None for p in baseline)
                else None
            )
    synthetic = any(r.get("dataset") == "SYNTHETIC" for r in rows)
    status = "SYNTHETIC_PIPELINE_TEST" if synthetic else "EXPERIMENTAL_UNCALIBRATED"
    dest = Path(output)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if synthetic and "synthetic" not in dest.name.lower():
        raise ValueError("Synthetic checkpoint must be named synthetic")
    artifact = {
        "weights": model.cpu().state_dict(),
        "labels": labels,
        "grader": grader,
        "architecture": "paired_cnn_256_v1",
        "training_status": status,
        "seed": seed,
        "metrics": results,
        "source_sha256": [r["sha256"] for r in rows],
        "back_source_sha256": [r["back_sha256"] for r in rows],
        "specimen_fingerprints": {
            r["physical_specimen_id"]: _specimen_fingerprint(r) for r in rows
        },
        "split_specimens": {
            k: [r["physical_specimen_id"] for r in rr] for k, rr in parts.items()
        },
    }
    torch.save(artifact, dest)
    report = {
        "checkpoint": str(dest),
        "checkpoint_sha256": hashlib.sha256(dest.read_bytes()).hexdigest(),
        "training_status": status,
        "game": "pokemon",
        "grader": grader,
        "used_specimens": len(rows),
        "excluded": rejected,
        "metrics": results,
        "seed": seed,
        "device": device,
        "torch": str(torch.__version__),
        "python": platform.python_version(),
        "trained_at": now(),
        "architecture": "paired_cnn_256_v1",
        "pretrained": False,
        "limitations": [
            "Small CNN baseline, not a trained defect detector",
            "No calibrated grade probabilities",
            "Economics require point-in-time sold comps",
        ],
        "split_specimens": artifact["split_specimens"],
    }
    dest.with_suffix(".json").write_text(json.dumps(report, indent=2))
    directory = dest.parent / (dest.stem + "_evaluation")
    directory.mkdir(exist_ok=True)
    for name, data in (
        ("model_card", report),
        ("training_manifest", parts),
        ("metrics", results),
        ("heldout_predictions", predictions),
        (
            "leak_check",
            {
                "status": "PASS_CONNECTED_GROUPS",
                "seed": seed,
                "splits": artifact["split_specimens"],
            },
        ),
    ):
        (directory / (name + ".json")).write_text(json.dumps(data, indent=2))
    (directory / "failure_gallery.json").write_text(
        json.dumps([r for r in predictions if not r["correct"]], indent=2)
    )
    return report


def predict(checkpoint, image_path, back_image_path=None, card_only_verified=False):
    if not back_image_path:
        return {"status": "ABSTAIN", "reason": "missing_back"}
    if not card_only_verified:
        return {"status": "ABSTAIN", "reason": "card_only_crop_not_verified"}
    torch, _, _, _ = _torch()
    c = torch.load(checkpoint, map_location="cpu", weights_only=True)
    if c.get("training_status") == "SYNTHETIC_PIPELINE_TEST":
        return {"status": "ABSTAIN", "reason": "synthetic_model_not_real_grader"}
    from .image_review import quality

    for p in (image_path, back_image_path):
        qa = quality(p)
        if qa["warnings"]:
            return {"status": "ABSTAIN", "reason": "image_quality_review", "qa": qa}
    if c.get("architecture") != "paired_cnn_256_v1":
        return {"status": "ABSTAIN", "reason": "unsupported_checkpoint"}
    model = _pair_model(len(c["labels"]))
    model.load_state_dict(c["weights"])
    model.eval()
    with torch.no_grad():
        scores = model(_pair_tensor(image_path, back_image_path)[None])[0]
    order = scores.argsort(descending=True).tolist()
    return {
        "status": "EXPERIMENTAL_UNCALIBRATED",
        "grader": c["grader"],
        "candidate_grades": [c["labels"][i] for i in order[:3]],
        "probability": None,
        "warning": "Uncalibrated outcome ranks; no certification or invisible-defect guarantee",
    }


def evaluate(checkpoint, manifest, output):
    """Re-evaluate the frozen test specimens; never re-split to improve test results."""
    from .evaluation import metrics as measure

    torch, _, _, _ = _torch()
    c = torch.load(checkpoint, map_location="cpu", weights_only=True)
    rows, rejected = _training_rows(manifest, c["grader"])
    wanted = set(c["split_specimens"]["test"])
    test = [r for r in rows if r["physical_specimen_id"] in wanted]
    if any(
        _specimen_fingerprint(r)
        != c.get("specimen_fingerprints", {}).get(r["physical_specimen_id"])
        for r in test
    ):
        raise ValueError("Frozen test specimen/target/source mapping changed")
    if set(r["physical_specimen_id"] for r in test) != wanted:
        raise ValueError("Frozen test specimens missing")
    if any(r["sha256"] not in c["source_sha256"] for r in test):
        raise ValueError("Frozen test source changed")
    if c.get("back_source_sha256") and any(
        r["back_sha256"] not in c["back_source_sha256"] for r in test
    ):
        raise ValueError("Frozen test back source changed")
    model = _pair_model(len(c["labels"]))
    model.load_state_dict(c["weights"])
    model.eval()
    truth = []
    pred = []
    with torch.no_grad():
        for r in test:
            truth.append(c["labels"].index(r["grade"]))
            pred.append(
                int(
                    model(
                        _pair_tensor(r["image_path"], r["back_image_path"])[None]
                    ).argmax(1)
                )
            )
    result = {
        "status": c["training_status"],
        "frozen_test_metrics": measure(truth, pred, c["labels"], c["grader"]),
        "checkpoint_sha256": hashlib.sha256(Path(checkpoint).read_bytes()).hexdigest(),
    }
    Path(output).write_text(json.dumps(result, indent=2))
    return result


def main(argv=None):
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command", required=True)
    tr = sub.add_parser("train")
    tr.add_argument("--manifest", required=True)
    tr.add_argument("--grader", choices=LABELS, required=True)
    tr.add_argument("--out", required=True)
    tr.add_argument("--epochs", type=int, default=4)
    pr = sub.add_parser("predict")
    pr.add_argument("--checkpoint", required=True)
    pr.add_argument("--image", required=True)
    pr.add_argument("--back")
    pr.add_argument("--card-only-verified", action="store_true")
    ev = sub.add_parser("evaluate")
    ev.add_argument("--checkpoint", required=True)
    ev.add_argument("--manifest", required=True)
    ev.add_argument("--out", required=True)
    a = p.parse_args(argv)
    if a.command == "evaluate":
        print(json.dumps(evaluate(a.checkpoint, a.manifest, a.out), indent=2))
        return
    result = (
        train(a.manifest, a.grader, a.out, a.epochs)
        if a.command == "train"
        else predict(a.checkpoint, a.image, a.back, a.card_only_verified)
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
