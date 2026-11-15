"""Preregistered fixed-FY revision versus price controls, including failed folds."""
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from common import *
from train_r02 import F,sample_weights


def eligible_training(g,year,h):
    return g.date.lt(pd.Timestamp(year,1,1)) & g[f'maturity{h}'].lt(pd.Timestamp(year,1,1)) & g[f'excess{h}'].notna()

def run():
    out=ROOT/'outputs/r25'
    panel=pd.read_parquet(ROOT/'data/monthly_panel.parquet');panel['log_members']=np.log(panel.members)
    cov=pd.read_parquet(ROOT/'data/r25_revision_coverage.parquet')
    merged=cov.merge(panel,on=KEY+['date'],suffixes=('_coverage',''),validate='many_to_one')
    assert (merged.members_coverage>0).all()
    base=merged[merged.price_ready].dropna(subset=F+['covered_member_median']).copy()
    preds=[];folds=[];parameters=[];associations=[];cohorts=[]
    methods={'price_only':F,'expectation_only':['expectation'],'price_plus_expectation':F+['expectation']}
    for (era,level,offset),v in base.groupby(['era','level','fy_offset']):
        for population,mask in [('strict',v.eligible),('partial_diagnostic',v.known.ge(5)&~v.eligible)]:
            g=v[mask].copy();g['expectation']=g.covered_member_median
            datesize=g.groupby('date').date.transform('size');g=g[datesize>=2]
            if g.empty:
                cohorts.append(dict(era=era,level=level,fy_offset=offset,population=population,rows=0,months=0));continue
            cohorts.append(dict(era=era,level=level,fy_offset=offset,population=population,rows=len(g),months=g.date.nunique()))
            ranks=g.groupby('date')[F+['expectation']].transform(centered_rank)
            for date,z in g.groupby('date'):
                for name in ['past_excess20','past_excess60','excess20','excess60']:
                    q=z[['expectation',name]].dropna()
                    rho=q.expectation.corr(q[name],method='spearman') if len(q)>=5 and q.expectation.nunique()>1 and q[name].nunique()>1 else np.nan
                    associations.append(dict(era=era,level=level,fy_offset=offset,population=population,date=date,target=name,n=len(q),rho=rho))
            for h in [20,60]:
                for year in range(2021,2027):
                    fit=eligible_training(g,year,h);test=g.date.dt.year.eq(year)
                    if not test.any():continue
                    tr=g[fit];te=g[test];reason='' if len(tr)>=300 and tr.date.nunique()>=18 else 'insufficient_train_rows_or_months'
                    rec=dict(era=era,level=level,fy_offset=offset,population=population,horizon=h,year=year,train_rows=len(tr),train_months=tr.date.nunique(),test_rows=len(te),max_maturity=tr[f'maturity{h}'].max())
                    folds.append(dict(rec,status='skip' if reason else 'fit',reason=reason))
                    if reason:continue
                    for method,cols in methods.items():
                        scaler=StandardScaler().fit(ranks.loc[tr.index,cols]);model=Ridge(alpha=10).fit(scaler.transform(ranks.loc[tr.index,cols]),tr[f'excess{h}'],sample_weight=sample_weights(tr))
                        p=te[KEY+['date',f'maturity{h}',f'excess{h}']].rename(columns={f'maturity{h}':'maturity',f'excess{h}':'target'}).copy()
                        p['prediction']=model.predict(scaler.transform(ranks.loc[te.index,cols]));p['method']=method;p['row_id']=te.index
                        for k in ['population','fy_offset','horizon','year']:p[k]=rec[k]
                        preds.append(p)
                        parameters.append(dict(rec,method=method,columns=cols,scaler_mean=scaler.mean_.tolist(),scaler_scale=scaler.scale_.tolist(),coef=model.coef_.tolist(),intercept=float(model.intercept_)))
    pd.DataFrame(cohorts).to_csv(out/'cohorts.csv',index=False)
    pd.DataFrame(folds).to_csv(out/'fold_ledger.csv',index=False);js(out/'model_parameters.json',parameters)
    assoc=pd.DataFrame(associations);assoc.to_csv(out/'lead_lag_by_date.csv',index=False)
    if len(assoc):assoc.groupby(['era','level','fy_offset','population','target']).agg(months=('rho','count'),mean_rho=('rho','mean')).to_csv(out/'lead_lag_summary.csv')
    prediction=pd.concat(preds,ignore_index=True) if preds else pd.DataFrame(columns=KEY+['date','maturity','target','prediction','method','row_id','population','fy_offset','horizon','year'])
    prediction.to_parquet(out/'predictions.parquet',index=False)
    metrics=[]
    for key,z in prediction.groupby(['era','level','fy_offset','population','horizon','method','date']):
        q=z.dropna(subset=['target'])
        metrics.append(dict(zip(['era','level','fy_offset','population','horizon','method','date'],key),origins=len(z),complete=len(q),unknown=len(z)-len(q),
            mse=((q.prediction-q.target)**2).mean(),rank_ic=q.prediction.corr(q.target,method='spearman') if len(q)>=5 and q.prediction.nunique()>1 and q.target.nunique()>1 else np.nan))
    metrics=pd.DataFrame(metrics);metrics.to_csv(out/'metrics_by_date.csv',index=False)
    if len(metrics):
        cols=['era','level','fy_offset','population','horizon','method']
        metrics.groupby(cols).agg(months=('mse','count'),ic_months=('rank_ic','count'),mse=('mse','mean'),rank_ic=('rank_ic','mean')).to_csv(out/'summary.csv')
        metrics.assign(year=pd.to_datetime(metrics.date).dt.year).groupby(cols+['year']).agg(months=('mse','count'),mse=('mse','mean'),rank_ic=('rank_ic','mean')).to_csv(out/'annual.csv')
    js(out/'receipt.json',dict(protocol_sha256=sha(ROOT/'protocols/r25.json'),code_sha256=sha(__file__),
      panel_sha256=sha(ROOT/'data/monthly_panel.parquet'),coverage_sha256=sha(ROOT/'data/r25_revision_coverage.parquet'),prediction_sha256=sha(out/'predictions.parquet'),
      rows=len(prediction),fitted_folds=sum(x['status']=='fit' for x in folds),skipped_folds=sum(x['status']=='skip' for x in folds),
      accepted_increment=False,reason='strict cohort insufficient; partial coverage diagnostic is ineligible for full-industry acceptance'))
    print('R25 predictions',len(prediction),'fits',sum(x['status']=='fit' for x in folds),flush=True)
if __name__=='__main__':run()
