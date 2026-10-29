"""Offline geometry-aware centering baseline. Never guesses a PSA grade or upgrade odds.

Calibrate on independently hand-measured originals before promoting centering
estimates into purchase/ranking evidence. No network, tokens, or remote AI.
Requires numpy and opencv-python-headless.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Any
import cv2
import numpy as np

VERSION = "centering-v2.1.0"
TARGET_W, TARGET_H = 700, 980

@dataclass(frozen=True)
class Calibration:
    layout: str = "auto"
    width: int = TARGET_W
    height: int = TARGET_H
    min_consensus: float = 0.65
    max_relative_dispersion: float = 0.24
    min_dimension: int = 440

def _order_quad(points: np.ndarray) -> np.ndarray:
    """Physical card TL TR BR BL; reject invalid four-corner geometry."""
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

def _outer_card_candidates(bgr: np.ndarray) -> list[dict]:
    height, width = bgr.shape[:2]
    scale = min(1., 1400. / max(height, width))
    sample = (cv2.resize(bgr, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
              if scale < 1 else bgr)
    h, w = sample.shape[:2]
    gray = cv2.GaussianBlur(cv2.cvtColor(sample, cv2.COLOR_BGR2GRAY), (5, 5), 0)
    ed = cv2.Canny(gray, 45, 120)
    ed = cv2.morphologyEx(ed, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    contours, _ = cv2.findContours(ed, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    selected = []
    for c in contours:
        area = abs(cv2.contourArea(c))
        frac = area / float(w * h)
        if not .11 <= frac <= .94:
            continue
        quad = cv2.approxPolyDP(c, .025 * cv2.arcLength(c, True), True)
        if len(quad) != 4:
            continue
        try:
            p = _order_quad(quad.reshape(4, 2))
        except ValueError:
            continue
        edge_lengths = [float(np.linalg.norm(p[i] - p[(i + 1) % 4])) for i in range(4)]
        hh = .5 * (edge_lengths[1] + edge_lengths[3])
        ww = .5 * (edge_lengths[0] + edge_lengths[2])
        ratio = ww / max(hh, 1)
        if not .65 <= ratio <= .79 or min(edge_lengths) < 100:
            continue
        score = 1 - abs(ratio - 2.5 / 3.5) * 2 + min(frac, .55) * .3
        selected.append({"points": (p / scale).tolist(), "area_frac": frac, "ratio": ratio, "score": score})
    selected.sort(key=lambda x: x["score"], reverse=True)
    out = []
    for x in selected:
        if not any(abs(x["area_frac"] - y["area_frac"]) < .035 for y in out):
            out.append(x)
    return out[:8]

def _layout(image: np.ndarray, side: str, requested: str) -> str:
    if requested != "auto":
        return requested
    if side == "back":
        return "blue_back"
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    strip = max(5, image.shape[1] // 38)
    def yellow_ratio(v):
        return np.mean((v[:, :, 0] >= 17) & (v[:, :, 0] <= 38) & (v[:, :, 1] > 65))
    return ("yellow_border" if min(yellow_ratio(hsv[:, :strip, :]),
                                   yellow_ratio(hsv[:, -strip:, :])) > .55
            else "unsupported_layout")

def _first_transition(lab: np.ndarray, side: str, sample_position: float, layout: str) -> float | None:
    """Find a sustained color change; don't choose strongest internal/text edge."""
    h, w = lab.shape[:2]
    if side in ("left", "right"):
        y = int(h * sample_position)
        block = lab[max(0, y - 3):min(h, y + 4)].astype(np.float32).mean(axis=0)
        if side == "right":
            block = block[::-1]
        n = w
    else:
        x = int(w * sample_position)
        block = lab[:, max(0, x - 3):min(w, x + 4)].astype(np.float32).mean(axis=1)
        if side == "bottom":
            block = block[::-1]
        n = h
    low = max(2, int(n * .015))
    high = max(low + 2, int(n * .035))
    reference = np.median(block[low:high], axis=0)
    distances = np.linalg.norm(block - reference[None, :], axis=1)
    threshold = 27 if layout == "yellow_border" else 22
    run = max(5, int(n * .009))
    for pos in range(int(n * .025), int(n * .20) - run):
        segment = distances[pos:pos + run]
        if np.mean(segment > threshold) >= .78 and np.median(segment) >= threshold:
            return float(pos)
    return None

def _ratios(left: float, right: float, top: float, bottom: float) -> dict:
    horizontal_left = 100 * left / (left + right)
    vertical_top = 100 * top / (top + bottom)
    return {"left_pct": round(horizontal_left, 2),
            "right_pct": round(100 - horizontal_left, 2),
            "top_pct": round(vertical_top, 2),
            "bottom_pct": round(100 - vertical_top, 2),
            "left_heavy": horizontal_left > 50,
            "top_heavy": vertical_top > 50}

def _abstain(reason: str, **more: Any) -> dict:
    return {"version": VERSION, "status": "ABSTAIN", "reason": reason,
            "ratios": None, "psa_grade_prediction": None,
            "validated_psa10_upgrade_probability": None, **more}

def measure_bgr(bgr: np.ndarray, *, side: str, layout: str = "auto",
                outer_quad: list | None = None, cfg: Calibration | None = None) -> dict:
    cfg = cfg or Calibration()
    if side not in {"front", "back"}:
        raise ValueError("side must be front or back")
    if bgr is None or bgr.ndim != 3 or bgr.shape[2] != 3:
        return _abstain("unreadable_image")
    h, w = bgr.shape[:2]
    if min(h, w) < cfg.min_dimension:
        return _abstain("low_resolution", width=w, height=h)
    candidates = _outer_card_candidates(bgr) if outer_quad is None else []
    if outer_quad is None:
        if not candidates:
            return _abstain("outer_card_not_found", outer_candidates=0)
        if len(candidates) >= 2 and abs(candidates[0]["score"] - candidates[1]["score"]) < .16:
            return _abstain("outer_card_ambiguous_slab_or_frame", outer_candidates=len(candidates))
        outer_quad = candidates[0]["points"]
    try:
        quad = _order_quad(outer_quad)
    except ValueError as e:
        return _abstain(str(e))
    if (np.any(quad[:, 0] < -1) or np.any(quad[:, 1] < -1)
            or np.any(quad[:, 0] > w) or np.any(quad[:, 1] > h)):
        return _abstain("quad_outside_image")
    dest = np.array([[0, 0], [cfg.width - 1, 0], [cfg.width - 1, cfg.height - 1],
                     [0, cfg.height - 1]], dtype=np.float32)
    transform = cv2.getPerspectiveTransform(quad, dest)
    rectified = cv2.warpPerspective(bgr, transform, (cfg.width, cfg.height))
    kind = _layout(rectified, side, layout)
    if kind not in {"yellow_border", "blue_back"}:
        return _abstain("unsupported_layout_requires_reference", layout=kind, outer_quad=quad.tolist())
    lab = cv2.cvtColor(rectified, cv2.COLOR_BGR2LAB)
    samples = [0.24, 0.36, 0.50, 0.64, 0.76]
    observations = {name: [_first_transition(lab, name, s, kind) for s in samples]
                    for name in ("left", "right", "top", "bottom")}
    widths, diagnostics = {}, {}
    for name, measures in observations.items():
        good = np.array([x for x in measures if x is not None], dtype=float)
        if len(good) < max(3, int(np.ceil(len(samples) * cfg.min_consensus))):
            return _abstain(name + "_boundary_unobservable", layout=kind,
                            outer_quad=quad.tolist(), transitions=observations)
        median = float(np.median(good))
        dispersion = float(1.4826 * np.median(abs(good - median)) / max(median, 1))
        diagnostics[name] = {"n": len(good), "median": round(median, 2),
                             "relative_mad": round(dispersion, 3)}
        if dispersion > cfg.max_relative_dispersion:
            return _abstain(name + "_boundary_disagreement", layout=kind,
                            outer_quad=quad.tolist(), transitions=observations,
                            edge_diagnostics=diagnostics)
        widths[name] = median
    ratios = _ratios(*(widths[n] for n in ("left", "right", "top", "bottom")))
    if any(v < cfg.width * .015 or v > cfg.width * .20 for k, v in widths.items()
           if k in ("left", "right")):
        return _abstain("horizontal_border_implausible", layout=kind, edge_diagnostics=diagnostics)
    if any(v < cfg.height * .015 or v > cfg.height * .20 for k, v in widths.items()
           if k in ("top", "bottom")):
        return _abstain("vertical_border_implausible", layout=kind, edge_diagnostics=diagnostics)
    return {"version": VERSION, "status": "MEASURED_NEEDS_VALIDATION", "layout": kind,
            "side": side, "ratios": ratios, "outer_quad": quad.tolist(),
            "border_px_rectified": {k: round(v, 2) for k, v in widths.items()},
            "edge_diagnostics": diagnostics, "transitions": observations,
            "psa_grade_prediction": None, "validated_psa10_upgrade_probability": None}

def measure_file(image_path: str | Path, *, side: str, layout="auto",
                 outer_quad=None, cfg=None) -> dict:
    path = Path(image_path)
    if not path.is_file():
        return _abstain("missing_original_image")
    original = path.read_bytes()
    bgr = cv2.imdecode(np.frombuffer(original, np.uint8), cv2.IMREAD_COLOR)
    result = measure_bgr(bgr, side=side, layout=layout, outer_quad=outer_quad, cfg=cfg)
    result.update({"original_sha256": hashlib.sha256(original).hexdigest(),
                   "source_path": str(path), "original_bytes_unchanged": True})
    return result
