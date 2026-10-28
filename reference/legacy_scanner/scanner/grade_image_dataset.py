"""Audit rights-verified locally held graded card images; no scraping/downloading."""
import argparse,csv,hashlib,json
from collections import Counter,defaultdict
from pathlib import Path
from .photo_grader import read_image
FIELDS=('image_id','card_id','certification_number','card_identity','grade_company','grade','side','local_path','source_url','rights_basis','rights_evidence','image_sha256','split')
RIGHTS={'self_photographed','explicit_permission','verified_permissive_license'}
def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()
def audit(rows,min_unique_images=1000,min_each_grade=80):
    accepted=[];rejected=[];hashes=set();ids=set();classes=Counter();groups=defaultdict(set)
    for i,row in enumerate(rows,2):
        reasons=[];key=str(row.get('image_id') or '').strip()
        group=str(row.get('card_id') or row.get('certification_number') or '').strip()
        if not key or key in ids:reasons.append('duplicate_or_missing_image_id')
        ids.add(key)
        if not group:reasons.append('specimen_group_missing')
        grade=str(row.get('grade') or '').strip()
        if grade not in ('8','9','10'):reasons.append('grade_must_be_verified_8_9_10')
        if str(row.get('grade_company') or '').upper() not in ('PSA','CGC','BGS'):reasons.append('invalid_grader')
        if str(row.get('side') or '').lower() not in ('front','back'):reasons.append('missing_image_side')
        if row.get('rights_basis') not in RIGHTS or not str(row.get('rights_evidence') or '').strip():
            reasons.append('missing_valid_rights_evidence')
        path=str(row.get('local_path') or '').strip()
        sha=''
        if not path:reasons.append('missing_local_image')
        else:
            try:
                read_image(path);sha=digest(path)
                if sha in hashes:reasons.append('duplicate_image_bytes')
            except (OSError,ValueError):reasons.append('unreadable_image')
        if reasons:rejected.append({'line':i,'image_id':key,'reasons':reasons});continue
        hashes.add(sha)
        rec={k:row.get(k,'') for k in FIELDS};rec['image_sha256']=sha
        accepted.append(rec);classes[grade]+=1
        groups[group].add((grade,str(row.get('grade_company')).upper()))
    conflicts=sum(1 for v in groups.values() if len(v)>1)
    specimen_count=len(groups)
    ready=(len(accepted)>=min_unique_images and specimen_count>=min_unique_images//2
           and all(classes[g]>0 and classes[g]>=min_each_grade for g in ('8','9','10'))
           and conflicts==0)
    return {'accepted':accepted,'rejected':rejected,'summary':{
        'input_rows':len(rows),'unique_usable_images':len(accepted),'distinct_specimens':specimen_count,
        'by_grade':dict(classes),'rejected':len(rejected),'conflicting_specimen_labels':conflicts,
        'requested_minimum':min_unique_images,'grade_floor':min_each_grade,
        'ready_for_training_review':ready,'model_trained':False,
        'warning':'Sample size alone does not validate grading. Need independent specimen/card/source holdouts and rights verification.'}}
def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',required=True);p.add_argument('--output',default='outputs/photo_dataset_audit')
    a=p.parse_args(argv)
    with Path(a.manifest).open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    result=audit(rows);root=Path(a.output);root.mkdir(parents=True,exist_ok=True)
    with (root/'accepted.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(result['accepted'])
    (root/'rejected.json').write_text(json.dumps(result['rejected'],indent=2))
    (root/'summary.json').write_text(json.dumps(result['summary'],indent=2))
    print(json.dumps(result['summary'],indent=2))
if __name__=='__main__':main()
