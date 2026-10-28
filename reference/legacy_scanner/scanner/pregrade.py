"""Conservative, offline photo pre-grade triage for graded-card research listings.

Never predicts or guarantees a PSA grade. No image downloads, APIs, or trades.
"""

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

# Approximate published PSA 10 centering guideline, NOT a grade predictor.
LIMITS = {'front_lr': 55.0, 'front_tb': 55.0, 'back_lr': 75.0, 'back_tb': 75.0}
PAIR_FIELDS = {
    'front_lr': ('front_left_px', 'front_right_px'),
    'front_tb': ('front_top_px', 'front_bottom_px'),
    'back_lr': ('back_left_px', 'back_right_px'),
    'back_tb': ('back_top_px', 'back_bottom_px'),
}
DEFECTS = ('scratches', 'print_lines', 'whitening', 'corner_wear',
           'dents', 'creases', 'stains', 'gloss_loss', 'trimming')
INSPECTION_FIELDS = (
    'marketplace_item_id', 'front_photo_url', 'back_photo_url',
    'photo_quality', 'measurement_method', 'measurement_uncertainty_pp',
    *(f for pair in PAIR_FIELDS.values() for f in pair),
    *(f'defect_{f}' for f in DEFECTS),
    'reviewer_concern', 'reviewer_notes',
)
RESULT_FIELDS = (
    'marketplace_item_id', 'title', 'listing_url', 'starting_grade',
    'pregrade_status', 'front_lr_ratio', 'front_tb_ratio',
    'back_lr_ratio', 'back_tb_ratio', 'centering_uncertainty_pp',
    'psa10_screen_concerns', 'manual_concern', 'unverified_items',
    'psa10_probability', 'purchase_approved',
)


def read_csv(path):
    with Path(path).open('r', encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def parse_number(raw):
    if raw is None or str(raw).strip() == '':
        return None
    try:
        n = float(raw)
    except (ValueError, TypeError):
        raise ValueError(f'Invalid measurement: {raw!r}') from None
    if not 0 <= n < 1e8:
        raise ValueError(f'Out of range measurement: {raw!r}')
    return n


def ratio_from_pixels(data, first, second):
    a, b = parse_number(data.get(first)), parse_number(data.get(second))
    if a is None or b is None:
        return None
    if a == 0 or b == 0:
        raise ValueError('Both visible border measurements must be positive')
    return 100 * max(a, b) / (a + b)


def inspect(listing, inspection):
    item_id = (listing.get('marketplace_item_id') or listing.get('listing_id') or '').strip()
    title = (listing.get('title') or '').strip()
    url = listing.get('url') or listing.get('listing_url') or ''
    grade = listing.get('grade') or listing.get('original_grade') or ''
    concern, unknown = [], []
    manual_concern = str(inspection.get('reviewer_concern') or '').strip()
    quality = str(inspection.get('photo_quality') or '').strip().lower() == 'high'
    front = str(inspection.get('front_photo_url') or '').strip()
    back = str(inspection.get('back_photo_url') or '').strip()
    if not front: unknown.append('front_photo_missing')
    if not back: unknown.append('back_photo_missing')
    if not quality: unknown.append('straight_on_high_resolution_photo_pair_unconfirmed')
    method = str(inspection.get('measurement_method') or '').strip().lower()
    if method not in ('manual_straight_on_border_pixels', 'rectified_photo_border_pixels'):
        unknown.append('measurement_provenance_unconfirmed')
    uncertainty = parse_number(inspection.get('measurement_uncertainty_pp'))
    if uncertainty is None or uncertainty > 20:
        unknown.append('credible_measurement_uncertainty_missing')
    ratios = {}
    for axis, (a, b) in PAIR_FIELDS.items():
        try:
            ratios[axis] = ratio_from_pixels(inspection, a, b)
        except ValueError as exc:
            ratios[axis] = None
            unknown.append(f'{axis}_invalid_pixels:{exc}')
        if ratios[axis] is None:
            unknown.append(f'{axis}_unmeasured')
    evidence_ready = bool(front and back and quality and method in (
        'manual_straight_on_border_pixels', 'rectified_photo_border_pixels') and
        uncertainty is not None and uncertainty <= 20)
    if evidence_ready:
        for axis, major in ratios.items():
            if major is None: continue
            limit = LIMITS[axis]
            if major - uncertainty > limit:
                concern.append(f'{axis}_outside_guideline_{major:.1f}/{100-major:.1f}')
            elif major + uncertainty >= limit:
                unknown.append(f'{axis}_borderline_{major:.1f}/{100-major:.1f}')
    for defect in DEFECTS:
        state = str(inspection.get(f'defect_{defect}') or '').strip().lower()
        if state == 'seen' and evidence_ready:
            concern.append(f'visible_{defect}')
        elif state not in ('not_visible', 'seen') or not evidence_ready:
            unknown.append(f'{defect}_unverified')
    if not evidence_ready or any(x is None for x in ratios.values()):
        status = ('PRELIMINARY_CONCERN_UNMEASURED' if manual_concern
                  else 'INSUFFICIENT_PHOTO_EVIDENCE')
    elif concern:
        status = 'PSA10_VISUAL_CONCERN'
    elif unknown or manual_concern:
        status = 'BORDERLINE_OR_UNVERIFIED'
    else:
        status = 'PHOTO_SCREEN_PLAUSIBLE_NOT_A_GRADE'
    # A photo screen may not authorize the PSA10 path, even when visibly plausible.
    return dict(marketplace_item_id=item_id, title=title, listing_url=url,
        starting_grade=grade, pregrade_status=status,
        **{k+'_ratio': (round(v, 2) if v is not None else '') for k,v in ratios.items()},
        centering_uncertainty_pp=uncertainty if uncertainty is not None else '',
        psa10_screen_concerns='; '.join(concern), manual_concern=manual_concern,
        unverified_items='; '.join(unknown),
        psa10_probability='', purchase_approved='false')


def build(listings, inspections=None):
    inspections = inspections or []
    keyed = {}
    for r in inspections:
        item_id = str(r.get('marketplace_item_id') or '').strip()
        if not item_id or item_id in keyed:
            raise ValueError('Inspection IDs must be nonempty and unique')
        keyed[item_id] = r
    template = []
    results = []
    for l in listings:
        item_id = str(l.get('marketplace_item_id') or l.get('listing_id') or '').strip()
        if not item_id: raise ValueError('Listing is missing a marketplace item ID')
        ins = keyed.get(item_id, {})
        templ = {f: ins.get(f, '') for f in INSPECTION_FIELDS}
        templ['marketplace_item_id'] = item_id
        template.append(templ)
        results.append(inspect(l, ins))
    return template, results


def write_csv(path, rows, fields):
    with Path(path).open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--listings', default='reports/project_1000/new_market_listings.csv')
    p.add_argument('--inspections', help='Reviewer-supplied high-resolution photo measurements')
    p.add_argument('--output', default='outputs/pregrade_review')
    a = p.parse_args(argv)
    listings = read_csv(a.listings)
    inspections = read_csv(a.inspections) if a.inspections else []
    template, results = build(listings, inspections)
    output = Path(a.output)
    output.mkdir(parents=True, exist_ok=True)
    write_csv(output/'inspection_template.csv', template, INSPECTION_FIELDS)
    write_csv(output/'pregrade_results.csv', results, RESULT_FIELDS)
    summary = {'listings_preserved': len(results), 'status_counts': dict(Counter(
        r['pregrade_status'] for r in results)),
        'pregrade_is_not_PSA_certification': True,
        'unknown_probabilities': len(results), 'purchase_approvals': 0,
        'source': 'PSA published approximately 55/45 front, 75/25 back centering; photo inspection is incomplete by itself'}
    (output/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
