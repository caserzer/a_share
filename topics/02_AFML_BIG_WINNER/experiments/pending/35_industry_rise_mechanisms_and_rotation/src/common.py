from pathlib import Path
import hashlib
import json
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
EP32 = ROOT.parent/'32_industry_rotation_cycle_observation'
CACHE = Path('/home/xiaolv/.cache/a_share/ep32')
KEY = ['era','level','industry_code']

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda:f.read(1<<20), b''): h.update(block)
    return h.hexdigest()

def clean(obj):
    if isinstance(obj,dict): return {str(k):clean(v) for k,v in obj.items()}
    if isinstance(obj,(tuple,list)): return [clean(v) for v in obj]
    if isinstance(obj,np.generic): return clean(obj.item())
    if isinstance(obj,float) and not np.isfinite(obj): return None
    return obj

def js(p,obj):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(clean(obj),ensure_ascii=False,indent=2,default=str,allow_nan=False)+'\n')

def centered_rank(s):
    return (s.rank(method='average')-.5)/s.count()-.5
