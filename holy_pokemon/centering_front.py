"""Automatic neutral-frame front measurement with explicit four-edge support.

Candidate rectangles are only search windows. The physical card starts at the
supported neutral frame, not at the rectangle/slab candidate. No grade inputs.
"""
import cv2
import numpy as np


def silver_frame(image, candidates):
    if any(np.linalg.norm(np.mean(a['points'],axis=0)-np.mean(b['points'],axis=0)) > np.sqrt(abs(cv2.contourArea(np.float32(a['points']))))*.7 for i,a in enumerate(candidates) for b in candidates[i+1:]):
        return None
    measurements=[]
    for candidate in candidates:
        q=np.float32(candidate['points'])
        dest=np.float32([[0,0],[699,0],[699,979],[0,979]])
        matrix=cv2.getPerspectiveTransform(q,dest)
        rect=cv2.warpPerspective(image,matrix,(700,980))
        hsv=cv2.cvtColor(rect,cv2.COLOR_BGR2HSV)
        mask=(hsv[:,:,1]<65)&(hsv[:,:,2]>185)
        edges={};failed=False
        for name in ('left','right','top','bottom'):
            strip=mask[196:784] if name in ('left','right') else mask[:,140:560].T
            if name in ('right','bottom'):strip=strip[:,::-1]
            n=strip.shape[1];profile=strip.mean(axis=0)
            limit=int(n*.09);start=None;end=None
            # Supported neutral ring must be bounded by a darker/nonneutral
            # outside and printed artwork inside. No holder-as-card assumption.
            runs=[]
            pos=0
            while pos<limit:
                if profile[pos]>=.85:
                    begin=pos
                    while pos<limit and profile[pos]>=.85:pos+=1
                    if pos-begin>=4:runs.append((begin,pos))
                else:pos+=1
            if not runs:failed=True;break
            start,end=max(runs,key=lambda pair:pair[1]-pair[0])
            if end>=limit-1 or end-start<4 or end-start>n*.065:
                failed=True;break
            # Spatial segments corroborate the same neutral ring; artwork can also
            # contain neutral pixels, so six independent edge regions must agree.
            support=0
            for chunk in np.array_split(strip,10):
                local=chunk.mean(axis=0)
                if local[start:end].mean()>=.8 and local[end+2:min(end+8,n)].mean()<.7:
                    support+=1
            if support<6:failed=True;break
            edges[name]=(start,end,support)
        if failed:continue
        l,r,t,b=[edges[n][0] for n in ('left','right','top','bottom')]
        il,ir,it,ib=[edges[n][1] for n in ('left','right','top','bottom')]
        # Reject a neutral holder frame with a black gap before the actual card.
        # An authentic silver border directly adjoins chromatic print inside.
        sat=hsv[:,:,1]
        interior=sat[it+4:979-ib-4,il+4:699-ir-4]
        if interior.size==0 or np.mean(interior>75)<.35:continue
        outer_rect=np.float32([[[l,t],[699-r,t],[699-r,979-b],[l,979-b]]])
        inner_rect=np.float32([[[il,it],[699-ir,it],[699-ir,979-ib],[il,979-ib]]])
        inverse=np.linalg.inv(matrix)
        outer=cv2.perspectiveTransform(outer_rect,inverse)[0]
        inner=cv2.perspectiveTransform(inner_rect,inverse)[0]
        widths=dict(left=float(il-l),right=float(ir-r),top=float(it-t),bottom=float(ib-b))
        measurements.append(dict(outer_quad=outer.tolist(),inner_quad=inner.tolist(),widths=widths,
                                  support={k:v[2] for k,v in edges.items()}))
    # Multiple distinct cards must not turn into a single measurement.
    unique=[]
    for result in measurements:
        if not any(np.max(np.linalg.norm(np.array(result['outer_quad'])-np.array(other['outer_quad']),axis=1))<8 for other in unique):
            unique.append(result)
    return unique[0] if len(unique)==1 else None
