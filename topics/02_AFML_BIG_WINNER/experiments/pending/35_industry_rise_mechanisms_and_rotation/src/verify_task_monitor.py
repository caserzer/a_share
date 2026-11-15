from common import *
import pandas as pd
from versioned_observations import digest_json


def run():
 out=ROOT/'outputs/r22';rec=json.loads((out/'receipt.json').read_text())
 for p,h in rec['reads'].items():assert sha(p)==h
 for p,h in rec['outputs'].items():assert sha(out/p)==h
 d=pd.read_csv(out/'task_monitor.csv');assert len(d)==12264
 keys=KEY+['asof','task','horizon','method']
 assert not d.duplicated(keys).any()
 assert not {'y','excess','entry_date','maturity','raw_prediction'}&set(d)
 assert d[d['asof']=='2026-10-21'].prediction.isna().all()
 checked=0
 for round_,levels in [('r02',['L2','L3']),('r16',['L1'])]:
  p=pd.read_parquet(ROOT/f'outputs/{round_}/predictions.parquet',columns=KEY+['date','cohort','method','task','horizon','prediction'])
  p=p[p.cohort.eq(p.method)&p.method.isin(['F','FD'])];p['asof']=p.date.dt.strftime('%Y-%m-%d')
  actual=d[d.level.isin(levels)&d.prediction.notna()]
  joined=actual.merge(p,on=keys,suffixes=('_monitor','_source'),validate='one_to_one')
  assert len(joined)==len(actual) and np.allclose(joined.prediction_monitor,joined.prediction_source,atol=1e-14)
  for date,group in d[d.level.isin(levels)].groupby('asof'):
   base_keys=KEY+['task','horizon','method']
   latest=p[p.date.le(pd.Timestamp(date))].sort_values('date').groupby(base_keys).tail(1)
   check=group.merge(latest[base_keys+['date','prediction']],on=base_keys,how='left',suffixes=('_monitor','_source'),validate='one_to_one')
   assert np.allclose(check.last_prediction,check.prediction_source,equal_nan=True,atol=1e-14)
   assert (pd.to_datetime(check.last_prediction_date).fillna(pd.Timestamp('1900-01-01'))==check.date.fillna(pd.Timestamp('1900-01-01'))).all()
  models={digest_json(m):m for m in json.loads((ROOT/f'outputs/{round_}/model_parameters.json').read_text())}
  for h,g in actual.groupby('model_sha256'):
   m=models[h];assert pd.Timestamp(m['fit_max_maturity'])<pd.Timestamp(m['year'],1,1)
   if m['task']!='return':
    assert m['calibration_coefficient'] is not None and m['calibration_intercept'] is not None
    assert pd.Timestamp(m['fit_max_maturity'])<pd.Timestamp(m['year']-1,7,1)
    assert pd.Timestamp(m['cal_max_maturity'])<pd.Timestamp(m['year'],1,1)
    assert m['n_cal']>=100 and m['cal_months']>=4
    assert g.prediction.between(0,1).all()
   else:assert g.calibration_status.eq('not_applicable_regression').all()
  checked+=len(joined)
 assert d.loc[d.prediction.notna(),'status'].eq('formal_historical_output').all()
 assert pd.to_datetime(d.last_prediction_date.dropna()).le(pd.to_datetime(d.loc[d.last_prediction_date.notna(),'asof'])).all()
 assert d[d.level.eq('L1')&d.task.ne('return')].prediction.isna().all()
 js(out/'verification.json',dict(status='PASS',full_grid_rows=len(d),frozen_predictions_checked=checked,code_sha256=sha(__file__),limitation='formal historical output integration; calibration process qualification does not establish future reliability'))
 print('R22 verified',len(d),'task rows;',checked,'frozen predictions')

if __name__=='__main__':run()
