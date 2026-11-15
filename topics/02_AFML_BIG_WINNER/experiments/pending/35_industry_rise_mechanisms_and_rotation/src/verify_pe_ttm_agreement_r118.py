"""Independent amounts, cohort pairing and full descriptive-statistic audit."""
import pandas as pd
from common import *
METRICS=['symmetric_distance','sign_agreement','within_1pct','within_5pct','absolute_cny_distance','abs_log_magnitude_ratio']
def close(a,b):np.testing.assert_allclose(a,b,rtol=1e-11,atol=1e-10,equal_nan=True)
def run():
    out=ROOT/'outputs/r118';rec=json.loads((out/'receipt.json').read_text())
    for p,h in rec['reads'].items():assert sha(p)==h
    for p,h in rec['outputs'].items():assert sha(out/p)==h
    orig=pd.read_parquet(ROOT/'outputs/r117/linked_monthly.parquet');p=pd.read_parquet(out/'agreement_rows.parquet');pd.testing.assert_frame_equal(p[orig.columns],orig);v=p.comparison_eligible
    q=p[v];a=q.cap.to_numpy()/q.vendor_pe_ttm.to_numpy();b=q.ttm_profit.to_numpy();den=abs(a)+abs(b);diff=abs(a-b);close(a,q.implied_total_profit)
    expected={'symmetric_distance':np.divide(2*diff,den,out=np.zeros(len(q)),where=den!=0),'sign_agreement':np.sign(a)==np.sign(b),'within_1pct':diff<=.01*abs(b),'within_5pct':diff<=.05*abs(b),'absolute_cny_distance':diff,'signed_relative':np.divide(a-b,abs(b),out=np.full(len(q),np.nan),where=b!=0)}
    same=np.sign(a)==np.sign(b);same&=(a!=0)&(b!=0);rat=np.full(len(q),np.nan);rat[same]=abs(np.log(abs(a[same]))-np.log(abs(b[same])));expected['abs_log_magnitude_ratio']=rat
    for c,x in expected.items():close(q[c],x)
    assert p.loc[~v,['implied_total_profit']+list(expected)].isna().all().all()
    pair=pd.read_parquet(out/'clock_pairs.parquet');keys=['security_id','date'];assert len(pair)*2==len(p) and not pair.duplicated(keys).any()
    for clock in ['notice','update']:
        source=p[p.clock==clock].set_index(keys).reindex(pd.MultiIndex.from_frame(pair[keys]))
        for c in ['comparison_eligible','report_period','ttm_profit','implied_total_profit']:pd.testing.assert_series_equal(pair[c+'_'+clock].reset_index(drop=True),source[c].reset_index(drop=True),check_names=False)
    common=pair.comparison_eligible_notice&pair.comparison_eligible_update;same=common&pair.report_period_notice.eq(pair.report_period_update)
    assert common.equals(pair.common) and same.equals(pair.same_period) and (common&~same).equals(pair.different_period)
    mapping=pair.set_index(keys)
    for c in ['common','same_period','different_period']:assert np.array_equal(p[c],mapping[c].reindex(pd.MultiIndex.from_frame(p[keys])))
    assert pair.loc[same,'ttm_profit_notice'].eq(pair.loc[same,'ttm_profit_update']).all();assert pair.loc[same,'implied_total_profit_notice'].eq(pair.loc[same,'implied_total_profit_update']).all()
    d=pd.read_csv(out/'date_metrics.csv',parse_dates=['date']);visited=0
    for cohort in ['all_eligible','common','same_period','different_period']:
        subset=p[p.comparison_eligible if cohort=='all_eligible' else p[cohort]]
        for (clock,date),g in subset.groupby(['clock','date']):
            rr=d[(d.cohort==cohort)&(d.clock==clock)&(d.date==date)];assert len(rr)==1;r=rr.iloc[0];visited+=1
            assert r.rows==len(g) and r.negative_implied==g.implied_total_profit.lt(0).sum() and r.negative_financial==g.ttm_profit.lt(0).sum()
            for c in METRICS:
                x=g[c].dropna().to_numpy();value=(np.median(x) if c in ['absolute_cny_distance','abs_log_magnitude_ratio'] else np.mean(x)) if len(x) else np.nan;close(r[c],value)
    assert visited==len(d)
    for name,ks in [('annual_metrics',['cohort','clock','year']),('summary',['cohort','clock'])]:
        table=pd.read_csv(out/f'{name}.csv');assert len(table)==d.groupby(ks).ngroups
        for key,g in d.groupby(ks):
            mask=np.ones(len(table),bool)
            for c,x in zip(ks,key):mask &= table[c].eq(x)
            assert mask.sum()==1;r=table[mask].iloc[0]
            for c in METRICS:close(r[c],g[c].dropna().mean())
            if name=='summary':assert r.months==len(g) and r.rows==g.rows.sum()
    quant=pd.read_csv(out/'row_quantiles.csv');assert len(quant)==42
    for r in quant.itertuples():
        x=q[q.clock==r.clock][r.metric].dropna().to_numpy();assert r.known==len(x);close(r.value,np.quantile(x,r.quantile))
    assert rec['source_rows']==len(p) and rec['common_pairs']==common.sum() and rec['same_period_pairs']==same.sum() and rec['different_period_pairs']==(common&~same).sum()
    js(out/'verification.json',dict(status='PASS',source_rows=len(p),eligible_rows=len(q),common_pairs=int(common.sum()),same_period_pairs=int(same.sum()),different_period_pairs=int((common&~same).sum()),date_metric_rows=len(d),same_period_values_identical=True,strict_PIT=False));print(json.loads((out/'verification.json').read_text()))
if __name__=='__main__':run()
