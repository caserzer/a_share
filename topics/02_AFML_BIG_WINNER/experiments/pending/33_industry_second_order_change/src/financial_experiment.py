"""R04 partial financial proxy; conservative update and dependency availability."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from price_experiment import EP, SOURCE, digest
from conditional_experiment import interval

CACHE=Path('/home/xiaolv/.cache/a_share/ep30_d2/proxy/financials')


def stock_events(path, calendar):
    cols=['REPORT_DATE','NOTICE_DATE','UPDATE_DATE','TOTALOPERATEREVE']
    f=pd.read_parquet(path,columns=cols)
    for c in cols[:3]: f[c]=pd.to_datetime(f[c],errors='coerce')
    f['revenue']=pd.to_numeric(f.TOTALOPERATEREVE,errors='coerce')
    f['period']=f.REPORT_DATE.dt.to_period('Q')
    # Ambiguous same-period records excluded, not resolved by future outcomes.
    f=f[f.period.notna() & ~f.period.duplicated(keep=False)].set_index('period').sort_index()
    if f.empty:return pd.DataFrame(),{'rows':0}
    f=f.reindex(pd.period_range(f.index.min(),f.index.max(),freq='Q'))
    availability=f[['NOTICE_DATE','UPDATE_DATE']].max(axis=1).where(f.NOTICE_DATE.notna()&f.UPDATE_DATE.notna())
    q=f.revenue-f.revenue.shift(1)
    q.loc[f.index.quarter==1]=f.loc[f.index.quarter==1,'revenue']
    qa=pd.concat([availability,availability.shift(1)],axis=1).max(axis=1)
    qa.loc[f.index.quarter==1]=availability.loc[f.index.quarter==1]
    qa=qa.where(q.notna())
    growth=(q/q.shift(4)-1).where(q.ge(0)&q.shift(4).gt(0))
    ga=pd.concat([qa,qa.shift(4)],axis=1).max(axis=1).where(growth.notna())
    acceleration=growth-growth.shift(1)
    aa=pd.concat([ga,ga.shift(1)],axis=1).max(axis=1).where(acceleration.notna())
    # Require every dependency availability; max(skipna) cannot hide a missing date.
    qa=qa.where(availability.notna()&((f.index.quarter==1)|availability.shift(1).notna()))
    ga=ga.where(qa.notna()&qa.shift(4).notna())
    aa=aa.where(ga.notna()&ga.shift(1).notna())
    out=pd.DataFrame({'period_end':f.index.to_timestamp(how='end').normalize(),
                      'growth':growth.to_numpy(),'finance_acceleration':acceleration.to_numpy(),
                      'available_date':aa.to_numpy()}).dropna()
    ix=calendar.searchsorted(out.available_date,side='right')
    out=out.loc[ix<len(calendar)].copy();ix=ix[ix<len(calendar)]
    out['known_date']=calendar[ix]
    # Only replace a state with an equal or newer report period.
    out=out.sort_values(['known_date','period_end'])
    out=out[out.period_end.ge(out.period_end.cummax())].drop_duplicates('known_date',keep='last')
    return out, {'rows':len(f),'valid_events':len(out),'updated_after_notice':int((f.UPDATE_DATE>f.NOTICE_DATE).sum())}


def main():
    out=EP/'outputs/r04';out.mkdir(parents=True,exist_ok=True)
    panel=pd.read_parquet('/tmp/ep33_r01_panel.parquet')
    calendar=pd.DatetimeIndex(pd.read_parquet(SOURCE/'CSI_ALL.parquet').index)
    weeks=pd.DatetimeIndex(sorted(panel.date.unique()))
    stock_rows=[];audits=[];sources={}
    for path in sorted(CACHE.glob('*.parquet')):
        try:events,audit=stock_events(path,calendar)
        except (KeyError, ValueError) as exc:
            audits.append({'file':path.name,'error':str(exc)});continue
        sources[str(path)]=digest(path)
        audits.append({'file':path.name,**audit})
        if events.empty:continue
        code,exchange=path.stem.split('.')
        f=pd.merge_asof(pd.DataFrame({'date':weeks}),events.sort_values('known_date'),left_on='date',right_on='known_date',direction='backward')
        f=f[f.known_date.notna() & ((f.date-f.period_end).dt.days<=550)].copy()
        assert f.known_date.le(f.date).all()
        f['instrument']=exchange+code
        stock_rows.append(f)
    stocks=pd.concat(stock_rows,ignore_index=True) if stock_rows else pd.DataFrame()
    path=Path('/home/xiaolv/.cache/a_share/ep32/extension_v2/products/assignments.parquet')
    cols=['month','era','level','industry_code','instrument','security_id','unresolved']
    assignments=pd.read_parquet(path,columns=cols);assignments=assignments[assignments.level.eq('L3')]
    sources[str(path)]=digest(path)
    aggregates=[]
    for date,g in panel.groupby('date'):
        a=assignments[assignments.month.eq(date.to_period('M')-1)]
        a=a.merge(stocks[stocks.date.eq(date)],on='instrument',how='left',validate='many_to_one')
        for (era,code),s in a.groupby(['era','industry_code']):
            known=s.finance_acceleration.notna();n=int(known.sum());total=len(s)+int(s.unresolved.max())
            aggregates.append(dict(date=date,era=era,industry_code=code,finance_count=n,finance_denominator=total,
                finance_coverage=n/total if total else 0,
                finance_acceleration=s.loc[known,'finance_acceleration'].median(),growth=s.loc[known,'growth'].median(),
                finance_positive_share=s.loc[known,'finance_acceleration'].gt(0).mean()))
    agg=pd.DataFrame(aggregates);agg.to_csv(out/'industry_coverage.csv.gz',index=False)
    joined=panel.merge(agg,on=['date','era','industry_code'],how='left',validate='one_to_one')
    selected=[];coverage=[]
    for date,g in joined.groupby('date'):
        price=g[g.acceleration.notna()&g.coverage.ge(.8)&g.members.ge(5)]
        pool=price[price.finance_count.ge(3)&price.finance_coverage.ge(.3)].dropna(subset=['finance_acceleration','growth'])
        coverage.append(dict(date=date,price_eligible=len(price),finance_eligible=len(pool)))
        for score in ['finance_acceleration','growth','velocity']:
            s=pool.sort_values([score,'industry_code'],ascending=[False,True]).head(10).copy()
            s['strategy']=score;selected.append(s)
    selected=pd.concat(selected,ignore_index=True)
    selected.to_csv(out/'selected.csv.gz',index=False)
    pd.DataFrame(coverage).to_csv(out/'coverage.csv',index=False)
    pd.DataFrame(audits).to_csv(out/'partition_audit.csv',index=False)
    pairs=[];datepairs=[]
    for control in ['growth','velocity']:
        for date,g in selected.groupby('date'):
            a=g[g.strategy.eq('finance_acceleration')];b=g[g.strategy.eq(control)]
            datepairs.append(dict(control=control,date=date,n=len(a),known_a=int(a.excess126.notna().sum()),known_b=int(b.excess126.notna().sum()),
                complete=bool(len(a)>0 and a.excess126.notna().all() and b.excess126.notna().all()),delta=a.excess126.mean()-b.excess126.mean()))
    dp=pd.DataFrame(datepairs);dp.to_csv(out/'date_pairs.csv',index=False)
    for control,g in dp.groupby('control'):
        c=g[g.complete].set_index('date');m=c.delta.groupby(c.index.to_period('M')).mean()
        ci=interval(m,12) if len(m)>=12 else [None,None]
        pairs.append(dict(control=control,complete_dates=len(c),months=len(m),delta=m.mean(),ci_low=ci[0],ci_high=ci[1]))
    pd.DataFrame(pairs).to_csv(out/'paired.csv',index=False)
    sources.update({str(p):digest(p) for p in [EP/'rounds/r04_plan.md',Path(__file__),Path('/tmp/ep33_r01_panel.parquet')]})
    receipt={'stage':'partial_financial_historical_proxy','partitions':len(audits),'stock_week_rows':len(stocks),
             'instruments_with_events':int(stocks.instrument.nunique()),'sources':sources,
             'limits':'supplier current vintages; selected 1647-stock coverage; not certified economic mechanism'}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(pd.DataFrame(pairs).to_string(index=False));print(pd.DataFrame(coverage).describe().to_string())

if __name__=='__main__':main()
