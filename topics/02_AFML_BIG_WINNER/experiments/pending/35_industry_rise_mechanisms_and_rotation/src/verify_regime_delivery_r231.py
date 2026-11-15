from common import *
import pandas as pd
import tempfile
import regime_monitor_r231 as monitor

def run():
 out=ROOT/'outputs/r231';s=pd.read_parquet(ROOT/'outputs/r195/market_regimes.parquet');close=pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').close.sort_index();assert close.index.equals(s.index);prices=close.tolist();vols=[];maximum=0.
 for i,(date,row) in enumerate(s.iterrows()):
  v=float(np.std([prices[j]/prices[j-1]-1 for j in range(i-20,i+1)],ddof=1)) if i>=21 else np.nan;prior=[x for x in vols[max(0,i-252):i] if np.isfinite(x)];threshold=float(np.median(prior)) if len(prior)>=126 else np.nan;trend=prices[i]/prices[i-63]-1 if i>=63 else np.nan;vols.append(v)
  for name,value in [('vol21',v),('prior_vol_median',threshold),('trend63',trend)]:
   assert np.isclose(s.at[date,name],value,atol=1e-14,equal_nan=True)
   if np.isfinite(value):maximum=max(maximum,abs(s.at[date,name]-value))
  expected=('up' if trend>=0 else 'down')+'_'+('high' if v>=threshold else 'low') if all(np.isfinite(x) for x in [trend,v,threshold]) else None;assert (pd.isna(row.regime) and expected is None) or row.regime==expected
 known=monitor.snapshot('2026-09-30','signal_close');prior=monitor.snapshot('2026-09-30','prior_close');assert prior['state_date']<known['state_date'];unknown=monitor.snapshot(str(s.index[0].date()),'signal_close');assert unknown['regime'] is None and unknown['state_dummies'] is None
 for name,obj in [('example_prior_close',prior),('example_unknown',unknown)]:monitor.write_snapshot(obj,out/(name+'.json'))
 rejects=0
 for day,clock in [(str((s.index[-1]+pd.Timedelta(days=1)).date()),'signal_close'),(str(s.index[0].date()),'prior_close'),('2026-09-30 10:00','signal_close'),('2026-09-30','unsupported')]:
  try:monitor.snapshot(day,clock)
  except ValueError:rejects+=1
  else:raise AssertionError('invalid request accepted')
 missing=next(x for x in pd.date_range(s.index[0],s.index[-1]) if x not in s.index)
 try:monitor.snapshot(str(missing.date()),'signal_close')
 except ValueError:rejects+=1
 else:raise AssertionError('missing date accepted')
 original=monitor.sha
 try:
  monitor.sha=lambda p:'0'*64
  try:monitor.snapshot('2026-09-30','signal_close')
  except AssertionError:rejects+=1
  else:raise AssertionError('source mismatch accepted')
 finally:monitor.sha=original
 with tempfile.TemporaryDirectory() as temp:
  p=Path(temp)/'snapshot.json';assert monitor.write_snapshot(known,p)=='created';assert monitor.write_snapshot(known,p)=='unchanged'
  try:monitor.write_snapshot(prior,p)
  except ValueError:rejects+=1
  else:raise AssertionError('conflicting overwrite accepted')
 ext=json.loads((out/'factor_dictionary_extension.json').read_text());base=ext['base_dictionary'];assert sha(ROOT/base['path'])==base['sha256'];assert len(ext['definitions'])==5;contract=json.loads((out/'monitor_contract.json').read_text())
 for obj in [known,prior,unknown]:assert set(contract['required'])<=obj.keys() and not obj['adoption'] and not obj['production_enabled'] and obj['prediction'] is None
 reads=[ROOT/'outputs/r195/market_regimes.parquet',CACHE/'forecast_v5/CSI_ALL.parquet',ROOT/'outputs/r167/factor_dictionary.json',ROOT/'src/regime_monitor_r231.py',ROOT/'src/regime_dictionary_r231.py',Path(__file__),ROOT/'protocols/r231.json']
 js(out/'verification.json',dict(status='PASS',independent_state_rows=len(s),max_error=maximum,rejection_cases=rejects,immutable_and_idempotent=True,definitions=5,model_adoption=False,inputs={str(p):sha(p) for p in reads},outputs={p.name:sha(p) for p in out.glob('*.json') if p.name!='verification.json'},scope='Independent all-date state calculation, clock/unknown/source integrity/output guards, dictionary preservation; not model validity or live data monitoring'))
 print(len(s),maximum,rejects)
if __name__=='__main__':run()
