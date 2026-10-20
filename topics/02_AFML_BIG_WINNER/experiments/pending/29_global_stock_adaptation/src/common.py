"""Shared paths and fixed numerical/statistical primitives for EP29."""
from pathlib import Path
import hashlib,json
import numpy as np
import pandas as pd
from scipy.special import expit,logit
EP=Path(__file__).resolve().parents[1];TOPIC=EP.parents[2]
EP28=EP.parent/'28_literature_guided_tail_risk'
C=json.loads((EP/'configs/preregistration.yaml').read_text())
CACHE=EP/'outputs/local_cache';OUT=EP/'outputs/metrics';AUDIT=EP/'outputs/audits';MANIFEST=EP/'outputs/manifests'


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()


def write_json(path,value):
    Path(path).write_text(json.dumps(value,indent=2,ensure_ascii=False,default=str,allow_nan=False)+'\n')


def labels(v):
    a=np.asarray(v,float);return np.where(np.isfinite(a),(a<C['threshold']).astype(float),np.nan)


def logodds(p):return logit(np.clip(np.asarray(p,float),C['probability_clip'],1-C['probability_clip']))


def keyhash(f):return hashlib.sha256(f[['date','instrument']].to_csv(index=False).encode()).hexdigest()


def tie(s):return hashlib.sha256(f"29:{s}".encode()).hexdigest()


def bootstrap_indices(n,block):
    rng=np.random.default_rng(C['bootstrap']['seed']);r=C['bootstrap']['replicates'];ix=np.empty((r,n),int)
    ix[:,0]=rng.integers(n,size=r)
    for j in range(1,n):ix[:,j]=np.where(rng.random(r)<1/block,rng.integers(n,size=r),(ix[:,j-1]+1)%n)
    return ix


def interval(draw,estimate,block,n):
    d=np.asarray(draw,float);d=d[np.isfinite(d)];q=.05/(2*C['bootstrap']['secondary_family_size'])
    lo,hi=np.quantile(d,[.025,.975]);flo,fhi=np.quantile(d,[q,1-q]);se=float(d.std(ddof=1))
    return dict(estimate=float(estimate),low95=float(lo),high95=float(hi),low_secondary=float(flo),high_secondary=float(fhi),
        block=block,months=n,valid_bootstrap_draws=len(d),approximate_blocks=n/block,se=se,approximate_80pct_detectable_effect=2.8*se)


def ci(values,block):
    v=np.asarray(values,float);assert np.isfinite(v).any()
    return interval(np.nanmean(v[bootstrap_indices(len(v),block)],axis=1),np.nanmean(v),block,len(v))


def warnings(p,stocks,fraction):
    n=max(1,int(np.ceil(len(p)*fraction)));order=np.lexsort(([tie(s) for s in stocks],-np.asarray(p)))
    flag=np.zeros(len(p),bool);flag[order[:n]]=True;return flag
