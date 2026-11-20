"""Experimental card-border geometry, with explicit holder rejection.

Colored border segmentation proposes physical card edges. Independent line fitting
and four-sided boundary evidence are required; rectangle aspect alone never
identifies a card. Unsupported/occluded layouts abstain. No trained model or
validated accuracy is claimed. All coordinates refer to unchanged originals.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
import cv2
import numpy as np
from .centering_v2 import _order_quad

VERSION = "physical-border-helper-v1"

def _abstain(reason, **kwargs):
    return dict(version=VERSION, status='ABSTAIN', reason=reason, ratios=None,
                psa_grade_prediction=None, validated_psa10_upgrade_probability=None, **kwargs)

def _mask(image, kind):
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    lo, hi = (85, 135) if kind == 'blue_back' else (15, 40)
    return (((hsv[:,:,0] >= lo) & (hsv[:,:,0] <= hi) &
             (hsv[:,:,1] >= 65) & (hsv[:,:,2] >= 35)).astype(np.uint8) * 255)

def _intersection(a, b):
    # Lines are homogeneous ax + by + c = 0.
    p = np.cross(a, b)
    if abs(p[2]) < 1e-8:
        raise ValueError('parallel_card_edges')
    return p[:2] / p[2]

def _fit_quad(contour, initial):
    points = contour.reshape(-1, 2).astype(np.float32)
    lines, diagnostics = [], []
    for i in range(4):
        a, b = initial[i], initial[(i+1)%4]
        vector = b-a
        length = float(np.linalg.norm(vector))
        delta = points-a
        t = delta @ vector / (length*length)
        distance = abs(delta[:,0]*vector[1]-delta[:,1]*vector[0])/length
        # Excludes rounded corners and artwork edges deep inside the component.
        subset = points[(t > .16) & (t < .84) & (distance < length*.045)]
        if len(subset) < 30:
            raise ValueError('insufficient_straight_edge_support')
        vx, vy, x, y = cv2.fitLine(subset, cv2.DIST_HUBER, 0, .01, .01).ravel()
        line = np.array([-vy, vx, vy*x-vx*y], dtype=float)
        residual = abs(subset @ line[:2]+line[2])
        inliers = residual < max(1.5, length*.003)
        support = float(np.mean(inliers))
        if support < .75:
            raise ValueError('outer_edge_not_straight')
        lines.append(line)
        diagnostics.append(dict(points=len(subset), inlier_fraction=round(support,3),
                                median_residual_px=round(float(np.median(residual)),3)))
    q = np.array([_intersection(lines[(i-1)%4], lines[i]) for i in range(4)], np.float32)
    return _order_quad(q), diagnostics

def _warp(image, q, width=700, height=980):
    dest = np.array([[0,0],[width-1,0],[width-1,height-1],[0,height-1]], np.float32)
    matrix = cv2.getPerspectiveTransform(np.asarray(q,np.float32),dest)
    return cv2.warpPerspective(image,matrix,(width,height)),matrix

def _edge_support(image, q, kind):
    mask = _mask(image,kind)
    center = np.mean(q,axis=0)
    scores=[]
    for i in range(4):
        a,b=q[i],q[(i+1)%4]
        mid=(a+b)/2
        inward=center-mid
        inward/=np.linalg.norm(inward)
        edge = a[None,:]+np.linspace(.15,.85,80)[:,None]*(b-a)[None,:]
        # Positive evidence immediately inside physical edge; negative outside.
        d=max(3.,np.linalg.norm(b-a)*.008)
        def values(coords):
            xy=np.round(coords).astype(int)
            valid=(xy[:,0]>=0)&(xy[:,0]<mask.shape[1])&(xy[:,1]>=0)&(xy[:,1]<mask.shape[0])
            out=np.zeros(len(xy),float)
            out[valid]=mask[xy[valid,1],xy[valid,0]]/255
            return out
        inside=float(np.mean(values(edge+d*inward)))
        outside=float(np.mean(values(edge-d*inward)))
        scores.append(dict(inside_color_fraction=round(inside,3),outside_color_fraction=round(outside,3)))
    return scores

def detect_outer(image, side, layout='auto'):
    kinds = ['blue_back'] if side=='back' else ['yellow_border']
    if layout != 'auto':
        kinds=[layout] if layout in ('blue_back','yellow_border') else []
    scale=min(1.,1400/max(image.shape[:2]))
    sample=cv2.resize(image,None,fx=scale,fy=scale) if scale<1 else image
    candidates=[]
    rejected=[]
    for kind in kinds:
        mask=_mask(sample,kind)
        # No closing across slab gaps: connected border must be observed.
        contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)
        for c in contours:
            area=abs(cv2.contourArea(c))
            if area < sample.shape[0]*sample.shape[1]*.10:
                continue
            approx=cv2.approxPolyDP(c,.025*cv2.arcLength(c,True),True)
            if len(approx)!=4:
                rejected.append('colored_region_not_quadrilateral');continue
            try:
                initial=_order_quad(approx)
                quad,lines=_fit_quad(c,initial)
            except ValueError as e:
                rejected.append(str(e));continue
            lengths=np.linalg.norm(np.roll(quad,-1,axis=0)-quad,axis=1)
            ratio=float((lengths[0]+lengths[2])/(lengths[1]+lengths[3]))
            if not .60 < ratio < .83:
                rejected.append('card_aspect_incompatible');continue
            support=_edge_support(sample,quad,kind)
            if any(s['inside_color_fraction']<.85 or s['outside_color_fraction']>.25 for s in support):
                rejected.append(dict(reason='physical_edge_color_support_failed', outer_quad=(quad/scale).tolist(), edge_support=support));continue
            candidates.append(dict(outer_quad=(quad/scale).tolist(),layout=kind,
                line_diagnostics=lines,edge_support=support,aspect=ratio))
    if len(candidates)!=1:
        return _abstain('multiple_supported_cards' if candidates else 'physical_card_border_not_observable',
                        geometry_candidates=candidates,geometry_rejections=rejected)
    return candidates[0]
