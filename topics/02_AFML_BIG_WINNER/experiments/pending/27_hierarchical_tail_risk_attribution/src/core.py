"""EP27 observed-risk hierarchy and fixed information sets. No writes to prior episodes."""
from pathlib import Path
import hashlib,json,re
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from sklearn.metrics import roc_auc_score,average_precision_score
EP=Path(__file__).resolve().parents[1];TOPIC=EP.parents[2]
C=json.loads((EP/'config.json').read_text());OUT=EP/'outputs';CACHE=OUT/'local_cache'
EP24=EP.parent/'24_conditional_return_distribution_exploration';EP25=EP.parent/'25_incremental_distribution_validation';EP26=EP.parent/'26_left_tail_probability_validation'
PANEL=CACHE/'panel.parquet'


def digest(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    return h.hexdigest()


def write_json(p,v):
    Path(p).write_text(json.dumps(v,indent=2,ensure_ascii=False,default=str,allow_nan=False)+'\n')


def labels(actual):
    a=np.asarray(actual,float);return np.where(np.isfinite(a),(a<C['threshold']).astype(float),np.nan)


def keys_hash(frame):
    return hashlib.sha256(frame[['date','instrument']].to_csv(index=False).encode()).hexdigest()


def tie(instruments):
    return np.array([hashlib.sha256(f'27:{s}'.encode()).hexdigest() for s in instruments])


def feature_names(name):
    return C['risk_features']+[f for group in C['candidates'][name] for f in C[group+'_features']]


def weights(frame):
    w=1/frame.groupby('date').date.transform('size').to_numpy(float);return w/w.mean()


def fit_model(train,name,h):
    cols=feature_names(name);cats=[s for s in C['categorical_features'] if s in cols]
    y=labels(train[f'y_{h}']);assert np.isfinite(y).all() and len(np.unique(y))==2
    model=CatBoostClassifier(**C['catboost']);model.fit(train[cols],y,sample_weight=weights(train),cat_features=cats)
    return model


def predict(model,test,name):
    p=model.predict_proba(test[feature_names(name)])[:,list(model.classes_).index(1)]
    assert np.isfinite(p).all() and ((p>=0)&(p<=1)).all();return p


def split(panel,h,quarter):
    tr=panel[(panel.date<quarter.start_time)&(panel[f'end_{h}']<quarter.start_time)&panel[f'y_{h}'].notna()].copy()
    te=panel[panel.date.dt.to_period('Q')==quarter].copy().reset_index(drop=True)
    assert tr[f'end_{h}'].max()<quarter.start_time
    return tr,te


def load_panel():
    p=pd.read_parquet(PANEL);assert not p.duplicated(['date','instrument']).any();return p


def risk_cells(frame):
    g=frame.copy()
    for col,name in [('log_cap','size_bin'),('vol63','risk_bin')]:
        cuts=g[col].quantile([.5]).to_numpy();g[name]=np.searchsorted(cuts,g[col],side='right')
    g['risk_cell']=g.industry_id.astype(str)+':'+g.board.astype(str)+':'+g.size_bin.astype(str)+':'+g.risk_bin.astype(str)
    return g


def warning(p,instruments,fraction):
    flag=np.zeros(len(p),bool);n=max(1,int(np.ceil(len(p)*fraction)));order=np.lexsort((tie(instruments),-np.asarray(p)))
    flag[order[:n]]=True;return flag


def metrics(p,actual,flags=None):
    p=np.asarray(p,float);y=labels(actual);known=np.isfinite(y);p=p[known];y=y[known]
    if not len(p):return None
    common=(p.mean()-y.mean())**2;relative=np.mean(((p-p.mean())-(y-y.mean()))**2)
    r=dict(rows=len(p),events=int(y.sum()),base_rate=float(y.mean()),predicted=float(p.mean()),bias=float(p.mean()-y.mean()),brier=float(np.mean((p-y)**2)),common_brier=float(common),relative_brier=float(relative),
        auc=float(roc_auc_score(y,p)) if len(np.unique(y))==2 else np.nan,pr_auc=float(average_precision_score(y,p)) if y.sum()>0 else np.nan)
    if flags:
        for label,flag in flags.items():
            f=np.asarray(flag)[known];tp=float(y[f].sum());pr=float(y[f].mean()) if f.any() else np.nan
            r.update({f'precision{label}':pr,f'enrichment{label}':pr/y.mean() if y.mean()>0 else np.nan,f'recall{label}':tp/y.sum() if y.sum()>0 else np.nan,
                f'fpr{label}':float((1-y[f]).sum())/float((1-y).sum()) if (1-y).sum()>0 else np.nan})
    return r


def bootstrap_indices(n,block,reps=None):
    rng=np.random.default_rng(C['bootstrap']['seed']);r=C['bootstrap']['replicates'] if reps is None else reps
    ix=np.empty((r,n),np.int32);ix[:,0]=rng.integers(n,size=r)
    for j in range(1,n):ix[:,j]=np.where(rng.random(r)<1/block,rng.integers(n,size=r),(ix[:,j-1]+1)%n)
    return ix


def ci(values,block=6):
    v=np.asarray(values,float);assert len(v) and np.isfinite(v).any() and not np.isinf(v).any()
    sampled=v[bootstrap_indices(len(v),block)];den=np.isfinite(sampled).sum(axis=1);draw=np.nansum(sampled,axis=1)[den>0]/den[den>0]
    lo,hi=np.quantile(draw,[.025,.975]);flo,fhi=np.quantile(draw,[.00625,.99375]);se=float(draw.std(ddof=1))
    return dict(estimate=float(np.nanmean(v)),low95=float(lo),high95=float(hi),low_family=float(flo),high_family=float(fhi),months=len(v),defined_months=int(np.isfinite(v).sum()),block=block,approximate_blocks=len(v)/block,se=se,detectable_80pct_effect_approx=2.8*se)


def paired(a,b,metric):
    z=a[['date',metric]].merge(b[['date',metric]],on='date',suffixes=('_a','_b'),how='outer',validate='one_to_one',indicator=True)
    assert z._merge.eq('both').all();z=z.sort_values('date');return z[metric+'_a'].to_numpy()-z[metric+'_b'].to_numpy()


def loo_median(values,minimum_peers=5):
    v=np.asarray(values,float);known=np.isfinite(v);out=np.full(len(v),np.nan);m=int(known.sum())
    if m>=minimum_peers:out[~known]=np.median(v[known])
    if m-1<minimum_peers:return out
    ids=np.flatnonzero(known);order=np.argsort(v[ids],kind='stable');ordered=v[ids][order];ranks=np.empty(m,int);ranks[order]=np.arange(m)
    k0=(m-2)//2;k1=(m-1)//2
    out[ids]=(ordered[k0+(k0>=ranks)]+ordered[k1+(k1>=ranks)])/2
    return out


def rebuild_industry(panel,releases):
    parts=[];sources=[]
    for date,g in panel.groupby('date',sort=True):
        g=g.copy();available=[r for r in releases if pd.Timestamp(r['published'])<date]
        g['industry_id']='UNKNOWN';g['industry_sector']='UNKNOWN';g['industry_published']=pd.NaT;g['industry_age_days']=np.nan;g['industry_stale']=1.
        if available:
            item=max(available,key=lambda r:r['published']);path=Path(item['table_path']);table=pd.read_parquet(path).set_index('code');table.index=table.index.astype(str).str.zfill(6)
            major=g.instrument.str[2:].map(table.major);valid=major.fillna('').str.fullmatch('[A-S][0-9]{2}')
            era='legacy' if pd.Timestamp(item['published']).year<=2021 else 'revised'
            g.loc[valid,'industry_id']=era+':'+major[valid];sector=g.instrument.str[2:].map(table.sector)
            g.loc[valid,'industry_sector']=sector[valid];g['industry_published']=pd.Timestamp(item['published']);g['industry_age_days']=(date-pd.Timestamp(item['published'])).days
            g['industry_stale']=float((date-pd.Timestamp(item['published'])).days>365)
        for col in ['industry_mom63','industry_mom126','industry_breadth63','industry_peer_count']:g[col]=np.nan
        for name,group in g.groupby('industry_id',sort=True):
            if name=='UNKNOWN':continue
            g.loc[group.index,'industry_peer_count']=len(group)-1
            g.loc[group.index,'industry_mom63']=loo_median(group.mom63)
            g.loc[group.index,'industry_mom126']=loo_median(group.mom126)
            known=group.mom63.notna().to_numpy();positive=group.mom63.gt(0).to_numpy();den=known.sum()-known
            breadth=np.divide(positive.sum()-positive,den,out=np.full(len(group),np.nan),where=den>=5)
            g.loc[group.index,'industry_breadth63']=breadth
        parts.append(g)
    return pd.concat(parts,ignore_index=True).sort_values(['date','instrument']).reset_index(drop=True)


def prepare_panel():
    p=pd.read_parquet(EP24/'outputs/local_cache/four_horizon_panel.parquet').dropna(subset=C['eligibility_features']).copy()
    p['financial_age_days']=(p.date-p.financial_report_date).dt.days;p['state_turnover']=p.groupby('date').turnover21.transform('mean');p['state_breadth63']=p.groupby('date').mom63.transform(lambda x:x.gt(0).mean())
    p['regime']=np.where(p.market_mom126>0,'uptrend','non_uptrend');p['phase']=np.where(p.date<'2024-01-01','2021-2023','2024-2026')
    p['age_group']=pd.cut(p.financial_age_days,[-np.inf,365,456,548,np.inf],labels=['<=365','366-456','457-548','>548']).astype(str)
    releases=json.loads((EP24/'outputs/local_cache/r32_industry/parse_manifest.json').read_text())
    for r in releases:
        assert digest(Path(r['table_path']))==r['table_sha256'] and digest(Path(r['pdf_path']))==r['pdf_sha256']
    return rebuild_industry(p,releases),releases
