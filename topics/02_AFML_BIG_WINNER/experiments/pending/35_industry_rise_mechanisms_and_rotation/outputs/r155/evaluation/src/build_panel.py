"""Causal features and explicitly delayed labels on continuous basket segments."""
import pandas as pd
from common import *


def price_features(g):
    g=g.sort_values('date').copy(); p=g.nav
    g['mom20']=p/p.shift(20)-1;g['mom60']=p/p.shift(60)-1
    g['vol20']=p.pct_change(fill_method=None).rolling(20,min_periods=20).std()*np.sqrt(252)
    g['dd60']=p/p.rolling(60,min_periods=60).max()-1
    return g


def delayed_labels(g, market, horizons=(20,60)):
    g=g.copy(); p=g.nav; b=g.date.map(market)
    g['entry_date']=g.date.shift(-1)
    for h in horizons:
        g[f'maturity{h}']=g.date.shift(-h-1)
        g[f'return{h}']=p.shift(-h-1)/p.shift(-1)-1
        g[f'market_return{h}']=b.shift(-h-1)/b.shift(-1)-1
        g[f'excess{h}']=g[f'return{h}']-g[f'market_return{h}']
        # relative wealth trough vs entry, not hindsight peak-to-trough.
        rel=p/b
        future_min=rel.shift(-2)[::-1].rolling(h,min_periods=h).min()[::-1]
        g[f'rel_trough{h}']=future_min/rel.shift(-1)-1
    g['past_excess20']=g.mom20-(b/b.shift(20)-1)
    g['past_excess60']=g.mom60-(b/b.shift(60)-1)
    return g


def run():
    protocol=json.loads((ROOT/'protocols/r01.json').read_text())
    inventory=json.loads((ROOT/'outputs/r01/source_inventory.json').read_text())
    for item in inventory: assert sha(item['path'])==item['sha256'],item['path']
    d=pd.read_parquet(CACHE/'forecast_v5/daily_industries.parquet')
    b=pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').close
    e=pd.read_parquet(CACHE/'joint_pe_v35/daily_expansion.parquet',columns=KEY+['date','turn_rank504','pe_rank504','pe_known_fraction','pe_positive_fraction'])
    # Form signals at completed months only, independent of outcome availability.
    calendar=pd.Series(pd.DatetimeIndex(b.index),index=pd.DatetimeIndex(b.index))
    ends=calendar.groupby(calendar.index.to_period('M')).max()
    ends=ends[[period.end_time.normalize()<=b.index.max() for period in ends.index]]
    parts=[]
    for _,g in d.groupby(KEY+['block'],sort=False):
        g=price_features(g);g=delayed_labels(g,b)
        parts.append(g[g.date.isin(ends.values)])
    panel=pd.concat(parts,ignore_index=True).merge(e,on=KEY+['date'],how='left',validate='one_to_one')
    panel['price_ready']=panel[['mom20','mom60','vol20','dd60']].notna().all(axis=1)&panel.coverage.ge(.8)&panel.members.ge(5)
    panel['year']=panel.date.dt.year
    panel.to_parquet(ROOT/'data/monthly_panel.parquet',index=False)
    cov=[]
    for key,g in panel.groupby(['era','level','year']):
        for c in ['price_ready','breadth21','breadth63','turn_rank504','pe_rank504','excess20','excess60']:
            n=int(g[c].sum()) if c=='price_ready' else int(g[c].notna().sum())
            cov.append(dict(zip(['era','level','year'],key),field=c,rows=len(g),nonmissing=n))
    pd.DataFrame(cov).to_csv(ROOT/'outputs/r01/panel_coverage.csv',index=False)
    js(ROOT/'outputs/r01/panel_receipt.json',dict(rows=len(panel),price_ready=int(panel.price_ready.sum()),
        sha256=sha(ROOT/'data/monthly_panel.parquet'),protocol_sha256=sha(ROOT/'protocols/r01.json'),
        entry_delay=protocol['entry_delay_sessions'],horizons=[20,60],source_inventory_sha256=sha(ROOT/'outputs/r01/source_inventory.json')))
    print('PANEL',len(panel),'price ready',panel.price_ready.sum())

if __name__=='__main__': run()
