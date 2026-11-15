from common import *
import pandas as pd
from regime_onset_actions_r221 import IDS
out=ROOT/'outputs/r221';p=pd.read_parquet(out/'actions.parquet');paths=pd.read_parquet(out/'paths.parquet');d=pd.read_csv(out/'date_metrics.csv',parse_dates=['date']);prices=pd.concat([pd.read_parquet(ROOT/'outputs/r129/daily_2026-10-21.parquet'),pd.read_parquet(ROOT/'data/l1_daily.parquet')]);market=pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').close;look={k:g.set_index('date') for k,g in prices.groupby(KEY)};maxerr=0.;pathchecks=0
for row in paths.to_dict('records'):
 ix=market.index.get_indexer([row['date']])[0];h=row['horizon'];good=ix>=0 and ix+h+1<len(market)
 if good:
  dates=market.index[ix+1:ix+h+2];a=look[tuple(row[x] for x in KEY)].reindex(dates);good=a.nav.notna().all() and a.block.nunique()==1
 if not good:assert row['status']=='unknown_path';continue
 assert row['status']=='valid';v=a.nav.to_numpy()/a.nav.iloc[0];b=market.loc[dates].to_numpy()/market.loc[dates[0]];peak=1.;dd=0
 for z in v:peak=max(peak,z);dd=min(dd,z/peak-1)
 for c,value in [('ret',v[-1]-1),('market',b[-1]-1),('rel_trough',min(v/b)-1),('drawdown',dd)]:err=abs(value-row[c]);assert err<1e-12;maxerr=max(maxerr,err);pathchecks+=1
metrics={k:g for k,g in d.groupby(IDS+['date'])};checks=0;selections=0
for key,g in p.groupby(IDS+['date']):
 ordered=sorted(g.to_dict('records'),key=lambda x:(-x['prediction'],x['industry_code']));names={x['industry_code'] for x in ordered[:int(np.ceil(len(g)/5))]};assert names==set(g[g.alert].industry_code);selections+=1;known=g[g.status.eq('valid')];labels=g.dropna(subset=['y']);tp=sum(labels.alert&labels.y.eq(1));pos=sum(labels.y.eq(1));na=sum(labels.alert)
 for row in metrics[key].to_dict('records'):
  cost=row['cost'];cash=[];switch=[]
  for x in known.to_dict('records'):
   bought=(1-cost)*(1+x['ret'])*(1-cost);benchmark=(1-cost)*(1+x['market'])*(1-cost);cash.append(bought-1 if x['alert'] else 0.);switch.append(bought-benchmark if x['alert'] else 0.)
  values={'cash_policy_gain':np.mean(cash) if cash else np.nan,'market_policy_gain':np.mean(switch) if switch else np.nan,'precision':tp/na if na else np.nan,'recall':tp/pos if pos else np.nan}
  assert row['eligible']==len(g) and row['alerts']==len(names) and row['known_paths']==len(known) and row['known_labels']==len(labels)
  for c,v in values.items():assert np.isclose(v,row[c],atol=1e-12,equal_nan=True);checks+=1
js(out/'independent_verification.json',dict(status='PASS',path_value_checks=pathchecks,selection_groups=selections,metric_checks=checks,max_path_error=maxerr,scope='Every path/calendar/block and sequential drawdown; all frozen top20 selections; count coverage and independent purchase/hold/liquidation policy cashflows, precision and recall',script_sha256=sha(__file__)));print('PASS',pathchecks,selections,checks,maxerr)
