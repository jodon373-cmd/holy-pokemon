"""Read-only eBay Browse discovery; isolated from valuation and execution."""

import base64
from datetime import datetime, timezone, timedelta
import hashlib
import json
import os
from pathlib import Path
import stat
import time
import threading
import re
from decimal import Decimal, InvalidOperation
from email.utils import parsedate_to_datetime

_TOKEN_CACHE = {}
_TOKEN_LOCK = threading.RLock()
from urllib.parse import urlencode, urlparse, quote
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError
from .provider_common import public_url, timestamp


class EbayError(RuntimeError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def transport(method, url, headers, data=None):
    """Only official API host; never follow a credential-bearing redirect."""
    p = urlparse(url)
    if p.scheme != "https" or p.netloc != "api.ebay.com":
        raise EbayError("Unsupported API endpoint")
    if (
        method not in ("GET", "POST")
        or method == "POST"
        and p.path != "/identity/v1/oauth2/token"
        or method == "GET"
        and not p.path.startswith("/buy/browse/v1/")
    ):
        raise EbayError("Only token creation and read-only discovery requests allowed")
    from .ebay_network import context, failure, NetworkProblem
    from urllib.request import HTTPSHandler

    request = Request(url, data=data, headers=headers, method=method)
    try:
        with build_opener(NoRedirect, HTTPSHandler(context=context())).open(
            request, timeout=20
        ) as response:
            return response.status, dict(response.headers), json.load(response)
    except HTTPError as exc:
        try:
            payload = json.loads(exc.read(65536))
        except (ValueError, OSError):
            payload = {}
        return exc.code, {}, safe_errors(payload)
    except (OSError, __import__("urllib.error", fromlist=["URLError"]).URLError) as exc:
        raise failure(exc) from None
    except (ValueError, UnicodeError):
        raise NetworkProblem("RESPONSE") from None


def safe_errors(payload):
    """Only fixed OAuth codes/numeric provider IDs, never raw reflected messages."""
    allowed = {
        "invalid_client",
        "invalid_scope",
        "invalid_request",
        "unauthorized_client",
        "unsupported_grant_type",
        "temporarily_unavailable",
        "server_error",
    }
    out = {}
    if isinstance(payload, dict):
        if payload.get("error") in allowed:
            out["error"] = payload["error"]
        out["errors"] = [
            {"errorId": int(e["errorId"])}
            for e in (payload.get("errors") or [])
            if isinstance(e, dict) and str(e.get("errorId", "")).isdigit()
        ]
    return out


def credentials(path=None):
    if path:
        p = Path(path)
        if p.is_symlink() or stat.S_IMODE(p.stat().st_mode) & 0o077:
            raise EbayError(
                "Credential file must be private (chmod 600), not a symlink"
            )
        if p.suffix == ".env":
            from .ebay_config import read_env_file

            values = read_env_file(p)
            cid, secret = values.get("EBAY_CLIENT_ID"), values.get("EBAY_CLIENT_SECRET")
        else:
            values = json.loads(p.read_text())
            cid, secret = values.get("client_id"), values.get("client_secret")
    else:
        cid, secret = (
            os.environ.get("EBAY_CLIENT_ID"),
            os.environ.get("EBAY_CLIENT_SECRET"),
        )
    if not cid or not secret:
        raise EbayError(
            "Production credentials unavailable; account approval/setup required"
        )
    return cid, secret


def discovery_row(item, retrieved):
    url = public_url(item["itemWebUrl"])
    if urlparse(url).hostname not in ("ebay.com", "www.ebay.com"):
        raise EbayError("Unexpected listing link host")
    price = item.get("price") or {}
    currency = price.get("currency")
    options = item.get("shippingOptions") or []
    shipping = options[0].get("shippingCost", {}) if len(options) == 1 else {}
    # An ambiguous selection or currency is not free shipping.
    ship = shipping.get("value") if shipping.get("currency") == currency else None
    images = [
        x["imageUrl"]
        for x in [item.get("image", {}), *(item.get("additionalImages") or [])]
        if x.get("imageUrl")
    ]
    aspects = {
        str(a.get("name", "")).casefold(): a.get("value")
        for a in item.get("localizedAspects", [])
        if isinstance(a, dict)
    }
    certificate = aspects.get("certification number") or aspects.get(
        "certification_number"
    )
    auction = "AUCTION" in item.get("buyingOptions", [])
    return dict(
        listing_id=item["itemId"],
        title=item.get("title", ""),
        url=url,
        asking_price=price.get("value")
        if not auction or "FIXED_PRICE" in item.get("buyingOptions", [])
        else None,
        currency=currency,
        shipping=ship,
        shipping_options=options,
        buying_options=item.get("buyingOptions", []),
        auction_deadline=item.get("itemEndDate"),
        bid_count=item.get("bidCount"),
        current_bid=item.get("currentBidPrice"),
        image_urls=images,
        source="ebay_browse",
        retrieved_at=retrieved,
        observed_at=retrieved[:10],
        dataset="real",
        evidence_kind="active_listing_discovery_only",
        exact_identity_verified=False,
        certification_number=certificate,
        seller_aspects=aspects,
        availability=item.get("estimatedAvailabilities"),
        item_end_date=item.get("itemEndDate"),
        grade=None,
        slab_generation="unknown",
        purchase_tax_pct=None,
        buyer_premium_pct=None,
        actionable=False,
        valuation_eligible=False,
        probability_psa10=None,
    )


class EbayBrowse:
    def __init__(
        self,
        db,
        *,
        enabled=False,
        production_approved=False,
        client_id=None,
        client_secret=None,
        request=transport,
        daily_limit=30,
        max_pages=3,
        sleep=time.sleep,
        now=None,
        page_size=10,
        run_limit=None,
    ):
        if not 1 <= daily_limit <= 5000 or not 1 <= max_pages <= 50:
            raise ValueError("Invalid request/page limit")
        self.db, self.enabled, self.approved = db, enabled, production_approved
        self.cid, self.secret = client_id, client_secret
        self.live_transport = request is transport
        self.request, self.daily_limit, self.max_pages, self.sleep = (
            request,
            daily_limit,
            max_pages,
            sleep,
        )
        self.now = now or (lambda: datetime.now(timezone.utc))
        if run_limit is not None and (not isinstance(run_limit,int) or not 1<=run_limit<=5000):
            raise ValueError('Run limit must be1..5000')
        self.run_limit,self.run_calls=run_limit,0
        self.token = None
        self.expires = None
        self.on_usage = None
        self.page_size = page_size
        if not 1 <= page_size <= 200:
            raise ValueError("Page size must be 1..200")
        db.execute(
            "CREATE TABLE IF NOT EXISTS ebay_api_usage (requested_at TEXT,status INTEGER,cooldown_until TEXT)"
        )
        db.execute(
            "CREATE TABLE IF NOT EXISTS ebay_discovery_cache (cache_key TEXT PRIMARY KEY,retrieved_at TEXT,payload TEXT)"
        )

    def _observe(self, api, status, payload=None, **extra):
        if self.on_usage:
            usage_api = getattr(self,'request_kind','browse') if api=='browse' else api
            self.on_usage(usage_api, status, self.live_transport)
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS ebay_provider_events (at TEXT, api TEXT, status INTEGER, detail TEXT)"
        )
        detail = {
            **safe_errors(payload or {}),
            "verified_production_transport": self.live_transport,
            **extra,
        }
        with self.db:
            self.db.execute(
                "INSERT INTO ebay_provider_events VALUES (?,?,?,?)",
                (self.now().isoformat(), api, status, json.dumps(detail)),
            )

    def _call(self, method, url, headers, data=None, _attempt=0):
        now = self.now()
        if self.run_limit is not None and self.run_calls>=self.run_limit:
            raise EbayError('Per-run request cap reached')
        # Reserve quota before I/O. Separate workers cannot all pass the same last-slot check.
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            used = self.db.execute(
                "SELECT count(*) FROM ebay_api_usage WHERE substr(requested_at,1,10)=?",
                (now.date().isoformat(),),
            ).fetchone()[0]
            cooldown = self.db.execute(
                "SELECT max(cooldown_until) FROM ebay_api_usage"
            ).fetchone()[0]
            if used >= self.daily_limit:
                raise EbayError("Local daily request cap reached")
            if cooldown and timestamp(cooldown) > now:
                raise EbayError("eBay rate-limit cooldown remains active")
            reservation = self.db.execute('INSERT INTO ebay_api_usage VALUES(?,?,?)',
                (now.isoformat(),-1,None)).lastrowid
        self.sleep(1)
        self.run_calls+=1
        try:
            status, headers, payload = self.request(method, url, headers, data)
        except Exception as exc:
            with self.db:
                self.db.execute('UPDATE ebay_api_usage SET status=0 WHERE rowid=?',(reservation,))
            self._observe(
                "oauth" if method == "POST" else "browse", 0, network_error="CONNECTION"
            )
            from .ebay_network import NetworkProblem

            if isinstance(exc, NetworkProblem):
                raise
            raise EbayError(
                "eBay request failed; response and credentials omitted"
            ) from None
        self._observe(
            "oauth" if method == "POST" else "browse",
            status,
            payload,
            **(
                {"expires_in": int(payload.get("expires_in", 0))}
                if method == "POST" and status == 200
                else {}
            ),
        )
        until = None
        if status == 429:
            retry = headers.get("Retry-After") or headers.get("retry-after")
            try:
                delay = max(1, int(retry))
            except (ValueError, TypeError):
                try:
                    delay = max(1, int((parsedate_to_datetime(retry) - now).total_seconds()))
                except (ValueError, TypeError, OverflowError):
                    delay = 3600
            until = (now + timedelta(seconds=delay)).isoformat()
        with self.db:
            self.db.execute('UPDATE ebay_api_usage SET status=?,cooldown_until=? WHERE rowid=?',
                            (status,until,reservation))
        if status in (401, 403):
            path = self.db.execute("PRAGMA database_list").fetchone()[2]
            with _TOKEN_LOCK:
                _TOKEN_CACHE.pop(
                    (path, hashlib.sha256(str(self.cid).encode()).hexdigest()), None
                )
            self.token = None
            self.expires = None
        if status != 200:
            raise EbayError(
                f"eBay stopped: HTTP {status}; codes={safe_errors(payload)}; no automatic retry"
            )
        return payload

    def _token(self):
        path = self.db.execute("PRAGMA database_list").fetchone()[2]
        key = (
            (path, hashlib.sha256(str(self.cid).encode()).hexdigest()) if path else None
        )
        with _TOKEN_LOCK:
            if key and key in _TOKEN_CACHE:
                self.token, self.expires = _TOKEN_CACHE[key]
            token = self._mint_token()
            if key:
                _TOKEN_CACHE[key] = (self.token, self.expires)
            return token

    def _mint_token(self):
        if not self.token or self.expires <= self.now() + timedelta(seconds=60):
            auth = base64.b64encode((self.cid + ":" + self.secret).encode()).decode()
            result = self._call(
                "POST",
                "https://api.ebay.com/identity/v1/oauth2/token",
                {
                    "Authorization": "Basic " + auth,
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                urlencode(
                    {
                        "grant_type": "client_credentials",
                        "scope": "https://api.ebay.com/oauth/api_scope",
                    }
                ).encode(),
            )
            if not result.get("access_token") or int(result.get("expires_in", 0)) <= 60:
                raise EbayError("Invalid token response")
            self.token = result["access_token"]
            self.expires = self.now() + timedelta(seconds=int(result["expires_in"]))
        return self.token

    def search_page(self, query, *, offset=0, refresh=False, filters=None,
                    sort=None, aspect_filter=None, fieldgroups=None, max_price=None,
                    condition_ids=None, condition_descriptors=None,
                    expected_grader=None, expected_grade=None):
        """One authorized, persistently cached page with an explicit resume cursor."""
        if not self.enabled or not self.approved or not self.cid or not self.secret:
            raise EbayError("Live Browse requires explicit enablement, approved Production access and local credentials")
        if not isinstance(query, str) or not query.strip() or len(query) > 100:
            raise ValueError("Query must contain 1..100 characters")
        if '*' in query:
            raise ValueError('Browse does not support wildcard searches; use (term1,term2) OR groups')
        if not isinstance(offset, int) or offset < 0 or offset >= 10000 or offset % self.page_size:
            raise ValueError("Offset must be a page-size multiple below 10000")
        params = dict(q=query, category_ids="183454", limit=self.page_size, offset=offset)
        filters = dict(filters or {})
        if condition_ids:
            ids = [str(v) for v in condition_ids]
            if not all(v.isdigit() for v in ids):
                raise ValueError('Condition IDs must be numeric')
            filters['conditionIds'] = '{' + '|'.join(ids) + '}'
        options = set(re.findall(r'[A-Z_]+', filters.get('buyingOptions', '')))
        if {'FIXED_PRICE', 'AUCTION'} <= options:
            raise ValueError('Run FIXED_PRICE and AUCTION as separate passes')
        if sort is not None:
            if sort not in {'newlyListed', 'endingSoonest', 'price', '-price'}:
                raise ValueError('Unsupported Browse sort')
            params['sort'] = sort
        if aspect_filter:
            if isinstance(aspect_filter, dict):
                def safe_aspect(value):
                    value = str(value)
                    if any(c in value for c in '{}|,:'):
                        raise ValueError('Aspect delimiter in value')
                    return value
                aspects = ['categoryId:183454']
                for key, values in sorted(aspect_filter.items()):
                    values = values if isinstance(values, (list, tuple)) else [values]
                    aspects.append(safe_aspect(key)+':{'+ '|'.join(safe_aspect(v) for v in values)+'}')
                params['aspect_filter'] = ','.join(aspects)
            elif str(aspect_filter).startswith('categoryId:183454,'):
                params['aspect_filter'] = str(aspect_filter)
            else:
                raise ValueError('aspect_filter must include categoryId:183454')
        if fieldgroups is not None:
            if fieldgroups != 'EXTENDED':
                raise ValueError('Only EXTENDED fieldgroups is supported')
            params['fieldgroups'] = fieldgroups
        if max_price is None and 'price' in filters:
            match = re.fullmatch(r'\[(?:[\d.]+)?\.\.([\d.]+)\]', filters['price'])
            max_price = match.group(1) if match else None
        if max_price is not None:
            try:
                cap = Decimal(str(max_price))
                if not cap.is_finite() or cap < 0:
                    raise ValueError('Invalid max price')
            except InvalidOperation:
                raise ValueError('Invalid max price') from None
            filters['price'] = '[..'+str(cap)+']'
            filters.setdefault('priceCurrency', 'USD')
        if filters:
            allowed = {"price", "priceCurrency", "buyingOptions", "itemLocationCountry", 'conditionIds', 'itemEndDate'}
            if not isinstance(filters, dict) or set(filters) - allowed:
                raise ValueError("Unsupported official Browse filter")
            params["filter"] = ",".join(str(k) + ":" + str(v) for k, v in filters.items())
        url = "https://api.ebay.com/buy/browse/v1/item_summary/search?" + urlencode(params)
        key = hashlib.sha256((self.cid + url).encode()).hexdigest()
        cached = self.db.execute("SELECT retrieved_at,payload FROM ebay_discovery_cache WHERE cache_key=?", (key,)).fetchone()
        now = self.now()
        if not refresh and cached and 0 <= (now - timestamp(cached[0])).total_seconds() < 18000:
            payload = json.loads(cached[1])
            # Older application caches contain just rows; their exact totals are unknown.
            if isinstance(payload, list):
                payload = dict(rows=payload, total=None, has_more=len(payload) == self.page_size)
            return self._precision_rows(dict(payload, cache_hit=True), max_price=max_price,
                expected_grader=expected_grader, expected_grade=expected_grade,
                condition_descriptors=condition_descriptors)
        self.request_kind = 'search'
        result = self._call("GET", url, {
            "Authorization": "Bearer " + self._token(),
            "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
        })
        items = result.get("itemSummaries", [] if result.get("total") == 0 else None)
        if not isinstance(items, list):
            raise EbayError("Invalid listing response")
        retrieved = self.now().isoformat()
        rows = []
        rejected_items = 0
        for item in items:
            try:
                rows.append(dict(discovery_row(item,retrieved),
                    condition_id=item.get('conditionId'), condition_descriptors=item.get('conditionDescriptors', []),
                    production_api_verified=self.live_transport,marketplace='EBAY_US'))
            except (ValueError,KeyError,TypeError,EbayError):
                # Fail closed for one malformed/credential-bearing listing while
                # preserving valid siblings and the authorized pagination cursor.
                rejected_items += 1
        total = result.get("total")
        total = total if isinstance(total, int) and total >= 0 else None
        has_more = bool(items) and (offset + self.page_size < total if total is not None else len(items) == self.page_size)
        payload = dict(rows=rows, total=total, has_more=has_more,
                       items_received=len(items),rejected_items=rejected_items,
                       window_exhausted=has_more and offset + self.page_size >= 10000)
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO ebay_discovery_cache VALUES (?,?,?)", (key, retrieved, json.dumps(payload)))
        return self._precision_rows(dict(payload, cache_hit=False), max_price=max_price,
            expected_grader=expected_grader, expected_grade=expected_grade,
            condition_descriptors=condition_descriptors)

    @staticmethod
    def _precision_rows(payload, *, max_price=None, expected_grader=None,
                        expected_grade=None, condition_descriptors=None):
        """Local checks also apply to cache hits. Descriptor IDs are not an undocumented wire filter."""
        from .title_parser import parse_title
        from .compsniper import money
        kept, rejected = [], 0
        for source in payload['rows']:
            row = dict(source)
            amount = money(row.get('asking_price') or row.get('current_bid'))
            if max_price is not None and (row.get('currency')!='USD' or amount is None or amount > Decimal(str(max_price))):
                rejected += 1
                continue
            parsed = parse_title(row.get('title', ''))
            if ((expected_grader and parsed.grader != expected_grader.upper()) or
                (expected_grade and parsed.grade != str(expected_grade))):
                rejected += 1
                continue
            if condition_descriptors:
                actual = {str(x.get('name')): x.get('values', []) for x in row.get('condition_descriptors', [])}
                # Search summaries may omit descriptors; preserve that uncertainty for item-detail review.
                row['condition_descriptor_check'] = 'VERIFIED' if all(
                    str(v) in {str(z.get('content') or z.get('value') or z) if isinstance(z, dict) else str(z)
                               for z in actual.get(str(k), [])}
                    for k, v in condition_descriptors.items()) else 'UNVERIFIED_OR_MISMATCH'
                row['requested_condition_descriptors'] = condition_descriptors
            kept.append(row)
        return dict(payload, rows=kept, local_precision_rejections=rejected)

    def search_passes(self, query, *, max_price=None, include_auctions=True, **kwargs):
        """Distinct BIN/new and auction/ending passes; never send BEST_OFFER as a third option."""
        output = []
        for option, sort in [('FIXED_PRICE', 'newlyListed'), ('AUCTION', 'endingSoonest')]:
            if option == 'AUCTION' and not include_auctions:
                continue
            for row in self.search(query, filters={'buyingOptions': '{'+option+'}'},
                                   sort=sort, max_price=max_price, **kwargs):
                output.append(dict(row, discovery_pass=option))
        return output

    def search(self, query, *, refresh=False, filters=None, **precision):
        output, seen = [], set()
        for page in range(self.max_pages):
            result = self.search_page(query, offset=page * self.page_size, refresh=refresh, filters=filters, **precision)
            for row in result["rows"]:
                if row["listing_id"] not in seen:
                    output.append(row)
                    seen.add(row["listing_id"])
            if not result["has_more"] or result.get("window_exhausted"):
                break
        return output

    def item(self, item_id):
        """Read-only official item detail, separately cached from search asks."""
        import re

        if not self.enabled or not self.approved or not self.cid or not self.secret:
            raise EbayError("Live Browse requires approved access and credentials")
        if not re.fullmatch(r"v1\|[0-9]{5,20}\|[0-9]{1,20}", item_id):
            raise ValueError("Invalid Browse item id")
        url = "https://api.ebay.com/buy/browse/v1/item/" + quote(item_id, safe="")
        key = hashlib.sha256((self.cid + url).encode()).hexdigest()
        cached = self.db.execute(
            "SELECT retrieved_at,payload FROM ebay_discovery_cache WHERE cache_key=?",
            (key,),
        ).fetchone()
        if cached and 0 <= (self.now() - timestamp(cached[0])).total_seconds() < 3600:
            return json.loads(cached[1])
        self.request_kind = 'item_detail'
        payload = self._call(
            "GET",
            url,
            {
                "Authorization": "Bearer " + self._token(),
                "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
            },
        )
        row = discovery_row(payload, self.now().isoformat())
        row["seller"] = {
            k: (payload.get("seller") or {}).get(k)
            for k in ("username", "feedbackPercentage", "feedbackScore")
        }
        row["returns"] = payload.get("returnTerms")
        row["condition"] = payload.get("condition")
        row["vault_status"] = "unknown"
        row["vault_eligible"] = "unknown"
        row["psa_consignment_listing"] = "unknown"
        with self.db:
            self.db.execute(
                "INSERT OR REPLACE INTO ebay_discovery_cache VALUES(?,?,?)",
                (key, row["retrieved_at"], json.dumps(row)),
            )
        return row


def main(argv=None):
    import argparse
    from contextlib import closing
    import sqlite3, csv

    connect = sqlite3.connect

    def export_csv(path, rows, fields):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--query", action="append", default=[])
    p.add_argument("--database", default="outputs/ebay_discovery.sqlite")
    p.add_argument("--output", default="outputs/ebay_discovery.csv")
    p.add_argument("--credentials-file")
    p.add_argument("--live", action="store_true")
    p.add_argument("--production-approved", action="store_true")
    p.add_argument("--status", action="store_true")
    p.add_argument("--max-pages", type=int, default=1)
    a = p.parse_args(argv)
    if a.status:
        try:
            credentials(a.credentials_file)
            ready = True
        except (EbayError, FileNotFoundError):
            ready = False
        print(
            json.dumps(
                {
                    "credentials_available": ready,
                    "live_requested": a.live,
                    "production_approval_confirmed": a.production_approved,
                    "mode": "listing_discovery_only",
                    "pricing_integration": False,
                    "buying_enabled": False,
                }
            )
        )
        return
    if not a.live or not a.production_approved:
        p.error("Live and approved Production access must be explicitly confirmed")
    if not a.query:
        p.error("At least one query required")
    try:
        cid, secret = credentials(a.credentials_file)
        Path(a.database).parent.mkdir(parents=True, exist_ok=True)
        with closing(connect(a.database)) as db:
            client = EbayBrowse(
                db,
                enabled=True,
                production_approved=True,
                client_id=cid,
                client_secret=secret,
                max_pages=a.max_pages,
            )
            rows = {}
            for query in a.query:
                for row in client.search(query):
                    rows[row["listing_id"]] = row
            export_csv(
                a.output,
                list(rows.values()),
                (
                    "listing_id",
                    "title",
                    "url",
                    "asking_price",
                    "shipping",
                    "currency",
                    "retrieved_at",
                    "valuation_eligible",
                ),
            )
        print(f"Discovery listings: {len(rows)}. Valuation/execution disabled.")
    except EbayError as exc:
        p.exit(1, str(exc) + "\n")


if __name__ == "__main__":
    main()
