"""Independent coverage and cohort checks plus original algebra/calendar audits."""
import pandas as pd
from common import *
import battery_pilot_r64,verify_battery_pilot_r64,verify_battery_gates_r65
K=KEY+['date'];F=['mom20','mom60','vol20','dd60','past_excess20','past_excess60','log_members']
def run():
 out=ROOT/'outputs/r140';root=out/'evaluation';receipt=json.loads((out/'comparison.json').read_text())
 for p,h in receipt['reads'].items():assert sha(p)==h
 panel=pd.read_parquet(ROOT/'outputs/r130/monthly_panel.parquet');panel=panel[panel.era.eq('SW2021')&panel.industry_code.isin(['801737.SI','857371.SI'])].copy();panel['log_members']=np.log(panel.members);panel=panel.merge(pd.read_parquet(ROOT/'data/r30_size_control.parquet')[K+['size_control']],on=K,validate='one_to_one',how='left')
 series=pd.DataFrame(json.loads((ROOT/'outputs/r60/frozen_monthly_series.json').read_text()));series['available']=pd.to_datetime(series.growth_available_at);series['period']=pd.PeriodIndex(series.month,freq='M');coverage=pd.DataFrame(json.loads((root/'outputs/r61/signal_coverage.json').read_text()));coverage['date']=pd.to_datetime(coverage.date);look=coverage.set_index(K);assert set(look.index)==set(pd.MultiIndex.from_frame(panel[K]))
 for r in panel.to_dict('records'):
  row=look.loc[tuple(r[k] for k in K)];month=r['date'].to_period('M');candidates=series[series.available.le(r['date'])&series.period.between(month-2,month)].sort_values('period');chosen=candidates.iloc[-1] if len(candidates) else None
  assert row.price_complete==bool(r['price_ready'] and all(pd.notna(r[c]) for c in F));assert row.size_complete==pd.notna(r['size_control'])
  for name,field in [('economic_month','month'),('log_yoy','log_yoy'),('growth_available_at','growth_available_at')]:
   expected=chosen[field] if chosen is not None else None;actual=row[name];assert (pd.isna(actual) and pd.isna(expected)) or actual==expected
 cols=F+['size_control','market_beta126','residual_vol126','log_yoy'];panel=panel.merge(coverage[K+['economic_month','growth_available_at','log_yoy']],on=K,validate='one_to_one');panel=panel.merge(pd.read_parquet(ROOT/'outputs/r133/market_controls.parquet')[K+['market_beta126','residual_vol126']],on=K,how='left',validate='one_to_one');expected=panel[panel.price_ready&panel[cols].notna().all(axis=1)].set_index(K).sort_index();saved=pd.read_parquet(out/'cohort_new.parquet').set_index(K).sort_index();assert saved.index.equals(expected.index)
 for c in cols+['excess20','excess60','return20','return60','rel_trough20','rel_trough60']:assert np.allclose(saved[c],expected[c],equal_nan=True)
 battery_pilot_r64.ROOT=root;verify_battery_pilot_r64.ROOT=root;verify_battery_gates_r65.ROOT=root;verify_battery_pilot_r64.run();verify_battery_gates_r65.run()
 for item in receipt['artifacts']:
  a=json.loads((ROOT/f"outputs/{item['family']}/{item['artifact']}.json").read_text());b=json.loads((root/f"outputs/{item['family']}/{item['artifact']}.json").read_text());assert item['exactly_equal']==(a==b);assert len(a)==item['old_rows'] and len(b)==item['new_rows']
 metrics=json.loads((root/'outputs/r64/metrics.json').read_text());pred=pd.DataFrame(json.loads((root/'outputs/r64/predictions.json').read_text()))
 for m in metrics:
  g=pred.copy()
  for k in KEY+['horizon']:g=g[g[k].eq(m[k])]
  if m['period']!='all':g=g[g.year.eq(int(m['period']))]
  a=g[g.method.eq(m['control'])].dropna(subset=['target']);b=g[g.method.eq(m['augmented'])].dropna(subset=['target']);assert np.isclose(m['mse_mean'],((a.target-a.mean_prediction)**2).mean());assert np.isclose(m['mae_control'],(a.target-a.prediction).abs().mean());assert np.isclose(m['mae_augmented'],(b.target-b.prediction).abs().mean());assert np.isclose(m['mse_improvement'],m['mse_control']-m['mse_augmented'])
 js(out/'verification.json',dict(status='PASS',coverage_rows=len(coverage),complete_cohort_rows=len(saved),return_models=32,prediction_rows=len(pred),classification_folds=40,eligible_classification_folds=0,all_six_artifacts_identical=all(x['exactly_equal'] for x in receipt['artifacts']),verifier_sha256=sha(__file__),subchecks={str(p.relative_to(out)):sha(p) for p in [root/'outputs/r64/verification.json',root/'outputs/r65/verification.json']}))
 print('BATTERY REPAIR VERIFIED',len(coverage),len(saved),len(pred),flush=True)
if __name__=='__main__':run()
