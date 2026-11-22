"""Real, local PyTorch training/inference pipeline for user-approved card-only photos.

No weights are pretended to exist. No remote image downloads, credentials or AI API.
The model is experimental until holdout metrics validate it.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import random
from pathlib import Path

ALLOWED_RIGHTS = {"self_photographed", "explicit_permission", "verified_permissive_license"}
LABELS = {
    "PSA": ("6","7","8","9","10"),
    "CGC": ("7.5","8","8.5","9","9.5","10","Pristine 10"),
    "BGS": ("8","8.5","9","9.5","10"),
}

def read_manifest(path, grader):
    """Hard gate against label leakage and duplicate specimen/video split."""
    if grader not in LABELS: raise ValueError("Select supported target grader")
    with open(path,encoding="utf-8-sig",newline="") as f: rows=list(csv.DictReader(f))
    selected=[]; excluded=[]
    seen=set()
    for i,row in enumerate(rows,2):
        reasons=[]
        if row.get("grader")!=grader:continue
        if row.get("grade") not in LABELS[grader]:reasons.append("unknown_grader_grade")
        if row.get("rights_basis") not in ALLOWED_RIGHTS or not row.get("rights_evidence"):
            reasons.append("no_authorized_training_rights")
        if row.get("card_only_verified","").lower() not in ("true","1","yes"):
            reasons.append("unverified_card_only_crop_label_leakage_risk")
        if row.get("pre_decision_visible","").lower() not in ("true","1","yes"):
            reasons.append("post_outcome_image_not_buyer_visible")
        if not row.get("physical_specimen_id") or not row.get("source_video_id"):
            reasons.append("unidentified_group")
        image=Path(row.get("image_path",""))
        if not image.is_file() or image.suffix.lower() not in (".jpg",".jpeg",".png",".webp"):
            reasons.append("missing_local_supported_image")
        sha=""
        if not reasons:
            sha=hashlib.sha256(image.read_bytes()).hexdigest()
            if sha in seen:reasons.append("duplicate_photo")
        if reasons:excluded.append({"row":i,"reasons":reasons});continue
        seen.add(sha);selected.append({**row,"sha256":sha})
    return selected, excluded

def split_by_video(rows,seed=73):
    """Keep all physical copies in one video/submission together to limit leakage."""
    if not rows:raise ValueError("No rights-verified image rows")
    groups={}
    for row in rows:
        groups.setdefault(row["source_video_id"],[]).append(row)
    vids=sorted(groups)
    if len(vids)<5:raise ValueError("At least five separate source videos/groups needed for a held-out experimental test")
    random.Random(seed).shuffle(vids)
    test_count=max(1,round(len(vids)*.2))
    validation_count=max(1,round(len(vids)*.2))
    test=set(vids[:test_count]); val=set(vids[test_count:test_count+validation_count])
    parts={"train":[],"val":[],"test":[]}
    for video_id,group in groups.items():
        target="test" if video_id in test else "val" if video_id in val else "train"
        parts[target].extend(group)
    physical_assignment={}
    for split,rr in parts.items():
        for row in rr:
            key=row["physical_specimen_id"]
            if key in physical_assignment and physical_assignment[key]!=split:
                raise ValueError("Physical specimen across different videos/splits: resolve duplicate before training")
            physical_assignment[key]=split
    if any(not rr for rr in parts.values()):raise ValueError("Empty data split")
    return parts

def _torch():
    try:
        import torch
        from torch import nn
        from torchvision import transforms
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("Install torch, torchvision and pillow locally before training") from exc
    return torch,nn,transforms,Image

def model_for(num_classes):
    torch,nn,_,_=_torch()
    return nn.Sequential(
        nn.Conv2d(3,12,3,padding=1),nn.ReLU(),nn.MaxPool2d(2),
        nn.Conv2d(12,24,3,padding=1),nn.ReLU(),nn.MaxPool2d(2),
        nn.Conv2d(24,32,3,padding=1),nn.ReLU(),
        nn.AdaptiveAvgPool2d((1,1)),nn.Flatten(),
        nn.Linear(32,num_classes),
    )

def train(manifest,grader,output,epochs=4,seed=73):
    torch,nn,T,Image=_torch()
    rows,rejected=read_manifest(manifest,grader)
    parts=split_by_video(rows,seed)
    labels=list(LABELS[grader])
    torch.manual_seed(seed)
    random.seed(seed)
    transform=T.Compose([T.Resize((128,128)),T.ToTensor()])
    def tensors(rows):
        images=[];indices=[]
        for row in rows:
            with Image.open(row["image_path"]) as im:
                if im.width<128 or im.height<128:raise ValueError("Insufficient image resolution")
                images.append(transform(im.convert("RGB")))
            indices.append(labels.index(row["grade"]))
        return torch.stack(images),torch.tensor(indices)
    xy={k:tensors(v) for k,v in parts.items()}
    model=model_for(len(labels))
    device="mps" if getattr(torch.backends,"mps",None) and torch.backends.mps.is_available() else "cpu"
    model.to(device)
    optimizer=torch.optim.Adam(model.parameters(),lr=.001)
    criterion=nn.CrossEntropyLoss()
    for _ in range(epochs):
        model.train()
        x,y=xy["train"]
        for offset in range(0,len(x),16):
            xx=x[offset:offset+16].to(device);yy=y[offset:offset+16].to(device)
            optimizer.zero_grad()
            loss=criterion(model(xx),yy)
            loss.backward();optimizer.step()
    metrics={}
    model.eval()
    with torch.no_grad():
        for split,(x,y) in xy.items():
            scores=model(x.to(device))
            pred=scores.argmax(1).cpu()
            metrics[split]={"count":len(y),"accuracy":round(float((pred==y).float().mean()),4),
                "matched":int((pred==y).sum())}
    dest=Path(output);dest.parent.mkdir(parents=True,exist_ok=True)
    torch.save({"weights":model.cpu().state_dict(),"labels":labels,"grader":grader,
        "training_status":"EXPERIMENTAL_UNCALIBRATED","seed":seed,
        "metrics":metrics,"source_sha256":[r["sha256"] for r in rows],
        "split_specimens":{k:[r["physical_specimen_id"] for r in v] for k,v in parts.items()}},dest)
    report={"checkpoint":str(dest),"training_status":"EXPERIMENTAL_UNCALIBRATED",
        "game":"operator-provided_only","grader":grader,"used_images":len(rows),
        "excluded":len(rejected),"metrics":metrics,
        "note":"Never use the holdout accuracy as a universal grade probability; tiny creator-selected data are not representative."}
    dest.with_suffix(".json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    return report

def predict(checkpoint,image_path):
    torch,_,T,Image=_torch()
    p=Path(image_path)
    if not p.is_file():raise ValueError("Local image missing")
    with Image.open(p) as im:
        if im.width<128 or im.height<128:
            return {"status":"ABSTAIN","reason":"low_resolution"}
        x=T.Compose([T.Resize((128,128)),T.ToTensor()])(im.convert("RGB"))[None]
    c=torch.load(checkpoint,map_location="cpu",weights_only=True)
    model=model_for(len(c["labels"]));model.load_state_dict(c["weights"]);model.eval()
    with torch.no_grad():
        scores=torch.softmax(model(x),dim=1)[0]
    pred=int(scores.argmax())
    return {"status":"EXPERIMENTAL_MODEL_ONLY", "predicted_grade":c["labels"][pred],
        "grader":c["grader"],"model_status":c["training_status"],
        "scores_uncalibrated":[round(float(v),4) for v in scores],
        "warning":"Not a certified or calibrated grade prediction; card-only verified input required"}

def main(argv=None):
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest="command",required=True)
    tr=sub.add_parser("train");tr.add_argument("--manifest",required=True)
    tr.add_argument("--grader",choices=LABELS,required=True)
    tr.add_argument("--out",required=True);tr.add_argument("--epochs",type=int,default=4)
    pr=sub.add_parser("predict");pr.add_argument("--checkpoint",required=True)
    pr.add_argument("--image",required=True)
    a=p.parse_args(argv)
    result=train(a.manifest,a.grader,a.out,a.epochs) if a.command=="train" else predict(a.checkpoint,a.image)
    print(json.dumps(result,indent=2))
if __name__=="__main__":main()
