"""Independent OLS calculation and decision-identity replay verification."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP,PRIOR,CACHE,sha

def main():
 root=EP/'outputs/v2_b08';f=pd.read_parquet(root/'features.parquet');raw=pd.read_parquet(PRIOR/'daily_industries.parquet');market=pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').close
 rec=json.loads((PRIOR/'receipt.json').read_text());cal=pd.DatetimeIndex(pd.read_parquet(next(k for k in rec['inputs'] if k.endswith('/calendar.parquet'))).date)
 groups={k:g.set_index('date') for k,g in raw.groupby(['era','industry_code'])};fi=f.set_index(['date','era','industry_code']);checked={};results={}
 for arm in ['A','B']:
  ev=pd.read_parquet(root/'q5_d0'/arm/'events.parquet');pool=set();exitweeks={};newcount=0
  eg={d:g for d,g in ev.groupby('date')}
  for date,g in f.groupby('date',sort=True):
   week=int(g.week.iloc[0]);e=eg.get(date,ev.iloc[:0]);keys=lambda kind:set(zip(e.loc[e.kind.eq(kind),'era'],e.loc[e.kind.eq(kind),'industry_code']))
   removed=keys('EXIT');assert removed<=pool;pool-=removed
   for k in removed:exitweeks[k]=week
   assert pool==keys('UPDATE')
   rank=g[g.eligible].sort_values(['r20' if arm=='A' else 'adjusted_score','industry_code'],ascending=[False,True])
   candidates=[(r.era,r.industry_code) for r in rank.itertuples() if (r.era,r.industry_code) not in pool and week-exitweeks.get((r.era,r.industry_code),-100)>=4]
   added=keys('NEW');assert added==set(candidates[:len(added)]) and len(added)<=min(5,20-len(pool));pool|=added;newcount+=len(added)
  for r in ev[ev.kind.eq('NEW')].itertuples():
   key=(r.date,r.era,r.industry_code);feat=fi.loc[key];assert feat.eligible and feat.r5>0 and feat.r20>0
   if key not in checked:
    j=cal.get_loc(r.date);dates=cal[j-60:j+1];z=groups[(r.era,r.industry_code)].reindex(dates);m=market.reindex(dates)
    assert len(z)==61 and z.nav.gt(0).all() and z.block.eq(r.block).all() and m.gt(0).all()
    y=np.diff(np.log(z.nav.to_numpy()));x=np.diff(np.log(m.to_numpy()));beta=np.linalg.lstsq(np.column_stack([np.ones(60),x]),y,rcond=None)[0][1]
    adjusted=np.log(z.nav.iloc[-1]/z.nav.iloc[-21])-beta*np.log(m.iloc[-1]/m.iloc[-21])
    assert np.isclose(beta,feat.beta60,rtol=1e-8,atol=1e-8)
    assert np.isclose(adjusted,feat.adjusted_score,rtol=1e-8,atol=1e-8)
    checked[key]=True
   expected=feat.r20 if arm=='A' else feat.adjusted_score;assert np.isclose(r.score,expected)
  cat=pd.read_parquet(root/'q5_d0'/arm/'catalog_states.parquet');assert len(cat)==141872 and not cat.duplicated(['date','era','industry_code']).any()
  results[arm]=dict(new=newcount,all_new_scores_ols_checked=True,pool_rank_cooldown_identity_checked=True,catalog_rows=len(cat))
 a=pd.read_csv(root/'q5_d0/A/weekly_burden.csv');b=pd.read_csv(root/'q5_d0/B/weekly_burden.csv');assert a.new.equals(b.new)
 receipt=json.loads((root/'replay_receipt.json').read_text())
 for name,digest in receipt['inputs'].items():assert sha(Path(name))==digest
 for name,digest in receipt['artifacts'].items():assert sha(root/name)==digest
 results['unique_ols_windows']=len(checked);results['matched_weekly_new']=True;results['hashes_pass']=True
 (root/'independent_replay_checks.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results,indent=2))
if __name__=='__main__':main()
