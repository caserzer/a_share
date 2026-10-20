"""EP26 fixed binary probability experiment. Prior episodes are strictly read-only."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from sklearn.metrics import roc_auc_score, average_precision_score

EP=Path(__file__).resolve().parents[1]
TOPIC=EP.parents[2]
C=json.loads((EP/'config.json').read_text())
OLD=EP.parent/C['source_ep24'];PREV=EP.parent/C['source_ep25']
OUT=EP/'outputs';CACHE=OUT/'local_cache'
PREVC=json.loads((PREV/'config.json').read_text())
THRESHOLDS={10:-.1,20:-.2,30:-.3}
OLD_MODELS={'B1':'B1','D_R':'M_R','D_V':'M_V','D_F':'M_F','D_VF':'M_VF'}
ALL_MODELS=['B0']+list(OLD_MODELS)+list(C['candidates'])


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def write_json(path,value):
    Path(path).write_text(json.dumps(value,indent=2,ensure_ascii=False,default=str,allow_nan=False)+'\n')


def load_panel():
    raw=pd.read_parquet(OLD/'outputs/local_cache/four_horizon_panel.parquet')
    p=raw.dropna(subset=PREVC['eligibility_features']).copy()
    assert not p.duplicated(['date','instrument']).any()
    p['financial_age_days']=(p.date-p.financial_report_date).dt.days
    p['state_turnover']=p.groupby('date').turnover21.transform('mean')
    p['vol_x_market_vol']=p.vol63*p.market_vol63
    p['vol_x_credit']=p.vol63*p.credit_spread_3y
    known=p.financial_available_date.notna()
    assert (p.loc[known,'financial_available_date']<p.loc[known,'date']).all()
    assert (p.yield_observation_date<p.date).all()
    industry=pd.read_parquet(OLD/'outputs/local_cache/historical_industry_panel.parquet',columns=['date','instrument','industry_sector','industry_stale','industry_published'])
    assert not industry.duplicated(['date','instrument']).any()
    p=p.merge(industry,on=['date','instrument'],how='left',validate='one_to_one')
    p['industry_sector']=p.industry_sector.fillna('UNKNOWN')
    p['age_group']=pd.cut(p.financial_age_days,[-np.inf,365,456,548,np.inf],labels=['<=365','366-456','457-548','>548']).astype(str)
    p.loc[p.financial_age_days.isna(),'age_group']='missing'
    p['regime']=np.where(p.market_mom126>0,'uptrend','non_uptrend')
    p['phase']=np.where(p.date<'2024-01-01','2021-2023','2024-2026')
    return p.sort_values(['date','instrument']).reset_index(drop=True)


def feature_names(name):
    return C['risk_features']+[f for group in C['candidates'][name] for f in C[group+'_features']]


def weights(frame):
    w=1/frame.groupby('date').date.transform('size').to_numpy(float)
    return w/w.mean()


def fit_classifier(train,name,threshold):
    y=(train.y_6.to_numpy()<threshold).astype(int)
    assert len(np.unique(y))==2,'single-class training requires audit, not synthetic probabilities'
    model=CatBoostClassifier(**C['catboost'])
    model.fit(train[feature_names(name)],y,sample_weight=weights(train))
    return model


def predict(model,frame,name):
    p=model.predict_proba(frame[feature_names(name)])[:,list(model.classes_).index(1)]
    assert np.isfinite(p).all() and ((p>=0)&(p<=1)).all()
    return p


def coherence(p10,p20,p30):
    return np.maximum(p10,p20),p20,np.minimum(p30,p20)


def event_labels(actual,threshold):
    y=np.asarray(actual,float)
    return np.where(np.isfinite(y),(y<threshold).astype(float),np.nan)


def tie_keys(instruments):
    return np.array([hashlib.sha256(f"26:{s}".encode()).hexdigest() for s in instruments])


def risk_flags(probabilities,instruments,fraction):
    p=np.asarray(probabilities,float);n=max(1,int(np.ceil(len(p)*fraction)))
    order=np.lexsort((tie_keys(instruments),-p));flag=np.zeros(len(p),bool);flag[order[:n]]=True
    return flag


def point_metrics(probabilities,actual,threshold,flags=None):
    p=np.asarray(probabilities,float);y=event_labels(actual,threshold);known=np.isfinite(y)
    p=p[known];y=y[known];n=len(p)
    if not n:return None
    common=(p.mean()-y.mean())**2
    relative=np.mean(((p-p.mean())-(y-y.mean()))**2)
    result=dict(rows=n,events=int(y.sum()),base_rate=float(y.mean()),predicted=float(p.mean()),bias=float(p.mean()-y.mean()),
        brier=float(np.mean((p-y)**2)),common_brier=float(common),relative_brier=float(relative),
        auc=float(roc_auc_score(y,p)) if len(np.unique(y))==2 else np.nan,
        pr_auc=float(average_precision_score(y,p)) if y.sum()>0 else np.nan)
    if flags:
        for label,rawflag in flags.items():
            f=np.asarray(rawflag)[known];tp=float(y[f].sum());positives=float(y.sum());negatives=float((1-y).sum())
            precision=float(y[f].mean()) if f.any() else np.nan
            result.update({f'precision{label}':precision,f'enrichment{label}':precision/y.mean() if y.mean()>0 else np.nan,
                f'recall{label}':tp/positives if positives else np.nan,f'fpr{label}':float((1-y[f]).sum())/negatives if negatives else np.nan,
                f'warning_rows{label}':int(f.sum()),f'warning_fraction{label}':float(f.mean())})
    return result


def bootstrap_indices(n,block,reps=None,seed=None):
    rng=np.random.default_rng(C['bootstrap']['seed'] if seed is None else seed)
    r=C['bootstrap']['replicates'] if reps is None else reps
    idx=np.empty((r,n),dtype=np.int32);idx[:,0]=rng.integers(n,size=r)
    for t in range(1,n):
        restart=rng.random(r)<1/block
        idx[:,t]=np.where(restart,rng.integers(n,size=r),(idx[:,t-1]+1)%n)
    return idx


def ci(values,block=6):
    v=np.asarray(values,float);assert len(v) and np.isfinite(v).any() and not np.isinf(v).any()
    sampled=v[bootstrap_indices(len(v),block)]
    valid=np.isfinite(sampled).sum(axis=1)
    draws=np.nansum(sampled,axis=1)[valid>0]/valid[valid>0]
    lo,hi=np.quantile(draws,[.025,.975]);flo,fhi=np.quantile(draws,[.00625,.99375]);sd=draws.std(ddof=1)
    return dict(estimate=float(np.nanmean(v)),low95=float(lo),high95=float(hi),low_family=float(flo),high_family=float(fhi),
        months=len(v),defined_months=int(np.isfinite(v).sum()),block=block,approximate_blocks=len(v)/block,se=float(sd),detectable_80pct_effect_approx=float(2.8*sd))


def paired(a,b,metric):
    z=a[['date',metric]].merge(b[['date',metric]],on='date',suffixes=('_a','_b'),validate='one_to_one',how='outer',indicator=True)
    assert z._merge.eq('both').all(),'different paired months'
    z=z.sort_values('date')
    return z[metric+'_a'].to_numpy()-z[metric+'_b'].to_numpy()


def shuffle_within_month(frame,seed=2602):
    result=frame.copy()
    for date,g in result.groupby('date',sort=True):
        g=g[g.y_6.notna()]
        local=int(hashlib.sha256(f'{seed}:{date}'.encode()).hexdigest()[:12],16)
        rng=np.random.default_rng(local)
        result.loc[g.index,'y_6']=rng.permutation(g.y_6.to_numpy())
    return result


def train_test(panel,quarter):
    cutoff=quarter.start_time
    train=panel[(panel.date<cutoff)&(panel.end_6<cutoff)&panel.y_6.notna()].copy()
    test=panel[panel.date.dt.to_period('Q')==quarter].copy().reset_index(drop=True)
    assert train.end_6.max()<cutoff and train.date.max()<cutoff
    return train,test
