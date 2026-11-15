"""Verify raw-score identity, frozen model provenance and all annual process counts."""
import pandas as pd
from scipy.special import expit
from common import *

def run():
 out=ROOT/'outputs/r159';root=out/'evaluation';rec=json.loads((out/'receipt.json').read_text())
 for p,h in rec['reads'].items():assert sha(p)==h,p
 assert rec['calibrated'] is False and rec['identity_link_not_fitted'] is True
 original=json.loads((ROOT/'outputs/r16/raw_parameters.json').read_text());original={m['year']:m for m in original if m['cohort']=='F' and m['method']=='F' and m['task']=='onset' and m['horizon']==20};adapted=json.loads((root/'outputs/r02/model_parameters.json').read_text());scores=pd.read_parquet(root/'data/r09_daily_scores.parquet');assert scores.era.eq('SW2021').all() and scores.level.eq('L1').all();checked=0
 for m in adapted:
  old=original[m['year']];assert m['coefficient']==old['coef'] and m['intercept']==old['intercept'];assert m['calibration_coefficient']==[[1.]] and m['calibration_intercept']==[0.]
  g=scores[scores.date.dt.year.eq(m['year'])];ranks=g.groupby('date')[old['columns']].rank(method='average');counts=g.groupby('date')[old['columns']].transform('count');ranks=(ranks-.5)/counts-.5;x=(ranks.to_numpy()-old['scaler_mean'])/old['scaler_scale'];pred=expit(x@np.asarray(old['coef'])+old['intercept']);assert np.allclose(pred,g.score,atol=1e-12,rtol=1e-10);checked+=len(g)
 assert checked==len(scores)
 monthly=pd.read_parquet(ROOT/'outputs/r16/raw_predictions.parquet');monthly=monthly[monthly.cohort.eq('F')&monthly.method.eq('F')&monthly.task.eq('onset')&monthly.horizon.eq(20)];p=monthly.merge(scores,on=KEY+['date'],suffixes=('_monthly','_daily'),validate='one_to_one');assert len(p)==len(monthly) and np.allclose(p.raw_score,p.score,atol=1e-10) and np.allclose(p.y_monthly,p.y_daily,equal_nan=True)
 alerts=pd.read_parquet(root/'outputs/r09/alerts.parquet');hits=pd.read_csv(root/'outputs/r09/event_hits.csv',parse_dates=['date']);annual=pd.read_csv(out/'annual_process.csv')
 for row in annual.itertuples():
  a=alerts[alerts.strategy.eq(row.strategy)&alerts.date.dt.year.eq(row.year)];h=hits[hits.strategy.eq(row.strategy)&hits.date.dt.year.eq(row.year)];v=h[h.evaluable];assert len(a)==row.alerts and a.y.notna().sum()==row.mature and a.y.isna().sum()==row.unknown;assert len(v)==row.events and v.hit.sum()==row.hit_events and (~h.evaluable).sum()==row.left_censored;assert np.isclose(a.y.mean(),row.precision) and np.isclose(v.hit.mean(),row.recall) and np.isclose(v.loc[v.hit,'lead_sessions'].median(),row.median_lead,equal_nan=True)
 ledger=pd.read_csv(ROOT/'outputs/r16/fold_ledger.csv');cal=ledger[ledger.cohort.eq('F')&ledger.task.eq('onset')&ledger.horizon.eq(20)&ledger.year.isin([2025,2026])];assert len(cal)==2 and cal.reason.eq('insufficient_calibration').all();cal.to_csv(out/'original_calibration_gates.csv',index=False)
 assert json.loads((root/'outputs/r09/verification.json').read_text())['status']=='PASS'
 js(out/'verification.json',dict(status='PASS',raw_daily_scores=checked,monthly_reconstruction_rows=len(p),annual_groups=len(annual),calibrated=False,original_calibration_failures_preserved=2,verifier_sha256=sha(Path(__file__))))
 print('R159 VERIFIED',checked,len(p))
if __name__=='__main__':run()
