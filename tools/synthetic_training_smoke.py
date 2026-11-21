"""Explicit SYNTHETIC execution test. Never a source of real grading metrics."""

from pathlib import Path
import csv, json, random
from PIL import Image
from holy_pokemon.vision_training import (
    train,
    evaluate,
    _pair_model,
    _pair_tensor,
    _torch,
    predict,
)

root = Path(__file__).resolve().parents[1]
out = root / "outputs/synthetic_pipeline"
out.mkdir(parents=True, exist_ok=True)
rows = []
for i in range(10):
    paths = []
    for side in ("front", "back"):
        rng = random.Random(str(i) + side)
        im = Image.frombytes(
            "RGB", (256, 256), bytes(rng.randrange(256) for _ in range(256 * 256 * 3))
        )
        path = out / f"SYNTHETIC_{i}_{side}.png"
        im.save(path)
        paths.append(str(path))
    rows.append(
        {
            "grader": "PSA",
            "grade": str(8 + i % 3),
            "original_grade": "9",
            "game": "pokemon",
            "dataset": "SYNTHETIC",
            "physical_specimen_id": f"SYNTHETIC-copy-{i}",
            "source_video_id": f"SYNTHETIC-video-{i}",
            "rights_basis": "self_photographed",
            "rights_evidence": "Locally generated random pixel test fixture; not a photograph",
            "card_only_verified": "true",
            "back_card_only_verified": "true",
            "pre_decision_visible": "true",
            "outcome_verified": "true",
            "outcome_evidence": "SYNTHETIC fixture label, not actual grading",
            "image_path": paths[0],
            "back_image_path": paths[1],
        }
    )
manifest = out / "SYNTHETIC_manifest.csv"
with manifest.open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
checkpoint = root / "local_models/synthetic_pipeline.pt"
report = train(manifest, "PSA", checkpoint, epochs=1)
result = evaluate(checkpoint, manifest, out / "SYNTHETIC_frozen_evaluation.json")
torch, _, _, _ = _torch()
c = torch.load(checkpoint, map_location="cpu", weights_only=True)
a = _pair_model(5)
b = _pair_model(5)
a.load_state_dict(c["weights"])
b.load_state_dict(c["weights"])
a.eval()
b.eval()
x = _pair_tensor(rows[0]["image_path"], rows[0]["back_image_path"])[None]
with torch.no_grad():
    assert torch.equal(a(x), b(x)), "Reload changed inference"
assert (
    predict(checkpoint, rows[0]["image_path"], rows[0]["back_image_path"], True)[
        "reason"
    ]
    == "synthetic_model_not_real_grader"
)
# Changing a frozen test target must invalidate evaluation.
changed = [dict(r) for r in rows]
for row in changed:
    if row["physical_specimen_id"] in c["split_specimens"]["test"]:
        row["grade"] = "10" if row["grade"] != "10" else "9"
        break
bad_manifest = out / "SYNTHETIC_changed_target.csv"
with bad_manifest.open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(changed[0]))
    writer.writeheader()
    writer.writerows(changed)
try:
    evaluate(checkpoint, bad_manifest, out / "SHOULD_NOT_EXIST.json")
    raise AssertionError("Changed frozen target was accepted")
except ValueError:
    pass
summary = {
    "status": "PASS_SYNTHETIC_PIPELINE_ONLY",
    "real_grading_accuracy": None,
    "checkpoint_saved": str(checkpoint),
    "checkpoint_sha256": report["checkpoint_sha256"],
    "device": report["device"],
    "train_specimens": report["metrics"]["train"]["count"],
    "validation_specimens": report["metrics"]["val"]["count"],
    "test_specimens": report["metrics"]["test"]["count"],
    "reload_exact": True,
    "changed_frozen_target_rejected": True,
    "synthetic_model_refused_for_real_inference": True,
}
(out / "execution_summary.json").write_text(json.dumps(summary, indent=2))
print(json.dumps(summary, indent=2))
