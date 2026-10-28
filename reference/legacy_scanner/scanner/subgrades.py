"""Conservative visual triage, explicitly not a grading probability model."""
import csv
from collections import Counter
from .strategy_common import export_csv

DEFECTS=('scratches','print_lines','whitening','corner_wear','dents','creases','stains','gloss_loss','trimming')

def screen(row):
    reasons=[]; veto=[]; score=100
    if not row.get('cert_verified'): reasons.append('certificate unverified')
    if not row.get('slab_generation_confirmed'): reasons.append('slab era unverified')
    quality=row.get('photo_quality')=='high' and all(row.get(k) for k in ('front_photo_url','back_photo_url'))
    if not quality: reasons.append('high quality front/back images required')
    if not row.get('inspection_source_url'): reasons.append('inspection provenance missing')
    for part in ('centering','corners','edges','surface'):
        value=row.get('subgrade_'+part)
        if value is None or value=='': reasons.append(part+' subgrade missing');score-=10
        else:
            value=float(value);score-=max(0,10-value)*10
            if part=='surface' and value<=9: reasons.append('surface 9 requires macro inspection')
    if not row.get('subgrades_verified'): reasons.append('subgrades unverified')
    error=row.get('measurement_error')
    for name,limit in (('front_lr',55),('front_tb',55),('back_lr',75),('back_tb',75)):
        value=row.get(name)
        if value in (None,'') or error in (None,''): reasons.append(name+' measurement/error missing');continue
        value=float(value);error=float(error)
        major=max(value,100-value)
        if quality and major-error>limit: veto.append(name+' outside approximate PSA 10 centering')
        elif major+error>=limit: reasons.append(name+' borderline or uncertain')
    for defect in DEFECTS:
        state=row.get('defect_'+defect,'unknown')
        if state=='seen':
            score-=15
            if quality: veto.append('visible '+defect)
            else: reasons.append('confirm '+defect+' with better images')
        elif state!='not_visible': reasons.append(defect+' uninspected')
    return {**row,'heuristic_screen_score':max(0,min(100,round(score))),
            'score_kind':'inspection heuristic, not probability','probability_psa10':None,
            'screen_status':'reject' if veto else 'manual_review' if reasons else 'inspection_shortlist',
            'hard_vetoes':veto,'manual_review_reasons':reasons}


def cohort_audit(path):
    """Retain selected creator evidence without turning it into population odds."""
    from pathlib import Path
    with Path(path).open(encoding='utf-8-sig') as f: rows=list(csv.DictReader(f))
    selected=[];seen=set();duplicates=0
    for row in rows:
        if row.get('starting_company','').strip().upper()!='CGC' or row.get('starting_grade') not in ('9','9.5'): continue
        if row.get('target_company','').strip().upper()!='PSA': continue
        cert=row.get('certification_number')
        key=('cert',cert) if cert else (row.get('source_video_id') or row.get('study_id'),row.get('record_id'))
        if key in seen: duplicates+=1;continue
        seen.add(key)
        selected.append({k:row.get(k,'') for k in ('record_id','study_id','card_name','set','starting_grade','subgrades','submission_type','final_grade','source_url','source_video_id','timestamp','status','identity_status','dedup_status','overlap_flags')})
    import hashlib
    return selected,{'source_sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest(),'counts_are':'source rows, not independent specimens or success frequencies','group_holdout':'study_id/source_video_id; creator unknown unless explicitly supplied','source_rows':len(rows),'cgc_rows':len(selected),'duplicates':duplicates,
                     'observed_outcome_counts':dict(Counter(r['final_grade'] or 'unknown' for r in selected)),
                     'calibration_eligible':0,'probability_psa10':None,
                     'exclusion':'Selected creator/ASR evidence; incomplete specimens, certs, label eras and sampling frames. No representative independent cohort.'}


def write_inspection_reports(output,rows,cohort=None):
    from pathlib import Path
    import json
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    export_csv(output/'cgc_subgrade_candidates.csv',[screen(r) for r in rows],('listing_id','screen_status','heuristic_screen_score','probability_psa10'))
    audit={}
    if cohort:
        evidence,audit=cohort_audit(cohort)
        export_csv(output/'cgc_observed_outcomes.csv',evidence)
    (output/'cgc_crossover_model_audit.md').write_text('# CGC inspection audit\n\nScores are deterministic inspection heuristics, never PSA 10 probabilities. Missing measurements and subgrades require manual review. Low quality photos cannot establish a hard veto.\n\nNo calibrated model or confidence interval is published: independent representative specimen coverage is unavailable. A useful calibration cohort needs complete inclusion and exclusions, original/final certs, label era, method, creator/time holdouts and at least 30 independent outcomes (preferably 100).\n\n'+json.dumps(audit,indent=2)+'\n\nNegative control: [2021 E4 self-report](https://www.elitefourum.com/t/the-giant-professional-grading-thread/30930?page=98) reports an intact minimum-10 failure with centering 9 and the other subgrades 10. Card/cert/label era are unknown; this is a counterexample to a guarantee, not a probability estimate.\n\nStandards: [PSA](https://www.psacard.com/gradingstandards); [crossover fees apply on rejection](https://www.psacard.com/services/tradingcardgrading/crossover).\n')


def main(argv=None):
    import argparse
    from datetime import date
    from contextlib import closing
    from .ingestion import connect,records
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--database',required=True);p.add_argument('--asof',required=True)
    p.add_argument('--output',required=True);p.add_argument('--cohort');p.add_argument('--knowledge-at')
    a=p.parse_args(argv)
    with closing(connect(a.database)) as db:
        rows=[r for r in records(db,'listings',date.fromisoformat(a.asof),a.knowledge_at) if r['grader']=='CGC' and r['grade'] in ('9','9.5')]
    write_inspection_reports(a.output,rows,a.cohort)

if __name__=='__main__': main()
