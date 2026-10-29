"""Unlimited, OFFLINE research query generator for Holy Pokemon.

This is intentionally NOT a crawler, a recommender calibrated to crossovers,
or a fixed top-card whitelist. It accepts any external CSV of new Pokemon
identities and enumerates all configured routes without paid API calls.
"""
from __future__ import annotations
import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JUNGLE = ROOT / "research/jungle_2026/all_64_cards_and_special_variants.csv"
DEFAULT_CROSS_SET = ROOT / "research/cross_set_gap_2026/populations_and_guide_references.csv"
ROUTES_PATH = ROOT / "research/strategy_discovery/routes.json"

@dataclass(frozen=True)
class Identity:
    set: str
    card: str
    number: str
    edition: str
    year: str = ""
    language: str = "English"
    rarity: str = ""
    source: str = ""

def _clean(value) -> str:
    return " ".join(str(value or "").split())

def _load(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def identity_from_row(row: dict, *, source: str) -> Identity | None:
    """Accept canonical columns and legacy Jungle/all-set aliases."""
    game_set = _clean(row.get("set") or row.get("set_name"))
    card = _clean(row.get("card") or row.get("name"))
    number = _clean(row.get("number") or row.get("card_number"))
    edition = _clean(row.get("edition") or row.get("variant"))
    year = _clean(row.get("year"))
    language = _clean(row.get("language")) or "English"
    rarity = _clean(row.get("rarity"))
    if not game_set and source.endswith("all_64_cards_and_special_variants.csv"):
        game_set = "Jungle"
    # Do not invent an edition or mix variants. Missing variant stays unsearchable.
    if not all((game_set, card, number, edition)):
        return None
    if source.endswith("all_64_cards_and_special_variants.csv"):
        if rarity == "holo_rare" and "holo" not in edition.lower():
            edition += " holo"
        elif rarity == "nonholo_rare" and "nonholo" not in edition.lower():
            edition += " nonholo"
    return Identity(game_set,card,number,edition,year,language,rarity,source)

def load_universe(paths: Iterable[Path]) -> tuple[list[Identity], list[dict]]:
    """Dedup exact identities; keep an audit of skipped incomplete input rows."""
    records={}
    skipped=[]
    for path in paths:
        path=Path(path)
        for line_no,row in enumerate(_load(path),2):
            identity=identity_from_row(row,source=str(path))
            if identity is None:
                skipped.append({"file":str(path),"line":line_no,"reason":"MISSING_EXACT_IDENTITY"})
                continue
            key=tuple(getattr(identity, field).casefold() for field in
                      ("set","card","number","edition","language"))
            if key not in records:
                records[key]=identity
    return list(records.values()),skipped

def route_registry(path: Path = ROUTES_PATH) -> list[dict]:
    data=json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("version") != "open_arbitrage_route_registry_v1":
        raise ValueError("Wrong strategy registry version")
    routes=data.get("routes")
    if not isinstance(routes,list) or not routes:
        raise ValueError("No configured strategies")
    ids=[route["id"] for route in routes]
    if len(ids)!=len(set(ids)):
        raise ValueError("Duplicate strategy identifiers")
    for route in routes:
        if not all(_clean(route.get(k)) for k in ("id","origin_query","exit_query")):
            raise ValueError("Incomplete strategy")
    return routes

def generate(identities: Iterable[Identity],routes: Iterable[dict]) -> list[dict]:
    """Build evidence-gathering queries only; never results, counts or recommendations."""
    result=[]
    for card in identities:
        base=" ".join(filter(None,["Pokemon",card.year,card.language,card.set,
                                  card.card,card.number,card.edition]))
        for route in routes:
            result.append({
                "identity":{"set":card.set,"card":card.card,"number":card.number,
                            "edition":card.edition,"year":card.year,
                            "language":card.language,"source":card.source},
                "route_id":route["id"],
                "origin_search_query":base+" "+route["origin_query"],
                "target_sold_comp_query":base+" "+route["exit_query"]+" sold",
                "research_questions":["Exact variant and genuine slab?","Front/back condition photos?",
                    "Source-dated exact-grade completed sales?","Current active listing inventory?",
                    "True total purchase and resale fees?","Grading/holder downgrade risk?",
                    "Independently validated conditional crossover performance?"],
                "active_listings_checked":False,
                "reported_active_listing_count":None,
                "source_verified_sold_count":None,
                "measured_grade_upgrade_probability":None,
                "estimated_profit":None,
                "status":"UNEXECUTED_RESEARCH_QUERY",
                "trade_approved":False
            })
    return result

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--universe",action="append",type=Path,default=[],
                   help="Additional CSV: set,card,number,edition,year,language. Repeatable. Any set or card accepted.")
    p.add_argument("--no-builtins",action="store_true",
                   help="Use only owner-provided universe CSVs.")
    p.add_argument("--routes-file",type=Path,default=ROUTES_PATH)
    p.add_argument("--route",action="append",default=[],
                   help="Specific route ID; repeat. By default generate ALL configured routes.")
    p.add_argument("--output",type=Path,help="Optional output JSON file.")
    p.add_argument("--limit",type=int,default=None,
                   help="Optional owner-selected limit; NO default cap or predefined top-card restriction.")
    args=p.parse_args(argv)
    paths=list(args.universe)
    if not args.no_builtins:
        paths=[DEFAULT_JUNGLE,DEFAULT_CROSS_SET,*paths]
    if not paths:
        p.error("Provide at least one --universe or enable builtins")
    if args.limit is not None and args.limit < 1:
        p.error("--limit must be positive")
    identities,skipped=load_universe(paths)
    routes=route_registry(args.routes_file)
    if args.route:
        selected=set(args.route)
        known={r["id"] for r in routes}
        if selected-known:
            p.error("Unknown route(s): "+", ".join(sorted(selected-known)))
        routes=[r for r in routes if r["id"] in selected]
    prospects=generate(identities,routes)
    if args.limit is not None:
        prospects=prospects[:args.limit]
    report={
        "mode":"OFFLINE_RESEARCH_QUERIES_NOT_SEARCH_RESULTS",
        "auto_purchase":False,
        "executed_provider_searches":0,
        "universe_files":[str(s) for s in paths],
        "exact_card_identities_loaded":len(identities),
        "strategy_routes":len(routes),
        "generated_queries_returned":len(prospects),
        "skipped_unresolved_rows":skipped,
        "candidate_queries":prospects
    }
    contents=json.dumps(report,ensure_ascii=False,indent=2)+"\n"
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(contents,encoding="utf-8")
        print(json.dumps({"saved":str(args.output),"count":len(prospects)}))
    else:
        print(contents,end="")

if __name__=="__main__":
    main()
