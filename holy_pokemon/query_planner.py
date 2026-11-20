"""Priority-ranked eBay & CompSniper query planner for Holy Pokémon.

Generates precision search queries with negative exclusions (-lot, -proxy,
-orica, -custom, -reprint, -digital, -empty) and ranks targets by historical
comp spread and liquidity so limited API quotas hit the best leads first.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Iterable

from .comp_index import CompIndex
from .open_strategy_discovery import DEFAULT_CROSS_SET, DEFAULT_JUNGLE, Identity, load_universe

NEGATIVE_EXCLUSIONS = ("-lot", "-proxy", "-orica", "-custom", "-reprint", "-digital", "-empty", "-damaged")


@dataclass(frozen=True)
class PlannedQuery:
    card: str
    set_name: str
    number: str
    edition: str
    language: str
    origin_grader: str
    origin_grade: str
    target_grader: str
    target_grade_bucket: str
    ebay_query: str
    compsniper_keyword: str
    priority_score: float
    target_comp_count: int
    target_p25_usd: str | None
    origin_p25_usd: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "card": self.card,
            "set_name": self.set_name,
            "number": self.number,
            "edition": self.edition,
            "language": self.language,
            "origin": f"{self.origin_grader} {self.origin_grade}",
            "target": f"{self.target_grader} {self.target_grade_bucket}",
            "ebay_query": self.ebay_query,
            "compsniper_keyword": self.compsniper_keyword,
            "priority_score": self.priority_score,
            "target_comp_count": self.target_comp_count,
            "target_p25_usd": self.target_p25_usd,
            "origin_p25_usd": self.origin_p25_usd,
        }


def build_ebay_query(
    identity: Identity,
    *,
    origin_grader: str = "PSA",
    origin_grade: str = "9",
    include_negatives: bool = True,
    max_length: int = 100,
) -> str:
    """Build a compact, high-precision eBay Browse query (<=100 chars)."""
    parts = [
        "Pokemon",
        identity.set,
        identity.card,
        identity.number,
    ]
    ed_lower = identity.edition.lower()
    if "1st" in ed_lower:
        parts.append("1st Edition")
    elif "shadowless" in ed_lower:
        parts.append("Shadowless")
    if "nonholo" in ed_lower or "non-holo" in ed_lower:
        parts.append("Non-Holo")
    elif "holo" in ed_lower:
        parts.append("Holo")
    if origin_grader and origin_grade:
        parts.append(f"{origin_grader} {origin_grade}")

    base = " ".join(p for p in parts if p)
    if max_length < 1 or len(base) > max_length:
        raise ValueError("Exact identity exceeds query length; shorten identity explicitly")
    if not include_negatives:
        return base

    for neg in NEGATIVE_EXCLUSIONS:
        candidate = f"{base} {neg}"
        if len(candidate) <= max_length:
            base = candidate
        else:
            break
    return base


def plan_queries(
    identities: Iterable[Identity],
    comp_index: CompIndex,
    *,
    origin_grader: str = "PSA",
    origin_grade: str = "9",
    target_grader: str = "CGC",
    target_grade_bucket: str = "GEM_MINT_10",
    limit: int | None = None,
) -> list[PlannedQuery]:
    """Rank search queries by historical comp spread and comp depth."""
    planned: list[PlannedQuery] = []
    for ident in identities:
        target_comp = comp_index.summarize(
            card=ident.card,
            number=ident.number,
            grader=target_grader,
            grade_bucket=target_grade_bucket,
            set_name=ident.set,
            edition=ident.edition,
        )
        origin_comp = comp_index.summarize(
            card=ident.card,
            number=ident.number,
            grader=origin_grader,
            grade_bucket=origin_grade,
            set_name=ident.set,
            edition=ident.edition,
        )

        prio = 10.0
        if target_comp is not None:
            prio += min(40.0, float(target_comp.count) * 8.0)
            if origin_comp is not None and origin_comp.p25_usd > 0:
                spread = target_comp.p25_usd - origin_comp.p25_usd
                if spread > 0:
                    prio += min(50.0, float(spread / Decimal("10")))
            else:
                prio += min(30.0, float(target_comp.p25_usd / Decimal("25")))

        ebay_q = build_ebay_query(ident, origin_grader=origin_grader, origin_grade=origin_grade)
        cs_kw = " ".join(p for p in ("Pokemon", ident.set, ident.card, ident.number) if p)

        planned.append(
            PlannedQuery(
                card=ident.card,
                set_name=ident.set,
                number=ident.number,
                edition=ident.edition,
                language=ident.language,
                origin_grader=origin_grader,
                origin_grade=origin_grade,
                target_grader=target_grader,
                target_grade_bucket=target_grade_bucket,
                ebay_query=ebay_q,
                compsniper_keyword=cs_kw,
                priority_score=round(prio, 1),
                target_comp_count=target_comp.count if target_comp else 0,
                target_p25_usd=str(target_comp.p25_usd.quantize(Decimal("0.01"))) if target_comp else None,
                origin_p25_usd=str(origin_comp.p25_usd.quantize(Decimal("0.01"))) if origin_comp else None,
            )
        )

    planned.sort(key=lambda x: (x.priority_score, x.target_comp_count), reverse=True)
    return planned[:limit] if limit is not None else planned


def plan_default_universe(*, limit: int | None = 25) -> list[dict[str, Any]]:
    identities, _ = load_universe([DEFAULT_JUNGLE, DEFAULT_CROSS_SET])
    idx = CompIndex.from_csvs()
    return [q.to_dict() for q in plan_queries(identities, idx, limit=limit)]
