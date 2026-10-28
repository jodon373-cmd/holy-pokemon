# PSA Vault — end-to-end product pipeline (REQUIRED, not an optional CSV)

**Authority:** verified against PSA and eBay documentation on **2026-10-28**. This document is mandatory for Holy Pokémon's Codex build and supplements `docs/CODEX_MASTER_BUILD.md`. It expands an earlier incomplete "PSA Vault manual listings" description. The goal is a **complete practical PSA Vault buying, holding, regrading, selling and payout analysis/reconciliation workflow** within available lawful access, not imaginary direct access to an undocumented PSA Vault API.

## 0. Reality of the access surface and hard boundaries

- PSA's documented public API offers *single-item certification verification*, NOT a general PSA Vault personal inventory/search/offer/transactions API: https://www.psacard.com/publicapi/documentation .
- PSA Vault is integrated with eBay: cards already vaulted can display a vault badge, purchases can be vaulted where eligible, and PSA consignment can list 7-day auctions and Buy It Now: https://www.ebay.com/vault ; https://www.psacard.com/info/psa-vault ; https://www.psacard.com/info/sell-with-psa .
- eBay Browse is authorized active-listing discovery *only where user has approved production API access*. eBay does not guarantee every Vault badge or vault flag is present in API fields. **Never invent a `vaulted=true` API field**. Flag `vault_status=unknown` unless the seller's actual listing metadata, authenticated export, user observation, or documented official data field establishes the status.
- Seller Hub/Product Research exports or actual eBay sold records supplied by the operator can support historical comps; a live listing ask is not a sale. An eBay PSA Store item need not be held by the operator; PSA consignment is a sale channel, and seller identity alone is not proof the specific card is physically vaulted.
- PSA collection or Vault account may be browsed by its owner in the official site/app. Until a separately documented read-only API or export method is available, support manual/import-based private-account synchronization (CSV, file, screen transcription entered by the user) with an operator-initiated `Open PSA Vault` deep link. No password capture in this bot, no reverse-engineering private endpoints, extension cookie exfiltration, unauthorized automated login, anti-bot bypass or scraping.
- **All financial transfers, sales, vault-to-vault ownership transfers, withdrawals, bids, Partner Offer acceptance, grading submissions and consignment publication require operator interaction directly in PSA/eBay.** This tool is research, reconciliation and workflow guidance, not a secret buyer/seller automation.
- APIs and account features evolve; adapter capability detection must reflect documented/supported access, not unsupported promises.

## 1. End-to-end flow and the *decision engine*

Explicit state machine with persisted events, dates, source links and fees:

`DISCOVER_EBAY_OR_USER_LEAD` → `IDENTIFY_EXACT_CARD_AND_SLAB` → `VERIFY_VAULT_ELIGIBILITY_AND_STATUS` → `VALUE_AS_IS_AND_GRADING_PATHS` → `PROPOSE_PURCHASE_AND_DESTINATION` → (manual external transaction) → `ACQUIRED_PENDING_AUTHENTICATION` → `VAULTED_IN_USER_COLLECTION` OR `SHIPPED_TO_OWNER` → `HOLD/MONITOR` → choose `SELL_AS_IS_IN_VAULT`, `ACCEPT_PARTNER_OFFER`, `WITHDRAW_FOR_REGRADING`, `VAULT_TO_VAULT_EXTERNAL_TRANSFER`, or `SHIP_TO_OWNER` → `SOLD_OR_TRANSFERRED` / `AWAITING_PAYOUT` → `PAYOUT_RECONCILED` / `EXCEPTION`.

Keep an event log recording evidence timestamp, initiated date, PSA/eBay IDs where available, claimed status, amounts, payout and user-confirmed source. Manual user entry is always labeled; don't turn user-provided order history into marketplace-wide comps automatically.

## 2. Buy-side discovery and identity: high-upside opportunities, vaulted and eligible

- Search active Pokémon PSA/BGS/CGC slab listings across eBay using approved Browse, plus direct user URLs, listing screenshots, saved seller exports. Search the official PSA eBay Store as a seller-scoped research filter where eBay provides an authenticated seller field; do not misinterpret that as the entire Vault market.
- Support a **Vault discovery filter** with three independent notions: `already_in_psa_vault` yes/no/unknown; `vault_eligible` yes/no/unknown (based on approved holder/card and local service rules); and `psa_consignment_listing` yes/no/unknown. Do not merge these.
- Recognize PSA Vault badge from original operator screenshots/user validation or a documented API representation only. Image/AI OCR classification may suggest `possible` but may never turn into `verified` automatically. Unclear source triggers inspection task, **not exclusion from discoveries**.
- Exact variants: Pokémon English/Japanese; WOTC 1st/Shadowless/unlimited, holo/reverse/nonholo, stamped/incorrect-symbol variations, promos, EX era, and modern standout; exact cert and grader ID. Use PSA cert API when authorized; BGS/CGC holder must remain distinct.
- Offer `ship_to_vault`, `buy_already_vaulted_and_keep_vaulted`, `buy_and_ship_to_owner` as separate what-if scenario modes; do not assume all marketplace listings are eligible or checkout destination is always offered. Require explicit user confirmation of any actual shipping/Tax treatment at checkout.
- Track available condition photos, glare, hidden slab defects; send to local AI grader with abstention if incomplete. A vaulted card cannot be cracked/regraded while still physically in vault; withdraw, account for transport and verification steps, then resubmit if desired.

## 3. User's inventory, custody, orders and status sync

- First-class `Vault Collection` screen and import schema, not a buried CSV: `item_id`, `psa_cert`, `grader`, `current_grade`, `vault_id_masked`, `psa_collection_url`, `ebay_item_id`, `vaulted_at`, `owner_acquired_at`, `purchase_price`, `purchase_tax_paid`, `source_listing_url`, `state`, `last_verified_at`, `source_type`, `notes`.
- Implement import of permitted PSA account/download/export or user entered table, dated seller receipts, eBay own purchase and sale CSV, own PSA consignment statuses and Stripe payout receipts. Map to canonical local holdings without duplicate ownership or duplicate card specimens.
- Import must accept partial data and visibly report unknown fields. Card may be PSA/BGS/CGC/SGC graded; check current PSA vault holder eligibility separately.
- Track `vaulted`, `consigned`, `listed_auction`, `listed_bin`, `unsold`, `sale_pending_payment`, `sold`, `paid_out`, `withdraw_requested`, `withdrawn`, `transferred`; separate documented PSA statuses from application-internal labels. Provide manually confirmable actions/links and clear account-sync freshness.
- Detailed reconciliation: match own collection item → listing → sale → PSA consignment fee → Stripe payout; compare expected versus observed dollars, flag unpaid auctions/relistings and duplicated payout receipts. Only verified actual payouts become `realized_net_cash`.
- No cloud syncing/private account login without a suitable authorized connector/API. Storing user financial/order details locally requires encryption or at minimum documented file permissions, sensitive field avoidance and credential redaction.

## 4. The Vault-specific EXIT ENGINE: an explicit fee comparison

For each acquired or candidate slab, calculate **multiple equivalent and differing strategic exits** side-by-side:
1. `sell_on_ebay_via_psa_auction` (7-day auction, expected net from sale comps, auction downside, listing timeline, buyer payment possibility).
2. `sell_on_ebay_via_psa_buy_it_now` (asking/offer prices, timeline, confirmed sale-only actual profit).
3. `accept_psa_partner_offer` (owner-provided actual offer and expiry; no fee per PSA's currently advertised model, NEVER create fictitious offer or use random PSA market estimate).
4. `hold_in_vault` (current estimated value, hypothetical exit fees and capital duration; no cash proceeds).
5. `withdraw_then_resell_on_own_ebay` (vault withdrawal + insured shipping + early withdrawal + full personal-selling fees + shipment, tax effects).
6. `withdraw_then_crack_and_regrade_then_resell` (plus PSA/CGC/BGS service tiers, grading shipping, insurance/upcharges and loss cases; directly compared with sale-as-is from Vault).
7. `psa_vault_to_vault_transfer` (operator-coordinated external transfer, no automatic irreversible action; include off-platform payment uncertainty and ownership verification).
8. `ship_to_owner` (cost-only terminal path, no fictitious sale).
9. `new_psa_grading_submission_to_vault_then_sell` (when appropriate, card-by-card submission destination after grade, separate original grading fees and consignment economics).

For each branch compute: exact monetary basis; source and effective date; expected sale venue; expected proceeds before/after venue fee; tax if applicable; handling/withdrawal/shipping/insurance/service fees; holding period; remaining capital; downside and minimum viable sale price; liquidity; actual vs prospective profit. **Compare against doing nothing and against direct resale of the intact existing slab**. Use Decimal and config-driven versioned fee schedules.

DO NOT DOUBLE-CHARGE fees: PSA's consignment service advertises **one PSA consignment fee with no additional eBay seller fee** (for that exact channel). PSA's $200 example uses 13% fee, payout $174, but this is only ONE tier and cannot justify hard-coding 13% across all tiers. Retrieve full current fee schedule if the official page exposes it, otherwise require user entry of the effective quoted tier/fee and show an explicit unknown. https://www.psacard.com/info/consignment-rates and https://www.psacard.com/info/psa-vault .
Partner Offer route is PSA-advertised fee-free, while actual amount is a private customer-specific offer entered by the user: https://www.psacard.com/info/psa-partner-offers .
eBay payout processing can go through Stripe; track actual payout/settlement timestamps and avoid assuming it is instant.

### Time-sensitive and taxable nuances (verify at runtime)
- **Starting Oct 29, 2026**, PSA advertises U.S. premium insured withdrawal shipping tiered by shipment declared value: under $500 = $19.99; $500–$4,999 = $24.99; $5,000–$24,999 = $42.99; $25,000–$74,999 = $57.99; $75,000–$299,999 = $139.99; $300,000+ custom quote. If >10 items, add $0.99 for each extra item; international handling separate. These are publicly stated as upcoming on Oct 28, not necessarily yet effective. Source https://www.psacard.com/info/psa-vault .
- Withdrawal within **90 days of initial vaulting** currently advertises a **$4.99 early withdrawal fee per item**; ensure the app has date-aware per-item logic and scenario compares hold vs early ship. Revalidate fee and policy source at time of use.
- PSA markets a tax-advantaged *buy-and-keep-vaulted* route. **Do NOT categorically assume no tax is ever owed or that ordinary out-of-state withdrawals are exempt.** Compare `checkout_tax_paid` and potential withdrawal/sales/use-tax obligations as unknown/manual tax inputs by jurisdiction, consistent with PSA's own terms. Never provide definitive tax/legal advice or a fake tax savings.
- Seller eBay consignment fee, ordinary eBay seller fee, grading cost, PSA vault insured withdrawal shipping and PSA partner offer haircut are separate conceptual components. Only charge the fees applicable to the chosen route.

### Own portfolio state / risk
- Budget $2,000 first batch all-in, $5,000 reserved, no automatic spending.
- Vault trading can **delay or preclude physical inspection**; AI grade estimate from listing photos may be insufficient. A vaulted 9.5 BGS does not instantly become a PSA10.
- Portfolio net-worth view must distinguish `paper_value`, `eligible_partner_offer_cash`, `expected_consignment_net`, `best_case_regrade_net`, `realized_payout`; liquidity and lock-up time vary.
- Tax-exempt claims, storage insurance terms and transit coverage may be conditional on declared value and service terms; show verified source and uncertainty.

## 5. Owner-in-the-loop PSA Vault task center

A first-class `PSA Vault` UI page with:
- **Discover Vaulted Deals**: merged authorized eBay listings + user's manually verified vault listing, grade path, fee-adjusted opportunity rank, direct live link; empty provider status shows next action.
- **Collection**: locally imported owned cards, cert/grade, custody states and timestamps, show links to PSA account and matching eBay listings.
- **Vault vs Withdraw Comparator**: route-by-route net P&L, dates and fee waterfall; tax and quote inputs.
- **Sell Options**: PSA auction, PSA Buy It Now, Partner Offer (actual input), withdraw + own listing, later regrade, vault-to-vault transfer; decision explanation.
- **Actions/Status**: safe links to official PSA/eBay account pages for *manual user action*; checklist for user-confirmed execution and status updates. Do not automate transfer, withdrawal, sale or offer acceptance.
- **Reconciliation**: own consignment sale and Stripe receipt imports; expected vs actual; export tax/audit log.
- **Provider Health**: eBay API approval, PSA cert API status, PSA Vault private sync mode `manual` / `authorized_provider`, when verified, last source refresh, fee schedule effective dates.

Operations should remain useful with NO personal PSA account connection and NO eBay production credentials, through manual entry/CSV and exact eBay listing URL inputs.

## 6. Mandatory data structs and adapter interfaces

Separate provider objects, never fuse into one ambiguous `psa` field:
- `EbayBrowseActiveListingAdapter`: official active listings.
- `PSAConsignmentListingFilter`: seller-scoped/verified PSA shop identification where allowed.
- `PSACertificateVerificationAdapter`: documented single-cert PSA Public API when credentials are available.
- `PSAVaultStatusEvidenceAdapter`: user-supplied status screenshots/exports, plus officially documented programmatic data only when access approved.
- `PSAVaultCollectionImportAdapter`: private owner inventory and custody events imported locally with explicit provenance.
- `PSAPartnerOfferManualAdapter`: private offers (amount/expiry/actual eligibility), NEVER scrape owner vault.
- `PSAConsignmentFeesEngine`: dated schedule and quote inputs.
- `PSAVaultWithdrawalFeesEngine`: 90-day rule, value tier, quantity, country, insurance/effective date and unknown terms.
- `PSAVaultReconciliationAdapter`: receipts, owner payout CSV, listing id and physical copy reconciliation.
- `PSAVaultWorkflowEngine`: state machine + user approval required for each external operational step.

All adapters include version, source URL, retrieved_at, observed_at, capability/permission state and explicit not-available mode.

## 7. Acceptance tests — non-optional

1. eBay active listing with documented vault badge vs PSA Store seller without documented badge vs eligible nonvaulted listing have distinct statuses; unknown is NOT silently yes.
2. Missing eBay Browse credential: manual URL/listing import, vault comparison, status reporting and source links still work; no fake live status.
3. PSA cert API credential missing: verification pending, never claims `cert_verified=true`.
4. $200 PSA consignment sale example: 13% **single PSA fee** → $174 **gross payout before other independent user costs**; no additional eBay seller fee. Unknown fee tiers do not silently default to 13%.
5. Effective-date withdrawal test: on Oct 28 2026 do not apply Oct 29 shipping schedule as already effective; on Oct 29 and later, calculate all published shipping bands, boundary thresholds, +10-item additional fees, early <=90-day rule correctly, and international unknown handling.
6. User-provided Partner Offer $X is evaluated as a specific **actual offer** with expiry, zero PSA offer fee as advertised; generic PSA price estimates never become offers.
7. Regrade route includes withdrawal before crack + transit/grading fees and compares to conservative sell-in-vault fallback; no phantom PSA10 result.
8. No cards sold on eBay, accepted offers, withdrawn, transferred or purchased by any bot code. External irreversible Vault-to-Vault transfer is NEVER auto-executed.
9. Original owner vault portfolio holdings import and payout reconciliation dedup same card/listing and do not count a payout twice. Outstanding/unpaid consignment flagged.
10. A user can launch Mac local app, import an owned vault sample and a candidate vaulted eBay URL, receive fully sourced scenarios and export a review decision even without PSA Vault API.

## References last checked October 28, 2026
- https://www.psacard.com/info/psa-vault
- https://www.psacard.com/info/consignment-rates
- https://www.psacard.com/info/sell-with-psa
- https://www.psacard.com/info/psa-partner-offers
- https://www.psacard.com/info/psa-vault-to-vault-transfer-template
- https://www.psacard.com/publicapi/documentation
- https://www.ebay.com/vault
- https://www.ebay.com/help/selling/trading-cards-listing-tools/using-the-ebay-vault?id=5342
- https://developer.ebay.com/develop/api/buy
- https://www.psacard.com/vaultterms

**This is a hard acceptance requirement for the FIRST ALL-IN-ONE Holy Pokémon build.** No green check for `PSA Vault pipeline` until real manual mode, fee modeling, custody, regrade/exit decisions, user review, reconciliation and tests are demonstrated. Unavailable private API access must be clearly marked as such, not misrepresented as a failure of the supported offline/full-decision workflow.
