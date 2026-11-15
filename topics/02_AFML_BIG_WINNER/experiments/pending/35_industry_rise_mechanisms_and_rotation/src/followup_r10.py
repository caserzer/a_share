"""Fixed alert follow-up and exit economics, preserving unknown outcomes."""
import pandas as pd
from common import *


def path_metrics(g,market):
    g=g.sort_values('date');p=g.nav.to_numpy(float);b=g.date.map(market).to_numpy(float);n=len(g)
    out=g[KEY+['block','date','day_i']].copy()
    out['entry_date']=g.date.shift(-1)
    for h in [5,20,60]:
        count=n-h-1
        for name in [f'return{h}',f'excess{h}',f'market{h}',f'drawdown{h}',f'min_from_entry{h}']:out[name]=np.nan
        out[f'maturity{h}']=g.date.shift(-h-1).to_numpy()
        if count>0:
            ret=p[h+1:]/p[1:-h]-1;bm=b[h+1:]/b[1:-h]-1
            windows=np.lib.stride_tricks.sliding_window_view(p,h+1)[1:]
            dd=(windows/np.maximum.accumulate(windows,axis=1)-1).min(axis=1)
            adverse=(windows/windows[:,[0]]-1).min(axis=1)
            for name,values in [(f'return{h}',ret),(f'excess{h}',ret-bm),(f'market{h}',bm),(f'drawdown{h}',dd),(f'min_from_entry{h}',adverse)]:
                out.iloc[:count,out.columns.get_loc(name)]=values
    out['continuation20_60']=(1+out.return60)/(1+out.return20)-1
    out['continuation_market20_60']=(1+out.market60)/(1+out.market20)-1
    out['continuation_excess20_60']=out.continuation20_60-out.continuation_market20_60
    out['success20']=((out.return20>=.05)&(out.excess20>=.03)).astype(float).where(out.return20.notna())
    out['breadth_change20']=g.breadth21.shift(-21).to_numpy()-g.breadth21.to_numpy()
    return out


def exit_economics(ret,market,c):
    return (1-c)-(1+ret)*(1-c),(1-c)**3*(1+market)-(1+ret)*(1-c)


def run():
    out=ROOT/'outputs/r10';source=CACHE/'forecast_v5/daily_industries.parquet';d=pd.read_parquet(source)
    market=pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').close
    parts=[path_metrics(g,market) for _,g in d.groupby(KEY+['block'],sort=False)]
    paths=pd.concat(parts,ignore_index=True);assert not paths.duplicated(KEY+['date']).any()
    alert_path=ROOT/'outputs/r09/alerts.parquet';a=pd.read_parquet(alert_path)
    alerts=a[KEY+['date','strategy','score','y','return20','excess20']].merge(paths,on=KEY+['date'],how='left',suffixes=('_r09',''),validate='many_to_one')
    assert len(alerts)==len(a)
    for name in ['return20','excess20']:assert np.allclose(alerts[name],alerts[name+'_r09'],equal_nan=True)
    assert np.allclose(alerts.y,alerts.success20,equal_nan=True)
    alerts.to_parquet(ROOT/'data/r10_alert_followup.parquet',index=False)
    summary=[];annual=[]
    for key,g in alerts.groupby(['era','level','strategy']):
        for h in [5,20,60]:
            valid=g[g[f'return{h}'].notna()]
            row=dict(zip(['era','level','strategy'],key),horizon=h,alerts=len(g),complete=len(valid),unknown=len(g)-len(valid),
                absolute_mean=valid[f'return{h}'].mean(),excess_mean=valid[f'excess{h}'].mean(),
                positive_absolute_fraction=valid[f'return{h}'].gt(0).mean(),mean_drawdown=valid[f'drawdown{h}'].mean(),
                drawdown_p10=valid[f'drawdown{h}'].quantile(.1),mean_min_return=valid[f'min_from_entry{h}'].mean())
            summary.append(row)
            for year,v in valid.groupby(valid.date.dt.year):annual.append(dict(row,year=year,alerts=len(v),absolute_mean=v[f'return{h}'].mean(),excess_mean=v[f'excess{h}'].mean()))
    pd.DataFrame(summary).to_csv(out/'followup_summary.csv',index=False)
    # Annual rows recomputed independently, not inherited pooled counts.
    annual=[]
    for key,g in alerts.assign(year=alerts.date.dt.year).groupby(['era','level','strategy','year']):
        for h in [5,20,60]:
            v=g[g[f'return{h}'].notna()]
            annual.append(dict(zip(['era','level','strategy','year'],key),horizon=h,alerts=len(g),complete=len(v),unknown=len(g)-len(v),
                absolute_mean=v[f'return{h}'].mean(),excess_mean=v[f'excess{h}'].mean(),mean_drawdown=v[f'drawdown{h}'].mean()))
    pd.DataFrame(annual).to_csv(out/'followup_annual.csv',index=False)
    continuation=[]
    for key,g in alerts.groupby(['era','level','strategy']):
        for label,v in [('all',g),('success20',g[g.success20.eq(1)]),('not_success20',g[g.success20.eq(0)])]:
            full=v[v.continuation_excess20_60.notna()]
            continuation.append(dict(zip(['era','level','strategy'],key),cohort=label,selected=len(v),complete=len(full),unknown=len(v)-len(full),
                absolute_increment=full.continuation20_60.mean(),relative_increment=full.continuation_excess20_60.mean(),
                positive_relative_fraction=full.continuation_excess20_60.gt(0).mean(),breadth_change20=full.breadth_change20.mean()))
    pd.DataFrame(continuation).to_csv(out/'continuation.csv',index=False)
    p_path=ROOT/'outputs/r02/predictions.parquet';p=pd.read_parquet(p_path);p=p[(p.cohort=='F')&(p.method=='F')&(p.task=='reversal')].copy()
    p=p.merge(paths,on=KEY+['date'],how='left',suffixes=('','_path'),validate='many_to_one');p['alert']=False
    for _,g in p.groupby(['era','level','date','horizon']):
        idx=g.sort_values(['prediction','industry_code'],ascending=[False,True]).head(int(np.ceil(.2*len(g)))).index;p.loc[idx,'alert']=True
    records=[];bydate=[]
    for key,g in p.groupby(['era','level','horizon']):
        h=key[2]
        assert np.allclose(g.excess,g[f'excess{h}'],equal_nan=True)
        for cohort,v in [('all_trending',g),('risk_alert',g[g.alert]),('not_alert',g[~g.alert])]:
            complete=v[v[f'return{h}'].notna()&v[f'market{h}'].notna()]
            for cost in [0,.002,.005]:
                for date,z in complete.groupby('date'):
                    ret=z[f'return{h}'];bm=z[f'market{h}'];cash,switch=exit_economics(ret,bm,cost)
                    bydate.append(dict(zip(['era','level','horizon'],key),cohort=cohort,date=date,cost=cost,n=len(z),
                        cash_improvement=cash.mean(),market_improvement=switch.mean(),
                        wrong_exit_absolute=ret.gt(0).mean(),wrong_exit_relative=z.excess.gt(0).mean(),
                        missed_positive_absolute=ret.clip(lower=0).mean(),avoided_negative_absolute=(-ret.clip(upper=0)).mean(),
                        risk_precision=z.y.mean()))
                cash,switch=exit_economics(complete[f'return{h}'],complete[f'market{h}'],cost)
                records.append(dict(zip(['era','level','horizon'],key),cohort=cohort,cost=cost,origins=len(v),complete=len(complete),unknown=len(v)-len(complete),
                    cash_improvement_row_mean=cash.mean(),market_improvement_row_mean=switch.mean(),
                    wrong_exit_absolute=complete[f'return{h}'].gt(0).mean(),wrong_exit_relative=complete.excess.gt(0).mean(),
                    risk_precision=complete.y.mean()))
    p.to_parquet(ROOT/'data/r10_risk_followup.parquet',index=False)
    pd.DataFrame(records).to_csv(out/'exit_summary_rows.csv',index=False);daily=pd.DataFrame(bydate);daily.to_csv(out/'exit_date_metrics.csv',index=False)
    cols=['cash_improvement','market_improvement','wrong_exit_absolute','wrong_exit_relative','missed_positive_absolute','avoided_negative_absolute','risk_precision']
    dates=daily.groupby(['era','level','horizon','cohort','cost'])[cols].mean();dates['months']=daily.groupby(['era','level','horizon','cohort','cost']).date.nunique()
    dates.to_csv(out/'exit_summary_dates.csv')
    js(out/'receipt.json',dict(protocol_sha256=sha(ROOT/'protocols/r10.json'),code_sha256=sha(__file__),
        sources={str(p):sha(p) for p in [source,alert_path,p_path]},alert_rows=len(alerts),risk_rows=len(p),
        exact_r09_outcome_match=True,exact_r02_risk_excess_match=True,
        quality='historical synthetic baskets; not an executable exit strategy'))
    print(dates.query("cohort=='risk_alert' and horizon==20 and cost==0.002").to_string(),flush=True)

if __name__=='__main__':run()
