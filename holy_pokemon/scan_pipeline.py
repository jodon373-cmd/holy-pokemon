"""Unified offline/live scan pipeline for Holy Pokémon.

Ties together title_parser -> comp_index -> optional centering_v3 -> roi_scorer,
producing ranked JSON and CSV research reports without autonomous purchasing.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from .comp_index import CompIndex
from .roi_scorer import FeeSchedule, _money, listing_ask, score_opportunity
from .strategy_common import export_csv
from .ingestion import SeenListingStore


def load_saved_listings(database, *, limit=100):
    """Read the saved feed without writing to its database. None scans the entire cache."""
    import sqlite3
    if limit is not None and int(limit) < 1:
        raise ValueError('Saved-lead limit must be positive')
    path = Path(database).resolve()
    if not path.is_file():
        return []
    db = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
    try:
        rows = db.execute(
            "SELECT payload FROM record WHERE kind='lead' ORDER BY created_at DESC LIMIT ?",
            (-1 if limit is None else int(limit),),
        )
        return [
            dict(json.loads(payload), source_dataset='SAVED_BOT_CACHE_AVAILABILITY_NOT_REFRESHED')
            for (payload,) in rows
        ]
    finally:
        db.close()


def dedupe_listings(listings):
    """Union aliases before selection, including bridge rows sharing a cert and an item ID."""
    rows=[dict(r) for r in listings]
    parent=list(range(len(rows)))
    def find(i):
        while parent[i]!=i:
            parent[i]=parent[parent[i]]
            i=parent[i]
        return i
    aliases={}
    for i,row in enumerate(rows):
        for key in SeenListingStore.aliases(row):
            if key in aliases:
                parent[find(i)]=find(aliases[key])
            aliases[key]=i
    groups={}
    for i,row in enumerate(rows):
        groups.setdefault(find(i),[]).append(row)
    result=[]
    for group in groups.values():
        # Prefer the latest observation; never silently choose the cheapest sighting.
        group.sort(key=lambda r:str(r.get('retrieved_at') or r.get('observed_at') or ''))
        combined={}
        for row in group:
            combined.update({k:v for k,v in row.items() if v is not None})
        combined['query_priority'] = max((row.get('query_priority') or 0 for row in group), default=0)
        combined['matched_lanes']=sorted({str(r.get('lane')) for r in group if r.get('lane')})
        combined['seen_aliases']=sorted({a for r in group for a in SeenListingStore.aliases(r)})
        combined['route_options']=[dict(target_grader=g,target_grade_bucket=b) for g,b in
            sorted({(r['proposed_target_grader'],r['proposed_target_grade']) for r in group
                    if r.get('proposed_target_grader') and r.get('proposed_target_grade')})]
        combined['duplicate_sightings']=len(group)-1
        ids={str(r.get('listing_id') or r.get('id')) for r in group}
        combined['shared_cert_multiple_listings']=len(ids)>1 and any(a.startswith('cert:') for a in combined['seen_aliases'])
        result.append(combined)
    return result


def inspect_listing_images(item):
    """Read originals; v3 geometry and quality warnings never become a grade prediction."""
    from .centering_v3 import measure_file
    import hashlib
    photos=list(item.get('photo_paths') or [])
    for side in ('front','back'):
        path=item.get(side+'_image_path')
        if path:
            photos.append(dict(path=path,side=side,layout=item.get(side+'_layout','auto')))
    if item.get('image_path'):
        photos.append(dict(path=item['image_path'],side=item.get('side','front'),layout=item.get('layout','auto')))
    observations=[]
    warnings=[]
    roles=set()
    for photo in photos:
        if not isinstance(photo,dict) or photo.get('side') not in ('front','back'):
            warnings.append('UNVERIFIED_PHOTO_SIDE')
            if isinstance(photo,dict) and photo.get('path'):
                for proposed_side in ('front','back'):
                    try:
                        geometry=measure_file(photo['path'],side=proposed_side,layout='auto')
                    except (OSError,ValueError,ImportError) as exc:
                        geometry=dict(status='ABSTAIN',reason=type(exc).__name__)
                    observations.append(dict(side='UNVERIFIED_'+proposed_side.upper(),
                        source_path=photo['path'],geometry=geometry))
            continue
        side=photo['side'];roles.add(side)
        path=Path(photo['path'])
        try:
            before=hashlib.sha256(path.read_bytes()).hexdigest()
            geometry=measure_file(path,side=side,layout=photo.get('layout','auto'))
            after=hashlib.sha256(path.read_bytes()).hexdigest()
            if before!=after:
                raise ValueError('Original image changed during inspection')
            # Highlight clipping is a diagnostic, not a trained glare or defect classifier.
            import cv2
            import numpy as np
            im=cv2.imread(str(path))
            if im is not None and geometry.get('outer_quad'):
                mask=np.zeros(im.shape[:2],dtype=np.uint8)
                cv2.fillPoly(mask,[np.asarray(geometry['outer_quad'],dtype=np.int32)],1)
                hsv=cv2.cvtColor(im,cv2.COLOR_BGR2HSV)
                clipping=float(np.sum((hsv[:,:,2]>=250)&(hsv[:,:,1]<25)&(mask>0)))/max(int(mask.sum()),1)
                geometry['clipped_highlight_fraction']=round(clipping,4)
                geometry['glare_detection_status']='HEURISTIC_REQUIRES_REVIEW'
                if clipping>.18 and (item.get('condition_review') or {}).get('slab_glare') is not False:
                    warnings.append('POSSIBLE_SLAB_GLARE')
        except (OSError,ValueError,ImportError) as exc:
            geometry=dict(status='ABSTAIN',reason=type(exc).__name__,grade_prediction=None)
        observations.append(dict(side=side,source_path=str(path),geometry=geometry))
        if geometry.get('status','').startswith('ABSTAIN'):
            warnings.append('IMAGE_QUALITY_OR_GEOMETRY_UNRESOLVED:'+str(geometry.get('reason')))
        # A glare suspicion blocks clearance, not a claim of physical damage.
        if photo.get('glare') is True or (item.get('condition_review') or {}).get('slab_glare') is True:
            warnings.append('SLAB_GLARE')
    if 'back' not in roles:
        warnings.append('MISSING_BACK_PHOTO')
    if 'front' not in roles:
        warnings.append('MISSING_FRONT_PHOTO')
    review=item.get('condition_review') or {}
    if review.get('visible_defect') is True or review.get('visible_condition')=='REJECT':
        warnings.append('VISIBLE_DEFECT_VETO')
    return dict(status='VETO_OR_REVIEW' if warnings else 'GEOMETRY_REQUIRES_MANUAL_VALIDATION',
        warnings=sorted(set(warnings)),observations=observations,grade_prediction=None,
        centering_badge='UNVALIDATED_GEOMETRY_ONLY',trade_approved=False)


def download_listing_photos(item, directory):
    """Opt-in eBay image ingress only; no redirects, overwritten originals, or side guesses."""
    import hashlib
    from urllib.parse import urlparse
    from urllib.request import Request, build_opener
    from .ebay_browse import NoRedirect
    dest=Path(directory);dest.mkdir(parents=True,exist_ok=True)
    paths=[]
    for url in list(item.get('image_urls') or [])[:6]:
        u=urlparse(url)
        if u.scheme!='https' or u.hostname!='i.ebayimg.com' or u.username or u.password or u.port not in (None,443):
            continue
        key=hashlib.sha256(url.encode()).hexdigest()
        path=dest/(key+'.image')
        if not path.exists():
            with build_opener(NoRedirect()).open(Request(url,headers={'User-Agent':'HolyPokemonResearch/0.2'}),timeout=20) as response:
                data=response.read(20_000_001)
            if len(data)>20_000_000:
                raise ValueError('Photo exceeds size cap')
            from PIL import Image
            import io
            with Image.open(io.BytesIO(data)) as im:
                im.verify()
            with path.open('xb') as handle:
                handle.write(data)
        paths.append(dict(path=str(path),side=None,source_url=url))
    return paths


def discover_listings(client, plan, *, pages_per_query=1):
    """Fan out identical requests and visit each first page before requesting deeper pages."""
    if pages_per_query < 1:
        raise ValueError('pages_per_query must be positive')
    requests = {}
    for query in plan:
        params = {
            'filters': {'buyingOptions': '{' + query['buying_option'] + '}'},
            'sort': query['sort'],
        }
        if query.get('item_end_date'):
            params['filters']['itemEndDate'] = query['item_end_date']
        for key in ('max_price', 'condition_ids', 'fieldgroups', 'aspect_filter',
                    'expected_grader', 'expected_grade', 'condition_descriptors'):
            if query.get(key) is not None:
                params[key] = query[key]
        key = (query['ebay_query'], json.dumps(params, sort_keys=True))
        requests.setdefault(key, (params, []))[1].append(query)
    pending = [(keyword, params, queries) for (keyword, _), (params, queries) in requests.items()]
    rows = []
    for depth in range(pages_per_query):
        if not pending:
            break
        offset = depth * client.page_size if depth else 0
        if offset >= 10000:
            break
        next_page = []
        for keyword, params, queries in pending:
            try:
                page = client.search_page(keyword, offset=offset, **params)
            except (RuntimeError, ValueError) as exc:
                return rows, [dict(query=keyword, offset=offset, error=type(exc).__name__)]
            for row in page['rows']:
                for query in queries:
                    rows.append(dict(
                        row, lane=query['lane'], query_priority=query.get('priority_score', 0),
                        proposed_target_grader=query.get('target_grader', 'CGC'),
                        proposed_target_grade=query.get('target_grade_bucket', 'GEM_MINT_10'),
                    ))
            if page.get('has_more') and not page.get('window_exhausted'):
                next_page.append((keyword, params, queries))
        pending = next_page
    return rows, []


def _route_rank(route):
    target_count = (route.get('target_comp') or {}).get('count', 0)
    original_count = (((route.get('original_grade_fallback') or {}).get('comp')) or {}).get('count', 0)
    incremental = route.get('incremental_over_original')
    return (
        route.get('financial_gate') == 'WITHIN_MODELED_CEILING',
        incremental is not None and float(incremental) > 0,
        target_count >= 3 and original_count >= 3,
        route['opportunity_score'],
        float(incremental) if incremental is not None else float('-inf'),
        route['target_route'],
    )


def _score_routes(item, index, default_route, fees):
    primary = (item.get('proposed_target_grader', default_route[0]),
               item.get('proposed_target_grade', default_route[1]))
    routes = {primary}
    if not item.get('route_steps'):
        routes.update((opt['target_grader'], opt['target_grade_bucket'])
                      for opt in item.get('route_options', []))
    return sorted([
        score_opportunity(
            listing=item, card=str(item.get('card') or '').strip(),
            number=str(item.get('number') or '').strip(), comp_index=index,
            target_grader=grader, target_grade_bucket=grade,
            set_name=item.get('set_name') or item.get('set'),
            edition=item.get('edition'), fees=fees,
        )
        for grader, grade in routes
    ], key=_route_rank, reverse=True)


def _comp_lookup_key(item, grader, grade):
    identity = (item.get('card'), item.get('number'), item.get('set_name') or item.get('set'),
                item.get('edition'), item.get('finish'), item.get('language') or 'English')
    return (*[str(value or '').strip().casefold() for value in identity], grader, grade)


def _thin_route_sides(route):
    grader, grade = route['target_route'].split('_', 1)
    if (route.get('target_comp') or {}).get('count', 0) < 3:
        yield grader, grade
    origin = route['parsed']
    original_comp = (route.get('original_grade_fallback') or {}).get('comp') or {}
    if origin['grader'] and origin['grade'] and original_comp.get('count', 0) < 3:
        yield origin['grader'], origin['cgc_sub_tier'] or origin['grade']


def scan_listings(
    listings: Iterable[Mapping[str, Any]],
    *,
    comp_index: CompIndex | None = None,
    target_grader: str = "CGC",
    target_grade_bucket: str = "GEM_MINT_10",
    fees: FeeSchedule | None = None,
    include_disqualified: bool = False,
    inspect_images: bool = True,
    condition_first: bool = False,
    only_new: bool = False,
    seen_store=None,
    live: bool = False,
    comp_client=None,
    image_fetcher=None,
    inspection_price_limit=500,
) -> dict[str, Any]:
    """Parse, match against dated comps, and rank a batch of listings."""
    idx = comp_index or CompIndex.from_csvs()
    results: list[dict[str, Any]] = []
    disqualified_count = 0
    duplicate_count=0
    raw=list(listings)
    deduped=dedupe_listings(raw)
    duplicate_count=len(raw)-len(deduped)
    old_count=0

    default_route = (target_grader, target_grade_bucket)
    candidates = []
    for item in deduped:
        if seen_store is not None:
            fresh = seen_store.observe(item)
            if only_new and not fresh:
                old_count += 1
                continue
            item['new_listing_alert'] = fresh
        if not item.get('card'):
            title = str(item.get('title') or '')
            poor_title = 'poor_title' in item.get('matched_lanes', [])
            proposal = idx.match_title(title, allow_missing_set=poor_title)
            if not proposal and poor_title:
                from .title_parser import repair_known_card_typos

                repaired = repair_known_card_typos(title)
                if repaired != title:
                    item['identity_review_proposal'] = idx.match_title(repaired, allow_missing_set=True)
            if proposal:
                item.update(proposal)
                item['identity_basis'] = 'UNIQUE_TITLE_CATALOG_PROPOSAL_NOT_PHOTO_VERIFIED'
        routes = _score_routes(item, idx, default_route, fees)
        review = item.get('condition_review') or {}
        promising = (review.get('original_photos_reviewed') is True
                     and review.get('visible_condition') == 'PROMISING')
        candidates.append((item, routes, promising))

    enrichments = {}
    if live and comp_client is not None:
        from .compsniper import enrich_comp_index

        # Spend provider quota on the strongest unresolved routes across the entire batch.
        pending = sorted(candidates, key=lambda entry: (
            entry[2], _route_rank(entry[1][0]), entry[0].get('query_priority') or 0,
            str(entry[0].get('listing_id') or entry[0].get('id') or ''),
        ), reverse=True)
        for item, routes, promising in pending:
            if comp_client.calls >= comp_client.max_calls:
                break
            for route in routes:
                if (route['status'] not in ('SCORED_LEAD', 'MISSING_TARGET_COMPS')
                    or route.get('financial_gate') == 'OVER_MAX_OFFER'
                    or not (promising or route['opportunity_score'] > 0
                            or (item.get('query_priority') or 0) >= 60)):
                    continue
                for grader, grade in _thin_route_sides(route):
                    key = _comp_lookup_key(item, grader, grade)
                    if key in enrichments or comp_client.calls >= comp_client.max_calls:
                        continue
                    try:
                        idx, enrichment = enrich_comp_index(
                            comp_client, idx, item, target_grader=grader, target_grade=grade)
                    except (RuntimeError, ValueError) as exc:
                        enrichment = dict(status='PROVIDER_STOPPED', reason=type(exc).__name__, added=0)
                        comp_client.max_calls = comp_client.calls
                    enrichments[key] = enrichment

    for item, initial_routes, promising in candidates:
        ranked = _score_routes(item, idx, default_route, fees) if enrichments else initial_routes
        scored = ranked[0]
        review = item.get('condition_review') or {}
        scored.update(condition_review=review, owner_comp_review_requested=promising,
                      condition_priority=int(promising))
        strong = (scored['opportunity_score'] >= 60 or promising
                  or (item.get('query_priority') or 0) >= 60)
        grader, grade = scored['target_route'].split('_', 1)
        scored['live_comp_enrichment'] = enrichments.get(_comp_lookup_key(item, grader, grade))
        origin = scored['parsed']
        scored['original_comp_enrichment'] = enrichments.get(
            _comp_lookup_key(item, origin['grader'], origin['cgc_sub_tier'] or origin['grade'])
        )
        ask = _money(listing_ask(item))
        has_local_photos = any(item.get(key) for key in ('photo_paths', 'image_path', 'front_image_path', 'back_image_path'))
        if inspect_images and ask is not None and ask <= inspection_price_limit and (strong or has_local_photos):
            if image_fetcher is not None and not item.get('photo_paths'):
                try:
                    item['photo_paths']=image_fetcher(item)
                except (OSError,ValueError) as exc:
                    scored['image_download_error']=type(exc).__name__
            scored['inspection']=inspect_listing_images(item)
            scored['warnings'].extend(scored['inspection']['warnings'])
        else:
            scored['inspection']=dict(status='NOT_INSPECTED',grade_prediction=None,trade_approved=False)
        scored['matched_lanes']=item.get('matched_lanes',[])
        scored['identity_review_proposal'] = item.get('identity_review_proposal')
        scored['listing_evidence'] = {
            'source_dataset': item.get('source_dataset'),
            'retrieved_at': item.get('retrieved_at') or item.get('observed_at'),
            'buying_options': item.get('buying_options', []),
            'availability_refreshed': False,
        }
        scored['route_comparison'] = [
            {key: route.get(key) for key in (
                'target_route', 'status', 'total_investment_usd', 'target_comp',
                'conservative_net_profit_usd', 'incremental_over_original', 'max_offer_usd',
                'financial_gate', 'failure_scenarios', 'source_urls', 'warnings',
            )}
            for route in ranked
        ]
        veto = (review.get('visible_defect') is True or review.get('visible_condition') == 'REJECT'
                or review.get('slab_glare') is True)
        if veto:
            scored['opportunity_score'] = 0.0
            scored['warnings'] = list(dict.fromkeys([*scored['warnings'], 'CONDITION_REVIEW_VETO']))
        scored['review_queue'] = (
            'REJECTED_CONDITION' if veto else
            'PRIORITY_REVIEW' if (_route_rank(scored)[:3] == (True, True, True)
                                  and not item.get('shared_cert_multiple_listings')) else
            'RESEARCH'
        )
        scored['new_listing_alert']=item.get('new_listing_alert',False)
        if item.get('shared_cert_multiple_listings'):
            scored['warnings'].append('SHARED_CERT_MULTIPLE_LISTINGS')
        scored['valuation_estimate_usd'] = item.get('valuation_estimate_usd')
        scored['valuation_estimate_status'] = 'UNVERIFIED_OWNER_REVIEW_ONLY' if item.get('valuation_estimate_usd') is not None else None
        if scored["status"] == "DISQUALIFIED":
            disqualified_count += 1
            if not include_disqualified:
                continue
        results.append(scored)

    results.sort(key=lambda row: (
        {'PRIORITY_REVIEW': 2, 'RESEARCH': 1, 'REJECTED_CONDITION': 0}[row['review_queue']],
        row['condition_priority'] if condition_first else 0, _route_rank(row),
    ), reverse=True)
    return {
        "mode": "LIVE_RESEARCH_ONLY" if live else "OFFLINE_SCAN_RESEARCH_ONLY",
        "comp_enrichment_attempts": len(enrichments),
        "conflicting_ebay_sales_excluded": len(idx.conflicting_ebay_item_ids),
        "trade_approved": False,
        "condition_first": condition_first,
        "total_scanned": len(deduped)-old_count,
        "raw_input_count":len(raw),
        "disqualified_filtered": disqualified_count,
        "returned_count": len(results),
        "cross_query_duplicates":duplicate_count,
        "previously_seen_filtered":old_count,
        "ranked_leads": results,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", help="JSON candidates")
    p.add_argument('--saved-db', type=Path, help='Replay the saved SQLite lead cache read-only')
    p.add_argument('--saved-limit', type=int, help='Limit replay to the most recent saved rows')
    p.add_argument('--export-limit', type=int, help='Export only the first N ranked rows while retaining scan counts')
    p.add_argument("--output-json", help="Optional path to write ranked JSON report")
    p.add_argument("--output-csv", help="Optional path to write ranked CSV report")
    p.add_argument("--target-grader", default="CGC")
    p.add_argument("--target-grade", default="GEM_MINT_10")
    p.add_argument("--include-disqualified", action="store_true")
    p.add_argument('--inspect-images', action=argparse.BooleanOptionalAction, default=True,
                   help='Run local v3 diagnostics for top leads; --no-inspect-images skips them')
    p.add_argument('--comp-csv', action='append', type=Path, help='Dated reported sold evidence CSV; repeatable')
    p.add_argument('--condition-first', action='store_true', help='Prioritize explicitly reviewed promising copies; retain unknown comps for owner review')
    p.add_argument('--live',action='store_true',help='Opt into bounded provider quota use; no purchases')
    p.add_argument('--discover',action='store_true',help='Run the four-lane Browse plan; requires --live')
    p.add_argument('--plan',action='store_true',help='Print the four-lane plan without network calls')
    p.add_argument('--query-limit',type=int,default=25)
    p.add_argument('--universe', action='append', type=Path, help='Exact catalog CSV to add to the built-in discovery seeds')
    p.add_argument('--exploration-offset', type=int, help='Rotate a third of remaining query slots into the catalog tail')
    p.add_argument('--pages-per-query', type=int, default=1, help='Round-robin page depth for Browse searches')
    p.add_argument('--max-price',type=float,default=500)
    p.add_argument('--auction-window-hours',type=float,default=6)
    p.add_argument('--max-requests',type=int,default=30)
    p.add_argument('--daily-limit',type=int,default=5000)
    p.add_argument('--comp-max-calls',type=int,default=3)
    p.add_argument('--only-new',action='store_true')
    p.add_argument('--seen-db',default='outputs/seen_listings.sqlite3')
    args = p.parse_args(argv)
    if args.saved_db and not args.saved_db.is_file():
        p.error('--saved-db must point to an existing database')
    if any(value is not None and value < 1 for value in (args.saved_limit, args.export_limit)):
        p.error('Replay and export limits must be positive')
    if args.pages_per_query < 1:
        p.error('--pages-per-query must be positive')

    raw = json.loads(Path(args.input).read_text(encoding="utf-8")) if args.input else []
    listings = raw["listings"] if isinstance(raw, dict) and "listings" in raw else raw
    if args.saved_db and not args.plan:
        saved = load_saved_listings(args.saved_db, limit=args.saved_limit)
        listings = [*listings, *saved] if listings else saved
    from .comp_index import DEFAULT_SOURCES
    idx = CompIndex.from_csvs([*DEFAULT_SOURCES, *(args.comp_csv or [])])
    discovery_errors=[]
    if args.plan or args.discover:
        from .query_planner import four_lane_plan
        identities = None
        if args.universe:
            from .open_strategy_discovery import DEFAULT_JUNGLE, DEFAULT_CROSS_SET, load_universe
            identities, skipped_universe_rows = load_universe([DEFAULT_JUNGLE, DEFAULT_CROSS_SET, *args.universe])
            if skipped_universe_rows:
                import sys
                print(f'Skipped {len(skipped_universe_rows)} incomplete catalog rows', file=sys.stderr)
        plan = four_lane_plan(identities=identities, comp_index=idx, limit=args.query_limit,
            auction_window_hours=args.auction_window_hours, max_price=args.max_price,
            exploration_offset=args.exploration_offset)
        if args.plan:
            print(json.dumps(dict(mode='OFFLINE_FOUR_LANE_PLAN',queries=plan,trade_approved=False),indent=2))
            return 0
        if not args.live:
            p.error('--discover requires explicit --live')
        from .ebay_config import read_env_file, ENV_FILE, operator_authorized
        from .ebay_browse import EbayBrowse,credentials
        from .store import Store
        import os
        if ENV_FILE.exists():
            for key,value in read_env_file().items():
                os.environ.setdefault(key,value)
        if not operator_authorized():
            p.error('eBay production approval must be configured before discovery')
        cid,secret=credentials()
        with Store() as store:
            client=EbayBrowse(store.db,enabled=True,production_approved=True,
                client_id=cid,client_secret=secret,daily_limit=args.daily_limit,
                run_limit=args.max_requests,page_size=100)
            discovered,discovery_errors=discover_listings(client, plan, pages_per_query=args.pages_per_query)
            listings=[*listings,*discovered]
    comp_client=None
    if args.live:
        from .compsniper import CompSniperClient
        comp_client=CompSniperClient(live=True,max_calls=args.comp_max_calls)
    seen=SeenListingStore(args.seen_db) if args.only_new else None
    report = scan_listings(
        listings,
        target_grader=args.target_grader,
        target_grade_bucket=args.target_grade,
        include_disqualified=args.include_disqualified,
        inspect_images=args.inspect_images,
        comp_index=idx,
        condition_first=args.condition_first,
        live=args.live,comp_client=comp_client,only_new=args.only_new,seen_store=seen,
        inspection_price_limit=args.max_price,
        image_fetcher=(lambda item:download_listing_photos(item,'outputs/scan_photos')) if args.live else None,
    )
    if seen:
        seen.close()
    report['discovery_errors']=discovery_errors
    report['review_queue_counts'] = {}
    for row in report['ranked_leads']:
        queue = row['review_queue']
        report['review_queue_counts'][queue] = report['review_queue_counts'].get(queue, 0) + 1
    if args.export_limit is not None:
        report['ranked_leads'] = report['ranked_leads'][:args.export_limit]
    report['exported_count'] = len(report['ranked_leads'])
    if args.output_json:
        out = Path(args.output_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if args.output_csv:
        flat = [
            {
                "listing_id": r.get("listing_id"),
                "card": r.get("card"),
                "number": r.get("number"),
                "title": r.get("title"),
                "status": r.get("status"),
                "opportunity_score": r.get("opportunity_score"),
                "landed_cost_usd": r.get("landed_cost_usd"),
                "conservative_net_profit_usd": r.get("conservative_net_profit_usd"),
                "upside_net_profit_usd": r.get("upside_net_profit_usd"),
                "downside_net_profit_usd": r.get("downside_net_profit_usd"),
                "break_even_upgrade_rate": r.get("break_even_upgrade_rate"),
                "url": r.get("url"),
                "trade_approved": False,
                "max_offer_usd":r.get('max_offer_usd'),
                "max_bid_ceiling":r.get('max_bid_ceiling'),
                "incremental_over_original":r.get('incremental_over_original'),
                "source_urls":r.get('source_urls',[]),
                "warnings":r.get('warnings',[]),
                "financial_gate":r.get('financial_gate'),
                "review_queue":r.get('review_queue'),
            }
            for r in report["ranked_leads"]
        ]
        export_csv(args.output_csv, flat)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
