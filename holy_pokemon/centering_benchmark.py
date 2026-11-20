"""Replay local, hash-pinned known-label photos. No network or image uploads."""
import argparse
import hashlib
import json
from pathlib import Path
from collections import Counter
from .centering_v3 import VERSION, measure_file


def run(manifest, image_root):
    document = json.loads(Path(manifest).read_text())
    results = []
    for row in document['records']:
        path = Path(image_root) / row['path']
        if hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
            raise ValueError('Original image hash mismatch: ' + row['id'])
        prediction = measure_file(path, side=row['side'])
        ratios = prediction.get('ratios')
        limit = 55 if row['side'] == 'front' else 75
        within = max(ratios['max_horizontal_pct'], ratios['max_vertical_pct']) <= limit if ratios else None
        # Grade labels are used only by this evaluator, never passed to detector.
        results.append(dict(id=row['id'],side=row['side'],observed_grade=row['observed_grade'],
                            label_provenance=row['label_provenance'],original_sha256=row['sha256'],
                            status=prediction['status'],reason=prediction.get('reason'),ratios=ratios,
                            within_side_screening_band=within, outer_quad=prediction.get('outer_quad')))
    return dict(version=VERSION,detector_sha256=hashlib.sha256(Path(__file__).with_name('centering_v3.py').read_bytes()).hexdigest(),
                photos=len(results),specimens=len({r['id'].rsplit('_',1)[0] for r in results}),
                measured=sum(r['ratios'] is not None for r in results),
                within_band=sum(r['within_side_screening_band'] is True for r in results),
                abstentions=dict(Counter(r['reason'] for r in results if not r['ratios'])),
                evaluation_status='KNOWN_LABEL_DIAGNOSTIC_NOT_BLIND_ACCURACY_ESTIMATE',
                grade_prediction=None,results=results)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',required=True);p.add_argument('--image-root',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();report=run(a.manifest,a.image_root)
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='results'},indent=2))

if __name__=='__main__':main()
