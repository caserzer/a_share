"""Independent rank calculation and decision-identity replay verification."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP,PRIOR,CACHE,sha

def main():
 root=EP/'outputs/v2_b09';f=pd.read_parquet(root/'features.parquet')
 vf=EP/'outputs/r04/volume_features.parquet';seal=json.loads((vf.parent/'prediction_seal.json').read_text());assert sha(vf)==seal['artifacts'][vf.name]
 v=pd.read_parquet(vf);v['date']=pd.to_datetime(v.date)
 z=f.merge(v,on=['date','era','industry_code'],suffixes=('','_sealed'),validate='one_to_one')
 for col in ['supported','volume_ratio','coverage','valid_members']:
  pd.testing.assert_series_equal(z[col],z[col+'_sealed'],check_names=False)
 assert f.eligible.equals(f.original_eligible & f.supported.eq(True) & np.isfinite(f.volume_ratio))
 for date,g in f[f.eligible].groupby('date'):
  # Average ranks computed directly by less-than and equality counts.
  def pct(values):
   x=values.to_numpy();return np.array([((x<t).sum()+((x==t).sum()+1)/2)/len(x) for t in x])
  expected=.5*pct(g.r20)+.5*pct(g.volume_ratio)
  assert np.allclose(expected,g.adjusted_score,rtol=0,atol=1e-12)
 fi=f.set_index(['date','era','industry_code']);checked={};results={}
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
   checked[key]=True
   expected=feat.r20 if arm=='A' else feat.adjusted_score;assert np.isclose(r.score,expected)
  cat=pd.read_parquet(root/'q5_d0'/arm/'catalog_states.parquet');assert len(cat)==141872 and not cat.duplicated(['date','era','industry_code']).any()
  results[arm]=dict(new=newcount,all_new_scores_checked=True,pool_rank_cooldown_identity_checked=True,catalog_rows=len(cat))
 a=pd.read_csv(root/'q5_d0/A/weekly_burden.csv');b=pd.read_csv(root/'q5_d0/B/weekly_burden.csv');assert a.new.equals(b.new)
 receipt=json.loads((root/'replay_receipt.json').read_text())
 for name,digest in receipt['inputs'].items():assert sha(Path(name))==digest
 for name,digest in receipt['artifacts'].items():assert sha(root/name)==digest
 results['unique_new_feature_rows']=len(checked);results['matched_weekly_new']=True;results['hashes_pass']=True
 (root/'independent_replay_checks.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results,indent=2))
if __name__=='__main__':main()
