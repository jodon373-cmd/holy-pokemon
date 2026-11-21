"""Private, resumable video evidence sampling using recorder clock synchronization.

Preview frames are review aids, not eligible training images. No source is modified.
"""

from __future__ import annotations
import argparse
import bisect
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from PIL import Image, ImageDraw
from .store import Store, ROOT, stable, now


def clock_points(meta):
    start = meta["captureStartMs"]
    points = sorted(
        ((r["wallMs"] - start) / 1000, float(r["videoTime"]))
        for r in meta.get("clockSync", [])
    )
    if len(points) < 2:
        raise ValueError("Recorder clock synchronization missing")
    return points


def interpolate(points, x, *, reverse=False):
    if reverse:
        points = sorted((b, a) for a, b in points)
    if x < points[0][0] or x > points[-1][0]:
        raise ValueError("Outside recorded clock coverage")
    i = max(1, bisect.bisect_left([p[0] for p in points], x))
    i = min(i, len(points) - 1)
    a, b = points[i - 1], points[i]
    return a[1] + (x - a[0]) / (b[0] - a[0]) * (b[1] - a[1]) if b[0] != a[0] else a[1]


def frame_at(path, seconds):
    import av

    with av.open(str(path)) as c:
        stream = c.streams.video[0]
        stream.thread_type = "AUTO"
        c.seek(max(0, int(seconds * av.time_base)), backward=True)
        for frame in c.decode(stream):
            if frame.time is not None and float(frame.time) >= seconds:
                return frame.to_image(), float(frame.time)
    raise ValueError("Requested timestamp outside decoded recording")


def sample_all(dataset, *, step=30, max_frames=60):
    if not 10 <= step <= 300 or not 1 <= max_frames <= 200:
        raise ValueError("Bounded sample interval/frame count required")
    directory = Path(dataset).resolve(strict=True)
    videos = defaultdict(list)
    for p in directory.glob("Fredy_Video_*.webm"):
        videos[p.name[len("Fredy_Video_") :][:11]].append(p)
    metadata = {}
    for p in directory.glob("Fredy_Meta_*.txt"):
        try:
            r = json.loads(p.read_text())
            metadata[int(r["captureStartMs"])] = r
        except (ValueError, KeyError):
            continue
    report = {
        "generated_at": now(),
        "videos": [],
        "preview_frames": 0,
        "originals_modified": False,
        "training_pairs_created": 0,
    }
    out = ROOT / "outputs/video_review"
    out.mkdir(parents=True, exist_ok=True)
    with Store() as store:
        for video_id, options in sorted(videos.items()):
            # Prefer verified recorder clock coverage over file size: a frozen capture can be larger.
            def coverage(path):
                try:
                    capture = int(path.stem.rsplit("_", 1)[1])
                    points = clock_points(metadata[capture])
                    return max(y for _, y in points) - min(
                        y for _, y in points
                    ), path.stat().st_size
                except (KeyError, ValueError):
                    return 0, path.stat().st_size

            p = max(options, key=coverage)
            try:
                capture = int(p.stem.rsplit("_", 1)[1])
                meta = metadata.get(capture)
                if not meta:
                    raise ValueError("Matching recorder metadata missing")
                points = clock_points(meta)
                source_sha = store.index(p, "video")
                rows = []
                start = int(points[0][1] // step + 1) * step
                for source_seconds in list(range(start, int(points[-1][1]), step))[
                    :max_frames
                ]:
                    id = stable(source_sha, source_seconds, "preview720_v1")
                    prior = store.get("video_frame", id)
                    if prior:
                        rows.append(prior)
                        continue
                    recorded = interpolate(points, source_seconds, reverse=True)
                    im, actual = frame_at(p, recorded)
                    original_size = list(im.size)
                    im.thumbnail((720, 450))
                    path = out / video_id / f"{id}.jpg"
                    path.parent.mkdir(parents=True, exist_ok=True)
                    im.save(path, "JPEG", quality=85)
                    row = {
                        "id": id,
                        "video_id": video_id,
                        "source_video": str(p),
                        "source_sha256": source_sha,
                        "source_seconds_estimated": source_seconds,
                        "requested_recording_seconds": recorded,
                        "decoded_recording_seconds": actual,
                        "original_size": original_size,
                        "preview_path": str(path),
                        "preview_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        "clock_mapping": "RECORDER_CLOCK_INTERPOLATED_REQUIRES_TEMPORAL_REVIEW",
                        "stage": "UNKNOWN",
                        "side": "UNKNOWN",
                        "physical_specimen_id": None,
                        "actual_outcome": None,
                        "training_allowed": False,
                        "exclusion": "PREVIEW_ONLY_STAGE_SPECIMEN_OUTCOME_AND_LABEL_MASK_UNREVIEWED",
                    }
                    store.put("video_frame", id, row)
                    rows.append(row)
                if not rows:
                    raise ValueError(
                        "No usable clock-mapped samples; inspect recapture metadata"
                    )
                sheet = Image.new(
                    "RGB", (720, 130 * ((len(rows) + 3) // 4)), (12, 20, 36)
                )
                draw = ImageDraw.Draw(sheet)
                for i, row in enumerate(rows):
                    with Image.open(row["preview_path"]) as image:
                        image.thumbnail((174, 104))
                        x = (i % 4) * 180
                        y = (i // 4) * 130
                        sheet.paste(image, (x, y))
                        draw.text(
                            (x + 3, y + 106),
                            f"source ~{row['source_seconds_estimated']}s",
                            fill="white",
                        )
                sheet.save(out / f"{video_id}_CONTACT.jpg", quality=88)
                report["preview_frames"] += len(rows)
                report["videos"].append(
                    {
                        "video_id": video_id,
                        "recaptures": len(options),
                        "selected_original": p.name,
                        "selection": "maximum_recorder_clock_coverage_not_completeness_proof",
                        "source_duration_claim": meta.get("videoDurationSeconds"),
                        "clock_coverage_seconds": [points[0][1], points[-1][1]],
                        "frames": len(rows),
                        "contact_sheet": str(out / f"{video_id}_CONTACT.jpg"),
                        "status": "SAMPLED_NOT_LABELLED",
                    }
                )
                print(
                    video_id,
                    len(rows),
                    "review previews; no training labels",
                    flush=True,
                )
            except Exception as exc:
                report["videos"].append(
                    {"video_id": video_id, "status": "FAILED", "error": str(exc)}
                )
            (out / "video_audit.json").write_text(json.dumps(report, indent=2))
    return report


def full_frame(store, id):
    row = store.get("video_frame", id)
    if not row:
        raise ValueError("Unknown video evidence frame")
    if store.index(row["source_video"], "video") != row["source_sha256"]:
        raise ValueError("Source recording changed; re-audit before decoding")
    path = ROOT / "outputs/video_review/full" / f"{id}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.is_file():
        im, actual = frame_at(row["source_video"], row["decoded_recording_seconds"])
        im.save(path, "PNG")
    store.index(
        path,
        "image",
        {
            "decoded_from": row["source_sha256"],
            "decoded_pts": row["decoded_recording_seconds"],
            "stage": "UNKNOWN",
            "physical_copy": "UNKNOWN",
            "transform": "lossless_encoding_of_decoded_original_video_frame_no_retouch",
        },
    )
    return {
        "id": stable(str(path.resolve())),
        "path": str(path),
        "source_video_id": row["video_id"],
        "stage": "UNKNOWN",
        "outcome": None,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", default=str(ROOT / "research/local/fredy_results"))
    p.add_argument("--step", type=int, default=30)
    p.add_argument("--max-frames", type=int, default=60)
    a = p.parse_args()
    r = sample_all(a.dataset, step=a.step, max_frames=a.max_frames)
    print(
        json.dumps(
            {
                "videos": len(r["videos"]),
                "review_previews": r["preview_frames"],
                "training_pairs": 0,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
