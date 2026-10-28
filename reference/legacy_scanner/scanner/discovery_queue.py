"""Research-only opportunity hunt from unverified CGC 9.5 seller-title leads.

Sorts *inspection priority*, never probability of PSA10, expected return or trade eligibility.
For financial validation, use scanner.high_upside.
"""
import argparse,csv,json,re
from pathlib import Path
from urllib.parse import quote_plus

RICH=("expedition","aquapolis","skyridge","ex dragon","ex sandstorm","ex ruby",
      "ex deoxys","ex legend","ex holon","ex unseen","ex team","ex fire",
      "ex hidden","split earth","wind from the sea","miracle crystal")
DEMAND=("charizard","blastoise","venusaur","pikachu","eevee","squirtle","charmander",
        "bulbasaur","dragonite","gengar","mewtwo","mew","umbreon","espeon",
        "jolteon","vaporeon","flareon","lugia","ho-oh","arcanine","rapidash",
        "houndoom","typhlosion","celebi","articuno","zapdos","moltres")

def money(value):
    if value in ("",None): return None
    try: amount=float(value)
    except (ValueError,TypeError): return None
    return amount if 0 <= amount < 1e8 else None

def determine_priority(row):
    title=(row.get("title") or "").strip()
    grade=str(row.get("original_grade") or "").strip()
    lower=title.casefold()
    if not title: return None  # Discovery: do not filter by grade, price, holder, photos, or missing sold comps.
    asking=money(row.get("asking_price"));shipping=money(row.get("shipping"))
    subtotal=round(asking+shipping,2) if asking is not None and shipping is not None else None
    score=0;reasons=[];warnings=[]
    blue=bool(re.search(r"blue\s*label|old\s*(?:blue\s*)?label|legacy\s*blue",title,re.I))
    mintplus="mint+" in lower or row.get("grade_designation")=="mint_plus"
    gem=not mintplus and ("gem mint" in lower or row.get("grade_designation")=="gem_mint")
    lane=("legacy_blue_gem_mint95_claim" if grade=="9.5" and blue and gem else
          "mint_plus95_separate" if mintplus else
          "cgc9_separate" if grade=="9" else "unverified_95_other")
    if mintplus:score-=22;warnings.append("Mint+ separate from old CGC Gem Mint9.5")
    if grade=="9":score-=18;warnings.append("CGC9 does not reholder as CGC10")
    if any(x in lower for x in ("choose your card","pick your card","lot of ")):
        score-=20;warnings.append("multi-card or variable-price listing; inspect option")
    if blue:score+=16;reasons.append("seller claims blue/old label")
    else:warnings.append("old CGC holder unverified")
    if gem:score+=9;reasons.append("seller claims Gem Mint")
    else:warnings.append("Gem Mint vs Mint+ unknown")
    if any(x in lower for x in RICH):score+=19;reasons.append("e-Series or EX research")
    elif "neo destiny" in lower:score+=15;reasons.append("Neo Destiny research")
    elif "neo" in lower:score+=8;reasons.append("Neo-era research")
    if any(x in lower for x in ("black star promo","black star promos","premium file","wotc promo","league")):
        score+=12;reasons.append("promo research")
    if any(re.search(r"\b"+re.escape(x)+r"\b",lower) for x in DEMAND):
        score+=14;reasons.append("desirable character hypothesis")
    if any(x in lower for x in ("1st ed","1st edition","1 st edition")):
        score+=7;reasons.append("first edition claim")
    if any(x in lower for x in ("reverse holo","reverse foil","holo","foil")):
        score+=5;reasons.append("special finish claim")
    if "japan" in lower or "split earth" in lower:
        score+=3;reasons.append("Japanese vintage")
    if subtotal is None:score-=5;warnings.append("incomplete price/shipping")
    elif subtotal<=100:score+=7
    elif subtotal<=200:score+=5
    elif subtotal<=400:score+=2
    else:score-=14;warnings.append("price above exploratory $400 cap")
    if "signed" in lower or "autograph" in lower:
        score-=8;warnings.append("signed-card market is not a standard comp")
    rapidash=bool(re.search(r"\brapidash\b",lower) and "expedition" in lower
                 and re.search(r"(?:#\s*)?62\s*/\s*165",lower))
    if rapidash:
        score+=90
        reasons.append("PSA10 non-holo #62 sold-market reference exists; offered finish still unverified")
        warnings.append("must confirm #62 non-holo vs #62 reverse and #26 holo")
    warnings.append("verify exact card/edition/finish/cert/front-back/surface")
    warnings.append("verify recent exact-variant PSA10 sold comps and CGC fallback")
    direct=row.get("url") or ""
    if not direct.startswith("https://www.ebay.com/itm/"):direct=""
    return dict(title=title,asking_price=asking,shipping=shipping,
                subtotal_before_tax=subtotal,source_listing_url=direct,
                manual_search_url="https://www.ebay.com/sch/i.html?_nkw="+quote_plus(title),
                original_grade_claim=grade,discovery_lane=lane,legacy_blue_claim=blue,
                gem_mint_claim=gem,mintplus_claim=mintplus,hunt_priority=score,
                research_reasons=reasons,verification_blockers=warnings,
                rapidash_like_known_exit=rapidash,
                psa10_verified_exit_median_if_exact_variant=255.99 if rapidash else None,
                sold_reference_if_exact_variant="https://www.psacard.com/cert/67848026/psa" if rapidash else "",
                estimated_psa10_probability=None,expected_profit=None,
                category="RESEARCH_ONLY_NOT_A_TRADE")

def build_queue(source_rows):
    included=[];excluded=0;seen=set()
    for row in source_rows:
        item=determine_priority(row)
        if item is None:excluded+=1;continue
        key=item["source_listing_url"] or item["title"].casefold()
        if key in seen:continue
        seen.add(key);included.append(item)
    included.sort(key=lambda x:(-x["hunt_priority"],x["subtotal_before_tax"] if x["subtotal_before_tax"] is not None else float("inf"),x["title"]))
    return included,excluded

def write_csv(path,items):
    if not items:return
    with Path(path).open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=list(items[0]))
        writer.writeheader()
        for item in items:
            writer.writerow({key:json.dumps(value) if isinstance(value,list) else
                            "" if value is None else value for key,value in item.items()})

def run(source_path,output):
    with Path(source_path).open(encoding="utf-8-sig",newline="") as f:
        source=list(csv.DictReader(f))
    queue,excluded=build_queue(source)
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    write_csv(out/"discovery_all_research.csv",queue)
    write_csv(out/"discovery_top20_inspect.csv",queue[:20])
    write_csv(out/"discovery_top50_inspect.csv",queue[:50])
    write_csv(out/"discovery_top20_searches.csv",[
        dict(title=x["title"],query_url=x["manual_search_url"],
             direct_item_url=x["source_listing_url"],
             next_step="Research exact PSA10 sold comps; then item URL, cert, and slab photos")
        for x in queue[:20]])
    result=dict(input_rows=len(source),investigation_queue=len(queue),
                blue_gem_mint95_claims=sum(x["discovery_lane"]=="legacy_blue_gem_mint95_claim" for x in queue),
                mint_plus_separate=sum(x["discovery_lane"]=="mint_plus95_separate" for x in queue),
                cgc9_separate=sum(x["discovery_lane"]=="cgc9_separate" for x in queue),
                excluded_rows=excluded,top20_investigation=min(20,len(queue)),
                verified_profit_ranked=0,probabilities_assumed=0,money_committed=0,
                note="Title-based discovery hypothesis only; full trade approval in scanner.high_upside")
    (out/"discovery_summary.json").write_text(json.dumps(result,indent=2)+"\n")
    return result

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--leads",required=True);p.add_argument("--output",default="outputs/discovery_hunt")
    a=p.parse_args(argv)
    print(json.dumps(run(a.leads,a.output)))

if __name__=="__main__":main()
