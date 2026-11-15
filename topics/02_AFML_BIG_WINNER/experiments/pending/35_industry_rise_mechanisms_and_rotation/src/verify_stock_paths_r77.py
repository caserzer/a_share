import pandas as pd
from common import *
def run():
 out=ROOT/'outputs/r77';rec=json.loads((out/'receipt.json').read_text())
 for p,h in rec['reads'].items():assert sha(p)==h
 for p,h in rec['price_partitions'].items():assert sha(p)==h
 paths={Path(p).stem:Path(p) for p in rec['price_partitions']};audit=pd.read_parquet(out/'stock_interval_audit.parquet');pos=pd.read_parquet(ROOT/'outputs/r76/nominal_positions.parquet');keys=['method','origin','security_id'];pd.testing.assert_frame_equal(audit[keys+['weight']].sort_values(keys).reset_index(drop=True),pos[keys+['weight']].sort_values(keys).reset_index(drop=True));rows=json.loads((out/'intervals.json').read_text());by={(x['method'],pd.Timestamp(x['origin'])):x for x in rows};calendar=pd.DatetimeIndex(pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').index)
 for x in audit.sample(n=min(100,len(audit)),random_state=35077).to_dict('records'):
  iv=by[(x['method'],x['origin'])];dates=calendar[(calendar>=pd.Timestamp(iv['entry']))&(calendar<=pd.Timestamp(iv['exit']))];f=pd.read_parquet(paths[x['security_id']]).set_index('date').reindex(dates);v=pd.to_numeric(f.qfq_close).where(f.close_conflict.eq(False)&pd.to_numeric(f.qfq_close).gt(0));valid=bool(v.notna().all());stable=bool(f.factor_chain_id.notna().all() and f.factor_chain_id.nunique()==1);assert valid==x['price_valid'] and stable==x['chain_stable'];assert (pd.isna(v.iloc[0]) and pd.isna(x['entry_price'])) or v.iloc[0]==x['entry_price'];assert (pd.isna(v.iloc[-1]) and pd.isna(x['exit_price'])) or v.iloc[-1]==x['exit_price']
 groups={k:g for k,g in audit.groupby(['method','origin'])};coverage={(x['method'],pd.Timestamp(x['origin'])):x for x in json.loads((ROOT/'outputs/r76/target_coverage.json').read_text())};old=pd.read_csv(ROOT/'outputs/r17/intervals.csv',parse_dates=['origin']).set_index(['method','origin'])
 for key,g in groups.items():
  x=by[key];good=g.price_valid & g.chain_stable;u=coverage[key]['unknown_weight'];ready=bool(u<1e-12 and good.all() and np.isclose(g.weight.sum(),1));assert ready==x['full_path_valued'];assert x['price_bad']==int((~g.price_valid).sum()) and x['chain_bad']==int((~g.chain_stable).sum());assert abs(x['unvalued_known_weight']-g.loc[~good,'weight'].sum())<1e-12
  if ready:
   ret=sum(z.weight*z.exit_price/z.entry_price for z in g.itertuples())-1;assert abs(ret-x['fixed_stock_gross'])<1e-12;assert abs(ret-old.loc[key,'gross_return']-x['gross_difference'])<1e-12
  else:assert x['fixed_stock_gross'] is None and x['gross_difference'] is None
 for x in json.loads((out/'summary.json').read_text()):
  q=[z for z in rows if z['method']==x['method']];ok=[z for z in q if z['full_path_valued']];assert len(q)==x['planned'] and len(ok)==x['valued'] and x['whole_path_valid']==(len(q)==len(ok))
 js(out/'verification.json',dict(status='PASS',source_hashes=len(rec['price_partitions']),direct_daily_stock_windows=100,interval_aggregations=len(rows),fixed_weight_rows=len(audit),scope='all source hashes, all weights and interval valuation accounting; 100 independently replayed daily stock windows; execution permission counts descriptive, not execution certification'));print('R77 VERIFIED',len(rows),len(audit),'100 direct windows')
if __name__=='__main__':run()
