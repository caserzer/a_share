"""Independent financing/model/selection audits and repaired exit price checks."""
import shutil
import pandas as pd
from common import *
import margin_models_r46,verify_margin_factor_r45,verify_margin_models_r46,verify_classifiers_margin_r47,verify_margin_selection_r47,verify_exits_margin_r48

def run():
 out=ROOT/'outputs/r143';root=out/'evaluation'
 for p,h in json.loads((out/'summary.json').read_text())['reads'].items():assert sha(p)==h
 margin_models_r46.ROOT=root
 for module in [verify_margin_factor_r45,verify_margin_models_r46,verify_classifiers_margin_r47,verify_margin_selection_r47]:module.ROOT=root;module.run()
 cache=root/'cache/forecast_v5';cache.mkdir(parents=True,exist_ok=True);cols=KEY+['date','block','nav'];daily=pd.concat([pd.read_parquet(ROOT/'outputs/r129/daily_2026-10-21.parquet',columns=cols),pd.read_parquet(ROOT/'data/l1_daily.parquet',columns=cols)]);daily.to_parquet(cache/'daily_industries.parquet',index=False);shutil.copyfile(CACHE/'forecast_v5/CSI_ALL.parquet',cache/'CSI_ALL.parquet');verify_exits_margin_r48.ROOT=root;verify_exits_margin_r48.CACHE=root/'cache';verify_exits_margin_r48.run()
 # Verify all exit labels, not just the independent price-window sample.
 cols=KEY+['date','return20','market_return20','return60','market_return60'];panel=pd.concat([pd.read_parquet(root/f'data/{f}',columns=cols) for f in ['monthly_panel.parquet','l1_monthly_panel.parquet']]).set_index(KEY+['date']);p=pd.read_parquet(root/'data/r48_exit_origins.parquet');q=panel.loc[pd.MultiIndex.from_frame(p[KEY+['date']])]
 for c in cols[len(KEY)+1:]:assert np.allclose(p[c],q[c],equal_nan=True)
 pairs=pd.read_parquet(out/'factor_pairs.parquet');shared=pairs[pairs._merge.eq('both')];columns=['members','margin_known','cap_known','ratio_known','raw_median','coverage','financing_intensity'];changes={c:int((~np.isclose(shared[c+'_old'],shared[c+'_new'],rtol=1e-12,atol=1e-12,equal_nan=True)).sum()) for c in columns}
 newkeys=pairs.loc[pairs._merge.eq('right_only'),KEY+['date']]
 newpanel=pd.concat([pd.read_parquet(root/'data/monthly_panel.parquet'),pd.read_parquet(root/'data/l1_monthly_panel.parquet')]);added=newkeys.merge(newpanel[KEY+['date','price_ready']],on=KEY+['date'],validate='one_to_one');assert not added.price_ready.any();added.to_csv(out/'added_factor_price_eligibility.csv',index=False)
 margin_models_r46.ROOT=ROOT;oldbase=margin_models_r46.panel().set_index(KEY+['date']).sort_index();margin_models_r46.ROOT=root;newbase=margin_models_r46.panel().set_index(KEY+['date']).sort_index();assert oldbase.index.equals(newbase.index)
 cols=margin_models_r46.METHODS['FSE']+['excess20','excess60','maturity20','maturity60','return20','return60','rel_trough20','rel_trough60'];pd.testing.assert_frame_equal(oldbase[cols],newbase[cols])
 comparisons=[]
 for family,file,keys in [('r46','increments.json',['era','level','horizon']),('r47','increments.csv',['era','level','task','horizon','comparison']),('r48','paired_policy.csv',['era','level','horizon','cost','metric','comparison'])]:
  def read(path):return pd.DataFrame(json.loads(path.read_text())) if path.suffix=='.json' else pd.read_csv(path)
  a=read(ROOT/f'outputs/{family}/{file}').set_index(keys).sort_index();b=read(root/f'outputs/{family}/{file}').set_index(keys).sort_index();assert a.index.equals(b.index);numeric=[c for c in a if pd.api.types.is_numeric_dtype(a[c]) and not pd.api.types.is_bool_dtype(a[c])];maximum=max(float((a[c]-b[c]).abs().max()) for c in numeric);equal=all(np.allclose(a[c],b[c],rtol=1e-12,atol=1e-12,equal_nan=True) for c in numeric);fields=[c for c in a if c not in numeric]
  assert all(a[c].equals(b[c]) for c in fields);comparisons.append(dict(family=family,rows=len(a),numeric_equal_1e_12=equal,max_numeric_change=maximum,non_numeric_equal=True));a.join(b,lsuffix='_old',rsuffix='_new').to_csv(out/f'{family}_metric_comparison.csv')
 allmetrics=pd.read_parquet(root/'outputs/r46/metrics_by_date.parquet');increments=json.loads((root/'outputs/r46/increments.json').read_text())
 for x in increments:
  m=allmetrics[allmetrics.era.eq(x['era'])&allmetrics.level.eq(x['level'])&allmetrics.horizon.eq(x['horizon'])];w=m.pivot(index='date',columns='method',values=['mse','ic']);delta=w.ic.FSE-w.ic.FS;years=delta.dropna().groupby(delta.dropna().index.year).mean();assert np.isclose(x['mse_improvement'],(w.mse.FS-w.mse.FSE).mean());assert x['historical_support']==bool(delta.count()>=24 and len(years)>=3 and years.gt(0).all() and x['low99']>0)
 proofs=[root/f'outputs/{f}/{n}' for f,n in [('r45','verification.json'),('r46','verification.json'),('r47','verification.json'),('r47','selection_verification.json'),('r48','verification.json')]]
 js(out/'verification.json',dict(status='PASS',factor_shared_changes=changes,added_factor_rows=len(added),added_price_ready=int(added.price_ready.sum()),identical_model_cohort_rows=len(newbase),metric_comparisons=comparisons,all_exit_outcomes_checked=len(p),subchecks={str(x.relative_to(out)):sha(x) for x in proofs},direct_price_source_sha256=sha(cache/'daily_industries.parquet'),verifier_sha256=sha(__file__)))
 print('FINANCING VERIFIED',comparisons,flush=True)
if __name__=='__main__':run()
