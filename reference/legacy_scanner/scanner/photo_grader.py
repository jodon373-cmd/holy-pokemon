"""Offline photograph pre-grading research. Not a PSA certification or PSA10 probability."""
import argparse,json
from pathlib import Path
import numpy as np
from PIL import Image,ImageOps,UnidentifiedImageError

def read_image(path):
    p=Path(path)
    if not p.is_file() or p.suffix.lower() not in ('.jpg','.jpeg','.png','.webp'):
        raise ValueError('Local JPG/PNG/WebP file required; no URLs or network requests')
    try:
        with Image.open(p) as im:
            if im.width*im.height>24_000_000: raise ValueError('Image exceeds 24MP')
            array=np.asarray(ImageOps.exif_transpose(im).convert('RGB'))
    except (OSError,UnidentifiedImageError,Image.DecompressionBombError) as e:
        raise ValueError('Invalid photograph') from e
    if min(array.shape[:2])<220: raise ValueError('Image too small for screening')
    return array

def quality(image):
    import cv2
    gray=cv2.cvtColor(image,cv2.COLOR_RGB2GRAY)
    t=cv2.resize(gray,(min(700,gray.shape[1]),min(700,gray.shape[0])))
    focus=float(cv2.Laplacian(t,cv2.CV_64F).var())
    exposure=float(np.mean((gray<13)|(gray>247)))
    white=float(np.mean(np.all(image>247,axis=2)))
    return {'blur_variance':round(focus,2),'extreme_exposure_fraction':round(exposure,4),
            'white_pixel_fraction':round(white,4),'blur_warning':focus<75,
            'exposure_warning':exposure>.40,'glare_proxy_warning':white>.20}

def order_corners(pts):
    total=pts.sum(axis=1)
    diff=pts[:,0]-pts[:,1]
    return np.float32([pts[np.argmin(total)],pts[np.argmax(diff)],
                       pts[np.argmax(total)],pts[np.argmin(diff)]])

def find_card(image):
    """Card-vs-slab ambiguity is always flagged; returned rectangle is unverified."""
    import cv2
    h,w=image.shape[:2]
    factor=min(1,1100/max(h,w))
    thumb=cv2.resize(image,(round(w*factor),round(h*factor)))
    gray=cv2.cvtColor(thumb,cv2.COLOR_RGB2GRAY)
    edges=cv2.Canny(cv2.GaussianBlur(gray,(5,5),1),35,125)
    cont=cv2.findContours(edges,cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)[0]
    candidates=[]
    for c in cont:
        area=cv2.contourArea(c)/np.prod(gray.shape)
        if not .22<area<.94:continue
        poly=cv2.approxPolyDP(c,.028*cv2.arcLength(c,True),True)
        if len(poly)!=4 or not cv2.isContourConvex(poly):continue
        pts=order_corners(poly.reshape(4,2).astype(np.float32))
        side=[np.linalg.norm(pts[(i+1)%4]-pts[i]) for i in range(4)]
        a,b=(side[0]+side[2])/2,(side[1]+side[3])/2
        aspect=min(a,b)/max(a,b)
        if .64<aspect<.80:candidates.append((area,pts/factor,aspect))
    if not candidates:return None,{'status':'NO_RELIABLE_QUADRILATERAL','candidate_count':0}
    candidates.sort(key=lambda x:x[0],reverse=True)
    if len(candidates)>1 and candidates[1][0]>.80*candidates[0][0]:
        return None,{'status':'AMBIGUOUS_CARD_VS_SLAB','candidate_count':len(candidates)}
    area,pts,aspect=candidates[0]
    dest=np.float32([[0,0],[499,0],[499,699],[0,699]])
    warped=cv2.warpPerspective(image,cv2.getPerspectiveTransform(pts,dest),(500,700))
    return warped,{'status':'AUTO_RECTIFIED_UNVERIFIED','candidate_count':len(candidates),
                   'area_fraction':round(area,3),'aspect':round(aspect,3)}

def estimated_border(image):
    """Estimates inner printed-frame insets, NOT verified card centering."""
    import cv2
    gray=cv2.GaussianBlur(cv2.cvtColor(image,cv2.COLOR_RGB2GRAY),(7,7),0)
    h,w=gray.shape
    x=np.abs(np.diff(gray.astype(np.float32),axis=1))
    y=np.abs(np.diff(gray.astype(np.float32),axis=0))
    profiles={'lr':(np.mean(x[int(h*.3):int(h*.7)],axis=0),w),
              'tb':(np.mean(y[:,int(w*.3):int(w*.7)],axis=1),h)}
    def peak(profile,size,reverse):
        low,high=int(size*.025),int(size*.23)
        a,b=(size-high,size-low) if reverse else (low,high)
        segment=profile[a:b]
        if len(segment)<10:return None
        pos=int(np.argmax(segment))+a
        return size-pos if reverse else pos,float(segment.max()/max(np.median(segment),.001))
    results={}
    for axis,(profile,size) in profiles.items():
        p,q=peak(profile,size,False),peak(profile,size,True)
        if not p or not q:results[axis]=None;continue
        major=100*max(p[0],q[0])/(p[0]+q[0])
        results[axis]={'major_percent':round(major,2),
                       'minor_percent':round(100-major,2),
                       'border_pixels':[int(p[0]),int(q[0])],
                       'edge_peak_ratios':[round(p[1],2),round(q[1],2)],
                       'low_contrast':p[1]<1.4 or q[1]<1.4}
    return results

def predict_onnx(image,model):
    """External published model's uncalibrated five-score inference."""
    import cv2
    try:import onnxruntime as ort
    except ImportError as e:raise RuntimeError('Install onnxruntime for --model') from e
    session=ort.InferenceSession(str(model),providers=['CPUExecutionProvider'])
    inp=session.get_inputs()[0]
    if list(inp.shape)[1:]!=[3,380,380]:raise ValueError('Unexpected model input shape')
    image=cv2.resize(image,(380,380)).astype(np.float32)/255
    image=(image-np.array([.485,.456,.406],dtype=np.float32))/np.array([.229,.224,.225],dtype=np.float32)
    tensor=np.transpose(image,(2,0,1))[None,...]
    values=np.asarray(session.run(None,{inp.name:tensor})[0]).reshape(-1)
    if values.size!=5 or not np.isfinite(values).all() or values.min()<-.1 or values.max()>1.1:
        raise ValueError('Unexpected model output schema')
    return dict(zip(('overall','surface','corners','edges','centering'),
                    [round(float(np.clip(a,0,1)*9+1),2) for a in values]))

def analyze(front,back=None,model=None,already_cropped=False):
    front_arr=read_image(front); back_arr=read_image(back) if back else None
    result={'grade_estimate':None,'psa10_probability':None,'purchase_approved':False,
            'front_quality':quality(front_arr),'back_quality':quality(back_arr) if back_arr is not None else None,
            'front_centering_hint':None,'back_centering_hint':None,'reasons':[]}
    for side,array in [('front',front_arr),('back',back_arr)]:
        if array is None:result['reasons'].append(side+'_missing_image');continue
        crop,meta=(array,{'status':'USER_ASSERTED_CROPPED_CARD'}) if already_cropped else find_card(array)
        result[side+'_rectification']=meta
        if crop is None:result['reasons'].append(side+'_card_not_isolated')
        else:
            border=estimated_border(crop)
            result[side+'_centering_hint']=border
            for axis,r in border.items():
                if r and r['major_percent']>(55 if side=='front' else 75)+3:
                    result['reasons'].append(side+'_'+axis+'_possible_offcenter_review')
        if any(result[side+'_quality'][x] for x in ('blur_warning','exposure_warning','glare_proxy_warning')):
            result['reasons'].append(side+'_poor_photo_quality')
    if model:
        result['grade_estimate']=predict_onnx(front_arr,model)
        result['reasons'].append('unvalidated_third_party_model')
    result['status']='PHOTO_REVIEW_REQUIRED' if result['reasons'] else 'PRELIMINARY_VISUAL_SCREEN_ONLY'
    return result

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--front',required=True);p.add_argument('--back')
    p.add_argument('--model',help='locally saved ONNX file; no download')
    p.add_argument('--already-cropped',action='store_true')
    p.add_argument('--output')
    a=p.parse_args(argv)
    data=json.dumps(analyze(a.front,a.back,a.model,a.already_cropped),indent=2)+'\n'
    if a.output:Path(a.output).write_text(data)
    print(data)
if __name__=='__main__':main()
