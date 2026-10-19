"""R12: seven mutually exclusive classes and weighted within-class distributions."""
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from run_four_horizons import DEST, OUT, CACHE, TECH, VALUATION, FINANCIAL, CREDIT, BINS, BIN_NAMES


def classes(y):
    y=np.asarray(y)
    return np.select([y<-.2,y<-.05,y<0,y==0,y<.05,y<.2],[0,1,2,3,4,5],default=6)


def weighted_stats(atoms,weights,actual):
    y=np.asarray(actual)
    assert np.all(np.diff(atoms,axis=1)>=0)
    np.testing.assert_allclose(weights.sum(axis=1),1,atol=1e-10)
    cum=weights.cumsum(axis=1)
    p=(weights*(atoms>0)).sum(axis=1)
    out=pd.DataFrame(dict(p_up=p,p_down=(weights*(atoms<0)).sum(axis=1),p_zero=(weights*(atoms==0)).sum(axis=1)))
    quantiles=[]
    for q in [.05,.5,.95]:
        idx=(cum>=q).argmax(axis=1)
        quantiles.append(atoms[np.arange(len(atoms)),idx])
    q05,q50,q95=quantiles
    out['q05'],out['q50'],out['q95']=quantiles
    out['mean']=(weights*atoms).sum(axis=1)
    out['crps']=(weights*np.abs(atoms-y[:,None])).sum(axis=1)-(weights*atoms*(2*cum-weights-1)).sum(axis=1)
    out['brier']=(p-(y>0))**2
    out['pit']=(weights*((atoms<y[:,None])+(atoms<=y[:,None]).astype(float))*.5).sum(axis=1)
    out['below_q05']=(y<q05).astype(float)
    out['coverage90']=((y>=q05)&(y<=q95)).astype(float)
    bins=np.searchsorted(BINS,atoms,side='right')
    probs=np.stack([(weights*(bins==i)).sum(axis=1) for i in range(5)],axis=1)
    for i,name in enumerate(BIN_NAMES):out[f'p_{name}']=probs[:,i]
    out['multiclass_brier']=((probs-np.eye(5)[np.searchsorted(BINS,y,side='right')])**2).sum(axis=1)
    out.loc[~np.isfinite(y),['crps','brier','pit','below_q05','coverage90','multiclass_brier']]=np.nan
    return out


def run():
    panel=pd.read_parquet(OUT/'local_cache/four_horizon_panel.parquet').dropna(subset=TECH+['earnings_yield','book_yield'])
    cols=TECH+['financial_available','valuation_available']+VALUATION+FINANCIAL+CREDIT
    audits=[]
    for h in [1,3,6,12]:
        results=[]
        for quarter in pd.period_range('2021Q1','2026Q2',freq='Q'):
            train=panel[(panel[f'end_{h}']<quarter.start_time)&panel[f'y_{h}'].notna()]
            test=panel[panel.date.dt.to_period('Q')==quarter].reset_index(drop=True)
            if test.empty: continue
            y=train[f'y_{h}'].to_numpy(); c=classes(y)
            model=make_pipeline(SimpleImputer(strategy='median',keep_empty_features=True),StandardScaler(),LogisticRegression(C=.1,max_iter=500,solver='lbfgs'))
            model.fit(train[cols],c)
            pc=np.zeros((len(test),7))
            pc[:,model[-1].classes_]=model.predict_proba(test[cols])
            inner=[]
            placeholders=[-.3,-.1,-.025,0,.025,.1,.3]
            for k in range(7):
                v=y[c==k]
                inner.append(np.quantile(v,(np.arange(32)+.5)/32) if len(v) else np.full(32,placeholders[k]))
            atoms=np.tile(np.concatenate(inner),(len(test),1))
            weights=np.repeat(pc/32,32,axis=1)
            r=test[['date','instrument',f'y_{h}',f'end_{h}',f'target_{h}']].rename(columns={f'y_{h}':'actual',f'end_{h}':'label_end',f'target_{h}':'target_date'})
            r=pd.concat([r,weighted_stats(atoms,weights,r.actual)],axis=1)
            r['model']='logistic_bins';r['months']=h
            results.append(r)
            np.savez_compressed(CACHE/f'{h}_{quarter}_logistic_bins.npz',atoms=atoms.astype(np.float32),weights=weights.astype(np.float32))
            test[['date','instrument']].to_parquet(CACHE/f'{h}_{quarter}_logistic_keys.parquet',index=False)
            audits.append(dict(months=h,quarter=str(quarter),last_training_label=str(train[f'end_{h}'].max()),training_rows=len(train),iterations=int(model[-1].n_iter_.max())))
            print('R12',h,str(quarter),flush=True)
        path=DEST/f'predictions_{h}m.parquet'
        existing=pd.read_parquet(path)
        pd.concat([existing[existing.model!='logistic_bins'],*results],ignore_index=True).to_parquet(path,index=False)
    pd.DataFrame(audits).to_csv(DEST/'direct_probability_fit_audit.csv',index=False)


if __name__=='__main__':run()
