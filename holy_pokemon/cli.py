"""Local read-only research and what-if CLI. Never makes purchases or API requests."""
import argparse
import json
from pathlib import Path
from .fredy_business import monthly_analysis, inspect_transport, operating_rules
from .strategy_engine import compare, research_signal, budget_check

def main(argv=None):
    p=argparse.ArgumentParser(prog="holy_pokemon",description="Research-only Holy Pokémon")
    sub=p.add_subparsers(dest="command",required=True)
    m=sub.add_parser("monthly",help="Analyze source-reported February–September financial ledger")
    m.add_argument("--csv",default="research/fredy_monthly_2026.csv")
    a=sub.add_parser("inspect-transport",help="Audit the user-supplied 18-source compact data ZIP")
    a.add_argument("--zip",required=True)
    sub.add_parser("rules",help="Source-grounded Fredy operating rules")
    e=sub.add_parser("evaluate",help="Compare explicit grades and exit branches, from JSON file")
    e.add_argument("--file",required=True,help="JSON: {listing:{...}, routes:[...], optional candidate:{...}}")
    args=p.parse_args(argv)
    if args.command=="monthly": result=monthly_analysis(args.csv)
    elif args.command=="inspect-transport":result=inspect_transport(args.zip)
    elif args.command=="rules":result={"operating_rules":operating_rules()}
    else:
        doc=json.loads(Path(args.file).read_text(encoding="utf-8"))
        result={"scenarios":compare(doc["listing"],doc["routes"]),
            "candidate":research_signal(doc.get("candidate",doc["listing"])),
            "budget":budget_check(doc.get("commitments",[]))}
    print(json.dumps(result,indent=2,ensure_ascii=False))
    return 0
