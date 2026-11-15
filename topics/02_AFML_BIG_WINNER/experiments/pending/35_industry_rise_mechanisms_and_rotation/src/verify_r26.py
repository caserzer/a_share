import pandas as pd
from common import *

def run():
    out=ROOT/'outputs/r26';events=pd.read_parquet(ROOT/'data/r26_industry_events.parquet');mapped=pd.read_parquet(ROOT/'data/r26_mapped_report_events.parquet')
    valid=mapped.signal_date.notna()
    assert (mapped.loc[valid,'signal_date']>mapped.loc[valid,'publication_date']).all()
    assert (mapped.previous_date<mapped.publication_date).all()
    assert (mapped.publication_date-mapped.previous_date).dt.days.le(365).all()
    assert (mapped.month==mapped.signal_date.dt.to_period('M')-1).all()
    assert (events.event_companies<=events.members).all()
    context=pd.read_parquet(ROOT/'data/r26_non_event_context.parquet')
    metrics=['pre20','pre60','reaction','post20','post60']
    checks=0
    for key,g in events[events.quintile.notna()].groupby(['era','level','signal_date','quintile']):
        controls=context[(context.era==key[0])&(context.level==key[1])&(context.date==key[2])&(context.quintile==key[3])&~context.is_event]
        assert not set(controls.industry_code)&set(events.loc[(events.era==key[0])&(events.level==key[1])&(events.signal_date==key[2]),'industry_code'])
        for metric in metrics:
            expected=controls[metric].mean() if len(controls)>=3 and controls[metric].notna().all() else np.nan
            assert np.allclose(g['control_'+metric],expected,equal_nan=True)
            assert np.allclose(g['matched_'+metric],g[metric]-expected,equal_nan=True)
        checks+=1
    d=pd.read_parquet(CACHE/'forecast_v5/daily_industries.parquet');market=pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').close
    d['calendar_i']=market.index.get_indexer(d.date)
    assert d.calendar_i.ge(0).all()
    ordered=d.sort_values(KEY+['block','date'])
    assert ordered.groupby(KEY+['block']).calendar_i.diff().dropna().eq(1).all()
    groups={key:g.sort_values('date').reset_index(drop=True) for key,g in d.groupby(KEY+['block'])}
    sample=events[events.block.notna()].sort_values(KEY+['signal_date']).iloc[np.unique(np.linspace(0,events.block.notna().sum()-1,40,dtype=int))]
    price_checks=0
    for row in sample.itertuples():
        g=groups[(row.era,row.level,row.industry_code,row.block)]
        i=int(g.index[g.date==row.signal_date][0]);p=g.nav.to_numpy();b=g.date.map(market).to_numpy()
        for metric,start,end in [('pre20',i-21,i-1),('pre60',i-61,i-1),('reaction',i-1,i),('post20',i+1,i+21),('post60',i+1,i+61)]:
            expected=p[end]/p[start]-1-(b[end]/b[start]-1) if start>=0 and end<len(g) else np.nan
            assert np.allclose(getattr(row,metric),expected,equal_nan=True)
            price_checks+=1
    conservative=pd.read_parquet(ROOT/'data/r26_unknown_control_sensitivity.parquet')
    old_events=pd.read_parquet(ROOT/'data/r14_industry_events.parquet')
    event_keys=KEY+['signal_date','fiscal_year']
    assert set(map(tuple,conservative[event_keys].to_numpy()))==set(map(tuple,events[event_keys].to_numpy()))
    paired=old_events.merge(conservative,on=event_keys,suffixes=('_old','_new'),validate='one_to_one')
    for metric in metrics:
        assert np.allclose(paired['matched_'+metric+'_old'],paired['matched_'+metric+'_new'],equal_nan=True)
    review=json.loads((out/'unknown_control_receipt.json').read_text())
    assert sha(ROOT/'data/r26_unknown_control_sensitivity.parquet')==review['result_sha256']
    ledger=pd.read_csv(out/'event_ledger.csv')
    assert ledger.loc[ledger.status!='valid','revision'].isna().all()
    js(out/'verification.json',dict(status='PASS',industry_events=len(events),control_group_checks=checks,direct_price_window_checks=price_checks,
        checks=['strict next-session signal','continuous exchange calendar within blocks','previous-month membership','no unavailable predecessor promoted','event industry excluded from controls','missing controls suppress comparator','direct raw path pre/reaction/post decomposition']))
    print('R26 VERIFIED',checks,'control groups;',price_checks,'raw price windows')
if __name__=='__main__':run()
