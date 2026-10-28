# Holy Pokémon — automatic research discovery (October 28, 2026)

## What this actually does

- Runs **permitted eBay Browse API** searches for graded vintage Pokémon cards and auctions using a local, quota-limited scheduler.
- Uses `sort=newlyListed` for incoming fixed-price listings and `sort=endingSoonest` for time-sensitive **research** auction monitoring. The program never submits a bid.
- Takes user-supplied listing CSVs when no approved/working API key is available.
- Ranks **research interest only**. It never labels an ask a sale, calculates fictitious profits, or claims grading accuracy.
- Keeps historical first/last sightings, detects price changes, deduplicates by listing ID, outputs lead CSV/JSON and append-only alert events.
- Optionally sends a local macOS notification, and best-effort syncs lead records into the newer `market.import_rows(Store, 'lead', ...)` integration when that local module exists. The original linked Fredy dataset is untouched.
- Adds a standalone **single-cert PSA verification** helper with a private token. That is neither a general sold-comps API nor an authorized bulk PSA dataset download.

## Launch

**From the existing Holy Pokémon repo folder with its Python virtual environment active:**

Optional Mac double-click launcher: `mac/Start_Holy_Autodiscovery.command`. To use it, create `~/.config/holy_pokemon/ebay.json` containing `{"client_id":"YOUR_PRODUCTION_APP_ID","client_secret":"YOUR_PRODUCTION_CERT_ID"}` and set its permissions with `chmod 600 ~/.config/holy_pokemon/ebay.json`. Do not commit this file. The launcher opens only the automatic **research** loop and requires the Mac to remain running; it does not replace the main dashboard launcher.

```bash
# Zero-credential OFFLINE run with your own exported listings:
python3 -m holy_pokemon.automated_discovery --import-csv ~/Downloads/holy_listings.csv --sync-app --notify-mac --once

# Check live eBay Browse with one scheduled search (credentials must be configured):
python3 -m holy_pokemon.automated_discovery --live --authorized-keyset --queries-per-cycle 1 --daily-api-limit 30 --sync-app --once

# Repeat scheduled monitoring while the Mac and terminal are running:
python3 -m holy_pokemon.automated_discovery --live --authorized-keyset --queries-per-cycle 2 --daily-api-limit 30 --interval-minutes 30 --min-query-hours 6 --sync-app --notify-mac --watch

# PSA: verify ONE PSA certificate; do not paste the bearer token into code/chat.
python3 -m holy_pokemon.psa_cert_check 12345678
```

For eBay, configure `EBAY_CLIENT_ID` and `EBAY_CLIENT_SECRET` as private shell environment variables, or use a strictly private **0600** JSON credentials file accepted by the pre-existing `ebay_browse.credentials()` helper. To use PSA, set `PSA_ACCESS_TOKEN` privately on the local Mac. **Never paste either token into public code or GitHub.**

**CSV import schema:** Required: `title`, `source_url` (https://www.ebay.com/itm/...), `ask`. Recommended: `listing_id`, `currency`, `image_urls`, `shipping`, `observed_at`. No manufactured sold transactions. Use your own authorized saved-search / exported listing inputs.

**Outputs:** `outputs/auto_discovery/research_leads.csv`, `research_leads.json`, `listing_alerts.jsonl`; state `outputs/holy_auto_discovery.sqlite`. If Codex's newer local `market.py` / `store.py` are installed, `--sync-app` attempts to import research leads into the dashboard's shared local store. This bridge needs validation against that unpushed Mac branch; if unavailable, the export still works.

## Research integrations that remain separate

**For correct trade valuation:** import official completed-sale evidence through the project's sold-comps pipeline. Active eBay asking prices, TCGplayer raw-card market rates, model opinions and PSA cert results are *not* verified PSA 10 sold prices. PSA public API supports individual cert verification, not a general portfolio/PSA Vault API. The AI grader remains an unvalidated prototype until independent eligible training photos/outcomes exist.

## eBay access reality

- eBay's Partner Network developer questionnaire explicitly states that Browse API access *does not require additional approval*; its generic Buy API guide still describes broader production eligibility. Test the authorized production keyset; do not assume success or failure solely from documentation.
- The official default **Browse limit is 5,000 calls/day**, but the program caps itself at 30 by default, accounting for OAuth token calls. Higher quota can be requested through eBay's Application Growth Check.
- Marketplace Insights **sold comps** and Offer bidding are distinct **limited-release** services. This implementation does not call them.
- Official Trading `PlaceOffer` docs prohibit automatically scheduled calls such as sniping, and eBay is no longer accepting new PlaceOffer applications. **No automatic bidding, checkout, purchase, CAPTCHA bypass, multiple-account rotations, cookies, or undocumented APIs.**
- Browse item photos are never modified; record image URLs as evidence pointers, respecting provider license requirements. Sold comps must be independently licensed and exact variant matched.

## Reviewed external projects (patterns reviewed, code NOT copied)

1. `YaroslawBagriy/psa-auction-agent` — PSA-store seller filtering, timed auction discovery and human-reviewed max-bid route. Good conceptual architecture; not a reason to turn on unattended bids.
2. `clawdr/pokemon-scanner` — eBay Browse + TCG ID normalization + separate sold-data provider + dedup/Discord alerts. Its market integrations require separate paid or approved access.
3. `MuhammadMuazzain/ebay-pokemon-automation` — fuzzy title normalization, background scheduler, bargain scoring and image fallback. Raw-card TCG prices alone cannot value graded vintage arbitrage.
4. `dnadeau/sports-card-manager` — provider adapter split, and explicit warning that Browse does not return sold comps; avoid its disabled-by-default HTML scraper.
5. `vaberry/ebay-api-client` — clear distinction between Browse (active listings) and restricted Marketplace Insights (sold comps).
6. `heyalexej/bidkit` — safe app OAuth and file-token caching concepts. No need to copy a full SDK into the project.
7. `VincenzoImp/ebay-sniper-bot` / `figurophobia/gixenpy` — examples of browser automation or third-party sniping tools, **not** approved direct eBay API discovery or a sustainable data source.

No source code from these repositories was imported; ideas were reimplemented using the existing Holy Pokémon API adapter. Check each repository's license before incorporating third-party source in the future.

Official sources:
- https://partnernetwork.ebay.com/page/developer-questionnaire
- https://developer.ebay.com/develop/api/buy/api_call_limits
- https://developer.ebay.com/api-docs/buy/static/api-browse.html
- https://developer.ebay.com/api-docs/buy/static/ref-buy-browse-filters.html
- https://developer.ebay.com/devzone/XML/docs/reference/ebay/PlaceOffer.html
- https://developer.ebay.com/api-docs/buy/api-offer.html
- https://www.psacard.com/publicapi/documentation

## Optional pricing providers (separate license checks)

- **PriceCharting official Prices API** offers paid current grade/value indices; **not transaction-level historical sold comps**. Its Legendary CSV dump supports efficient batch internal valuation where licensed. Current limits: 1 call/sec, CSV 1 per 10 minutes; no use after subscription ends. https://www.pricecharting.com/api-documentation
- **PokemonPriceTracker** advertises multi-grader sales summaries and a developer API. However, its site says **commercial use requires the Business plan** and individual sold-listing detail availability depends on tier. Validate coverage for *legacy CGC label eras, exact edition, holo/reverse, stamp, and English/Japanese* before buying. https://www.pokemonpricetracker.com/api-reference
- Neither service should be automatically subscribed to or billed by the bot without the owner's explicit budget approval. Research-lead rankings are not "verified opportunity" profits.

## Unified dashboard and repository integration

This is a native `holy_pokemon` package module, not a separate application.
After the GitHub feature branch is integrated into the Mac's existing Codex
working branch, use `--sync-app` to place active-listing research leads into the
existing Store/market import route. The import must remain tagged as **active
listing**, not a sold comp or purchase-ready deal.

The dashboard can also display a bounded, read-only feed without duplicating
marketplace calls:

```python
from holy_pokemon.discovery_service import discovery_snapshot
state["discovery"] = discovery_snapshot()
```

The locally developed nine-screen dashboard was not available on the GitHub
`main` branch at integration time. **Do not overwrite that newer UI with the
old GitHub dashboard**. Add a Discovery/Research view wired to this state object
and/or the existing lead queue after merging. This step requires the Mac's
current unpushed local code. The HTTP/CLI discovery module and storage work
without UI wiring; the exact current UI integration is not yet verified.

### Integration branch instructions for existing Codex session

1. Preserve worktree changes and record the current local feature branch.
2. Fetch `feat/automated-research-discovery` from the existing `origin`.
3. Merge/cherry-pick reviewed changes into the current local branch (without
resetting or overwriting files); resolve conflicts by retaining the latest Mac
app and importing the additive discovery modules.
4. Run `python -m unittest discover -s tests -v` and verify the Mac launcher.
5. Start a safe offline discovery CSV import; verify the resulting lead appears
in the application's Research/Discovery queue and retains its source URL.
6. Test one official authorized eBay Browse query when keys are available.
7. Confirm the UI explicitly distinguishes active asks, actual sold comps,
research ranking, and manual purchase-readiness decisions.

Do not merge GitHub's older `main` implementation over the newer local
worktree. If local Codex already created equivalent modules, reconcile changes
rather than running competing discovery daemons.