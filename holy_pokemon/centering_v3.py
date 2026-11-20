"""Centering v3: supported physical borders, perspective correction and ratios.

Automatic measurement supports blue backs and observable yellow-border fronts.
Unsupported full-art and asymmetric designs abstain rather than measuring artwork.
No final-grade or upgrade-probability predictions. No network calls.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Any, Sequence

try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except ImportError:  # pragma: no cover - pure-Python helpers still importable
    cv2 = None  # type: ignore[assignment]
    np = None  # type: ignore[assignment]
    HAS_CV2 = False

VERSION = "centering-v3.2.0"
TARGET_W, TARGET_H = 700, 980
CARD_ASPECT = 2.5 / 3.5  # ~0.7143


@dataclass(frozen=True)
class CalibrationV3:
    layout: str = "auto"
    width: int = TARGET_W
    height: int = TARGET_H
    min_consensus: float = 0.55
    max_relative_dispersion: float = 0.22
    min_dimension: int = 240
    min_laplacian_var: float = 35.0
    max_keystone_skew: float = 0.18
    slab_aware: bool = True


def compute_ratios(left: float, right: float, top: float, bottom: float) -> dict[str, Any]:
    """Compute horizontal and vertical centering percentages from border widths."""
    import math
    if not all(math.isfinite(v) for v in (left, right, top, bottom)) or min(left, right, top, bottom) <= 0:
        raise ValueError("Border widths must be positive")
    h_left = 100.0 * left / (left + right)
    v_top = 100.0 * top / (top + bottom)
    h_right = 100.0 - h_left
    v_bottom = 100.0 - v_top
    max_h = max(h_left, h_right)
    max_v = max(v_top, v_bottom)
    return {
        "left_pct": round(h_left, 2),
        "right_pct": round(h_right, 2),
        "top_pct": round(v_top, 2),
        "bottom_pct": round(v_bottom, 2),
        "max_horizontal_pct": round(max_h, 2),
        "max_vertical_pct": round(max_v, 2),
        "worst_pct": round(max(max_h, max_v), 2),
        "left_heavy": h_left > 50.0,
        "top_heavy": v_top > 50.0,
    }


def centering_eligibility(
    front_ratios: dict[str, Any] | None,
    back_ratios: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate geometric centering bands only (NOT a grade prediction).

    These are experimental screening thresholds, not verified current grading
    standards. The 50.5 Pristine tolerance is a local heuristic. Both sides and
    independently validated geometry are required before interpreting a band.
    """
    if not front_ratios:
        return {
            "threshold_status": "EXPERIMENTAL_UNVERIFIED_SCREENING_HEURISTICS",
        "geometry_only_check": True,
            "grade_prediction": None,
            "centering_score": None,
            "bands": {},
        }
    f_worst = max(
        float(front_ratios.get("max_horizontal_pct", max(front_ratios["left_pct"], front_ratios["right_pct"]))),
        float(front_ratios.get("max_vertical_pct", max(front_ratios["top_pct"], front_ratios["bottom_pct"]))),
    )
    b_worst = None
    if back_ratios:
        b_worst = max(
            float(back_ratios.get("max_horizontal_pct", max(back_ratios["left_pct"], back_ratios["right_pct"]))),
            float(back_ratios.get("max_vertical_pct", max(back_ratios["top_pct"], back_ratios["bottom_pct"]))),
        )

    def _ok(f_max: float, b_max: float | None = None) -> bool | None:
        if f_worst > f_max:
            return False
        if b_max is not None and b_worst is None:
            return None  # front passes, back not yet measured
        if b_max is not None and b_worst is not None:
            return b_worst <= b_max
        return True

    # Score: 100 at 50/50, 0 at >= 75/25
    front_dev = max(0.0, f_worst - 50.0)
    score = max(0.0, round(100.0 - front_dev * 4.0, 1))
    if b_worst is not None:
        back_dev = max(0.0, b_worst - 50.0)
        score = round(0.75 * score + 0.25 * max(0.0, 100.0 - back_dev * 2.5), 1)

    return {
        "threshold_status": "EXPERIMENTAL_UNVERIFIED_SCREENING_HEURISTICS",
        "geometry_only_check": True,
        "grade_prediction": None,
        "front_worst_pct": round(f_worst, 2),
        "back_worst_pct": round(b_worst, 2) if b_worst is not None else None,
        "centering_score": score,
        "bands": {
            "psa_10_centering_band": _ok(55.0, 75.0),
            "cgc_gem_10_centering_band": _ok(55.0, 75.0),
            "cgc_pristine_10_centering_band": _ok(50.5, 55.0),
            "bgs_9_5_centering_band": _ok(55.0, 60.0),
            "psa_9_centering_band": _ok(60.0, 90.0),
        },
    }


def keystone_distortion_score(quad: Sequence[Sequence[float]]) -> float:
    """Measure perspective skew of a 4-point quad (TL, TR, BR, BL). 0 = rectangle."""
    if len(quad) != 4:
        raise ValueError("Quad must have 4 points")
    pts = [(float(p[0]), float(p[1])) for p in quad]

    def dist(a: tuple[float, float], b: tuple[float, float]) -> float:
        return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5

    top = dist(pts[0], pts[1])
    right = dist(pts[1], pts[2])
    bottom = dist(pts[2], pts[3])
    left = dist(pts[3], pts[0])
    d1 = dist(pts[0], pts[2])
    d2 = dist(pts[1], pts[3])
    h_skew = abs(top - bottom) / max(top, bottom, 1e-6)
    v_skew = abs(left - right) / max(left, right, 1e-6)
    d_skew = abs(d1 - d2) / max(d1, d2, 1e-6)
    return round(max(h_skew, v_skew, d_skew), 4)


def quad_bbox_iou(q1: Sequence[Sequence[float]], q2: Sequence[Sequence[float]]) -> float:
    """Fast bounding-box IoU between two quads for detector consensus."""
    def bbox(q: Sequence[Sequence[float]]) -> tuple[float, float, float, float]:
        xs = [float(p[0]) for p in q]
        ys = [float(p[1]) for p in q]
        return min(xs), min(ys), max(xs), max(ys)

    ax1, ay1, ax2, ay2 = bbox(q1)
    bx1, by1, bx2, by2 = bbox(q2)
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    return round(inter / union, 4) if union > 0 else 0.0


def _require_cv2() -> None:
    if not HAS_CV2:
        raise RuntimeError("opencv-python-headless and numpy are required for image centering")


def _order_quad(points: Any) -> Any:
    _require_cv2()
    p = np.asarray(points, dtype=np.float32).reshape(4, 2)
    if not np.isfinite(p).all():
        raise ValueError("nonfinite_outer_quad")
    y_idx = np.argsort(p[:, 1])
    top = p[y_idx[:2]][np.argsort(p[y_idx[:2], 0])]
    bottom = p[y_idx[2:]][np.argsort(p[y_idx[2:], 0])]
    out = np.array([top[0], top[1], bottom[1], bottom[0]], dtype=np.float32)
    if abs(cv2.contourArea(out)) < 400:
        raise ValueError("degenerate_outer_quad")
    if not cv2.isContourConvex(out.reshape(-1, 1, 2)):
        raise ValueError("nonconvex_outer_quad")
    return out


def _extract_quads_from_binary(binary: Any, w: int, h: int, scale: float, detector: str) -> list[dict[str, Any]]:
    contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    out = []
    for c in contours:
        area = abs(cv2.contourArea(c))
        frac = area / float(w * h)
        if not 0.10 <= frac <= 0.94:
            continue
        quad = cv2.approxPolyDP(c, 0.024 * cv2.arcLength(c, True), True)
        if len(quad) != 4:
            continue
        try:
            p = _order_quad(quad.reshape(4, 2))
        except ValueError:
            continue
        edges = [float(np.linalg.norm(p[i] - p[(i + 1) % 4])) for i in range(4)]
        hh = 0.5 * (edges[1] + edges[3])
        ww = 0.5 * (edges[0] + edges[2])
        ratio = ww / max(hh, 1.0)
        if not 0.63 <= ratio <= 0.80 or min(edges) < 90:
            continue
        pts_full = (p / scale).tolist()
        skew = keystone_distortion_score(pts_full)
        aspect_score = 1.0 - abs(ratio - CARD_ASPECT) * 2.2
        area_score = min(frac, 0.60) * 0.25
        skew_penalty = skew * 0.4
        score = aspect_score + area_score - skew_penalty
        out.append({
            "points": pts_full,
            "area_frac": round(frac, 4),
            "ratio": round(ratio, 4),
            "skew": skew,
            "score": round(score, 4),
            "detector": detector,
        })
    return out


def _outer_card_candidates_v3(bgr: Any, *, slab_aware: bool = True) -> tuple[list[dict[str, Any]], bool]:
    """Dual-detector consensus (Canny + Adaptive Threshold) with slab-aware inner detection."""
    _require_cv2()
    height, width = bgr.shape[:2]
    scale = min(1.0, 1400.0 / max(height, width))
    sample = (
        cv2.resize(bgr, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        if scale < 1.0
        else bgr
    )
    h, w = sample.shape[:2]
    gray = cv2.GaussianBlur(cv2.cvtColor(sample, cv2.COLOR_BGR2GRAY), (5, 5), 0)

    # Detector 1: Multi-threshold Canny
    ed1 = cv2.Canny(gray, 35, 110)
    ed1 = cv2.morphologyEx(ed1, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    cands_canny = _extract_quads_from_binary(ed1, w, h, scale, "canny")

    # Detector 2: Adaptive threshold + morphological edge
    adap = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 21, 5
    )
    adap = cv2.morphologyEx(adap, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    cands_adap = _extract_quads_from_binary(adap, w, h, scale, "adaptive")

    # Merge with consensus bonus when both detectors agree (IoU >= 0.85)
    merged: list[dict[str, Any]] = []
    for c in cands_canny + cands_adap:
        matched = False
        for m in merged:
            if quad_bbox_iou(c["points"], m["points"]) >= 0.85:
                matched = True
                if c["detector"] != m["detector"] and not m["consensus"]:
                    m["consensus"] = True
                    m["score"] = round(max(m["score"], c["score"]) + 0.18, 4)
                break
        if not matched:
            merged.append({**c, "consensus": False})

    merged.sort(key=lambda x: x["score"], reverse=True)

    # Slab-aware check: if top candidate encloses a smaller valid card quad (0.45..0.85 area ratio)
    slab_detected = False
    if slab_aware and len(merged) >= 2:
        outer = merged[0]
        for inner in merged[1:]:
            area_ratio = inner["area_frac"] / max(outer["area_frac"], 1e-6)
            if 0.45 <= area_ratio <= 0.86 and quad_bbox_iou(outer["points"], inner["points"]) >= 0.45:
                # Inner quad is nested inside the outer slab quad; prefer inner card
                slab_detected = True
                inner["score"] = round(outer["score"] + 0.05, 4)
                inner["slab_inner_card"] = True
                merged.sort(key=lambda x: x["score"], reverse=True)
                break

    return merged[:8], slab_detected


def _refine_corners_subpixel(bgr: Any, quad: Any) -> Any:
    """Refine quad corners at full resolution using cv2.cornerSubPix."""
    _require_cv2()
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    corners = np.asarray(quad, dtype=np.float32).reshape(-1, 1, 2)
    h, w = gray.shape[:2]
    # Keep corners safely inside image bounds for cornerSubPix window
    corners[:, 0, 0] = np.clip(corners[:, 0, 0], 6, w - 7)
    corners[:, 0, 1] = np.clip(corners[:, 0, 1], 6, h - 7)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 25, 0.05)
    refined = cv2.cornerSubPix(gray, corners, (5, 5), (-1, -1), criteria)
    return _order_quad(refined.reshape(4, 2))


def _detect_layout_v3(image: Any, side: str, requested: str) -> str:
    if requested != "auto":
        return requested
    if side == "back":
        return "blue_back"
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    strip = max(5, image.shape[1] // 38)
    left_s = hsv[:, :strip, :]
    right_s = hsv[:, -strip:, :]

    def _frac(mask_fn: Any) -> float:
        return min(float(np.mean(mask_fn(left_s))), float(np.mean(mask_fn(right_s))))

    yellow = _frac(lambda v: (v[:, :, 0] >= 17) & (v[:, :, 0] <= 38) & (v[:, :, 1] > 65))
    if yellow > 0.50:
        return "yellow_border"
    silver = _frac(lambda v: (v[:, :, 1] < 48) & (v[:, :, 2] > 145))
    if silver > 0.55:
        return "silver_border"
    dark = _frac(lambda v: (v[:, :, 2] < 72))
    if dark > 0.55:
        return "dark_border"
    return "unsupported_layout"


def _transition_v3(lab: Any, grad_mag: Any, side: str, sample_pos: float, layout: str) -> float | None:
    """Dual-signal transition: LAB color jump corroborated by Sobel gradient."""
    h, w = lab.shape[:2]
    if side in ("left", "right"):
        y = int(h * sample_pos)
        block = lab[max(0, y - 3):min(h, y + 4)].astype(np.float32).mean(axis=0)
        g_line = grad_mag[max(0, y - 3):min(h, y + 4)].mean(axis=0)
        if side == "right":
            block = block[::-1]
            g_line = g_line[::-1]
        n = w
    else:
        x = int(w * sample_pos)
        block = lab[:, max(0, x - 3):min(w, x + 4)].astype(np.float32).mean(axis=1)
        g_line = grad_mag[:, max(0, x - 3):min(w, x + 4)].mean(axis=1)
        if side == "bottom":
            block = block[::-1]
            g_line = g_line[::-1]
        n = h

    low = max(2, int(n * (0.005 if layout == "yellow_border" else 0.015)))
    high = max(low + 2, int(n * (0.015 if layout == "yellow_border" else 0.035)))
    reference = np.median(block[low:high], axis=0)
    distances = np.linalg.norm(block - reference[None, :], axis=1)

    thresholds = {
        "yellow_border": 26.0,
        "silver_border": 18.0,
        "dark_border": 20.0,
        "blue_back": 22.0,
    }
    threshold = thresholds.get(layout, 22.0)
    run = max(5, int(n * 0.009))
    for pos in range(int(n * (0.015 if layout == "yellow_border" else 0.022)), int(n * (0.085 if layout == "yellow_border" else 0.20)) - run):
        segment = distances[pos:pos + run]
        if np.mean(segment > threshold) >= 0.78 and np.median(segment) >= threshold:
            # Refine to nearest local gradient peak within +/- 3 px if strong
            win_lo = max(low, pos - 3)
            win_hi = min(n - 1, pos + 4)
            local_g = g_line[win_lo:win_hi]
            if local_g.size > 0 and float(np.max(local_g)) > 18.0:
                return float(win_lo + int(np.argmax(local_g)))
            return float(pos)
    return None


def _abstain(reason: str, **more: Any) -> dict[str, Any]:
    return {
        "version": VERSION,
        "status": "ABSTAIN",
        "reason": reason,
        "ratios": None,
        "eligibility": None,
        "psa_grade_prediction": None,
        "validated_psa10_upgrade_probability": None,
        **more,
    }


def measure_bgr(
    bgr: Any,
    *,
    side: str,
    layout: str = "auto",
    outer_quad: list | None = None,
    cfg: CalibrationV3 | None = None,
) -> dict[str, Any]:
    _require_cv2()
    cfg = cfg or CalibrationV3()
    if side not in {"front", "back"}:
        raise ValueError("side must be front or back")
    if bgr is None or bgr.ndim != 3 or bgr.shape[2] != 3:
        return _abstain("unreadable_image")
    h, w = bgr.shape[:2]
    if min(h, w) < cfg.min_dimension:
        return _abstain("low_resolution", width=w, height=h)

    gray_full = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    blur_var = float(cv2.Laplacian(gray_full, cv2.CV_64F).var())
    if blur_var < cfg.min_laplacian_var:
        return _abstain("image_too_blurry", laplacian_var=round(blur_var, 2))

    slab_detected = False
    detector_consensus = False
    if outer_quad is None:
        from .centering_geometry import detect_outer
        geometry = detect_outer(bgr, side, layout)
        if geometry.get("status") == "ABSTAIN":
            return _abstain(geometry["reason"], geometry_diagnostics=geometry)
        outer_quad = geometry["outer_quad"]
        detector_consensus = True

    try:
        quad = _order_quad(outer_quad)
        if np.any(quad[:, 0] < 0) or np.any(quad[:, 1] < 0) or np.any(quad[:, 0] >= w) or np.any(quad[:, 1] >= h):
            return _abstain("quad_outside_image")
        # Physical corners are intersections of straight edges, not rounded tips.
    except ValueError as e:
        return _abstain(str(e))

    skew = keystone_distortion_score(quad.tolist())
    if skew > cfg.max_keystone_skew:
        return _abstain("severe_perspective_distortion", keystone_skew=skew, outer_quad=quad.tolist())

    if (
        np.any(quad[:, 0] < -1)
        or np.any(quad[:, 1] < -1)
        or np.any(quad[:, 0] > w + 1)
        or np.any(quad[:, 1] > h + 1)
    ):
        return _abstain("quad_outside_image")

    dest = np.array(
        [[0, 0], [cfg.width - 1, 0], [cfg.width - 1, cfg.height - 1], [0, cfg.height - 1]],
        dtype=np.float32,
    )
    transform = cv2.getPerspectiveTransform(quad, dest)
    rectified = cv2.warpPerspective(bgr, transform, (cfg.width, cfg.height))
    kind = _detect_layout_v3(rectified, side, layout)
    if kind not in {"yellow_border", "silver_border", "dark_border", "blue_back"}:
        return _abstain("unsupported_layout_requires_reference", layout=kind, outer_quad=quad.tolist())

    lab = cv2.cvtColor(rectified, cv2.COLOR_BGR2LAB)
    rect_gray = cv2.cvtColor(rectified, cv2.COLOR_BGR2GRAY)
    gx = cv2.Sobel(rect_gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(rect_gray, cv2.CV_32F, 0, 1, ksize=3)
    grad_mag = cv2.magnitude(gx, gy)

    samples = [0.18, 0.26, 0.34, 0.42, 0.50, 0.58, 0.66, 0.74, 0.82]
    observations = {
        name: [_transition_v3(lab, grad_mag, name, s, kind) for s in samples]
        for name in ("left", "right", "top", "bottom")
    }
    widths, diagnostics = {}, {}
    for name, measures in observations.items():
        good = np.array([x for x in measures if x is not None], dtype=float)
        if len(good) < max(4, int(np.ceil(len(samples) * cfg.min_consensus))):
            return _abstain(
                name + "_boundary_unobservable",
                layout=kind,
                outer_quad=quad.tolist(),
                transitions=observations,
            )
        median = float(np.median(good))
        dispersion = float(1.4826 * np.median(np.abs(good - median)) / max(median, 1.0))
        diagnostics[name] = {
            "n": len(good),
            "median": round(median, 2),
            "relative_mad": round(dispersion, 3),
        }
        if dispersion > cfg.max_relative_dispersion:
            return _abstain(
                name + "_boundary_disagreement",
                layout=kind,
                outer_quad=quad.tolist(),
                transitions=observations,
                edge_diagnostics=diagnostics,
            )
        widths[name] = median

    if side == "front" and (widths["left"] > cfg.width*.075 or widths["right"] > cfg.width*.075 or widths["top"] > cfg.height*.075 or widths["bottom"] > cfg.height*.075):
        return _abstain("asymmetric_or_unsupported_front_design", outer_quad=quad.tolist(), edge_diagnostics=diagnostics)
    ratios = compute_ratios(*(widths[n] for n in ("left", "right", "top", "bottom")))
    if any(v < cfg.width * 0.015 or v > cfg.width * 0.20 for k, v in widths.items() if k in ("left", "right")):
        return _abstain("horizontal_border_implausible", layout=kind, edge_diagnostics=diagnostics)
    if any(v < cfg.height * 0.015 or v > cfg.height * 0.20 for k, v in widths.items() if k in ("top", "bottom")):
        return _abstain("vertical_border_implausible", layout=kind, edge_diagnostics=diagnostics)

    inner_rect = np.float32([[[widths["left"], widths["top"]], [cfg.width-1-widths["right"], widths["top"]], [cfg.width-1-widths["right"], cfg.height-1-widths["bottom"]], [widths["left"], cfg.height-1-widths["bottom"]]]])
    inner_quad = cv2.perspectiveTransform(inner_rect, np.linalg.inv(transform))[0].tolist()
    elig = centering_eligibility(ratios if side == "front" else None, ratios if side == "back" else None)
    return {
        "version": VERSION,
        "status": "MEASURED_NEEDS_VALIDATION",
        "layout": kind,
        "side": side,
        "ratios": ratios,
        "eligibility": elig,
        "slab_detected": slab_detected,
        "detector_consensus": detector_consensus,
        "keystone_skew": skew,
        "laplacian_var": round(blur_var, 2),
        "outer_quad": quad.tolist(),
        "inner_quad": inner_quad,
        "border_px_rectified": {k: round(v, 2) for k, v in widths.items()},
        "edge_diagnostics": diagnostics,
        "transitions": observations,
        "psa_grade_prediction": None,
        "validated_psa10_upgrade_probability": None,
    }


def measure_file(
    image_path: str | Path,
    *,
    side: str,
    layout: str = "auto",
    outer_quad: list | None = None,
    cfg: CalibrationV3 | None = None,
) -> dict[str, Any]:
    _require_cv2()
    path = Path(image_path)
    if not path.is_file():
        return _abstain("missing_original_image")
    original = path.read_bytes()
    bgr = cv2.imdecode(np.frombuffer(original, np.uint8), cv2.IMREAD_COLOR)
    result = measure_bgr(bgr, side=side, layout=layout, outer_quad=outer_quad, cfg=cfg)
    result.update({
        "original_sha256": hashlib.sha256(original).hexdigest(),
        "source_path": str(path),
        "original_bytes_unchanged": True,
    })
    return result
