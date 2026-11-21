"""Priority-ranked eBay & CompSniper query planner for Holy Pokémon.

Generates precision search queries with negative exclusions (-lot, -proxy,
-orica, -custom, -reprint, -digital, -empty) and ranks targets by historical
comp spread and liquidity so limited API quotas hit the best leads first.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Iterable
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

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
        identity.language if identity.language and identity.language != 'English' else '',
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

    # Never truncate the grader/grade off a long query.
    base = " ".join(p for p in parts if p)
    if len(base) > max_length:
        raise ValueError('Identity cannot fit within eBay query limit without dropping set/variant')
    if not include_negatives:
        return base

    protective = []
    if 'unlimited' in ed_lower:
        protective += ['-"1st edition"', '-shadowless']
    if 'holo' in ed_lower and 'non' not in ed_lower:
        protective += ['-non-holo']
    for neg in (*protective, *NEGATIVE_EXCLUSIONS):
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


def plan_default_universe(*, limit: int | None = 25, **route) -> list[dict[str, Any]]:
    identities, _ = load_universe([DEFAULT_JUNGLE, DEFAULT_CROSS_SET])
    idx = CompIndex.from_csvs()
    return [q.to_dict() for q in plan_queries(identities, idx, limit=limit, **route)]


def four_lane_plan(identities=None, comp_index=None, *, limit=100,
                   auction_window_hours=6, now=None, max_price=500):
    """Quota-bounded research requests, with route seeds rather than a card whitelist."""
    from .title_parser import parse_title
    from .promo_priority import queries as promo_queries
    if auction_window_hours <= 0 or limit < 1:
        raise ValueError('Positive auction window and query limit required')
    idx = comp_index or CompIndex.from_csvs()
    if identities is None:
        identities, _ = load_universe([DEFAULT_JUNGLE, DEFAULT_CROSS_SET])
    identities = list(identities)
    clock = now or datetime.now(timezone.utc)
    registry = Path(__file__).resolve().parents[1]/'research/strategy_discovery/routes.json'
    documented = json.loads(registry.read_text()).get('routes', [])
    routes = [('PSA','8','CGC','GEM_MINT_10'), ('PSA','9','CGC','GEM_MINT_10'),
              ('PSA','9','PSA','10'), ('CGC','9','CGC','GEM_MINT_10'), ('BGS','9.5','PSA','10')]
    from .comp_index import _norm_grade_bucket
    from .fredy_business import operating_rules
    for route in documented:
        origin=route.get('origin',{});destination=route.get('destination',{})
        bucket=_norm_grade_bucket(destination.get('grader'),destination.get('grade'))
        if origin.get('grader') not in {'PSA','CGC','BGS'} or not bucket:
            continue
        if str(origin.get('grade')) not in {'7','8','9','9.5','10'} or bucket[1] in {'PRISTINE_10','UNKNOWN_10'}:
            continue
        routes.append((origin['grader'],str(origin['grade']),*bucket))
    routes=list(dict.fromkeys(routes))
    output = []
    for grader, grade, dest, bucket in routes:
        for p in plan_queries(identities, idx, origin_grader=grader, origin_grade=grade,
                              target_grader=dest, target_grade_bucket=bucket):
            common = dict(p.to_dict(), expected_grader=grader, expected_grade=grade,
                          target_grader=dest, target_grade_bucket=bucket,
                          max_price=max_price, condition_ids=[2750],
                          condition_descriptors={'27501': grader, '27502': grade},
                          fieldgroups='EXTENDED', route_registry_size=len(documented),
                          fredy_rule_ids=[r['id'] for r in operating_rules()])
            output.append(dict(common, lane='high_spread', sort='newlyListed',
                               buying_option='FIXED_PRICE'))
            if p.target_comp_count >= 3:
                end = (clock+timedelta(hours=auction_window_hours)).isoformat().replace('+00:00','Z')
                output.append(dict(common, lane='auction_sniper', sort='endingSoonest',
                                   buying_option='AUCTION', item_end_date='[..'+end+']'))
            # Low-competition omissions remain proposals, never exact identity approval.
            low = ' '.join([p.card, '#'+p.number, grader, grade, '-lot', '-proxy'])
            typos = {'Charizard':'(Charizard,Charzard)', 'Blastoise':'(Blastoise,Blastiose)',
                     'Gyarados':'(Gyarados,Gyrados)', 'Pikachu':'(Pikachu,Pickachu)'}
            for query in [low, low.replace(p.card,typos.get(p.card,p.card))]:
                if len(query) <= 100:
                    output.append(dict(common, lane='poor_title', ebay_query=query,
                        sort='newlyListed', buying_option='FIXED_PRICE', identity_requires_review=True))
    for q in promo_queries(limit=len(json.loads((registry.parents[1]/'pokemon_promo_priority.json').read_text())['queries'])):
        parsed = parse_title(q['q'])
        output.append(dict(lane='promo_priority', ebay_query=q['q'], sort='newlyListed',
            buying_option='FIXED_PRICE', max_price=max_price, priority_score=100,
            expected_grader=parsed.grader, expected_grade=parsed.grade,
            target_grader='PSA' if 'PSA_10' in q['route'] else 'CGC',
            target_grade_bucket='10' if 'PSA_10' in q['route'] else 'GEM_MINT_10',
            target_comp_count=0, condition_ids=[2750], fieldgroups='EXTENDED',
            promo_query_id=q['id']))
    # Reserve coverage for all four lanes before spending the remaining quota on ranked requests.
    unique = {}
    for q in output:
        key=(q['lane'],q['ebay_query'],q.get('target_grader'),q.get('target_grade_bucket'))
        unique.setdefault(key,q)
    pending=sorted(unique.values(),key=lambda r:r.get('priority_score',0),reverse=True)
    selected=[]
    for lane in ('high_spread','auction_sniper','poor_title','promo_priority'):
        first=next((q for q in pending if q['lane']==lane),None)
        if first:
            selected.append(first);pending.remove(first)
    return (selected+pending)[:limit]
