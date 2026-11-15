"""Same-month implied-versus-financial profit agreement; no PIT certification."""
import pandas as pd
from common import *
METRICS=['symmetric_distance','sign_agreement','within_1pct','within_5pct','absolute_cny_distance','abs_log_magnitude_ratio']
def measures(implied,actual):
    a=np.asarray(implied,dtype=float);b=np.asarray(actual,dtype=float);den=abs(a)+abs(b);d=abs(a-b)
    return dict(symmetric_distance=np.divide(2*d,den,out=np.zeros_like(d),where=den!=0),sign_agreement=np.sign(a)==np.sign(b),within_1pct=d<=.01*abs(b),within_5pct=d<=.05*abs(b),absolute_cny_distance=d,signed_relative=np.divide(a-b,abs(b),out=np.full_like(d,np.nan),where=b!=0),abs_log_magnitude_ratio=np.where((a*b>0),abs(np.log(np.divide(abs(a),abs(b),out=np.full_like(d,np.nan),where=b!=0))),np.nan))
def run():
    out=ROOT/'outputs/r118';out.mkdir(exist_ok=True);src=ROOT/'outputs/r117/linked_monthly.parquet';p=pd.read_parquet(src);valid=p.comparison_eligible
    p['implied_total_profit']=np.nan;p.loc[valid,'implied_total_profit']=p.loc[valid,'cap']/p.loc[valid,'vendor_pe_ttm']
    assert np.isfinite(p.loc[valid,'implied_total_profit']).all()
    metrics=measures(p.loc[valid,'implied_total_profit'],p.loc[valid,'ttm_profit'])
    for k,v in metrics.items():p[k]=np.nan;p.loc[valid,k]=np.asarray(v,dtype=float)
    keys=['security_id','date'];pair=p[p.clock=='notice'][keys+['comparison_eligible','report_period','ttm_profit','implied_total_profit']].merge(p[p.clock=='update'][keys+['comparison_eligible','report_period','ttm_profit','implied_total_profit']],on=keys,suffixes=('_notice','_update'),validate='one_to_one');pair['common']=pair.comparison_eligible_notice&pair.comparison_eligible_update;pair['same_period']=pair.common&pair.report_period_notice.eq(pair.report_period_update);pair['different_period']=pair.common&~pair.same_period
    p=p.merge(pair[keys+['common','same_period','different_period']],on=keys,how='left',validate='many_to_one');p.to_parquet(out/'agreement_rows.parquet',index=False);pair.to_parquet(out/'clock_pairs.parquet',index=False)
    rows=[]
    for cohort in ['all_eligible','common','same_period','different_period']:
        q=p[p.comparison_eligible if cohort=='all_eligible' else p[cohort]]
        for (clock,date),g in q.groupby(['clock','date']):
            r=dict(cohort=cohort,clock=clock,date=date,rows=len(g),negative_implied=int(g.implied_total_profit.lt(0).sum()),negative_financial=int(g.ttm_profit.lt(0).sum()))
            for c in METRICS:r[c]=g[c].median() if c in ['absolute_cny_distance','abs_log_magnitude_ratio'] else g[c].mean()
            rows.append(r)
    d=pd.DataFrame(rows);d['year']=d.date.dt.year;d.to_csv(out/'date_metrics.csv',index=False)
    annual=d.groupby(['cohort','clock','year'])[METRICS].mean().reset_index();annual.to_csv(out/'annual_metrics.csv',index=False)
    summary=d.groupby(['cohort','clock']).agg(months=('date','size'),rows=('rows','sum'),**{c:(c,'mean') for c in METRICS}).reset_index();summary.to_csv(out/'summary.csv',index=False)
    quantiles=[]
    for clock,g in p[valid].groupby('clock'):
        for c in ['symmetric_distance','absolute_cny_distance','abs_log_magnitude_ratio']:
            for q,val in g[c].quantile([0,.25,.5,.75,.9,.99,1]).items():quantiles.append(dict(clock=clock,metric=c,quantile=q,value=val,known=int(g[c].notna().sum())))
    pd.DataFrame(quantiles).to_csv(out/'row_quantiles.csv',index=False)
    same=pair[pair.same_period];assert same.ttm_profit_notice.eq(same.ttm_profit_update).all() and same.implied_total_profit_notice.eq(same.implied_total_profit_update).all()
    js(out/'receipt.json',dict(reads={str(x):sha(x) for x in [src,Path(__file__),ROOT/'protocols/r118.json',ROOT/'src/common.py']},outputs={n:sha(out/n) for n in ['agreement_rows.parquet','clock_pairs.parquet','date_metrics.csv','annual_metrics.csv','summary.csv','row_quantiles.csv']},source_rows=len(p),common_pairs=int(pair.common.sum()),same_period_pairs=int(pair.same_period.sum()),different_period_pairs=int(pair.different_period.sum()),strict_PIT=False,adopted=False));print(summary.to_string(index=False));print('same-period',len(same))
if __name__=='__main__':run()
