"""Resumable original-byte inventory and bounded research ZIP intake; no source writes."""

from __future__ import annotations
import argparse
import csv
import io
import json
import re
import zipfile
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from .store import Store, ROOT, stable, now

IMAGE = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO = {".webm", ".mp4", ".mov"}


def safe_members(z):
    members = z.infolist()
    if len(members) > 20000 or sum(m.file_size for m in members) > 2_000_000_000:
        raise ValueError("Archive decompression limit")
    for m in members:
        p = PurePosixPath(m.filename)
        if (
            p.is_absolute()
            or ".." in p.parts
            or "\\" in m.filename
            or (m.external_attr >> 16) & 0o170000 == 0o120000
        ):
            raise ValueError("Unsafe ZIP member")
        if m.file_size > 100_000_000 or m.file_size / max(1, m.compress_size) > 1000:
            raise ValueError("ZIP member limit")
    return members


def normalize(row):
    """Preserve source-native facts; no guess that an observation is a unique physical copy."""
    name = next(
        (row[k] for k in ("name", "card", "card_name", "pokemon") if row.get(k)), None
    )
    grade = next(
        (row[k] for k in ("final_grade", "result_grade", "actual_grade") if row.get(k)),
        None,
    )
    return {
        "name": name,
        "variant": row.get("variant") or row.get("set"),
        "game": "one_piece"
        if any("onepiece" in str(v).lower().replace(" ", "") for v in row.values())
        else "pokemon",
        "reported_final_grade": grade,
        "original_grade_path": row.get("original_grade_path")
        or row.get("starting_grade")
        or row.get("initial_grade"),
        "cert": row.get("final_cert") or row.get("certification"),
        "specimen_id": None,
        "identity_status": "UNRESOLVED_SOURCE_OBSERVATION",
        "evidence": row.get("evidence"),
        "timestamp": row.get("video_time") or row.get("timestamp_window"),
        "value_semantics": "CREATOR_REPORTED_NOT_VERIFIED_PAYOUT",
        "raw": row,
    }


def import_pack(store, path, expected):
    sha = store.index(path, "archive", {"canonical": expected["source_label"]})
    if sha != expected["sha256"]:
        return {"name": path.name, "status": "HASH_MISMATCH", "actual": sha}
    count = 0
    with zipfile.ZipFile(path) as z:
        members = safe_members(z)
        if z.testzip():
            raise ValueError("ZIP CRC failure")
        for m in members:
            if m.filename.endswith("card_cases.csv"):
                rows = list(csv.DictReader(io.StringIO(z.read(m).decode("utf-8-sig"))))
                for n, row in enumerate(rows, 2):
                    record = normalize(row)
                    if expected["source_type"] == "cross_game_reference":
                        record["game"] = "one_piece"
                    record.update(
                        source_sha256=sha,
                        source_archive=path.name,
                        source_member=m.filename,
                        source_row=n,
                        source_label=expected["source_label"],
                    )
                    observation_id = stable(sha, m.filename, n)
                    prior = next(
                        (
                            r
                            for r in store.rows("source_record")
                            if r.get("source_sha256") == sha
                            and r.get("source_member") == m.filename
                            and r.get("raw") == row
                        ),
                        None,
                    )
                    if prior:
                        observation_id = prior["id"]
                    else:
                        store.put("source_record", observation_id, record)
                    count += 1
                    # Only explicit source certs establish deterministic specimen aliases.
                    cert = (
                        row.get("original_cert")
                        or row.get("final_cert")
                        or row.get("certification")
                    )
                    if cert and cert.isdigit():
                        original = (
                            row.get("starting_grade") or row.get("initial_grade") or ""
                        )
                        final = row.get("final_grade") or ""
                        graded = original if row.get("original_cert") else final
                        company = next(
                            (c for c in ("PSA", "CGC", "BGS", "SGC") if c in graded),
                            None,
                        )
                        if company:
                            specimen = stable("cert", company, cert)
                            if not store.get("specimen", specimen):
                                store.put(
                                    "specimen",
                                    specimen,
                                    {
                                        "name": record["name"],
                                        "game": record["game"],
                                        "cert": cert,
                                        "grader": company,
                                        "link_basis": "SOURCE_REPORTED_EXPLICIT_CERT",
                                        "independent_verification": False,
                                        "source_observation": observation_id,
                                    },
                                )
                            for stage, text in (
                                ("original", original),
                                ("later", final),
                            ):
                                match = re.search(
                                    r"(PSA|CGC|BGS|SGC)\s+(?:(Pristine|Gem Mint|Mint)\s+)?(10|[1-9](?:\.5)?)(?![0-9])",
                                    text,
                                )
                                if match:
                                    company, designation, grade = match.groups()
                                    store.put(
                                        "grading_event",
                                        stable(specimen, observation_id, stage),
                                        {
                                            "specimen_id": specimen,
                                            "company": company,
                                            "grade": grade,
                                            "designation": designation,
                                            "stage": stage,
                                            "source_observation": observation_id,
                                            "observed_at": None,
                                            "status": "CREATOR_SOURCE_REPORTED",
                                        },
                                    )
        # Images are indexed as immutable archive members; decode only on user review.
        for m in members:
            if Path(m.filename).suffix.lower() in IMAGE:
                key = stable(sha, m.filename)
                store.put(
                    "annotation",
                    key,
                    {
                        "source_archive": str(path.resolve()),
                        "source_member": m.filename,
                        "source_sha256": sha,
                        "stage": "unknown",
                        "side": "unknown",
                        "specimen_id": None,
                        "grader": None,
                        "grade": None,
                        "rights_basis": "user_supplied_private_research",
                        "card_only_verified": False,
                        "pre_decision_visible": False,
                        "status": "REQUIRES_REVIEW",
                        "size": m.file_size,
                    },
                )
        if expected["source_type"] == "aggregate_study":
            store.put(
                "aggregate",
                sha,
                {
                    "source": path.name,
                    "label": expected["source_label"],
                    "independent_training_samples": 0,
                },
            )
    return {
        "name": path.name,
        "status": "VERIFIED",
        "rows": count,
        "expected_rows": int(expected["structured_case_rows"]),
    }


def audit(dataset, search_dirs, db=None):
    source = Path(dataset).resolve(strict=True)
    with Store(db) if db else Store() as store:
        files = sorted(
            p for p in source.rglob("*") if p.is_file() and p.name != ".DS_Store"
        )
        for p in files:
            ext = p.suffix.lower()
            kind = (
                "image"
                if ext in IMAGE
                else "video"
                if ext in VIDEO
                else "archive"
                if ext == ".zip"
                else "metadata"
            )
            store.index(p, kind)
        assets = [a for a in store.assets() if Path(a["path"]).is_relative_to(source)]
        groups = defaultdict(list)
        for a in assets:
            groups[a["sha256"]].append(a["path"])
        index_rows = []
        for p in source.rglob("INDEX.csv"):
            with p.open(encoding="utf-8-sig", newline="") as f:
                for row in csv.DictReader(f):
                    frame = p.parent / row["file"]
                    if frame.is_file():
                        record = {
                            **row,
                            "path": str(frame.resolve()),
                            "source_index": str(p),
                            "stage": "unknown",
                            "side": "unknown",
                            "physical_specimen_id": None,
                            "actual_grade": None,
                            "status": "UNLINKED_FRAME_NOT_TRAINING_LABEL",
                        }
                        store.put("annotation", stable(str(frame.resolve())), record)
                        index_rows.append(record)
        for asset in assets:
            p = Path(asset["path"])
            if p.name.startswith("Fredy_Transcript_") and p.suffix.lower() == ".txt":
                video_id = p.name[len("Fredy_Transcript_") :][:11]
                text = p.read_text(encoding="utf-8-sig", errors="replace")
                store.put(
                    "transcript",
                    asset["sha256"],
                    {
                        "source_sha256": asset["sha256"],
                        "source_path": str(p),
                        "video_id": video_id,
                        "url": "https://www.youtube.com/watch?v=" + video_id,
                        "text": text,
                        "provenance": "LOCAL_CAPTURED_CAPTIONS_NOT_INDEPENDENT_OUTCOMES",
                    },
                )
        manifest = list(csv.DictReader((ROOT / "research/manifest.csv").open()))
        results = []
        for expected in manifest:
            candidate = next(
                (
                    Path(d) / expected["canonical_zip_name"]
                    for d in search_dirs
                    if (Path(d) / expected["canonical_zip_name"]).is_file()
                ),
                None,
            )
            results.append(
                import_pack(store, candidate, expected)
                if candidate
                else {"name": expected["canonical_zip_name"], "status": "MISSING"}
            )
        # Verify compact archive payloads against extracted files by their original SHA.
        compact = []
        for p in source.rglob("Fredy_Evidence_*.zip"):
            matched = 0
            missing = 0
            different = 0
            with zipfile.ZipFile(p) as z:
                for m in safe_members(z):
                    if m.is_dir():
                        continue
                    import hashlib

                    data = z.read(m)
                    candidates = [
                        p.parent / p.stem / m.filename,
                        p.parent / m.filename,
                        p.parent / "cDaaJNBQreg_visual_data" / m.filename,
                    ]
                    found = next((x for x in candidates if x.is_file()), None)
                    if found is None:
                        missing += 1
                    elif (
                        hashlib.sha256(found.read_bytes()).digest()
                        == hashlib.sha256(data).digest()
                    ):
                        matched += 1
                    else:
                        different += 1
            compact.append(
                {
                    "archive": p.name,
                    "matched_members": matched,
                    "missing_members": missing,
                    "different_members": different,
                }
            )
        report = {
            "generated_at": now(),
            "dataset": str(source),
            "source_files": len(assets),
            "bytes": sum(a["size"] for a in assets),
            "unique_sha256": len(groups),
            "by_kind": dict(Counter(a["kind"] for a in assets)),
            "exact_duplicate_groups": [v for v in groups.values() if len(v) > 1],
            "canonical_packs": results,
            "source_rows_imported": len(store.rows("source_record")),
            "local_transcript_versions": len(store.rows("transcript")),
            "local_transcript_video_ids": len(
                {r["video_id"] for r in store.rows("transcript")}
            ),
            "compact_zip_comparison": compact,
            "indexed_frame_observations": len(index_rows),
            "unique_indexed_frame_paths": len({r["path"] for r in index_rows}),
            "verified_pre_buy_photo_outcome_pairs": 0,
            "real_training_status": "BLOCKED_DATA_REVIEW",
            "unknown_fields": [
                "physical_copy_link",
                "front_back",
                "pre_buy_vs_post_crack",
                "card_only_crop",
                "later_outcome_link",
                "image_training_rights",
            ],
            "perceptual_duplicates": "PENDING_IMAGE_QA",
            "physical_specimens_verified": 0,
            "source_reported_cert_linked_specimens": len(store.rows("specimen")),
            "source_reported_grading_events": len(store.rows("grading_event")),
            "note": "Frame classifier INSPECT is a recorder heuristic, not a verified card photo or before-buy stage. No automatic photo/outcome pairing from names or timestamps alone.",
            "missing_transports": [
                "HolyPokemon_Full_Fredy_Business_Source_Transport.zip",
                "Master_Index.csv (135-photo index)",
                "28-video original transcript ZIP",
            ],
        }
        video_report = ROOT / "outputs/video_review/video_audit.json"
        if video_report.is_file():
            video_audit = json.loads(video_report.read_text())
            report["clock_sampled_source_videos"] = sum(
                v["status"] == "SAMPLED_NOT_LABELLED" for v in video_audit["videos"]
            )
            report["quarantined_video_previews"] = video_audit["preview_frames"]
            report["video_stage_status"] = (
                "CLOCK_SAMPLED_NOT_PHYSICAL_COPY_OR_CAUSAL_LABEL_VERIFICATION"
            )
        out = ROOT / "outputs/grader"
        out.mkdir(parents=True, exist_ok=True)
        (out / "dataset_audit.json").write_text(json.dumps(report, indent=2))
        (out / "dataset_audit.md").write_text(
            f"# Real source audit\n\n{len(assets)} files; {report['bytes']:,} bytes; {len(groups)} unique hashes.\n\n{report['source_rows_imported']} canonical source observations imported, not independent physical specimens.\n\nVerified pre-buy photo/outcome pairs: **0**. Real training is blocked by unresolved image stage, physical-copy/outcome linkage and card-only leakage review. Original images remain untouched.\n\nSee dataset_audit.json for missing sources, duplicates and coverage.\n"
        )
        return report


def import_transport(store, path):
    """Bounded nested ZIP intake; source SHA/name/row identities match original pack intake."""
    path = Path(path)
    known = {
        r["canonical_zip_name"]: r
        for r in csv.DictReader((ROOT / "research/manifest.csv").open())
    }
    records = []
    transcripts = []

    def visit(data, depth=0):
        if depth > 3:
            raise ValueError("Nested archive depth limit")
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            members = safe_members(z)
            if z.testzip():
                raise ValueError("Corrupt transport member")
            for member in members:
                if member.filename.endswith("source_case_rows.jsonl"):
                    for line in z.read(member).decode("utf-8-sig").splitlines():
                        if not line.strip():
                            continue
                        r = json.loads(line)
                        expected = known.get(r.get("source_archive"))
                        if (
                            not expected
                            or r.get("archive_sha256") != expected["sha256"]
                            or not isinstance(r.get("source_row"), dict)
                            or not r.get("member_path")
                            or not isinstance(r.get("row_number"), int)
                        ):
                            raise ValueError("Transport source provenance mismatch")
                        records.append(r)
                elif member.filename.endswith(".zip"):
                    visit(z.read(member), depth + 1)
                elif member.filename.endswith(".txt") and (
                    "transcript" in member.filename.lower()
                    or "video" in member.filename.lower()
                ):
                    transcripts.append(
                        {
                            "source_member": member.filename,
                            "text": z.read(member).decode(
                                "utf-8-sig", errors="replace"
                            ),
                        }
                    )

    visit(path.read_bytes())
    if len(records) != 250:
        raise ValueError(
            f"Canonical transport must have 250 source rows, got {len(records)}"
        )
    added = 0
    for r in records:
        expected = known[r["source_archive"]]
        id = stable(r["archive_sha256"], r["member_path"], r["row_number"])
        if store.get("source_record", id) or any(
            x.get("source_sha256") == r["archive_sha256"]
            and x.get("source_member") == r["member_path"]
            and x.get("raw") == r["source_row"]
            for x in store.rows("source_record")
        ):
            continue
        record = normalize(r["source_row"])
        record.update(
            source_sha256=r["archive_sha256"],
            source_archive=r["source_archive"],
            source_member=r["member_path"],
            source_row=r["row_number"],
            source_label=expected["source_label"],
        )
        if expected["source_type"] == "cross_game_reference":
            record["game"] = "one_piece"
        added += store.put("source_record", id, record)
    for r in transcripts:
        store.put(
            "transcript",
            stable(r["text"]),
            {
                **r,
                "source_archive": path.name,
                "provenance": "SUPPLEMENTAL_CAPTIONS_NOT_INDEPENDENT_SAMPLES",
            },
        )
    store.index(path, "archive", {"type": "transport"})
    return {
        "raw_rows": len(records),
        "added": added,
        "already_imported": len(records) - added,
        "transcript_members": len(transcripts),
        "physical_unique": None,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", default=str(ROOT / "research/local/fredy_results"))
    p.add_argument("--search-dir", action="append")
    p.add_argument("--db")
    p.add_argument("--transport")
    a = p.parse_args()
    if a.transport:
        with Store(a.db) if a.db else Store() as store:
            print(json.dumps(import_transport(store, a.transport), indent=2))
        return
    r = audit(a.dataset, a.search_dir or [str(Path.home() / "Downloads")], a.db)
    print(
        json.dumps(
            {k: v for k, v in r.items() if k != "exact_duplicate_groups"}, indent=2
        )
    )


if __name__ == "__main__":
    main()
