"""Unified multi-dataset dated sold-comp index for Holy Pokémon.

Indexes all committed dated reported sales (Cross-Set, Jungle, Promos) and
optional user CSVs without blending PSA9 with Grade 9 guides or CGC Gem 10
with Pristine 10.
"""
from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
from statistics import median
from typing import Any, Iterable

from .title_parser import parse_title

ROOT = Path(__file__).resolve().parents[1] / "research"
DEFAULT_SOURCES = (
    ROOT / "cross_set_gap_2026" / "dated_source_reported_sales.csv",
    ROOT / "jungle_2026" / "dated_reported_sold_comps.csv",
    ROOT / "pokemon_promo_reported_sold_comps_2026-10-29.csv",
)

D = Decimal


def _norm_text(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def _norm_set(value: str | None) -> str:
    s = _norm_text(value)
    s = re.sub(r"\b(199\d|20[0-2]\d)\b", "", s)
    s = re.sub(r"\bpokemon\b", "", s)
    return " ".join(s.split())


def _norm_number(value: str | None) -> str:
    raw = str(value or "").strip()
    if "/" in raw:
        raw = raw.split("/", 1)[0].strip()
    return raw.lstrip("0") or raw


def _norm_edition(value: str | None) -> str:
    s = _norm_text(value)
    if "1st" in s or "first" in s:
        return "1st_edition"
    if "shadowless" in s:
        return "shadowless"
    if "promo" in s or "black star" in s:
        return "promo"
    return "unlimited"


def _norm_grade_bucket(grader: str | None, grade_raw: str | None) -> tuple[str, str] | None:
    g = str(grader or "").upper().strip()
    val = str(grade_raw or "").upper().strip()
    if not g or not val:
        return None
    val = val.removeprefix(g + "_")
    val = {"MINT_9": "9", "MINT_8": "8"}.get(val, val)
    if g == "CGC":
        aliases = {"10": "GEM_MINT_10", "PRISTINE 10": "PRISTINE_10"}
        val = aliases.get(val, val)
    # Never coerce decimal grades, guides or mixed grade classes to a whole grade.
    if val not in {"1", "2", "3", "4", "5", "6", "7", "8", "8.5", "9", "9.5", "10", "GEM_MINT_10", "PRISTINE_10"}:
        return None
    return g, val


def _money(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        v = D(str(value).replace("$", "").replace(",", "").strip())
    except (InvalidOperation, ValueError):
        return None
    return v if v.is_finite() and v > 0 else None


@dataclass(frozen=True)
class CompRecord:
    set_name: str
    card: str
    number: str
    edition: str
    grader: str
    grade_bucket: str
    sale_date: str
    price_usd: Decimal
    source_url: str
    title_context: str
    finish: str = "Unspecified"
    language: str = "English"
    source_status: str = "SOURCE_REPORTED_NOT_INDEPENDENTLY_CONFIRMED"


@dataclass(frozen=True)
class CompSummary:
    grader: str
    grade_bucket: str
    count: int
    median_usd: Decimal
    p25_usd: Decimal
    min_usd: Decimal
    max_usd: Decimal
    latest_date: str
    recency_weighted_usd: Decimal
    source_urls: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_status": "SOURCE_REPORTED_NOT_INDEPENDENTLY_CONFIRMED",
            "grader": self.grader,
            "grade_bucket": self.grade_bucket,
            "count": self.count,
            "median_usd": str(self.median_usd.quantize(D("0.01"))),
            "p25_usd": str(self.p25_usd.quantize(D("0.01"))),
            "min_usd": str(self.min_usd.quantize(D("0.01"))),
            "max_usd": str(self.max_usd.quantize(D("0.01"))),
            "latest_date": self.latest_date,
            "recency_weighted_usd": str(self.recency_weighted_usd.quantize(D("0.01"))),
            "source_urls": list(self.source_urls),
        }


class CompIndex:
    """In-memory index of dated reported sales keyed by normalized card identity."""

    def __init__(self, records: Iterable[CompRecord]) -> None:
        self.records = list(records)
        self._by_exact: dict[tuple[str, str, str, str], list[CompRecord]] = defaultdict(list)
        self._by_card_num: dict[tuple[str, str], list[CompRecord]] = defaultdict(list)
        for rec in self.records:
            ek = (_norm_set(rec.set_name), _norm_text(rec.card), _norm_number(rec.number), _norm_edition(rec.edition))
            self._by_exact[ek].append(rec)
            self._by_card_num[(_norm_text(rec.card), _norm_number(rec.number))].append(rec)

    @classmethod
    def from_csvs(cls, paths: Iterable[Path] = DEFAULT_SOURCES) -> "CompIndex":
        records: list[CompRecord] = []
        for path in paths:
            p = Path(path)
            if not p.is_file():
                continue
            with p.open(newline="", encoding="utf-8-sig") as handle:
                for row in csv.DictReader(handle):
                    rec = cls._parse_row(row, default_set="Promo" if "promo" in p.name.lower() else "")
                    if rec is not None:
                        records.append(rec)
        return cls(records)

    @staticmethod
    def _parse_row(row: dict[str, Any], *, default_set: str = "") -> CompRecord | None:
        card = str(row.get("card") or "").strip()
        number = str(row.get("card_number") or row.get("number") or "").strip()
        set_name = str(row.get("set") or default_set).strip()
        edition = str(row.get("edition") or row.get("variant") or "unlimited").strip()
        grader = str(row.get("grading_company") or row.get("grade_company") or row.get("grader") or "").strip()
        grade_raw = str(row.get("grade_class") or row.get("grade") or "").strip()
        bucket = _norm_grade_bucket(grader, grade_raw)
        price = _money(row.get("reported_price_usd") or row.get("reported_usd"))
        sale_date = str(row.get("reported_date") or row.get("reported_sale_date") or row.get("sale_date") or "").strip()
        url = str(row.get("source_url") or row.get("sale_or_report_source_url") or "").strip()
        title = str(row.get("reported_title_context") or row.get("reported_listing_title_or_context") or row.get("reported_sale_title") or "").strip()
        if not (card and number and bucket and price and re.fullmatch(r"\d{4}-\d{2}-\d{2}", sale_date)):
            return None
        try:
            date.fromisoformat(sale_date)
        except ValueError:
            return None
        parsed = parse_title(title + " " + edition, expected_language="")
        return CompRecord(
            set_name=set_name,
            card=card,
            number=number,
            edition=edition,
            grader=bucket[0],
            grade_bucket=bucket[1],
            sale_date=sale_date,
            price_usd=price,
            source_url=url,
            title_context=title,
            finish=str(row.get("finish") or parsed.finish),
            language=str(row.get("language") or parsed.language),
            source_status=str(row.get("source_status") or row.get("verification") or row.get("verification_status") or "SOURCE_REPORTED_NOT_INDEPENDENTLY_CONFIRMED"),
        )

    def card_keys(self) -> list[tuple[str, str]]:
        return sorted(self._by_card_num.keys())

    def summarize(
        self,
        *,
        card: str,
        number: str,
        grader: str,
        grade_bucket: str,
        set_name: str | None = None,
        edition: str | None = None,
        as_of: str | None = None,
        finish: str | None = None,
        language: str | None = None,
    ) -> CompSummary | None:
        as_of = as_of or date.today().isoformat()
        date.fromisoformat(as_of)
        pool = self._by_card_num.get((_norm_text(card), _norm_number(number)), [])
        if set_name:
            pool = [r for r in pool if _norm_set(r.set_name) == _norm_set(set_name)]
        if edition:
            pool = [r for r in pool if _norm_edition(r.edition) == _norm_edition(edition)]
        if finish and finish != "Unspecified":
            pool = [r for r in pool if r.finish.casefold() == finish.casefold()]
        if language:
            pool = [r for r in pool if r.language.casefold() == language.casefold()]
        pool = [r for r in pool if r.grader == grader.upper() and r.grade_bucket == grade_bucket]
        # An underspecified identity may not silently pool distinct variants.
        if len({(_norm_set(r.set_name), _norm_edition(r.edition), r.finish, r.language) for r in pool}) > 1:
            return None

        matched = [
            r for r in pool
            if r.grader == grader.upper() and r.grade_bucket == grade_bucket and r.sale_date <= as_of
        ]
        if not matched:
            return None

        matched.sort(key=lambda r: r.sale_date, reverse=True)
        prices = sorted(r.price_usd for r in matched)
        # IQR-based soft outlier trim when >= 5 comps exist
        if len(prices) >= 5:
            q1 = prices[(len(prices) - 1) // 4]
            q3 = prices[(3 * (len(prices) - 1)) // 4]
            iqr = q3 - q1
            lo, hi = q1 - D("1.5") * iqr, q3 + D("1.5") * iqr
            trimmed = [p for p in prices if lo <= p <= hi]
            if len(trimmed) >= 3:
                prices = trimmed
                matched = [r for r in matched if lo <= r.price_usd <= hi]

        med = D(str(median(prices)))
        p25 = prices[(len(prices) - 1) // 4]

        as_of_d = date.fromisoformat(as_of)
        weighted_sum = D("0")
        weight_total = D("0")
        for r in matched:
            days = max(0, (as_of_d - date.fromisoformat(r.sale_date)).days)
            w = D("1") / (D("1") + D(days) / D("30"))
            weighted_sum += r.price_usd * w
            weight_total += w
        rw = weighted_sum / weight_total if weight_total > 0 else med

        urls = tuple(dict.fromkeys(r.source_url for r in matched if r.source_url))[:5]
        return CompSummary(
            grader=grader.upper(),
            grade_bucket=grade_bucket,
            count=len(matched),
            median_usd=med,
            p25_usd=p25,
            min_usd=prices[0],
            max_usd=prices[-1],
            latest_date=matched[0].sale_date,
            recency_weighted_usd=rw,
            source_urls=urls,
        )
