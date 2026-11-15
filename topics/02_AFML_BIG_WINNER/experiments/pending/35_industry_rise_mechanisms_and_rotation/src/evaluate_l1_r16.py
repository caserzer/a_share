import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score, brier_score_loss
from common import *
from evaluate_r01 import bootstrap


def binary_metrics(g):
    v=g[g.y.notna()];n=len(v)
    if not n:return dict(n=0)
    bins=np.minimum((v.prediction*10).astype(int),9)
    cal=v.assign(bin=bins).groupby('bin').agg(n=('y','size'),p=('prediction','mean'),rate=('y','mean'))
    positives=v.y.sum(); alerts=v[v.alert]
    return dict(n=n,prevalence=v.y.mean(),brier=brier_score_loss(v.y,v.prediction),
        raw_brier=brier_score_loss(v.y,v.raw_prediction),baseline_brier=brier_score_loss(v.y,v.training_mean),
        pr_auc=average_precision_score(v.y,v.prediction) if positives else np.nan,
        roc_auc=roc_auc_score(v.y,v.prediction) if v.y.nunique()==2 else np.nan,
        ece=float((cal.n*(cal.p-cal.rate).abs()).sum()/n),alerts=len(alerts),
        precision=alerts.y.mean(),recall=alerts.y.sum()/positives if positives else np.nan,
        alert_fraction=len(alerts)/n,wrong_exit_positive_excess_fraction=alerts.excess.gt(0).mean(),
        missed_positive_excess=alerts.excess.clip(lower=0).mean(),alert_mean_excess=alerts.excess.mean(),
        pending=int(g.y.isna().sum()))


def run():
    out=ROOT/'outputs/r16';receipt=json.loads((out/'run_receipt.json').read_text())
    assert sha(out/'predictions.parquet')==receipt['prediction_sha256']
    d=pd.read_parquet(out/'predictions.parquet')
    assert not d.duplicated(['row_id','cohort','method','task','horizon','year']).any()
    d['alert']=False;date_rows=[];cal_rows=[]
    groups=['era','level','cohort','method','task','horizon']
    for key,g in d.groupby(groups+['date']):
        k=max(1,int(np.ceil(len(g)*.2)));selected=g.sort_values(['prediction','industry_code'],ascending=[False,True]).head(k).index
        d.loc[selected,'alert']=True;g=g.copy();g['alert']=g.index.isin(selected)
        valid=g[g.y.notna()]
        rec=dict(zip(groups+['date'],key),n_signal=len(g),n_mature=len(valid),alerts_signal=k)
        if key[4]=='return':
            rec['utility']=valid.prediction.corr(valid.y,method='spearman') if len(valid)>=20 and valid.prediction.nunique()>1 else np.nan
            top=g[g.alert];rec['top_excess']=top.excess.mean() if top.y.notna().all() else np.nan
            rec['top_excess_cost20bps']=rec['top_excess']-.004
        else:
            rec['utility']=-np.mean((valid.prediction-valid.y)**2) if len(valid) else np.nan
        date_rows.append(rec)
    dates=pd.DataFrame(date_rows);dates.to_csv(out/'date_metrics.csv',index=False)
    summaries=[]
    for key,g in d.groupby(groups):
        if key[4]=='return':
            r=dates
            for col,v in zip(groups,key):r=r[r[col].eq(v)]
            summaries.append(dict(zip(groups,key),n=int(g.y.notna().sum()),ic=r.utility.mean(),months=int(r.utility.notna().sum()),top_excess=r.top_excess.mean(),top_excess_cost20bps=r.top_excess_cost20bps.mean()))
        else:
            summaries.append(dict(zip(groups,key),**binary_metrics(g)))
            z=g[g.y.notna()].copy();z['bin']=np.minimum((z.prediction*10).astype(int),9)
            for bucket,v in z.groupby('bin'):
                cal_rows.append(dict(zip(groups,key),bin=bucket,n=len(v),prediction=v.prediction.mean(),observed=v.y.mean()))
    pd.DataFrame(summaries).to_csv(out/'summary.csv',index=False)
    annual=[]
    for key,g in d.groupby(groups+['year']):
        if key[4]!='return':annual.append(dict(zip(groups+['year'],key),**binary_metrics(g)))
    pd.DataFrame(annual).to_csv(out/'annual_binary.csv',index=False)
    dates.assign(year=dates.date.dt.year).groupby(groups+['year']).utility.agg(['count','mean']).to_csv(out/'annual_utility.csv')
    pd.DataFrame(cal_rows).to_csv(out/'calibration.csv',index=False)
    increments=[]
    for key,g in dates[dates.cohort.ne('F')].groupby(['era','level','cohort','task','horizon']):
        p=g.pivot(index='date',columns='method',values='utility').dropna()
        x=p[key[2]]-p.F;lo,hi=bootstrap(x);adjlo,adjhi=bootstrap(x,.05/3)
        increments.append(dict(zip(['era','level','cohort','task','horizon'],key),months=len(x),utility='delta_IC' if key[3]=='return' else 'Brier_reduction',
            increment=x.mean(),ci95_low=lo,ci95_high=hi,adjusted_low=adjlo,adjusted_high=adjhi,
            result='historical_increment_supported' if key[4]==20 and len(x)>=24 and adjlo>0 else 'not_established' if key[4]==20 else 'secondary_descriptive'))
    pd.DataFrame(increments).to_csv(out/'paired_increments.csv',index=False)
    js(out/'evaluation_receipt.json',dict(code_sha256=sha(__file__),prediction_sha256=sha(out/'predictions.parquet'),
        score_meaning='monthly research prediction; no causal or investability claim',date_rows=len(dates),summary_rows=len(summaries)))
    print(pd.DataFrame(increments).query('horizon==20')[['era','level','cohort','task','months','increment','result']].to_string(index=False))

if __name__=='__main__':run()
