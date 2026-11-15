import pandas as pd
from common import *

def run():
 out=ROOT/'outputs/r33';receipt=json.loads((out/'receipt.json').read_text())
 for path,digest in receipt['reads'].items():assert sha(path)==digest
 p=pd.read_parquet(ROOT/'data/r33_exit_origins.parquet');assert sha(ROOT/'data/r33_exit_origins.parquet')==receipt['origin_sha256']
 d=pd.read_csv(out/'date_metrics.csv',parse_dates=['date']);keys=['era','level','horizon','method','date'];look=d.set_index(keys+['cost']);checks=0
 for key,g in p.groupby(keys):
  expected=g.sort_values(['prediction','industry_code'],ascending=[False,True]).head(int(np.ceil(.2*len(g))))
  assert set(g.index[g.alert])==set(expected.index);h=key[2];r=g[f'return{h}'];b=g[f'market_return{h}'];known=r.notna()&b.notna();valid=known&g.alert
  for c in [0,.002,.005]:
   row=look.loc[key+(c,)];assert row.origins==len(g) and row.alerts==len(expected) and row.complete==known.sum() and row.policy_complete==known.all()
   hold=(1+r)*(1-c);cash=pd.Series(1-c,index=g.index)-hold;switch=(1-c)*(1-c)*(1+b)*(1-c)-hold
   assert np.isclose(row.alert_cash,cash[valid].mean(),equal_nan=True) and np.isclose(row.alert_market,switch[valid].mean(),equal_nan=True)
   for col,value in [('policy_cash',cash),('policy_market',switch)]:
    expected_policy=sum(value[g.alert])/len(g) if known.all() else np.nan;assert np.isclose(row[col],expected_policy,equal_nan=True)
   assert np.isclose(row.avoided_loss-row.missed_upside,-r[valid].mean(),equal_nan=True);checks+=1
 for _,g in p.groupby(['era','level','horizon','date']):
  frames=[z for _,z in g.groupby('method')];assert len(frames)==4
  for z in frames[1:]:assert set(z.industry_code)==set(frames[0].industry_code) and z.alert.sum()==frames[0].alert.sum()
 source=CACHE/'forecast_v5/daily_industries.parquet';daily=pd.read_parquet(source);market=pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').close;lookup={k:g.sort_values('date').reset_index(drop=True) for k,g in daily.groupby(KEY)};n=0
 sample=p.drop_duplicates(KEY+['date','horizon']).sample(n=100,random_state=33)
 for row in sample.itertuples():
  g=lookup[(row.era,row.level,row.industry_code)];idx=g.index[g.date.eq(row.date)][0];h=row.horizon
  if idx+h+1<len(g) and g.loc[idx:idx+h+1,'block'].nunique()==1:
   a=g.iloc[idx+1];b=g.iloc[idx+h+1];r=b.nav/a.nav-1;bm=market.loc[b.date]/market.loc[a.date]-1
   assert np.isclose(r,getattr(row,f'return{h}'),equal_nan=True) and np.isclose(bm,getattr(row,f'market_return{h}'),equal_nan=True)
  else:assert pd.isna(getattr(row,f'return{h}'))
  n+=1
 js(out/'verification.json',dict(status='PASS',date_cost_checks=checks,direct_price_windows=n,source_daily_sha256=sha(source),checks=['source hashes','top20 selection before outcomes','equal eligible universe and alert count','complete-universe policy denominator','terminal cash/market accounting','avoided loss minus missed gain identity','100 direct daily price windows'],limitation='not actual fills, financing, drawdown protection or continuous portfolio'))
 print('R33 VERIFIED',checks,n)
if __name__=='__main__':run()
