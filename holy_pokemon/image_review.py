"""Local image QA and reviewed derived crops. Never writes to source images."""

from __future__ import annotations
import hashlib
from pathlib import Path


def load_image(path):
    from PIL import Image, ImageOps

    Image.MAX_IMAGE_PIXELS = 40_000_000
    with Image.open(path) as im:
        if im.width * im.height > 40_000_000:
            raise ValueError("Image pixel limit")
        im.load()
        return ImageOps.exif_transpose(im).convert("RGB")


def quality(path):
    from PIL import ImageFilter, ImageStat

    im = load_image(path)
    gray = im.convert("L").resize((256, 256))
    hist = gray.histogram()
    n = sum(hist)
    bright = sum(hist[245:]) / n
    dark = sum(hist[:10]) / n
    edges = gray.filter(ImageFilter.FIND_EDGES)
    # Descriptive proxies, not validated defect detection or automatic centering.
    contrast = ImageStat.Stat(gray).stddev[0]
    edge_energy = ImageStat.Stat(edges).mean[0]
    small = gray.resize((9, 8))
    v = (
        list(small.get_flattened_data())
        if hasattr(small, "get_flattened_data")
        else list(small.getdata())
    )
    bits = 0
    for y in range(8):
        for x in range(8):
            bits = (bits << 1) | int(v[y * 9 + x] > v[y * 9 + x + 1])
    warnings = []
    if min(im.size) < 512:
        warnings.append("LOW_RESOLUTION")
    if edge_energy < 3:
        warnings.append("LOW_DETAIL_OR_BLUR")
    if bright > 0.15:
        warnings.append("BRIGHT_REGIONS_POSSIBLE_GLARE")
    if dark > 0.5:
        warnings.append("DARK_REGIONS")
    return {
        "width": im.width,
        "height": im.height,
        "edge_energy_proxy": round(edge_energy, 3),
        "bright_pixel_fraction": round(bright, 4),
        "dark_pixel_fraction": round(dark, 4),
        "contrast_proxy": round(contrast, 3),
        "dhash": f"{bits:016x}",
        "warnings": warnings,
        "centering": None,
        "defects": "UNANNOTATED",
        "note": "QA proxies do not establish physical condition; centering requires reviewed card geometry.",
    }


def reviewed_crop(source, box, destination):
    im = load_image(source)
    if len(box) != 4:
        raise ValueError("Card-only bounding box [left,top,right,bottom] required")
    x, y, r, b = map(int, box)
    if (
        not (0 <= x < r <= im.width and 0 <= y < b <= im.height)
        or min(r - x, b - y) < 128
    ):
        raise ValueError("Invalid or low-resolution crop")
    dest = Path(destination)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.resolve() == Path(source).resolve():
        raise ValueError("Cannot overwrite original")
    im.crop((x, y, r, b)).save(dest, "PNG")
    return {
        "source_sha256": hashlib.sha256(Path(source).read_bytes()).hexdigest(),
        "derived_sha256": hashlib.sha256(dest.read_bytes()).hexdigest(),
        "box": [x, y, r, b],
        "operation": "reviewed_card_only_crop_no_retouch",
        "path": str(dest),
    }
