"""Observed report revision timing, retaining unknowns and the non-event context."""
import pandas as pd
from common import *


def revision_events(values):
    q=values[(values.basis=='profit_cny')&values.broker.notna()]
    events=[];ledger=[]
    for key,g in q.groupby(['stock_code','broker','fiscal_year']):
        bydate=g.groupby('publication_proxy_date').value.agg(['nunique','first']).sort_index()
        previous=None
        for date,row in bydate.iterrows():
            value=row['first'] if row['nunique']==1 else np.nan
            reason=None;rev=np.nan
            if key[2]!=date.year+1:reason='not_next_fiscal_year'
            elif previous is None:reason='no_prior_cached_report'
            elif (date-previous[0]).days>365:reason='prior_older_than365'
            elif not np.isfinite(value) or not np.isfinite(previous[1]):reason='conflicting_current_or_prior'
            elif abs(value)+abs(previous[1])==0:reason='zero_denominator'
            else:rev=(value-previous[1])/(abs(value)+abs(previous[1]))
            rec=dict(stock_code=key[0],broker=key[1],fiscal_year=key[2],publication_date=date,
                previous_date=previous[0] if previous else pd.NaT,revision=rev,status=reason or 'valid')
            ledger.append(rec)
            if reason is None:events.append(rec)
            previous=(date,value)
    return pd.DataFrame(events),pd.DataFrame(ledger)


def window_context(g,market):
    g=g.sort_values('date');p=g.nav;b=g.date.map(market);out=g[KEY+['block','date']].copy()
    for h in [20,60]:
        out[f'pre{h}']=p.shift(1)/p.shift(h+1)-1-(b.shift(1)/b.shift(h+1)-1)
        out[f'post{h}']=p.shift(-h-1)/p.shift(-1)-1-(b.shift(-h-1)/b.shift(-1)-1)
    out['reaction']=p/p.shift(1)-1-(b/b.shift(1)-1)
    out['entry_date']=g.date.shift(-1);out['maturity20']=g.date.shift(-21);out['maturity60']=g.date.shift(-61)
    return out


def run():
    out=ROOT/'outputs/r14';source=ROOT/'data/r11_analyst_forecasts.parquet'
    values=pd.read_parquet(source);events,ledger=revision_events(values);ledger.to_csv(out/'event_ledger.csv',index=False)
    market=pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').close
    calendar=pd.DatetimeIndex(market.index).sort_values()
    positions=calendar.searchsorted(events.publication_date,side='right');events['signal_date']=pd.NaT
    valid=positions<len(calendar);events.loc[valid,'signal_date']=calendar[positions[valid]].to_numpy()
    events['month']=events.signal_date.dt.to_period('M')-1
    members=pd.read_parquet(CACHE/'extension_v2/products/assignments.parquet',columns=['month','era','level','industry_code','security_id','instrument'])
    members['stock_code']=members.instrument.str[2:]
    mapped=events.merge(members,on=['stock_code','month'],how='left',validate='many_to_many',indicator=True)
    mapped.to_parquet(ROOT/'data/r14_mapped_report_events.parquet',index=False)
    company=mapped[mapped._merge=='both'].groupby(KEY+['signal_date','fiscal_year','security_id']).agg(revision=('revision','median'),brokers=('broker','nunique'),latest_publication=('publication_date','max')).reset_index()
    aggregated=company.groupby(KEY+['signal_date','fiscal_year']).agg(revision=('revision','median'),event_companies=('security_id','nunique'),broker_company_pairs=('brokers','sum'),latest_publication=('latest_publication','max')).reset_index()
    denominator=members.groupby(['month']+KEY).security_id.nunique().rename('members').reset_index()
    aggregated['month']=aggregated.signal_date.dt.to_period('M')-1
    aggregated=aggregated.merge(denominator,on=['month']+KEY,validate='many_to_one')
    aggregated['event_member_fraction']=aggregated.event_companies/aggregated.members
    daily=pd.read_parquet(CACHE/'forecast_v5/daily_industries.parquet')
    context=pd.concat([window_context(g,market) for _,g in daily.groupby(KEY+['block'],sort=False)],ignore_index=True)
    signal_dates=set(aggregated.signal_date);context=context[context.date.isin(signal_dates)].copy()
    event_keys=aggregated[KEY+['signal_date']].drop_duplicates().rename(columns={'signal_date':'date'}).assign(is_event=True)
    context=context.merge(event_keys,on=KEY+['date'],how='left',validate='one_to_one');context['is_event']=context.is_event.fillna(False).astype(bool)
    context['quintile']=np.nan
    for _,g in context.groupby(['era','level','date']):
        ready=g.pre20.notna()
        if ready.sum()>=20:context.loc[g.index[ready],'quintile']=np.ceil(g.loc[ready,'pre20'].rank(method='average',pct=True)*5)
    aggregated=aggregated.merge(context.rename(columns={'date':'signal_date'}),on=KEY+['signal_date'],how='left',validate='many_to_one')
    controls=[];metrics=['pre20','pre60','reaction','post20','post60']
    for key,g in context[~context.is_event&context.quintile.notna()].groupby(['era','level','date','quintile']):
        rec=dict(zip(['era','level','signal_date','quintile'],key),control_count=len(g))
        for metric in metrics:rec['control_'+metric]=g[metric].mean() if len(g)>=3 and g[metric].notna().all() else np.nan
        controls.append(rec)
    aggregated=aggregated.merge(pd.DataFrame(controls),on=['era','level','signal_date','quintile'],how='left',validate='many_to_one')
    for metric in metrics:aggregated['matched_'+metric]=aggregated[metric]-aggregated['control_'+metric]
    aggregated['direction']=np.select([aggregated.revision.gt(0),aggregated.revision.lt(0)],['up','down'],default='flat')
    aggregated.to_parquet(ROOT/'data/r14_industry_events.parquet',index=False)
    context.to_parquet(ROOT/'data/r14_non_event_context.parquet',index=False)
    rows=[];date_rows=[]
    for key,g in aggregated.groupby(['era','level','direction']):
        for metric in metrics+['matched_'+m for m in metrics]:
            known=g[metric].notna();daily_mean=g.groupby('signal_date')[metric].mean()
            rows.append(dict(zip(['era','level','direction'],key),metric=metric,event_rows=len(g),known=int(known.sum()),unknown=int((~known).sum()),dates=g.signal_date.nunique(),known_dates=daily_mean.notna().sum(),industry_count=g.industry_code.nunique(),event_mean=g[metric].mean(),date_mean=daily_mean.mean()))
            for date,values_at in g.groupby('signal_date'):
                date_rows.append(dict(zip(['era','level','direction'],key),metric=metric,date=date,event_rows=len(values_at),known=int(values_at[metric].notna().sum()),mean=values_at[metric].mean()))
    pd.DataFrame(rows).to_csv(out/'summary.csv',index=False);dr=pd.DataFrame(date_rows);dr.to_csv(out/'by_date.csv',index=False)
    dr.assign(year=pd.to_datetime(dr.date).dt.year).groupby(['era','level','direction','metric','year']).agg(dates=('mean','count'),mean=('mean','mean')).to_csv(out/'annual.csv')
    js(out/'receipt.json',dict(protocol_sha256=sha(ROOT/'protocols/r14.json'),code_sha256=sha(__file__),
        sources={str(p):sha(p) for p in [source,CACHE/'extension_v2/products/assignments.parquet',CACHE/'forecast_v5/daily_industries.parquet',CACHE/'forecast_v5/CSI_ALL.parquet']},
        raw_report_date_candidates=len(ledger),valid_broker_events=len(events),unmapped_broker_events=int(mapped.loc[mapped._merge=='left_only'].shape[0]),industry_events=len(aggregated),
        unknown_industry_price_context=int(aggregated.block.isna().sum()),quality='Selected archived reports; descriptive event timing, not consensus or causal identification'))
    print('R14',len(events),'broker events;',len(aggregated),'industry events',flush=True)
if __name__=='__main__':run()
