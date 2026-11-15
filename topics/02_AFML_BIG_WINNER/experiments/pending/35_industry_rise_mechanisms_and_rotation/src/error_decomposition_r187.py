"""Frozen-prediction diagnostic: common versus cross-sectional error."""
from common import *
import pandas as pd
from scipy.stats import spearmanr
G=['era','level','cohort','horizon','year','method']

def run():
    out=ROOT/'outputs/r187';out.mkdir(exist_ok=True)
    source=ROOT/'outputs/r131/predictions.parquet'
    p=pd.read_parquet(source);p=p[p.task.eq('return')].copy()
    rows=[];pairs=[];worst=0.
    for key,g in p.groupby(G+['date']):
        ident=dict(zip(G+['date'],key));v=g[g.y.notna()]
        if v.empty:continue
        y=v.y.to_numpy();pred=v.prediction.to_numpy();b=v.training_mean.to_numpy()
        assert np.ptp(b)<1e-12
        mse=np.mean((pred-y)**2);common=(pred.mean()-y.mean())**2
        centered=np.mean(((pred-pred.mean())-(y-y.mean()))**2)
        base=np.mean((b-y)**2);bc=(b[0]-y.mean())**2;bv=np.var(y)
        # Independent variance of errors equals centered residual MSE.
        error=max(abs(mse-common-centered),abs(base-bc-bv),abs(centered-np.var(pred-y)))
        assert error<1e-12;worst=max(worst,float(error))
        ic=float(spearmanr(pred,y).statistic) if len(v)>1 and np.ptp(y)>0 and np.ptp(pred)>0 else np.nan
        rows.append(dict(ident,n=len(g),mature=len(v),unknown=len(g)-len(v),mse=mse,common=common,centered=centered,baseline=base,base_common=bc,base_centered=bv,rank_ic=ic))
    d=pd.DataFrame(rows);d.to_csv(out/'date_metrics.csv',index=False)
    metrics=['mse','common','centered','baseline','base_common','base_centered','rank_ic']
    folds=d.groupby(G)[metrics].mean().reset_index()
    folds['total_skill']=1-folds.mse/folds.baseline
    folds['centered_skill']=1-folds.centered/folds.base_centered
    folds.to_csv(out/'fold_metrics.csv',index=False)
    # Preserve exact identities for every extension comparison, including unknown labels.
    for key,g in p[p.cohort.ne('F')].groupby(G[:-1]+['date']):
        cohort=key[2];a=g[g.method.eq('F')].sort_values(KEY);b=g[g.method.eq(cohort)].sort_values(KEY)
        assert len(a)==len(b) and len(a)>0
        assert a[KEY+['y','maturity']].reset_index(drop=True).equals(b[KEY+['y','maturity']].reset_index(drop=True))
    for key,g in d[d.cohort.ne('F')].groupby(G[:-1]+['date']):
        a=g[g.method.eq('F')].iloc[0];b=g[g.method.eq(key[2])].iloc[0]
        rec=dict(zip(G[:-1]+['date'],key))
        for metric in ['mse','common','centered']:rec[metric+'_improvement']=a[metric]-b[metric]
        rec['ic_increment']=b.rank_ic-a.rank_ic
        assert abs(rec['mse_improvement']-rec['common_improvement']-rec['centered_improvement'])<1e-12
        pairs.append(rec)
    pair=pd.DataFrame(pairs);pair.to_csv(out/'paired_dates.csv',index=False)
    pf=pair.groupby(G[:-1]).mean(numeric_only=True).reset_index();pf.to_csv(out/'paired_folds.csv',index=False)
    # Reconcile with independently generated R186 test MSE and fixed-mean MSE.
    previous=pd.read_csv(ROOT/'outputs/r186/fold_metrics.csv');previous=previous[previous.split.eq('test')]
    check=folds.merge(previous,on=G,suffixes=('_new','_old'),validate='one_to_one')
    assert len(check)==len(folds)==len(previous)
    assert np.allclose(check.mse_new,check.mse_old,rtol=1e-12,atol=1e-15)
    assert np.allclose(check.baseline,check.baseline_mse,rtol=1e-12,atol=1e-15)
    summary=[]
    for (h,c,m),g in folds.groupby(['horizon','cohort','method']):
        summary.append(dict(horizon=int(h),cohort=c,method=m,folds=len(g),total_positive=int(g.total_skill.gt(0).sum()),centered_positive=int(g.centered_skill.gt(0).sum()),median_total_skill=g.total_skill.median(),median_centered_skill=g.centered_skill.median(),median_rank_ic=g.rank_ic.median()))
    js(out/'summary.json',summary)
    inputs=['outputs/r131/predictions.parquet','outputs/r186/fold_metrics.csv','protocols/r187.json','src/error_decomposition_r187.py','src/common.py']
    outputs=['date_metrics.csv','fold_metrics.csv','paired_dates.csv','paired_folds.csv','summary.json']
    js(out/'verification.json',dict(status='PASS',scope='Algebraic decomposition, exact paired identities, and R186 total error reconciliation',folds=len(folds),dates=len(d),paired_dates=len(pair),max_identity_error=worst,inputs={x:sha(ROOT/x) for x in inputs},outputs={x:sha(out/x) for x in outputs}))
    print((out/'summary.json').read_text())
if __name__=='__main__':run()
