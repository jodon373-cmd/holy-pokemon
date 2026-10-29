"""Run centering-v2 against SAVED eBay audit photos, without network or AI calls.

Supports the local 645-listing audit.csv and an optional JSONL side/photo map.
The audit and source images remain on the owner's Mac and are never uploaded.
"""
from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

from .centering_v2 import VERSION, measure_file

ID_FIELDS = ("listing_id", "item_id", "ebay_item_id", "id")
ASK_FIELDS = ("ask", "asking_price", "price", "item_price", "recorded_ask")
PHOTO_FIELDS = {
    "front": ("front_path", "front_image_path", "front_image", "front_photo"),
    "back": ("back_path", "back_image_path", "back_image", "back_photo"),
}

def _first(row, fields):
    for field in fields:
        value = row.get(field)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None

def _load_rows(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        data = list(csv.DictReader(handle))
    if not data:
        raise ValueError("Audit CSV is empty")
    ids = [_first(row, ID_FIELDS) for row in data]
    if any(not x for x in ids):
        raise ValueError("Some audit rows have no usable listing ID")
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate listing IDs; cannot reconcile results")
    return dict(zip(ids, data))

def _paths(audit, image_root, photo_manifest):
    """Audit columns or explicit JSONL mapping; never download images."""
    mapped = defaultdict(lambda: defaultdict(list))
    root = Path(image_root).expanduser().resolve()
    for listing, row in audit.items():
        for side, fields in PHOTO_FIELDS.items():
            p = _first(row, fields)
            if p:
                mapped[listing][side].append({"path": p, "layout": "auto"})
    if photo_manifest:
        with Path(photo_manifest).open(encoding="utf-8") as reader:
            for line_number, line in enumerate(reader, 1):
                if not line.strip():
                    continue
                item = json.loads(line)
                listing, side, p = str(item.get("listing_id", "")), item.get("side"), item.get("path")
                if listing not in audit:
                    raise ValueError(f"Manifest line {line_number} has unknown listing ID")
                if side not in {"front", "back"} or not isinstance(p, str) or not p:
                    raise ValueError(f"Manifest line {line_number}: invalid side/path")
                mapped[listing][side].append({"path": p, "layout": item.get("layout", "auto"),
                                              "outer_quad": item.get("outer_quad")})
    for listing, sides in mapped.items():
        for side, items in sides.items():
            for item in items:
                p = Path(item["path"]).expanduser()
                if not p.is_absolute():
                    p = root / p
                p = p.resolve()
                # No arbitrary file access outside explicitly provided image root.
                if not p.is_relative_to(root):
                    raise ValueError(f"Image outside --image-root: {p}")
                item["path"] = str(p)
                if item["layout"] not in {"auto", "yellow_border", "blue_back", "unsupported_layout"}:
                    raise ValueError("Unsupported layout setting")
    return mapped

def _cache_key(path, item, stat):
    blob = json.dumps({"version": VERSION, "path": path, "size": stat.st_size,
                       "mtime_ns": stat.st_mtime_ns, "layout": item.get("layout"),
                       "side": item["side"], "outer_quad": item.get("outer_quad")}, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()

def _measurement(item, cache_dir):
    path = Path(item["path"])
    if not path.is_file():
        return {"status": "ABSTAIN", "reason": "missing_original_image", "source_path": str(path)}
    key = _cache_key(str(path), item, path.stat())
    cached = cache_dir / (key + ".json")
    if cached.is_file():
        report = json.loads(cached.read_text(encoding="utf-8"))
        if hashlib.sha256(path.read_bytes()).hexdigest() == report.get("original_sha256"):
            return report
    result = measure_file(path, side=item["side"], layout=item.get("layout", "auto"),
                          outer_quad=item.get("outer_quad"))
    cached.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result

def _select_results(observations):
    measured = [x for x in observations if x.get("status") == "MEASURED_NEEDS_VALIDATION"]
    if len(measured) > 1:
        def variance(k):
            values = [x["ratios"][k] for x in measured]
            return max(values) - min(values)
        if variance("left_pct") > 3 or variance("top_pct") > 3:
            return {"status": "ABSTAIN", "reason": "multiple_photos_disagree",
                    "observations": observations}
    if measured:
        return measured[0]
    return {"status": "ABSTAIN", "reason": "no_reliable_photo", "observations": observations}

def _price(ask):
    try:
        if ask is None:
            return None
        number = float(str(ask).replace("$", "").replace(",", ""))
        if not (0 <= number <= 1_000_000):
            return None
        return number
    except ValueError:
        return None

def _annotated_metrics(records, gold_csv):
    if not gold_csv:
        return {"status": "NOT_EVALUATED_NO_INDEPENDENT_MANUAL_GROUND_TRUTH"}
    with Path(gold_csv).open(newline="", encoding="utf-8-sig") as f:
        annotations = list(csv.DictReader(f))
    errors, missed, manual_count = [], 0, 0
    for a in annotations:
        listing, side = a.get("listing_id"), a.get("side")
        if listing not in records or side not in ("front", "back"):
            raise ValueError("Manual truth refers to absent ID/side")
        manual_count += 1
        result = records[listing]["sides"][side]
        if result.get("status") != "MEASURED_NEEDS_VALIDATION":
            missed += 1
            continue
        left = abs(float(a["left_pct"]) - result["ratios"]["left_pct"])
        top = abs(float(a["top_pct"]) - result["ratios"]["top_pct"])
        errors.append({"listing_id": listing, "side": side,
                       "left_abs_pp": round(left, 2), "top_abs_pp": round(top, 2)})
    return {
        "status": "ANNOTATION_COMPARISON_NOT_GRADE_ACCURACY", "manual_faces": manual_count,
        "measured_faces": len(errors), "abstained_faces": missed,
        "mae_left_percentage_points": round(sum(x["left_abs_pp"] for x in errors) / len(errors), 2) if errors else None,
        "mae_top_percentage_points": round(sum(x["top_abs_pp"] for x in errors) / len(errors), 2) if errors else None,
        "within_3pp_both": sum(x["left_abs_pp"] <= 3 and x["top_abs_pp"] <= 3 for x in errors),
        "errors": errors,
    }

def run(audit_csv, image_root, out_dir, *, photo_manifest=None, gold_csv=None,
        expected=645, max_default_ask=500):
    audit = _load_rows(audit_csv)
    if expected is not None and len(audit) != expected:
        raise ValueError(f"Expected {expected} listing IDs; found {len(audit)}. Stopping to prevent partial accounting")
    paths = _paths(audit, image_root, photo_manifest)
    out_dir = Path(out_dir)
    if out_dir.resolve() == Path(image_root).resolve():
        raise ValueError("Report directory must not be the original-image root")
    out_dir.mkdir(parents=True, exist_ok=True)
    cache = out_dir / "measurement_cache"
    cache.mkdir(exist_ok=True)
    records, stats = {}, Counter()
    for listing_id, source in audit.items():
        price = _price(_first(source, ASK_FIELDS))
        sides = {}
        for side in ("front", "back"):
            photos = []
            for x in paths[listing_id][side]:
                item = dict(x, side=side)
                photos.append(_measurement(item, cache))
                stats["photos_reviewed"] += 1
            sides[side] = _select_results(photos)
            stats[side + "_" + sides[side]["status"]] += 1
        both = all(sides[s]["status"] == "MEASURED_NEEDS_VALIDATION" for s in sides)
        status = "DUAL_FACE_MEASURED_UNCALIBRATED" if both else "REQUIRES_GEOMETRY_REVIEW"
        stats[status] += 1
        price_lane = ("BUDGET_UNDER_500" if price is not None and price <= max_default_ask
                      else "PREMIUM_EXCEPTION_REQUIRES_INDEPENDENT_EVIDENCE" if price is not None
                      else "ASK_UNKNOWN")
        stats[price_lane] += 1
        records[listing_id] = {
            "listing_id": listing_id, "ask_usd": price, "price_lane": price_lane,
            "sides": sides, "status": status, "surface_condition_verified": False,
            "sold_comps_verified": False, "risk_adjusted_roi": None,
            "grade_upgrade_probability": None, "financial_rank": None,
            "trade_approved": False,
        }
    metrics = _annotated_metrics(records, gold_csv)
    final = {
        "version": VERSION, "source_audit": str(audit_csv),
        "source_photo_manifest": str(photo_manifest), "listing_count": len(records),
        "stats": dict(stats), "manual_ground_truth_metrics": metrics,
        "note": "No network/APIs/paid AI. Measurements are uncalibrated until independently annotated.",
        "records": records,
    }
    (out_dir / "report.json").write_text(json.dumps(final, indent=2), encoding="utf-8")
    with (out_dir / "audit-v2.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "listing_id", "ask_usd", "price_lane", "status",
            "front_status", "front_reason", "front_left_pct", "front_top_pct",
            "back_status", "back_reason", "back_left_pct", "back_top_pct", "trade_approved"])
        writer.writeheader()
        for x in records.values():
            f, b = x["sides"]["front"], x["sides"]["back"]
            writer.writerow({
                "listing_id": x["listing_id"], "ask_usd": x["ask_usd"],
                "price_lane": x["price_lane"], "status": x["status"],
                "front_status": f["status"], "front_reason": f.get("reason"),
                "front_left_pct": (f.get("ratios") or {}).get("left_pct"),
                "front_top_pct": (f.get("ratios") or {}).get("top_pct"),
                "back_status": b["status"], "back_reason": b.get("reason"),
                "back_left_pct": (b.get("ratios") or {}).get("left_pct"),
                "back_top_pct": (b.get("ratios") or {}).get("top_pct"),
                "trade_approved": False})
    return {"listing_count": len(records), "stats": dict(stats),
            "manual_ground_truth_metrics": {k: v for k, v in metrics.items() if k != "errors"},
            "report_path": str(out_dir / "report.json")}

def main(argv=None):
    p = argparse.ArgumentParser(description="Backtest centering on saved listings; zero API/AI calls")
    p.add_argument("--audit-csv", required=True)
    p.add_argument("--image-root", required=True)
    p.add_argument("--photo-manifest", help="JSONL: listing_id,side,path,optional layout,outer_quad")
    p.add_argument("--manual-truth", help="CSV: listing_id,side,left_pct,top_pct, independently annotated")
    p.add_argument("--output", required=True)
    p.add_argument("--expected", type=int, default=645)
    p.add_argument("--max-default-ask", type=float, default=500)
    a = p.parse_args(argv)
    print(json.dumps(run(a.audit_csv, a.image_root, a.output, photo_manifest=a.photo_manifest,
                         gold_csv=a.manual_truth, expected=a.expected,
                         max_default_ask=a.max_default_ask), indent=2))

if __name__ == "__main__":
    main()
