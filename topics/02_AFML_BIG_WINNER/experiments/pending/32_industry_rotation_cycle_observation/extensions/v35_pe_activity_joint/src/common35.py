from pathlib import Path
import sys,json
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];EXT=ROOT.parent;EP=EXT.parent
sys.path.insert(0,str(EXT/'v34_multiscale_expansion/src'))
from common34 import sha,js,md,episode_starts,top_k,OLD,ECON,KEY,IDENTITY,GROUPS as ACTIVITY
OUT=ROOT/'outputs';CACHE=OLD.parent/'joint_pe_v35';V34=OLD.parent/'multiscale_v34'
PE=['pe_change21','pe_change63','pe_change126','pe_change252','pe_rank504','pe_rank756','pe_breadth21']
MISSING=[x+'_missing' for x in PE]
MODELS={'pe':PE}
MODELS.update({'joint_'+k:v+PE for k,v in ACTIVITY.items()})
MODELS.update({'missing_'+k:v+MISSING for k,v in ACTIVITY.items()})
PE_ROOT=EP.parent/'30_pit_data_foundation_v1/extensions/v6_ttm_pe'
PE_RELEASE=Path(json.loads((PE_ROOT/'outputs/release.json').read_text())['path'])

def freeze():
    OUT.mkdir(parents=True,exist_ok=True);CACHE.mkdir(parents=True,exist_ok=True)
    refs={}
    for root in [EP]+sorted(EXT.glob('v*'))+[PE_ROOT]:
        if root==ROOT:continue
        p=root/'outputs/manifest.json'
        if not p.exists():continue
        for f in json.loads(p.read_text())['files']:
            source=root/f['path'];assert sha(source)==f['sha256'],source
            refs[str(source)]=f['sha256']
        refs[str(p)]=sha(p)
    refs[str(EP/'FOLLOWUP.md')]=sha(EP/'FOLLOWUP.md')
    js(OUT/'predecessors.json',refs)
    js(OUT/'freeze.json',dict(plan_sha256=sha(ROOT/'research_plan.md'),PE=PE,models=MODELS,
       pe_release=str(PE_RELEASE),strict_PIT='BLOCKED_DATA',quality='Historical-proxy',independent_holdout=False))

def stock_pe(panel):
    positive=panel.where(panel.gt(0)&np.isfinite(panel))
    out={}
    for w in [21,63,126,252]:
        ok=positive.rolling(w+1,min_periods=w+1).count().eq(w+1)
        out['pe_change'+str(w)]=np.log(positive/positive.shift(w)).where(ok)
    for w in [504,756]:
        out['pe_rank'+str(w)]=positive.rolling(w,min_periods=int(np.ceil(.75*w))).rank(pct=True).where(positive.notna())
    return out
