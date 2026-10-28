# Marketplace data strategy — official API first, lawful fallback always

Updated against provider documentation on 2026-10-28. Project is **research-only** by default and must never automate transactions.

## Live active listings
**eBay Browse API** supports keyword/category and image search and item details using OAuth application credentials. Access to production Buy APIs may require approval. Reuse the read-only, rate-limited, cached HTTP behavior of `reference/legacy_scanner/scanner/ebay_browse.py` after source review and new mocking tests. Do not assume developer enrollment alone establishes production approval. Sources:
- https://developer.ebay.com/api-docs/buy/static/api-browse.html
- https://developer.ebay.com/api-docs/buy/static/buy-requirements.html

Provider configuration: environment or encrypted local secret store, read-only, no credentials logged/committed, explicit API rate/credit budget, response cache with retrieved_at and freshness, backoff/429 handling, item-ID dedup, exact query audit. Missing shipping/taxes/seller trust/variant remain unknown. Never confuse active asking prices with sold prices.

## Sold comps: a different pipeline
The **Marketplace Insights** history API is a restricted / limited release; do not assume access or impersonate production scope. Browse API live results do not equal a completed-sales database. Use source dates and source type for every price. Official eBay Product Research (formerly Terapeak) exposes up to 3 years of sales info, including actual prices for accepted Best Offers, in Seller Hub. The product's existence does **not** authorize unattended scraping, extraction of a hidden API, CAPTCHA bypass, or automated session abuse.
- https://www.ebay.com/help/selling/terapeak-research/terapeak-product-research?id=4853
- https://developer.ebay.com/develop/get-started/get-started-on-a-buying-application

Build an **offline-first sold-import workflow** to accept user-provided exports and screenshots/PDFs (manual transcription/approved use), eBay Product Research findings, PSA's “sales of similar items” where legally usable, self-owned sold inventory exports, and approved provider CSVs. Each row must preserve image or source pointer, exact variant, transaction date, price basis, fee status, sale venue, seller authenticity, dedup key and confidence. A market summary/index is NOT a sale transaction. Refuse to mint fictitious individual sales from an aggregate or video.

## PSA API / PSA Vault
PSA's published public API has certificate verification by cert number, not a general-purpose PSA Vault sold-market feed. PSA Vault has listing and sales experiences but no universal public data API is assumed. Model it as `psa_vault_manual_import` and upgrade to a separate adapter **only if authorized, published API access is established**.
- https://www.psacard.com/publicapi/documentation
- https://www.psacard.com/cert

The certificate API can help verify a listing's claimed grade and card identification but cert match alone doesn't prove the photographed slab is genuine or grade likely to upgrade. Cache verification, honor terms; reject accidental cert leaks.

## Evidence alternatives, not fake APIs
Fredy's YouTube transcripts and monthly recaps are exceptional for **grading route outcomes, condition failure patterns, creator transaction claims and candidate discovery ideas**. They are not a substitute for today's eBay sold-prices or live inventory. The bot should build *reverse search queries* from source card/era/variant + grading pathways, and accept operator-supplied completed-sale evidence to close valuation gaps. Preserve distinction between creator estimated value, gross eBay sale claim and verified net payout.

## PSA Vault: UPDATED end-to-end mandate
The original minimal `psa_vault_manual_import` description above was only the fallback source adapter, **not** the full product requirement. The mandatory [PSA Vault end-to-end specification](PSA_VAULT_END_TO_END.md) includes eBay vaulted/eligible/consigned discovery, user-owned collection and custody, routes to PSA consignment auctions/Buy It Now, verified user-provided Partner Offers, withdraw and regrade decisions, effective-dated PSA fee schedule, manual official-account transfer status and Stripe payout reconciliation. Use only documented/authorized interfaces; this is an integrated complete workflow even when no general PSA Vault API exists.

## Version 1 provider deliverables
- Offline launch works with historical research ZIP + manually provided active listings and sold-comps CSV, produces clearly labeled unverified leads.
- eBay live adapter behind explicit `PRODUCTION_APPROVED` gate and mocked tests, with valid OAuth and safe budgets. Attempt live only when operator credentials/approval exist; do not buy or use paid endpoints automatically.
- PSA cert verification optional adapter; PSA Vault manual watchlist import; optional licensed price provider *only* with approved terms and spend cap.
- No selling, bids, auto-orders or browser scraping without explicit separate approval.
