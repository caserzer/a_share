"""EP37 shared contracts; all EP36 consumers are read-only."""
from pathlib import Path
import hashlib, json, platform
from functools import lru_cache
import numpy as np
import pandas as pd
import yaml
from scipy.stats import rankdata

EP = Path(__file__).resolve().parents[1]
SOURCE = EP.parent / '36_csi300_alpha_discovery_and_index_enhancement'
PRIVATE = SOURCE / 'private'
CACHE = EP / 'outputs/local_cache'
OUT = EP / 'outputs/publishable'
MAN = EP / 'outputs/manifests'
BASE = ['T15', 'T55', 'R1', 'R5']
INTER = [a+'_x_'+b for a in BASE[:2] for b in BASE[2:]]
JOINT = BASE + INTER + ['UD', 'DU', 'DD']
STATES = ['UU', 'UD', 'DU', 'DD']
MODELS = ['A_Z', 'J_Z', 'A_R', 'J_R', 'J_RW']
SCORES = ['MOM', 'REV', 'FIX'] + MODELS

@lru_cache(maxsize=1)
def config():
    return yaml.safe_load((EP/'config.yaml').read_text())

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()

def dump(path, value):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,default=str,allow_nan=False)+'\n')

def clean(value):
    if isinstance(value,dict): return {str(k):clean(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)): return [clean(v) for v in value]
    if isinstance(value,np.ndarray): return clean(value.tolist())
    if isinstance(value,(np.integer,)): return int(value)
    if isinstance(value,(float,np.floating)): return float(value) if np.isfinite(value) else None
    return value

def rankcorr(a,b):
    a=np.asarray(a,float);b=np.asarray(b,float)
    ok=np.isfinite(a)&np.isfinite(b);a=a[ok];b=b[ok]
    if len(a)<3 or np.std(a)<1e-12 or np.std(b)<1e-12:return np.nan
    return float(np.corrcoef(rankdata(a),rankdata(b))[0,1])

def centered_rank(s):
    return s.rank(method='average')/(s.count()+1)-.5

def classify(trend,short):
    trend=np.asarray(trend,float);short=np.asarray(short,float)
    return np.select([~np.isfinite(trend)|~np.isfinite(short), (trend==0)|(short==0),
                      (trend>0)&(short>0),(trend>0)&(short<0),(trend<0)&(short>0)],
                     ['UNKNOWN','ZERO','UU','UD','DU'],default='DD')

def assign_deciles(frame, score):
    order=frame.sort_values([score,'instrument'],kind='stable').index
    out=pd.Series(index=frame.index,dtype='int64')
    out.loc[order]=np.floor(10*np.arange(len(order))/len(order)).astype(int)+1
    return out.astype(int)

def state_weights(frame):
    out=pd.Series(1.,index=frame.index)
    for _,g in frame.groupby('signal_date'):
        counts=g.state.value_counts();w=len(g)/(len(counts)*g.state.map(counts).to_numpy(float))
        w=np.clip(w,.25,4);out.loc[g.index]=w/w.mean()
    return out.to_numpy()

def bootstrap(values, length=6, reps=2000, seed=20261118):
    """Keep missing slots in calendar; test against a centered null, never count stocks as iid."""
    x=np.asarray(values,float);n=len(x);valid=np.isfinite(x).sum()
    ans=dict(n=int(valid),calendar_n=n,mean=float(np.nanmean(x)) if valid else np.nan,
             low=np.nan,high=np.nan,p=np.nan,block=length)
    if valid<config()['statistics']['minimum_observed_rounds']:return ans
    rng=np.random.default_rng(seed)
    starts=rng.integers(0,n,size=(reps,int(np.ceil(n/length))))
    idx=((starts[:,:,None]+np.arange(length))%n).reshape(reps,-1)[:,:n]
    sample=x[idx];count=np.isfinite(sample).sum(axis=1)
    means=np.divide(np.nansum(sample,axis=1),count,out=np.full(reps,np.nan),where=count>0)
    means=means[np.isfinite(means)];mu=ans['mean']
    ans.update(low=float(np.quantile(means,.025)),high=float(np.quantile(means,.975)),
               p=float((1+np.sum(np.abs(means-mu)>=abs(mu)))/(1+len(means))))
    return ans

def holm(ps):
    # Missing members remain in the original family with p=1.
    ps=np.asarray(ps,float);safe=np.where(np.isfinite(ps),ps,1.);order=np.argsort(safe,kind='stable')
    adjusted=np.maximum.accumulate((len(ps)-np.arange(len(ps)))*safe[order]).clip(0,1)
    out=np.empty(len(ps));out[order]=adjusted;out[~np.isfinite(ps)]=np.nan
    return out

def record_stage(name,files,extra=None):
    rec=dict(stage=name,config_sha256=sha(EP/'config.yaml'),
             files=[dict(path=str(Path(p).relative_to(EP)),sha256=sha(p)) for p in files],
             code=[dict(path=str(p.relative_to(EP)),sha256=sha(p)) for p in sorted((EP/'code').glob('*.py'))])
    if extra:rec.update(extra)
    dump(MAN/(name+'.json'),clean(rec))

def verify_freeze():
    rec=json.loads((MAN/'execution_freeze.json').read_text())
    assert sha(EP/'config.yaml')==rec['config_sha256']
    for x in rec['inputs']:assert sha(x['path'])==x['sha256'],x['path']
    return rec

def freeze():
    p=MAN/'execution_freeze.json'
    if p.exists():return verify_freeze()
    names=['qfq_close.parquet','qfq_open.parquet','open.parquet','close.parquet','daily_members.parquet',
           'opening_trade_status_v2.parquet','limits/daily.parquet','suspensions/daily.parquet',
           'industry.parquet','market.parquet','money.parquet','turnover_rate.parquet']
    files=[PRIVATE/n for n in names]
    files += sorted((PRIVATE/'style_caps_20261117').glob('*.json'))
    files += [SOURCE/'outputs/manifests/data_snapshot.json']
    for x in json.loads((EP/'notes/source_snapshot.json').read_text())['files']:
        assert sha(EP.parents[4]/x['path'])==x['sha256'],x['path']
    import scipy,sklearn
    rec=dict(config_sha256=sha(EP/'config.yaml'),user_authorization='执行',
             prior_EP36_outcomes_seen=True,EP37_model_outcomes_seen=False,
             inputs=[dict(path=str(f),sha256=sha(f),bytes=f.stat().st_size) for f in files],
             environment=dict(python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__,
                              scipy=scipy.__version__,sklearn=sklearn.__version__))
    dump(p,rec);return rec
