# HOLY POKÉMON — THE CROSS-SET GEM-GAP STRATEGY

**Research frozen:** 2026-10-29. **Status:** prioritized research, not a trained crossover-probability model, and not a buy order.

## Fundamental discovery

FredyCards personally tracks PSA9→CGC10 successes and separately analyzes aggregate **GemRate.com** PSA-versus-CGC submission gem rates by card era. This is **not evidence he performs a card-level ratio + exit-profit screen** when purchasing. This repository adds that extra screening layer, without inventing probabilities.

Sources:
- Fredy historical 546-card retrospective: https://www.youtube.com/watch?v=00qFtZz6eZU — 178 intentionally selected PSA9 → CGC yielded 86 CGC10-or-better and 14 Pristines; 306 selected PSA8 → 72 CGC10-or-better and 4 Pristines. **Samples are selected and overlap his other videos; 48.3% is not the probability of a random PSA9 being CGC10.**
- Fredy 2-year grader-era comparison: https://www.youtube.com/watch?v=XmaISDa55DM — uses GemRate data. Reports approx 51.6% CGC vs 51.3% PSA overall; 2010–2019 CGC advantage sometimes around 20 percentage points, 2000–2009 generally CGC higher, 1990s gap smaller than expected, 2020+ about similar. The more recent 2010s gap is an **era-level observation not a set-specific conversion estimate**. Data and narration not audited down to each month.
- Historic arbitrage source report: project Fredy regrade evidence and research reports. Distinguish outcome grade from sale vs estimated value.

### What population rates mean

PSA10 / all PSA grades and CGC10 / all CGC grades are **different submissions**. A high CGC/PSA census ratio can reflect submission incentives, recent grading eras, cherry-picking, label type, production differences and grade standards. It is **NOT** the probability a PSA9 becomes a CGC10.

PriceCharting's per-item population **CGC grade 10 count is an inclusive 10-grade census**, not a clean CGC **Gem Mint** count necessarily excluding Pristine. The *sold price* field below separately requires `CGC GEM MINT 10`, not Pristine. Census denominators/half grades/special tags need direct provider corroboration. Population history sometimes includes obvious anomalies (e.g., Fossil Dragonite past CGC monthly totals near 3 but latest total 3866).

PriceCharting's **Grade 9 guide value is blended and not guaranteed to be a PSA9 sold price**, so our ranker never promotes that guide number to an observed transaction. CGC10 guide estimates also aren't individual sales.

## Set shortlist

This is a shortlist of **specific unlimited holo variants**, not proof that an entire set converts easily.

| Priority | Card | PSA 10 / PSA total | CGC 10 / CGC total | Price evidence | Interpretation |
|---|---|---|---|---|---|
| A low capital | **Fossil Lapras holo #10** | 51 / 12,740 = **0.40%** | 113 / 4,917 = **2.30%** | Grade9 *blended guide* ~$171; CGC GEM10 dated sales Oct24 $799, Oct17 $649.99, Oct7 $809, Oct6 $700, Sep30 $489, Sep14 $610 | Strongest inexpensive *current research lead*; seek actual PSA9 sold and live offers |
| A low capital / thin exit | **Base Set 2 Chansey holo #3** | 29 / 5,211 = **0.56%** | 31 / 1,937 = **1.60%** | Guide9 ~$180; CGC GEM10 $699 Sep20, $510.04 Mar23, $1150 Mar21 | High apparent upside and neglected set, but only three older CGC10 observations, wide exit variance |
| A higher capital | **Fossil Dragonite holo #4** | 60 / 14,946 = **0.40%** | 72 / 3,866 = **1.86%** | Grade9 guide ~$674; CGC10 Oct21 $1999, Sep19 $1750, Sep17 $1310, Aug23 $1500, Aug9 $975, May31 $1075 | Repeated CGC10 exits with big spread; expensive failed-case downside |
| A higher capital | **Team Rocket Dark Charizard holo #4** | 176 / 18,186 = **0.97%** | 74 / 3,279 = **2.26%** | PSA9 reported $920 Sep8 / $983.89 Jul3; CGC GEM10 $1375–$1999 at several dates | Best among studied for **both** PSA9 reported trades and CGC10 reported trades; variant must be holo #4, NOT nonholo #21 |
| B high capital | **Gym Heroes Sabrina's Gengar holo #14** | 34 / 7,946 = **0.43%** | 117 / 1,697 = **6.89%** | Guide9 ~$1516; recent CGC Gem10 Oct15 $2875, Oct5 $3195, Sep29 $2899, Sep22 $2999, Aug30 $2226 | **Largest documented relative census gap** among this shortlist; higher capital, pricing shifts, 1st edition **distinct** |
| B possible | **Gym Heroes Erika's Dragonair holo #4** | 82 / 3,811 = **2.15%** | 84 / 983 = **8.55%** | Oct6 PSA9 $269.97, Oct7 PSA9 $320; CGC10 reported $350–$600 | Grade gap good; actual fee-adjusted profit may be marginal on low CGC10 exits |
| B possible | **Fossil Gengar holo #5** | 51 / 12,761 = **0.40%** | 82 / 3,331 = **2.46%** | Guide9 ~$770 vs CGC10 guide ~$1158 | Thin margin for grader/shipping/downgrade risk; needs proper sold evidence |
| B thin exit | **Neo Genesis Feraligatr #5** | 22 / 2,146 = **1.03%** | 19 / 581 = **3.27%** | CGC10 two reports $1000 and $415 | Volatile, not a dependable sell-side reference |
| C poor economics | **Gym Heroes Rocket's Scyther holo #13** | 44 / 3,262 = **1.35%** | 74 / 961 = **7.70%** | Grade9 guide ~$250; actual CGC10 reports ~$310–$355 | Population gap alone does not pay for transaction costs |
| C poor economics | **Gym Heroes Blaine's Moltres holo #1** | 27 / 4,626 = **0.58%** | 57 / 1,154 = **4.94%** | Grade9 guide ~$550, CGC10 guide ~$495 | Negative gross spread despite strong census contrast |
| C refutes era generalization | **Plasma Storm Lugia EX #134** | 21 / 1,766 = 1.19% | 0 / 226 = 0% | Insufficient comparable CGC Gem10 sale history | 2010s era-level CGC advantage does NOT transfer to every specific card |
| C refutes era generalization | **Flashfire Charizard EX #100** | 184 / 3,922 = 4.69% | 1 / 467 = 0.21% | Insufficient CGC Gem10 sales | Huge CGC disadvantage despite Fredy's 2010s aggregate trend |

Data: `populations_and_guide_references.csv` contains **12** explicitly linked records with frozen pop totals and guide-value semantics. The latest pages are the source of truth; verify census with CGC/PSA official registry before trading.

**Preliminary best sets by trade design:**
- **Fossil Unlimited**: strongest *repeatable research category* among studied: Lapras (cheap entry), Dragonite (medium/high), Gengar (watch); same format but different actual card economics.
- **Gym Heroes Unlimited**: strongest *population gap* among studied, but only Sabrina's Gengar has a sufficiently large apparent gross upside; Rocket's Scyther / Blaine's Moltres demonstrate why a gap-only algorithm fails.
- **Base Set 2 Unlimited**: best **neglected lower-capital candidate**, Chansey #3, conditional on resale liquidity and actual PSA9 sold.
- **Team Rocket Unlimited**: standout higher-dollar **Dark Charizard holo #4**, strongest this pass for having multiple PSA9 AND CGC GEM10 source-reported sales.
- **2010–2019**: important *era to prospect*, **not a verified winning set**. Require exact card-by-card evidence; adverse grade-10-pop counterexamples documented above.

## Exact screen: G-GAP (Gem-Grade Arbitrage Prospecting)

1. **Identity:** exact English/Japanese, set, card number, first/unlimited/reverse, print variant, holo and card condition. Reject mixing artwork matches or 1st edition against unlimited.
2. **Census context, not probability:** begin with research heuristics **PSA10 rate <= 2%**, **CGC10 inclusive rate > PSA10 rate** (prefer 3x or greater only when both cohorts large), **PSA9 census >=100**, CGC cohort >=150. Also seek time-window rates to avoid historical cherry-pick. Keep rare small-sample exceptions visible with uncertainty.
3. **Economic filter:** require >=3 **actual dated source-reported CGC GEM10** sales and >=3 exact PSA9 sales before awarding a **SALES_OBSERVED** status; else show **GUIDE_ONLY / TRANSACTIONS_MISSING**. Require multiple venues or separately evidenced certificates to reduce duplicate-counting. Grade9 blended guide is only a preliminary context value. Recent 90/180-day conservative lower quartile is preferable to record high sales. No invented comps.
4. **Hypothetical spread:** `CGC_GEM10_Q1_sale * (1 - selling_fee) - PSA9_sold_median - acquisition_tax_ship - CGC_grading_insurance_upcharge`. Target positive conservative spread with some buffer for uncertainty; research example minimum $150, not a promise. Model the **failure branch** at actual CGC9/9.5 sales and altered/declined holder outcomes. Don't use resale of an unchanged PSA9 holder if you crack it.
5. **Native condition screening:** inspect both faces from the seller's originals. Measure centering with overlays. **Published PSA10 and CGC Gem10 front centering tolerance both roughly 55/45**; do not assume CGC magically excuses off-centering. More decisive: hidden holo scratches, print lines, whitening, cut defects, back edge/corner, pressure indents. Verify seller cert exact physical copy.
6. **Priority:** research signal is **strong conservative realized margin + liquidity + sufficient slab supply + good physical images**, with census gap as context. No invented `p(CGC10 | PSA9)`. Fredy's 48.3% selected rate is a **qualitative prior about selection**, not a calibrated card/set outcome.
7. **Operations:** save interesting near-miss candidates separately; only a manually inspected and fully costed listing may advance to owner approval. **Never auto-buy, crack, or send to a grader.**

The ideal is **not** a card with the largest 10-pop ratio. It is a card where *buying an unusually clean PSA9 at or under observed PSA9 trade prices gives large net CGC GEM10 upside, with a survivable failure exit*. Exact matching source and strong evidence beat gross multipliers.

## Repository implementation

- `populations_and_guide_references.csv`: 12 set-and-card specific census rows and guide references, including negative-control 2010s entries.
- `dated_source_reported_sales.csv`: **38** dated sale observations, strictly distinguishing Gem10 from Pristine and PSA9, individually linked back to report pages. Market results are **PriceCharting-reported**, not independently verified eBay payout.
- `holy_pokemon/gem_gap_research.py`: local **zero-network** code with census gap, grade-specific sold sale counts, guide-only spread, and hypothetical success-only historical sale spread. **Never** turns guide9 into PSA9 sold or Pristine into GEM.
- `tests/test_gem_gap_research.py`: checks variant/grade separation, absence-of-sold, and non-purchase behavior.

```sh
python3 -m holy_pokemon.gem_gap_research --top 25
python3 -m unittest tests.test_gem_gap_research -v
```

These records are committed directly to GitHub for offline/local use. **They do not yet modify the separately running Mac app.** No new Codex session, marketplace transaction, provider credentials or paid API call was used.

## Known limitations

- No truly **conditional** set/card PSA9→CGC10 success rate available from population ratios. Need actual original-PSA9 cert → resulting CGC10 cert paired studies.
- Source-reported sales may include duplicate listings/relistings; deal approval must validate exact edition, actual final price/buyer, buyer premium, market depth, and resale channel after fee.
- Gem rates vary by submission era, and the combined CGC 10 census may include Pristine grade.
- This pass did **not** exhaust every PSA/CGC population set and hundreds of new releases. It identifies grounded leaders across Fossil, Base2, Rocket and Gym rather than asserting an exhaustive winner.
- The prospective AI grading model has a documented failure distinguishing a vintage PSA10 from 8. It is not a substitute for high-resolution holo review or a measurable conditional crossover probability.

Sources: PriceCharting card-specific pop and price URLs stored in CSV; Fredy original videos above. No external photograph redistribution.
