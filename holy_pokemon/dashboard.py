"""Mac-local read-only web dashboard for Holy Pokémon's working core.

No external API calls, transactions, remote binding or secrets.
"""
from __future__ import annotations
import json
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse,parse_qs

from .fredy_business import monthly_analysis, operating_rules
from .strategy_engine import compare,research_signal,budget_check
from .vault_engine import withdrawal_quote,psa_consignment_net,partner_offer_net

ROOT = Path(__file__).resolve().parents[1]
HOME = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Holy Pokémon • Research Console</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root{font-family:system-ui,-apple-system,sans-serif;color:#eaf4f6;background:#0d1724}
body{max-width:1120px;margin:auto;padding:24px}h1{font-size:clamp(26px,5vw,42px)}
p{line-height:1.6;color:#afc1cc}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}
section,.tile{background:#162638;border:1px solid #27425a;border-radius:16px;padding:18px;margin:15px 0}
.tile strong{display:block;font-size:27px}small{color:#a6bbc7}code,pre{background:#0a141d;padding:10px;border-radius:8px;overflow:auto}
button{background:#17c0a6;color:#062018;border:0;border-radius:10px;padding:11px 15px;font-weight:700;cursor:pointer}
input,textarea{background:#0c1b29;color:#fff;border:1px solid #4d6d83;border-radius:9px;padding:10px;width:100%;box-sizing:border-box}
label{display:block;margin:10px 0}a{color:#76e6cf}header{display:flex;gap:16px;align-items:center}
.note{color:#ffe5a3}.ok{color:#76e6cf}.muted{color:#97adbb}
</style></head><body>
<header><div style="font-size:34px">🃏</div><div><h1>Holy Pokémon</h1><small>Research-led grading &amp; cash-flow console</small></div></header>
<p>Eight-month Fredy research • All outcomes tied to their sources • Read-only • No purchase automation</p>
<div class="cards">
<div class="tile"><small>Creator-reported cards sold, Feb–Sep</small><strong>506</strong></div>
<div class="tile"><small>Creator-reported revenue</small><strong>$444,671</strong></div>
<div class="tile"><small>Creator-reported pre-tax profit</small><strong>$230,594</strong></div>
</div>
<section><h2>Research and model status</h2><p class="note">Financials above are source-reported, not independently audited. No live eBay / private PSA Vault API or validated trained AI grading weights are connected here.</p>
<p><a href="/api/monthly">Monthly ledger JSON</a> · <a href="/api/rules">Business strategy rules</a> · <a href="/api/status">System status</a></p></section>
<section><h2>PSA Vault withdrawal what-if</h2>
<div class="cards"><label>Declared shipment value (USD)<input id="val" type="number" value="600" min="0"></label>
<label>Number of items<input id="count" type="number" value="1" min="1"></label>
<label>Items vaulted under 90 days<input id="recent" type="number" value="0" min="0"></label>
<label>Effective date<input id="day" type="date" value="2026-10-29"></label></div>
<button onclick="quote()">Calculate sourced fees</button><pre id="vout" aria-live="polite"></pre>
<small>Official fees subject to change. Actual account quote always controls.</small></section>
<section><h2>Financial grading route comparison</h2><p>Paste a listing + branch scenario JSON. Missing fees remain unknown, not zero.</p>
<textarea id="scenario" rows="12">{
  "listing":{"ask":"100","buyer_shipping":"5","purchase_tax":"7","buyer_premium":"0"},
  "routes":[
    {"route":"sell_original","exit_price":"160","fee_pct":"10","grading":"0","grading_shipping":"0","grading_insurance":"0","upcharge":"0","outbound_shipping":"0","vault_withdrawal":"0","vault_early_fee":"0","vault_consignment_fixed":"0","holding_cost":"0","contingency":"0"},
    {"route":"cgc_gem_10","exit_price":"350","fee_pct":"10","grading":"35","grading_shipping":"20","grading_insurance":"0","upcharge":"0","outbound_shipping":"0","vault_withdrawal":"0","vault_early_fee":"0","vault_consignment_fixed":"0","holding_cost":"0","contingency":"0"}
  ],
  "candidate":{"ask":"100","possible_best_exit":"350"}
}</textarea>
<button onclick="compare()">Compare routes</button><pre id="sout" aria-live="polite"></pre>
<small>Example above is SYNTHETIC, not a real deal or proven market price.</small></section>
<section><h2>What's being built next</h2><p>Historical per-card ingestion • Authorized eBay Browse • PSA Vault collection and payout imports • Trained card-only vision model • Multi-venue liquidation and watchlists</p>
<p>Repo: <a href="https://github.com/jodon373-cmd/holy-pokemon">Holy Pokémon</a></p></section>
<script>
async function quote(){try{let q=new URLSearchParams({date:day.value,declared:val.value,count:count.value,recent:recent.value});let r=await fetch('/api/vault-withdrawal?'+q);vout.textContent=JSON.stringify(await r.json(),null,2)}catch(e){vout.textContent=String(e)}}
async function compare(){try{let r=await fetch('/api/compare',{method:'POST',headers:{'content-type':'application/json'},body:scenario.value});sout.textContent=JSON.stringify(await r.json(),null,2)}catch(e){sout.textContent=String(e)}}
</script></body></html>
"""

class Handler(BaseHTTPRequestHandler):
    def _json(self,result,status=200):
        payload=json.dumps(result,indent=2,ensure_ascii=False).encode()
        self.send_response(status);self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Cache-Control","no-store");self.send_header("Content-Length",str(len(payload)))
        self.end_headers();self.wfile.write(payload)
    def do_GET(self):
        u=urlparse(self.path)
        try:
            if u.path=="/":
                content=HOME.encode();self.send_response(200)
                self.send_header("Content-Type","text/html; charset=utf-8")
                self.send_header("Content-Length",str(len(content)))
                self.end_headers();self.wfile.write(content)
            elif u.path=="/api/monthly":self._json(monthly_analysis(ROOT/"research/fredy_monthly_2026.csv"))
            elif u.path=="/api/rules":self._json({"rules":operating_rules()})
            elif u.path=="/api/status":
                self._json({"mode":"OFFLINE_READ_ONLY","real_trained_grader":False,
                    "live_ebay":False,"vault_private_api":False,"automatic_purchases":False})
            elif u.path=="/api/vault-withdrawal":
                q={k:v[0] for k,v in parse_qs(u.query).items()}
                self._json(withdrawal_quote(asof=date.fromisoformat(q["date"]),
                    declared_usd=q["declared"],item_count=int(q["count"]),
                    recently_vaulted_count=int(q.get("recent",0)),country=q.get("country","US")))
            else:self._json({"error":"Not found"},404)
        except (KeyError,ValueError) as e:self._json({"error":str(e)},400)
    def do_POST(self):
        if self.path!="/api/compare":return self._json({"error":"Not found"},404)
        try:
            length=int(self.headers.get("Content-Length","0"))
            if not 0<length<=65536:raise ValueError("JSON request too large or missing")
            body=json.loads(self.rfile.read(length))
            routes=compare(body["listing"],body["routes"])
            self._json({"routes":routes,"research_lead":research_signal(body.get("candidate",body["listing"])),
                "capital":budget_check(body.get("commitments",[]))})
        except (ValueError,KeyError,TypeError,json.JSONDecodeError) as e:self._json({"error":str(e)},400)

def serve(port=8765):
    server=ThreadingHTTPServer(("127.0.0.1",port),Handler)
    print(f"Holy Pokémon research console: http://127.0.0.1:{port}",flush=True)
    try:server.serve_forever()
    finally:server.server_close()

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--port",type=int,default=8765)
    args=p.parse_args();serve(args.port)
