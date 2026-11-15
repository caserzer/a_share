"""Pair frozen model top outcomes without hindsight selection or new optimization."""
from common import *
import pandas as pd
G=['era','level','cohort','horizon','year','date']

def run():
    out=ROOT/'outputs/r188';out.mkdir(exist_ok=True)
    p=pd.read_parquet(ROOT/'outputs/r131/predictions.parquet')
    p=p[p.task.eq('return')&p.cohort.ne('F')]
    rows=[];selected=[]
    for key,g in p.groupby(G):
        ident=dict(zip(G,key));c=ident['cohort'];metrics={};sets={}
        for method in ['F',c]:
            v=g[g.method.eq(method)].sort_values('industry_code')
            sets[method]=v
            k=max(1,int(np.ceil(len(v)*.2)))
            top=v.sort_values(['prediction','industry_code'],ascending=[False,True]).head(k)
            valid=top.y.notna()&top.excess.notna();complete=bool(valid.all())
            known=v[v.y.notna()]
            ic=known.prediction.corr(known.y,method='spearman') if len(known)>=20 and known.prediction.nunique()>1 else np.nan
            metrics[method]=dict(complete=complete,top_n=k,unknown=int((~valid).sum()),excess=float(top.excess.mean()) if complete else np.nan,ic=ic)
            for _,s in top.iterrows():selected.append(dict(ident,method=method,industry_code=s.industry_code,prediction=s.prediction,y=s.y,excess=s.excess))
        a=sets['F'];b=sets[c]
        assert a[['industry_code','y','excess']].reset_index(drop=True).equals(b[['industry_code','y','excess']].reset_index(drop=True))
        x=metrics['F'];y=metrics[c];valid=x['complete'] and y['complete']
        rows.append(dict(ident,n=len(a),top_n=x['top_n'],f_complete=x['complete'],extension_complete=y['complete'],f_unknown=x['unknown'],extension_unknown=y['unknown'],paired_complete=valid,f_excess=x['excess'],extension_excess=y['excess'],delta=y['excess']-x['excess'] if valid else np.nan,f_net20=x['excess']-.004,extension_net20=y['excess']-.004,f_ic=x['ic'],extension_ic=y['ic'],delta_ic=y['ic']-x['ic']))
    d=pd.DataFrame(rows);d.to_csv(out/'paired_dates.csv',index=False);pd.DataFrame(selected).to_csv(out/'selected.csv',index=False)
    summaries=[]
    for group in [G[:4],G[:5]]:
        for key,g in d.groupby(group):
            z=g[g.paired_complete];i=g[g.delta_ic.notna()];rec=dict(zip(group,key))
            if 'year' not in rec:rec['year']='all'
            summaries.append(dict(rec,scheduled=len(g),paired_complete=len(z),unknown_pair=len(g)-len(z),f_only_complete=int((g.f_complete&~g.extension_complete).sum()),extension_only_complete=int((~g.f_complete&g.extension_complete).sum()),both_incomplete=int((~g.f_complete&~g.extension_complete).sum()),f_excess=z.f_excess.mean(),extension_excess=z.extension_excess.mean(),delta=z.delta.mean(),f_net20=z.f_net20.mean(),extension_net20=z.extension_net20.mean(),ic_dates=len(i),delta_ic=i.delta_ic.mean(),joint_dates=int((g.paired_complete&g.delta_ic.notna()).sum()),joint_delta_ic=g.loc[g.paired_complete,'delta_ic'].mean()))
    pd.DataFrame(summaries).to_csv(out/'summary.csv',index=False)
    old=pd.read_csv(ROOT/'outputs/r131/evaluation/outputs/r02/date_metrics.csv');old=old[old.task.eq('return')];old.date=pd.to_datetime(old.date);old['year']=old.date.dt.year
    compared=0
    for method,label in [('F','f'),('extension','extension')]:
        current=d.copy();current['method']='F' if method=='F' else current.cohort
        z=current.merge(old,on=G+['method'],validate='one_to_one',suffixes=('','_old'))
        assert len(z)==len(d)
        assert np.allclose(z[label+'_excess'],z.top_excess,atol=1e-12,rtol=1e-12,equal_nan=True)
        assert np.allclose(z[label+'_ic'],z.utility,atol=1e-12,rtol=1e-12,equal_nan=True)
        compared+=len(z)
    v=d[d.paired_complete];assert np.allclose(v.delta,v.extension_net20-v.f_net20,atol=1e-12)
    files=['paired_dates.csv','selected.csv','summary.csv']
    inputs=['outputs/r131/predictions.parquet','outputs/r131/evaluation/outputs/r02/date_metrics.csv','src/paired_top_r188.py','src/common.py','protocols/r188.json']
    js(out/'verification.json',dict(status='PASS',scope='Exact paired universe/labels, original top selection outcome and IC reconciliation, fixed-cost cancellation',paired_dates=len(d),complete=int(d.paired_complete.sum()),unknown=int((~d.paired_complete).sum()),original_model_dates_matched=compared,inputs={x:sha(ROOT/x) for x in inputs},outputs={x:sha(out/x) for x in files}))
    print(pd.DataFrame(summaries).query("year=='all'").to_string(index=False))
if __name__=='__main__':run()
