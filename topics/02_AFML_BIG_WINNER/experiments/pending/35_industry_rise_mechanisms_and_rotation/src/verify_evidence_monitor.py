from common import *
import pandas as pd
from versioned_observations import verify_bundle


def run():
 out=ROOT/'outputs/r21';rec=json.loads((out/'receipt.json').read_text())
 for p,h in rec['reads'].items():assert sha(p)==h
 for p,h in rec['outputs'].items():assert sha(out/p)==h
 d=pd.read_csv(out/'evidence_matrix.csv');delta=pd.read_csv(out/'historical_changes.csv')
 assert len(d)==3066 and len(delta)==1533
 assert not d.duplicated(KEY+['asof','clock']).any()
 assert not {'excess20','excess60','entry_date','absolute_return'} & set(d)
 assert d.economic_stage.eq('not_established').all() and d.capture_kind.eq('historical_replay').all()
 assert d.clock_scope.str.contains('company_facts_only').all()
 ready=d[d.price_ready]
 assert np.allclose(ready[['momentum_contribution','volatility_contribution','drawdown_contribution']].sum(axis=1),ready.price_score,atol=1e-14)
 assert d.loc[~d.price_ready,'price_rank'].isna().all()
 known=d.expectation_date.notna()
 assert (pd.to_datetime(d.loc[known,'expectation_date'])<=pd.to_datetime(d.loc[known,'asof'])).all()
 stale=d.expectation_status.eq('older_snapshot_not_current');assert d.loc[stale,'expectation_age_days'].gt(0).all()
 for b in rec['bundles']:
  path=Path(b['path']);m=verify_bundle(path);assert sha(path/'manifest.json')==b['manifest_sha256']
  o=pd.read_parquet(path/'observations.parquet').set_index(KEY)
  for _,g in d[d['asof'].eq(m['identity']['asof'])].groupby('clock'):
   assert len(g)==511
   g=g.set_index(KEY).reindex(o.index)
   for c in ['price_score','price_rank','breadth21','breadth63']:assert np.allclose(g[c],o[c],equal_nan=True)
 for row in delta.itertuples(index=False):
  g=d[(d.era==row.era)&(d.level==row.level)&(d.industry_code==row.industry_code)&(d.clock==row.clock)].sort_values('asof')
  assert len(g)==2
  a,b=g.iloc[0],g.iloc[1]
  assert row.fact_count_change==b.facts-a.facts
  expected=b.price_rank-a.price_rank
  assert (pd.isna(expected) and pd.isna(row.rank_change)) or abs(expected-row.rank_change)<1e-12
 js(out/'verification.json',dict(status='PASS',matrix_rows=len(d),change_rows=len(delta),score_conservation_rows=len(ready),code_sha256=sha(__file__),limitation='historical evidence integrity, not economic stage validation or forward signal'))
 print('R21 verified',len(d),'matrix rows and',len(delta),'changes')

if __name__=='__main__':run()
