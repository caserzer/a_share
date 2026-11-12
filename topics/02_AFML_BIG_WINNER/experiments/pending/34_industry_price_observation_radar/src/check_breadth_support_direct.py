from pathlib import Path
import json,pandas as pd,numpy as np
p=Path('/home/xiaolv/code/a_share/topics/02_AFML_BIG_WINNER/experiments/pending/34_industry_price_observation_radar')
o=p/'outputs/breadth_feasibility';receipt=json.loads((p.parent/'33_industry_second_order_change/restart/p29/receipt.json').read_text())
f=pd.read_parquet(o/'weekly_support.parquet');a=pd.read_parquet('/home/xiaolv/.cache/a_share/ep32/extension_v2/products/assignments.parquet',columns=['month','security_id','industry_code','unresolved','level','era']);a=a[a.level.eq('L3')]
cal=pd.DatetimeIndex(pd.read_parquet(next(x for x in receipt['inputs'] if x.endswith('/calendar.parquet'))).date).sort_values();paths={Path(x).stem:x for x in receipt['price_reads']}
samples=f[f.members.notna()].groupby(['era','support5_80'],group_keys=False).sample(n=5,random_state=3403);checked=0
for r in samples.itertuples():
 members=a[(a.era==r.era)&(a.industry_code==r.industry_code)&(a.month.astype(str)==r.membership_month)]
 day=cal.get_loc(r.date);history=cal[max(0,day-20):day+1];n=now=0
 for sid in members.security_id:
  raw=pd.read_parquet(paths[sid],columns=['date','qfq_close','close_conflict','factor_chain_id']).set_index('date').reindex(history)
  ok=raw.qfq_close.notna()&np.isfinite(raw.qfq_close)&raw.qfq_close.gt(0)&raw.close_conflict.eq(False)&raw.factor_chain_id.notna()
  now+=int(ok.iloc[-1]);n+=int(len(raw)==21 and ok.all() and raw.factor_chain_id.nunique()==1);checked+=1
 assert n==r.history20_known and now==r.current_known
 assert np.isclose(n/(len(members)+members.unresolved.max()),r.coverage20)
result=dict(industry_week_checks=len(samples),member_window_checks=checked,status='PASS',method='Direct 21-calendar-date slice and unique chain count; no rolling run counter')
(o/'direct_validation.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
