"""Local application operations; no trading actions, remote image uploads or secret serialization."""

from __future__ import annotations
import base64
import csv
import io
import json
import os
import subprocess
import sys
import threading
import zipfile
from pathlib import Path
from .store import ROOT, stable, now
from .market import provider_status, rank_leads, import_rows, sales_summary
from .vault_workflow import collection, record_transition, record_payout, compare_exits
from .strategy_engine import budget_check
from .image_review import quality, reviewed_crop

JOBS = {}
LOCK = threading.Lock()


def asset_path(store, id):
    a = next(
        (a for a in store.assets() if a["id"] == id and a["kind"] == "image"), None
    )
    if a:
        return Path(a["path"])
    frame = store.get("video_frame", id)
    if frame:
        return Path(frame["preview_path"])
    r = store.get("annotation", id)
    if r and r.get("source_archive") and r.get("source_member"):
        from .ingest import safe_members

        path = ROOT / "outputs/cache" / id / Path(r["source_member"]).name
        if not path.is_file():
            with zipfile.ZipFile(r["source_archive"]) as z:
                safe_members(z)
                info = z.getinfo(r["source_member"])
                if info.file_size > 20_000_000:
                    raise ValueError("Image member limit")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(z.read(info))
        return path
    raise ValueError("Unknown indexed image")


def images(store):
    seen = set()
    out = []
    for a in store.assets():
        if a["kind"] == "image" and a["sha256"] not in seen:
            seen.add(a["sha256"])
            out.append(
                {
                    "id": a["id"],
                    "name": Path(a["path"]).name,
                    "sha256": a["sha256"],
                    "source": "local_original",
                }
            )
    for r in store.rows("annotation"):
        if r.get("source_archive") and r.get("source_member"):
            out.append(
                {
                    "id": r["id"],
                    "name": r["source_member"],
                    "source": Path(r["source_archive"]).name,
                }
            )
    return out


def discovery_database():
    return Path(
        os.getenv("HOLY_DISCOVERY_DATABASE")
        or ROOT / "outputs/holy_auto_discovery.sqlite"
    )


def state(store):
    path = ROOT / "outputs/grader/dataset_audit.json"
    audit = (
        json.loads(path.read_text()) if path.is_file() else {"status": "NOT_AUDITED"}
    )
    holdings = collection(store)
    known = []
    unknown = 0
    for h in holdings:
        v = h.get("all_in_cost")
        if v not in ("", None):
            from decimal import Decimal

            known.append(
                str(Decimal(v) + Decimal(h.get("additional_recorded_cash_spent", "0")))
            )
        else:
            unknown += 1
    budget = budget_check(known)
    budget["unknown_cost_holdings"] = unknown
    from .discovery_service import discovery_snapshot

    discovery = discovery_snapshot(discovery_database())
    leads = rank_leads(store)
    by_listing = {r.get("listing_id"): r["id"] for r in leads if r.get("listing_id")}
    for row in discovery["leads"]:
        row["app_lead_id"] = by_listing.get(row.get("listing_id"))
    return {
        "counts": store.counts(),
        "providers": provider_status(),
        "audit": audit,
        "leads": leads,
        "discovery": discovery,
        "research": store.rows("source_record"),
        "holdings": holdings,
        "sales": store.rows("sale"),
        "watchlist": store.rows("watch"),
        "reviews": store.rows("review"),
        "decisions": store.rows("decision"),
        "transcripts": store.rows("transcript"),
        "video_frames": store.rows("video_frame"),
        "searches": store.rows("search"),
        "quotes": store.rows("quote"),
        "models": store.rows("model"),
        "annotations": store.rows("annotation"),
        "jobs": dict(JOBS),
        "images": images(store),
        "budget": budget,
        "real_trained_grader": any(
            r.get("training_status") == "EXPERIMENTAL_UNCALIBRATED"
            for r in store.rows("model")
        ),
        "mode": "OFFLINE_MANUAL"
        if os.getenv("EBAY_ENABLED") != "true"
        else "CONFIGURED_LIVE_REQUIRES_APPROVAL",
        "automatic_purchases": False,
    }


def run_job(name, command):
    with LOCK:
        if any(v["status"] == "RUNNING" for v in JOBS.values()):
            raise ValueError("A local job is already running")
        id = stable(name, now())
        log = ROOT / "outputs/jobs" / f"{id}.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        JOBS[id] = {
            "id": id,
            "name": name,
            "status": "RUNNING",
            "started_at": now(),
            "log_path": str(log),
        }

    def execute():
        try:
            with log.open("w") as out:
                result = subprocess.run(
                    command,
                    cwd=ROOT,
                    stdout=out,
                    stderr=subprocess.STDOUT,
                    timeout=3600,
                )
            JOBS[id].update(
                status="COMPLETED" if result.returncode == 0 else "FAILED",
                exit_code=result.returncode,
            )
            if (
                result.returncode == 0
                and "--out" in command
                and name.startswith("Train ")
            ):
                from .store import Store

                output = Path(command[command.index("--out") + 1]).with_suffix(".json")
                report = json.loads(output.read_text())
                with Store() as db:
                    db.put("model", report["checkpoint_sha256"], report)
        except Exception as exc:
            JOBS[id].update(status="FAILED", error=type(exc).__name__)
        JOBS[id]["finished_at"] = now()

    threading.Thread(target=execute, daemon=True).start()
    return JOBS[id]


def command(store, action, b):
    if action == 'upgrade-saved-leads':
        import os
        from .scan_pipeline import load_saved_listings,scan_listings
        source=os.getenv('HOLY_SOURCE_DATABASE',str(ROOT/'outputs/holy.sqlite3'))
        limit = int(b.get('limit', 100))
        if not 1 <= limit <= 500:
            raise ValueError('Dashboard saved-lead limit must be 1..500')
        return scan_listings(load_saved_listings(source, limit=limit))
    if action == 'upgrade-scan':
        from .scan_pipeline import scan_listings
        listings=b.get('listings',[])
        if not isinstance(listings,list) or len(listings)>500:
            raise ValueError('Provide at most500 cached listings')
        return scan_listings(listings,target_grader=b.get('target_grader','CGC'),
            target_grade_bucket=b.get('target_grade','GEM_MINT_10'),
            inspect_images=b.get('inspect_images',True),condition_first=b.get('condition_first',False))
    if action == 'upgrade-query-plan':
        from .query_planner import four_lane_plan
        return dict(mode='OFFLINE_FOUR_LANE_PLAN',trade_approved=False,
            queries=four_lane_plan(limit=min(500,max(1,int(b.get('limit',25))))))
    if action == "import":
        rows = b.get("rows")
        if rows is None:
            rows = list(csv.DictReader(io.StringIO(b.get("csv", ""))))
        if not isinstance(rows, list) or len(rows) > 10000:
            raise ValueError("At most 10,000 rows per import")
        return import_rows(store, b["kind"], rows)
    if action == "decision":
        from .decision import review_candidate

        return review_candidate(store, b)
    if action == "discovery-import":
        import sqlite3
        from contextlib import closing
        from .automated_discovery import initialize, store_leads, sync_into_holy_pokemon

        rows = b.get("rows")
        if rows is None:
            rows = list(csv.DictReader(io.StringIO(b.get("csv", ""))))
        if not isinstance(rows, list) or len(rows) > 10000:
            raise ValueError("At most 10,000 discovery rows per import")
        path = discovery_database()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch(mode=0o600, exist_ok=True)
        path.chmod(0o600)
        with closing(sqlite3.connect(path, timeout=20)) as db:
            initialize(db)
            alerts = store_leads(
                db,
                [{**r, "source": "operator_import"} for r in rows],
                query_id="operator_import",
            )
            snapshots = [
                json.loads(r[0])
                for r in db.execute("SELECT snapshot_json FROM holy_auto_leads")
            ]
        return {
            "collector_count": len(snapshots),
            "new_or_changed": len(alerts),
            "app_sync": sync_into_holy_pokemon(snapshots, store=store),
        }
    if action == "discovery-sync":
        from .discovery_service import discovery_snapshot
        from .automated_discovery import sync_into_holy_pokemon

        feed = discovery_snapshot(discovery_database(), limit=1000)
        if feed["status"] not in ("READY", "NOT_STARTED"):
            raise ValueError("Discovery database unavailable; inspect source status")
        return sync_into_holy_pokemon(feed["leads"], store=store)
    if action == "discovery-scan":
        from .ebay_browse import credentials

        # This UI uses the same explicit configuration gates as existing Browse search.
        status = provider_status()["ebay_browse"]
        if not status["enabled"] or not status["production_approved"]:
            raise ValueError(
                "Configure authorized eBay credentials, EBAY_ENABLED=true and EBAY_PRODUCTION_APPROVED=true first. No request was made."
            )
        credentials_file = Path.home() / ".config/holy_pokemon/ebay.json"
        if os.getenv("EBAY_CLIENT_ID") and os.getenv("EBAY_CLIENT_SECRET"):
            credentials()
            extra = []
        elif credentials_file.is_file():
            credentials(credentials_file)
            extra = ["--credentials-file", str(credentials_file)]
        else:
            raise ValueError("Authorized eBay keyset missing; no request was made")
        return run_job(
            "Authorized discovery scan",
            [
                sys.executable,
                "-m",
                "holy_pokemon.automated_discovery",
                "--live",
                "--authorized-keyset",
                "--once",
                "--queries-per-cycle",
                "1",
                "--daily-api-limit",
                "30",
                "--database",
                str(discovery_database()),
                "--app-database",
                str(store.path),
                "--sync-app",
                *extra,
            ],
        )
    if action == "note":
        subject = b.get("subject")
        text = str(b.get("text", "")).strip()
        if not subject or not text:
            raise ValueError("Subject and note required")
        id = stable(subject, text, now())
        store.put(
            "review",
            id,
            {
                "subject": subject,
                "text": text,
                "reviewer": "local_operator",
                "at": now(),
            },
        )
        return {"saved": id}
    if action == "watch":
        r = {"subject": b["subject"], "notes": b.get("notes", ""), "added_at": now()}
        store.put("watch", stable(b["subject"]), r)
        return {"saved": True}
    if action == "vault-transition":
        return record_transition(store, b)
    if action == "grading-event":
        from .vault_workflow import record_grading_event

        return record_grading_event(store, b)
    if action == "payout":
        return record_payout(store, b)
    if action == "vault-compare":
        return compare_exits(b)
    if action == "comps":
        return sales_summary(
            store.rows("sale"),
            b["identity"],
            grader=b.get("grader"),
            grade=b.get("grade"),
            designation=b.get("designation"),
            label_era=b.get("label_era"),
        )
    if action == "venues":
        from .business_ops import venue_comparison

        return venue_comparison(b)
    if action == "retry":
        from .business_ops import retry_analysis

        return retry_analysis(
            b["stop_net"],
            b["success_exit"],
            b["failure_exit"],
            b["remaining_attempt_cost"],
        )
    if action == "upload":
        raw = base64.b64decode(b["base64"], validate=True)
        if len(raw) > 15_000_000:
            raise ValueError("15MB image limit")
        name = Path(b["name"]).name
        if Path(name).suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
            raise ValueError("Unsupported image format")
        import hashlib

        sha = hashlib.sha256(raw).hexdigest()
        path = ROOT / "uploads" / f"{sha}{Path(name).suffix.lower()}"
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_bytes(raw)
            path.chmod(0o600)
        try:
            qa = quality(path)
        except Exception:
            raise ValueError("Invalid image or unsafe dimensions") from None
        store.index(
            path,
            "image",
            {"source": "operator_upload", "original_name": name, "uploaded_at": now()},
        )
        id = stable(str(path.resolve()))
        return {"id": id, "qa": qa, "original_preserved": True}
    if action == "image-qa":
        return quality(asset_path(store, b["id"]))
    if action == "crop":
        source = asset_path(store, b["id"])
        dest = ROOT / "outputs/derived" / f"{stable(b['id'], b['box'])}.png"
        if b.get("card_only_verified") is not True:
            raise ValueError(
                "Human verification that crop excludes labels, subtitles and holder required"
            )
        transform = reviewed_crop(source, b["box"], dest)
        record = {
            **transform,
            "type": "crop",
            "asset_id": b["id"],
            "reviewed_at": now(),
            "card_only_verified": True,
        }
        store.put("review", stable(b["id"], b["box"]), record)
        return record
    if action == "annotation":
        allowed = {
            "whitening",
            "corner_wear",
            "chipping",
            "scratches",
            "print_lines",
            "stains",
            "dent",
            "crease",
            "gloss",
            "foil_texture",
            "obstruction",
            "centering",
        }
        if b.get("defect") not in allowed or b.get("visibility") not in (
            "seen",
            "not_visible",
            "unknown",
        ):
            raise ValueError("Unknown defect or visibility")
        asset_path(store, b["id"])
        r = {**b, "type": "defect", "reviewer": "local_operator", "at": now()}
        store.put("review", stable(r), r)
        return r
    if action == "training-label":
        # All causal and rights fields are explicit human assertions, preserved for audit.
        required = (
            "physical_specimen_id",
            "source_video_id",
            "grader",
            "grade",
            "image_id",
            "back_id",
            "outcome_evidence",
            "rights_basis",
            "rights_evidence",
        )
        if any(not b.get(k) for k in required):
            raise ValueError(
                "Missing specimen, video, pair, actual outcome or rights evidence"
            )
        if (
            b.get("pre_decision_visible") is not True
            or b.get("outcome_verified") is not True
        ):
            raise ValueError("Verify buyer-visible stage and later observed outcome")

        def crop(id):
            rr = [
                r
                for r in store.rows("review")
                if r.get("type") == "crop" and r.get("asset_id") == id
            ]
            if not rr:
                raise ValueError("Both sides require reviewed label-free crops")
            return rr[-1]["path"]

        r = {
            **b,
            "type": "training_label",
            "image_path": crop(b["image_id"]),
            "back_image_path": crop(b["back_id"]),
            "game": "pokemon",
            "card_only_verified": True,
            "back_card_only_verified": True,
            "at": now(),
        }
        store.put("review", stable(r), r)
        return {"saved": True}
    if action == "train":
        from .vision_training import LABELS, _training_rows
        from .evaluation import connected_split

        grader = b["grader"]
        if grader not in LABELS:
            raise ValueError("Unknown grader")
        rows = [
            r
            for r in store.rows("review")
            if r.get("type") == "training_label" and r.get("grader") == grader
        ]
        if not rows:
            raise ValueError(
                "No curated training labels. Review both crops, physical specimen, pre-buy stage and observed later outcome first."
            )
        dest = ROOT / "outputs/grader" / f"{grader}_approved.csv"
        fields = sorted({k for r in rows for k in r})
        with dest.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
        approved, excluded = _training_rows(dest, grader)
        connected_split(approved)
        output = ROOT / "local_models" / f"{grader}_{stable(now())[:12]}.pt"
        return run_job(
            "Train " + grader,
            [
                sys.executable,
                "-m",
                "holy_pokemon.vision_training",
                "train",
                "--manifest",
                str(dest),
                "--grader",
                grader,
                "--out",
                str(output),
                "--epochs",
                str(int(b.get("epochs", 4))),
            ],
        )
    if action == "infer":
        from .vision_training import predict

        candidates = [
            p for p in (ROOT / "local_models").glob("*.pt") if "synthetic" not in p.name
        ]
        if not candidates:
            return {
                "status": "ABSTAIN",
                "reason": "NO_REAL_TRAINED_MODEL",
                "missing_back": not b.get("back_id"),
            }

        def crop(id):
            rr = [
                r
                for r in store.rows("review")
                if r.get("type") == "crop" and r.get("asset_id") == id
            ]
            return rr[-1]["path"] if rr else None

        front = crop(b["id"])
        back = crop(b.get("back_id"))
        if not front or not back:
            return {
                "status": "ABSTAIN",
                "reason": "reviewed_front_and_back_card_only_crops_required",
            }
        return predict(
            max(candidates, key=lambda p: p.stat().st_mtime), front, back, True
        )
    if action == "video-frame-full":
        from .video_evidence import full_frame

        return full_frame(store, b["id"])
    if action == "video-sample":
        return run_job(
            "Video evidence review",
            [sys.executable, "-m", "holy_pokemon.video_evidence"],
        )
    if action == "audit":
        return run_job("Dataset audit", [sys.executable, "-m", "holy_pokemon.ingest"])
    if action == "ebay-search":
        from .ebay_browse import EbayBrowse, credentials

        status = provider_status()["ebay_browse"]
        cid, secret = credentials()
        client = EbayBrowse(
            store.db,
            enabled=status["enabled"],
            production_approved=status["production_approved"],
            client_id=cid,
            client_secret=secret,
            max_pages=1,
        )
        rows = client.search(b["query"])
        for r in rows:
            store.put(
                "lead",
                stable("ebay", r["listing_id"], r["retrieved_at"]),
                {
                    **r,
                    "ask": r.get("asking_price"),
                    "source_url": r["url"],
                    "provider": "ebay",
                    "observed_at": r["observed_at"],
                },
            )
        return {"imported": len(rows), "kind": "ACTIVE_ASKS_ONLY"}
    if action == "cert":
        from .psa_cert import PSACertificateAdapter

        return PSACertificateAdapter(store).verify(b["cert"])
    raise ValueError("Unknown local operation")
