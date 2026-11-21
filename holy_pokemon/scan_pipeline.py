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
from .roi_scorer import FeeSchedule, score_opportunity
from .strategy_common import export_csv
from .ingestion import SeenListingStore


def load_saved_listings(database, *, limit=100):
    """Read an existing bot cache without creating tables or changing its records."""
    import sqlite3
    if not 1 <= int(limit) <= 500:
        raise ValueError('Saved-lead limit must be1..500')
    path=Path(database).resolve()
    if not path.is_file():
        return []
    db=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)
    try:
        rows=db.execute("SELECT payload FROM record WHERE kind='lead' ORDER BY created_at DESC LIMIT ?",(int(limit),)).fetchall()
        return [dict(json.loads(r[0]),source_dataset='SAVED_BOT_CACHE_AVAILABILITY_NOT_REFRESHED') for r in rows]
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


def discover_listings(client, plan):
    rows=[];errors=[]
    for q in plan:
        filters={'buyingOptions':'{'+q['buying_option']+'}'}
        if q.get('item_end_date'):
            filters['itemEndDate']=q['item_end_date']
        try:
            page=client.search_page(q['ebay_query'],filters=filters,sort=q['sort'],
                max_price=q.get('max_price'),condition_ids=q.get('condition_ids'),
                fieldgroups=q.get('fieldgroups'),expected_grader=q.get('expected_grader'),
                expected_grade=q.get('expected_grade'),condition_descriptors=q.get('condition_descriptors'))
        except (RuntimeError,ValueError) as exc:
            errors.append(dict(query=q['ebay_query'],error=type(exc).__name__))
            break  # Never retry a failed provider call through another lane.
        for row in page['rows']:
            rows.append(dict(row,lane=q['lane'],query_priority=q.get('priority_score',0),
                proposed_target_grader=q.get('target_grader','CGC'),
                proposed_target_grade=q.get('target_grade_bucket','GEM_MINT_10')))
    return rows,errors


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

    for item in deduped:
        item = dict(item)
        if seen_store is not None:
            fresh=seen_store.observe(item)
            # Persist all merged aliases, including those appearing only in an earlier lane.
            from datetime import datetime,timezone
            with seen_store.db:
                seen_store.db.executemany('INSERT OR IGNORE INTO seen_listing_alias VALUES(?,?)',
                    [(a,datetime.now(timezone.utc).isoformat()) for a in item['seen_aliases']])
            if only_new and not fresh:
                old_count+=1
                continue
            item['new_listing_alert']=fresh
        if not item.get('card'):
            proposal = idx.match_title(str(item.get('title') or ''),allow_missing_set='poor_title' in item.get('matched_lanes',[]))
            if proposal:
                item.update(proposal)
                item['identity_basis'] = 'UNIQUE_TITLE_CATALOG_PROPOSAL_NOT_PHOTO_VERIFIED'
        card = str(item.get("card") or "").strip()
        number = str(item.get("number") or "").strip()
        geometry = None
        route_grader=item.get('proposed_target_grader',target_grader)
        route_grade=item.get('proposed_target_grade',target_grade_bucket)
        scored = score_opportunity(
            listing=item,
            card=card,
            number=number,
            comp_index=idx,
            target_grader=route_grader,
            target_grade_bucket=route_grade,
            set_name=item.get("set_name") or item.get("set"),
            edition=item.get("edition"),
            centering_result=geometry or item.get("centering"),
            fees=fees,
        )
        if geometry:
            scored['centering_v3_consensus'] = geometry
        review = item.get('condition_review') or {}
        promising = review.get('original_photos_reviewed') is True and review.get('visible_condition') == 'PROMISING'
        scored['condition_review'] = review
        scored['owner_comp_review_requested'] = bool(promising)
        scored['condition_priority'] = 1 if promising else 0
        strong=scored.get('opportunity_score',0)>=60 or promising or item.get('query_priority',0)>=60
        enrichment=None
        if live and comp_client is not None and strong and (scored.get('target_comp') or {}).get('count',0)<3:
            from .compsniper import enrich_comp_index
            if comp_client.calls < comp_client.max_calls:
                try:
                    idx,enrichment=enrich_comp_index(comp_client,idx,item,target_grader=route_grader,target_grade=route_grade)
                    if enrichment['added']:
                        scored=score_opportunity(listing=item,card=card,number=number,comp_index=idx,
                            target_grader=route_grader,target_grade_bucket=route_grade,set_name=item.get('set_name') or item.get('set'),
                            edition=item.get('edition'),fees=fees)
                        scored.update(condition_review=review,owner_comp_review_requested=promising,condition_priority=int(promising))
                except (RuntimeError,ValueError) as exc:
                    enrichment=dict(status='PROVIDER_STOPPED',reason=type(exc).__name__,added=0)
                    comp_client.max_calls=comp_client.calls
        scored['live_comp_enrichment']=enrichment
        if inspect_images and strong and float(item.get('asking_price') or item.get('ask') or 0)<=inspection_price_limit:
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
        alternatives=[]
        for option in item.get('route_options',[]):
            alt=score_opportunity(listing=item,card=card,number=number,comp_index=idx,
                target_grader=option['target_grader'],target_grade_bucket=option['target_grade_bucket'],
                set_name=item.get('set_name') or item.get('set'),edition=item.get('edition'),fees=fees)
            alternatives.append({k:alt.get(k) for k in ('target_route','status','total_investment_usd',
                'target_comp','conservative_net_profit_usd','incremental_over_original','max_offer_usd','financial_gate','warnings')})
        scored['route_comparison']=alternatives
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

    results.sort(key=lambda r: ((r['condition_priority'] if condition_first else 0),float(r.get('opportunity_score') or 0)), reverse=True)
    return {
        "mode": "OFFLINE_SCAN_RESEARCH_ONLY",
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
    p.add_argument("--input", help="JSON candidates; omitted means an empty offline scan")
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
    p.add_argument('--max-price',type=float,default=500)
    p.add_argument('--auction-window-hours',type=float,default=6)
    p.add_argument('--max-requests',type=int,default=30)
    p.add_argument('--daily-limit',type=int,default=5000)
    p.add_argument('--comp-max-calls',type=int,default=3)
    p.add_argument('--only-new',action='store_true')
    p.add_argument('--seen-db',default='outputs/seen_listings.sqlite3')
    args = p.parse_args(argv)

    raw = json.loads(Path(args.input).read_text(encoding="utf-8")) if args.input else []
    listings = raw["listings"] if isinstance(raw, dict) and "listings" in raw else raw
    idx=CompIndex.from_csvs(args.comp_csv) if args.comp_csv else CompIndex.from_csvs()
    discovery_errors=[]
    if args.plan or args.discover:
        from .query_planner import four_lane_plan
        plan=four_lane_plan(comp_index=idx,limit=args.query_limit,
            auction_window_hours=args.auction_window_hours,max_price=args.max_price)
        if args.plan:
            print(json.dumps(dict(mode='OFFLINE_FOUR_LANE_PLAN',queries=plan,trade_approved=False),indent=2))
            return 0
        if not args.live:
            p.error('--discover requires explicit --live')
        from .ebay_config import read_env_file, ENV_FILE
        from .ebay_browse import EbayBrowse,credentials
        from .store import Store
        import os
        if ENV_FILE.exists():
            for key,value in read_env_file().items():
                os.environ.setdefault(key,value)
        cid,secret=credentials()
        with Store() as store:
            client=EbayBrowse(store.db,enabled=True,production_approved=True,
                client_id=cid,client_secret=secret,daily_limit=args.daily_limit,
                run_limit=args.max_requests,page_size=100)
            discovered,discovery_errors=discover_listings(client,plan)
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
            }
            for r in report["ranked_leads"]
        ]
        export_csv(args.output_csv, flat)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
