"""Measured categorical and ordinal metrics; missing economics stay unknown."""

from __future__ import annotations
import math
from collections import defaultdict


def metrics(truth, prediction, labels, grader):
    if not truth or len(truth) != len(prediction):
        raise ValueError("Nonempty aligned predictions required")
    cm = [[0] * len(labels) for _ in labels]
    for t, p in zip(truth, prediction):
        cm[t][p] += 1
    rows = []
    for i, label in enumerate(labels):
        tp = cm[i][i]
        actual = sum(cm[i])
        pred = sum(r[i] for r in cm)
        precision = tp / pred if pred else 0
        recall = tp / actual if actual else 0
        rows.append(
            {
                "label": label,
                "n": actual,
                "predicted_count": pred,
                "precision": precision,
                "recall": recall,
                "f1": 2 * precision * recall / (precision + recall)
                if precision + recall
                else 0,
            }
        )
    numeric = lambda i: float(labels[i].replace("Pristine ", ""))
    errors = [numeric(p) - numeric(t) for t, p in zip(truth, prediction)]
    correct = sum(t == p for t, p in zip(truth, prediction))
    n = len(truth)
    rate = correct / n
    # Wilson interval for heldout categorical accuracy (small-n visibly broad).
    z = 1.96
    den = 1 + z * z / n
    center = (rate + z * z / (2 * n)) / den
    half = z * math.sqrt(rate * (1 - rate) / n + z * z / (4 * n * n)) / den
    result = {
        "count": n,
        "accuracy": rate,
        "accuracy_wilson95": [max(0, center - half), min(1, center + half)],
        "confusion_matrix": cm,
        "labels": labels,
        "per_class": rows,
        "macro_f1": sum(r["f1"] for r in rows if r["n"] or r["predicted_count"])
        / sum(bool(r["n"] or r["predicted_count"]) for r in rows),
        "grade_mae": sum(abs(e) for e in errors) / n,
        "within_one_grade": sum(abs(e) <= 1 for e in errors) / n,
        "severe_overgrade_rate": sum(e >= 2 for e in errors) / n,
        "calibration": "NOT_ESTABLISHED",
        "financial_backtest": {
            "status": "UNAVAILABLE_WITHOUT_POINT_IN_TIME_COMPS_AND_COSTS",
            "net": None,
        },
    }
    if grader == "PSA" and "10" in labels:
        ten = labels.index("10")
        neg = sum(t != ten for t in truth)
        false = sum(p == ten and t != ten for t, p in zip(truth, prediction))
        result["psa10_false_positives"] = false
        result["psa10_false_positive_rate"] = false / neg if neg else None
    return result


def connected_split(rows, seed=73):
    """Connected videos/specimens/certs/fingerprints; no random frame split."""
    import random

    parent = list(range(len(rows)))

    def root(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    seen = {}
    for i, r in enumerate(rows):
        for field in (
            "source_video_id",
            "physical_specimen_id",
            "cert",
            "duplicate_group",
            "perceptual_group",
            "source_bundle",
            "sha256",
            "back_sha256",
        ):
            v = r.get(field)
            if not v:
                continue
            key = ("image" if field in ("sha256", "back_sha256") else field, v)
            if key in seen:
                parent[root(i)] = root(seen[key])
            else:
                seen[key] = i
    groups = defaultdict(list)
    for i, r in enumerate(rows):
        groups[root(i)].append(r)
    keys = sorted(groups)
    if len(keys) < 5:
        raise ValueError("At least five independent connected source groups needed")
    random.Random(seed).shuffle(keys)
    n = max(1, round(len(keys) * 0.2))
    parts = {"train": [], "val": [], "test": []}
    for j, k in enumerate(keys):
        parts["test" if j < n else "val" if j < 2 * n else "train"].extend(groups[k])
    return parts
