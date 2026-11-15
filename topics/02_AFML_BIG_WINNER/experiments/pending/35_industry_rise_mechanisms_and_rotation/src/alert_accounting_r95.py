import pandas as pd
from common import *
def run():
 out=ROOT/'outputs/r95';out.mkdir(exist_ok=True);ap=ROOT/'data/r10_alert_followup.parquet';op=ROOT/'outputs/r94/observations.json';a=pd.read_parquet(ap);o=pd.DataFrame(json.loads(op.read_text()));o['snapshot']=pd.to_datetime(o.snapshot);groups={k:g.sort_values('snapshot') for k,g in o.groupby(KEY)};extra=[]
 for r in a.to_dict('records'):
  g=groups.get(tuple(r[k] for k in KEY));q=g[g.snapshot.lt(r['date'])] if g is not None else pd.DataFrame();x=q.iloc[-1] if len(q) else None;v=dict(accounting_snapshot=None,accounting_period=None,accounting_age_days=None,accounting_status='no_prior_source_snapshot',accounting_coherence=None,accounting_group='unknown')
  if x is not None:
   v.update(accounting_snapshot=x.snapshot,accounting_period=x.period,accounting_age_days=(r['date']-x.snapshot).days,accounting_status=x.status)
   if x.status=='source_limited_disclosed_period_available' and pd.notna(x.both_improve_fraction) and pd.notna(x.both_decline_fraction):
    z=x.both_improve_fraction-x.both_decline_fraction;v.update(accounting_coherence=z,accounting_group='positive' if z>0 else 'negative' if z<0 else 'zero')
  extra.append(v)
 d=pd.concat([a.reset_index(drop=True),pd.DataFrame(extra)],axis=1);d.to_parquet(out/'alerts.parquet',index=False);summary=[]
 for key,g in d.groupby(['era','level','strategy','accounting_group']):
  for metric in ['excess20','return20','continuation_excess20_60','breadth_change20']:
   known=g[g[metric].notna()];daily=known.groupby('date')[metric].mean();summary.append(dict(zip(['era','level','strategy','accounting_group'],key),metric=metric,alerts=len(g),known=len(known),unknown=len(g)-len(known),dates=g.date.nunique(),known_dates=len(daily),industries=g.industry_code.nunique(),source_snapshots=g.accounting_snapshot.nunique(),economic_periods=g.accounting_period.nunique(),mean_age_days=g.accounting_age_days.mean(),date_equal_mean=daily.mean()))
 js(out/'summary.json',summary);coverage=d.groupby(['era','level','strategy','accounting_status','accounting_group']).size().reset_index(name='alerts');js(out/'coverage.json',coverage.to_dict('records'));paths=[ap,op,ROOT/'outputs/r94/verification.json',ROOT/'protocols/r95.json',Path(__file__)];js(out/'receipt.json',dict(reads={str(p):sha(p) for p in paths},all_alerts=len(a),known_exposure=int(d.accounting_coherence.notna().sum()),source_future_actual_used=False));print(d.groupby(['strategy','accounting_group']).size().to_string());print(json.dumps([x for x in summary if x['strategy']=='monthly' and x['era']=='SW2021' and x['metric']=='excess20'],default=str))
if __name__=='__main__':run()
