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
from .title_parser import parse_title
from typing import Any, Iterable

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
    return "unlimited" if "unlimited" in s else "unspecified"


def _norm_grade_bucket(grader: str | None, grade_raw: str | None) -> tuple[str, str] | None:
    g = str(grader or "").upper().strip()
    val = str(grade_raw or "").upper().strip()
    if not g or not val:
        return None
    if g == 'PSA' and val in {'PSA_9', 'MINT_9'}:
        return g, '9'
    if g == "CGC":
        if val in {"PRISTINE_10", "CGC_PRISTINE_10", "PRISTINE 10"}:
            return g, "PRISTINE_10"
        if val in {"GEM_MINT_10", "CGC_GEM_MINT_10", "GEM MINT 10"}:
            return g, "GEM_MINT_10"
        if val in {"LEGACY_BLUE_9_5", "MINT_PLUS_9_5", "UNKNOWN_9_5"}:
            return g, val
        if val == "10":
            return g, "UNKNOWN_10"
        if val == "9.5":
            return g, "UNKNOWN_9_5"
    number = re.fullmatch(r"(?:PSA|BGS|CGC|SGC)?\s*(10|[1-9](?:\.5)?)", val)
    return (g, number.group(1)) if g in {"PSA", "BGS", "CGC", "SGC"} and number else None


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


def _ebay_sale_id(url: str) -> str | None:
    from urllib.parse import urlsplit

    try:
        parsed = urlsplit(url)
    except ValueError:
        return None
    if parsed.scheme not in ('http', 'https') or parsed.hostname not in (
        'ebay.com', 'www.ebay.com', 'ebay.co.uk', 'www.ebay.co.uk',
        'ebay.ca', 'www.ebay.ca', 'ebay.com.au', 'www.ebay.com.au',
        'ebay.de', 'www.ebay.de', 'ebay.fr', 'www.ebay.fr',
    ):
        return None
    match = re.fullmatch(r'/itm/(?:[^/]+/)?(\d{9,15})/?', parsed.path)
    return match[1] if match else None


def _sale_facts(record: CompRecord) -> tuple:
    return (
        _norm_set(record.set_name), _norm_text(record.card), _norm_number(record.number),
        _norm_edition(record.edition), record.grader, record.grade_bucket, record.sale_date,
        record.price_usd, _norm_text(record.finish), record.language.casefold(),
    )


class CompIndex:
    """In-memory index of dated reported sales keyed by normalized card identity."""

    def __init__(self, records: Iterable[CompRecord]) -> None:
        self.reported_records = tuple(dict.fromkeys(records))
        transactions: dict[str, CompRecord] = {}
        conflicts: set[str] = set()
        undeduplicated: list[CompRecord] = []
        for record in self.reported_records:
            item_id = _ebay_sale_id(record.source_url)
            if item_id is None:
                undeduplicated.append(record)
                continue
            prior = transactions.setdefault(item_id, record)
            if _sale_facts(prior) != _sale_facts(record):
                conflicts.add(item_id)
        self.conflicting_ebay_item_ids = frozenset(conflicts)
        self.records = undeduplicated + [
            record for item_id, record in transactions.items() if item_id not in conflicts
        ]
        self._by_number: dict[str, list[CompRecord]] = defaultdict(list)
        self._by_exact: dict[tuple[str, str, str, str], list[CompRecord]] = defaultdict(list)
        self._by_card_num: dict[tuple[str, str], list[CompRecord]] = defaultdict(list)
        for rec in self.records:
            ek = (_norm_set(rec.set_name), _norm_text(rec.card), _norm_number(rec.number), _norm_edition(rec.edition))
            self._by_exact[ek].append(rec)
            self._by_number[ek[2]].append(rec)
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
        # Normalized provider imports must identify resolved completed sales.
        # Historical committed reports do not have these optional columns.
        status = str(row.get('sale_status') or '').strip().casefold()
        if status and status not in ('sold', 'completed', 'settled'):
            return None
        currency = str(row.get('currency') or 'USD').strip().upper()
        if currency != 'USD':
            return None
        offer = str(row.get('best_offer_status') or '').strip().casefold()
        if offer and offer not in ('not_applicable', 'resolved', 'found'):
            return None
        card = str(row.get("card") or "").strip()
        number = str(row.get("card_number") or row.get("number") or "").strip()
        set_name = str(row.get("set") or default_set).strip()
        edition = str(row.get("edition") or row.get("variant") or "Unspecified").strip()
        grader = str(row.get("grading_company") or row.get("grade_company") or row.get("grader") or "").strip()
        grade_raw = str(row.get("grade_class") or row.get("grade") or "").strip()
        bucket = _norm_grade_bucket(grader, grade_raw)
        price = _money(row.get("reported_price_usd") or row.get("reported_usd") or row.get("transaction_price_usd"))
        sale_date = str(row.get("reported_date") or row.get("reported_sale_date") or row.get("sale_date") or "").strip()
        url = str(row.get("source_url") or row.get("sale_or_report_source_url") or "").strip()
        title = str(row.get("reported_title_context") or row.get("reported_listing_title_or_context") or row.get("reported_sale_title") or "").strip()
        if not (card and number and bucket and price and url and re.fullmatch(r"\d{4}-\d{2}-\d{2}", sale_date)):
            return None
        try:
            date.fromisoformat(sale_date)
        except ValueError:
            return None
        parsed = parse_title(title)
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
        )

    def card_keys(self) -> list[tuple[str, str]]:
        return sorted(self._by_card_num.keys())

    def match_title(self, title: str, *, allow_missing_set=False):
        """Catalog proposal only; relaxed queries still require an unambiguous exact variant."""
        exact = self.propose_identity(title)
        if exact or not allow_missing_set:
            return exact
        parsed = parse_title(title)
        if parsed.disqualified or parsed.edition == 'Unspecified':
            return None
        text = ' '+_norm_text(title)+' '
        choices = {}
        for r in self._by_number.get(parsed.card_number, []):
            if (' '+_norm_text(r.card)+' ') not in text or parsed.card_number != _norm_number(r.number):
                continue
            if (parsed.language != r.language or parsed.finish != r.finish or
                _norm_edition(parsed.edition) != _norm_edition(r.edition)):
                continue
            key = (r.set_name,r.card,r.number,r.edition,r.finish,r.language)
            choices[key] = dict(set_name=r.set_name,card=r.card,number=r.number,
                                edition=r.edition,finish=r.finish,language=r.language)
        return next(iter(choices.values())) if len(choices)==1 else None

    def propose_identity(self, title: str) -> dict[str, str] | None:
        """Unique title/catalog association only; never physical-copy verification."""
        parsed = parse_title(title)
        if parsed.edition == 'Unspecified':
            return None
        text = ' ' + _norm_text(title) + ' '
        proposals = {}
        for r in self._by_number.get(parsed.card_number, []):
            if (' '+_norm_text(r.card)+' ') not in text or (' '+_norm_set(r.set_name)+' ') not in text:
                continue
            if parsed.card_number != _norm_number(r.number):
                continue
            if parsed.edition != 'Unspecified' and _norm_edition(parsed.edition) != _norm_edition(r.edition):
                continue
            if parsed.finish != r.finish or parsed.language != r.language:
                continue
            key = (_norm_set(r.set_name),r.card,r.number,_norm_edition(r.edition),r.finish,r.language)
            proposals[key] = dict(card=r.card,number=r.number,set_name=r.set_name,edition=r.edition,
                                  finish=r.finish,language=r.language)
        return next(iter(proposals.values())) if len(proposals) == 1 else None

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
        max_age_days: int = 90,
    ) -> CompSummary | None:
        as_of = as_of or date.today().isoformat()
        as_of_d = date.fromisoformat(as_of)
        pool = self._by_card_num.get((_norm_text(card), _norm_number(number)), [])
        if set_name:
            pool = [r for r in pool if _norm_set(r.set_name) == _norm_set(set_name)]
        if edition:
            pool = [r for r in pool if _norm_edition(r.edition) == _norm_edition(edition)]
        if finish and finish != "Unspecified":
            pool = [r for r in pool if _norm_text(r.finish) == _norm_text(finish)]
        if language:
            pool = [r for r in pool if r.language.casefold() == language.casefold()]

        # An underspecified request must not pool different printings, languages or editions.
        if len({(_norm_set(r.set_name),_norm_edition(r.edition),r.finish,r.language) for r in pool})>1:
            return None

        matched = [
            r for r in pool
            if r.grader == grader.upper() and r.grade_bucket == grade_bucket
            and 0 <= (as_of_d - date.fromisoformat(r.sale_date)).days <= max_age_days
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
