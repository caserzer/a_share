from pathlib import Path
import sys,json
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];E=ROOT.parent;OUT=ROOT/'outputs';V15=E/'v15_rank_separation';V16=E/'v16_relative_goal_decision'
sys.path.insert(0,str(E/'v6_economic_diffusion/src'))
from context6 import sha,js
CACHE=Path('/home/xiaolv/.cache/a_share/ep32/forecast_v5')
MODELS=['risk_diffusion_min__market126']
POLICIES=[(f'all_p{p:g}',1.,p) for p in [round(.1+i*.005,3) for i in range(11)]]

def run():
 parent=E/'v26_market_regime_filter'
 previous=json.loads((parent/'outputs/predecessors.json').read_text());manifest=json.loads((parent/'outputs/manifest.json').read_text())
 previous.update({str(parent/f['path']):f['sha256'] for f in manifest['files']});previous[str(parent/'outputs/manifest.json')]=sha(parent/'outputs/manifest.json')
 assert all(sha(p)==h for p,h in previous.items());js(OUT/'predecessors.json',previous)
 receipt=json.loads((parent/'outputs/prediction_receipt.json').read_text())
 assert receipt['frozen_sha256']==sha(parent/'outputs/frozen_candidates.json')
 frozen=json.loads((parent/'outputs/frozen_candidates.json').read_text())
 assert frozen['code_sha256']==sha(parent/'src/regime26.py')
 assert frozen['plan_sha256']==sha(parent/'research_plan.md')
 labels=pd.read_parquet(CACHE/'stage_b_labels.parquet')
 phases=pd.read_parquet(CACHE/'daily_phases.parquet').set_index('phase_id').start_date
 js(OUT/'frozen_policy.json',dict(models=MODELS,policies=POLICIES,plan_sha256=sha(ROOT/'research_plan.md'),code_sha256=sha(__file__),labels_sha256=sha(CACHE/'stage_b_labels.parquet'),phases_sha256=sha(CACHE/'daily_phases.parquet'),target_precision=.235,target_event_recall=.4125))
 rows=[];years=[];strata=[]
 for artifact in receipt['tasks']:
  assert sha(artifact['path'])==artifact['sha256']
  f=pd.read_parquet(artifact['path'],filters=[('model','in',MODELS),('date','>=',pd.Timestamp('2021-01-01')),('date','<=',pd.Timestamp('2024-09-30'))])
  f=f.merge(labels,on=['row_id','threshold','benchmark'],validate='many_to_one')
  f.loc[f.label_available_at.gt(f.date+pd.DateOffset(months=24)),'y']=np.nan
  f['year']=f.date.dt.year
  for key,h in f[f.y.notna()].groupby(['frequency','threshold','benchmark','model','level','diffusion_complete']):
   losses=h.assign(loss=(h.prob-h.y)**2)
   strata.append(dict(zip(['frequency','threshold','benchmark','model','level','diffusion_complete'],key),n=len(h),positives=int(h.y.sum()),brier=losses.groupby('date').loss.mean().mean()))
  for key,g in f.groupby(['frequency','threshold','benchmark','model','level'],sort=False):
   rank=g.groupby('date').prob.rank(method='first',ascending=False);size=g.groupby('date').date.transform('size')
   assert np.array_equal((rank<=np.ceil(size*.1)).to_numpy(),g.alert.to_numpy())
   for name,b,p in POLICIES:
    alert=(rank<=np.ceil(size*b)) & (g.prob.ge(p) if p else True)
    sub=g.assign(selected=alert)
    for year,h in [(0,sub)]+list(sub.groupby('year')):
     known=h[h.y.notna()]; selected=known[known.selected];positive=known[known.y.eq(1)]
     events=positive.event_or_witness_id.nunique()
     hits=positive[positive.selected].groupby('event_or_witness_id').date.min()
     delay=(hits-phases.reindex(hits.index)).dt.days
     k=int(h.selected.sum()); nk=len(selected);tp=float(selected.y.sum())
     all_selected=h[h.selected]
     daily_alerts=all_selected.groupby('date').y.agg(total='size',known='count',positive='sum')
     lower=(daily_alerts.positive/daily_alerts.total).mean()
     upper=((daily_alerts.positive+daily_alerts.total-daily_alerts.known)/daily_alerts.total).mean()
     row=dict(zip(['frequency','threshold','benchmark','model','level'],key),policy=name,year=year,
      precision_lower=lower,precision_upper=upper,brier=known.assign(loss=(known.prob-known.y)**2).groupby('date').loss.mean().mean(),precision=selected.groupby('date').y.mean().mean(),micro_precision=tp/nk if nk else np.nan,
      point_recall=tp/len(positive) if len(positive) else np.nan,event_recall=len(hits)/events if events else np.nan,
      positives=len(positive),events=events,detected_events=len(hits),true_alerts=int(tp),alerts=k,known_alerts=nk,
      alert_unknown_fraction=(k-nk)/k if k else np.nan,
      dates=h.date.nunique(),active_dates=h.loc[h.selected,'date'].nunique(),
      known_active_dates=selected.date.nunique(),active_date_fraction=h.loc[h.selected,'date'].nunique()/h.date.nunique(),
      median_delay_days=delay.median(),mean_delay_days=delay.mean())
     (rows if year==0 else years).append(row)
  print('scored',artifact['task'],flush=True)
 metrics=pd.DataFrame(rows);annual=pd.DataFrame(years)
 pd.DataFrame(strata).to_csv(OUT/'missingness_strata.csv',index=False)
 metrics.to_csv(OUT/'metrics.csv',index=False);annual.to_csv(OUT/'annual_metrics.csv',index=False)
 def summarize(frame,group):
  values=['precision_lower','precision_upper','brier','precision','micro_precision','point_recall','event_recall','active_date_fraction','median_delay_days','mean_delay_days','alert_unknown_fraction']
  out=frame.groupby(group)[values].mean()
  out['tasks']=frame.groupby(group).size();out['precision_defined_tasks']=frame.groupby(group).precision.count()
  out['alerts']=frame.groupby(group).alerts.sum();out['known_alerts']=frame.groupby(group).known_alerts.sum()
  out['diagnostic_target_hit']=out.precision.ge(.235)&out.event_recall.ge(.4125)&out.tasks.eq(out.precision_defined_tasks)
  return out.reset_index()
 summary=summarize(metrics,['model','policy']);summary.to_csv(OUT/'summary.csv',index=False)
 summarize(metrics,['model','policy','frequency']).to_csv(OUT/'frequency_summary.csv',index=False)
 summarize(annual,['model','policy','year']).to_csv(OUT/'annual_summary.csv',index=False)
 original=pd.read_csv(parent/'outputs/metrics.csv').query("model in @MODELS and policy in ['all_p0.1','all_p0.15']")
 reproduced=metrics[metrics.policy.isin(['all_p0.1','all_p0.15'])].merge(original,on=['frequency','threshold','benchmark','model','level','policy'],validate='one_to_one',suffixes=('_new','_old'))
 assert len(reproduced)==72
 for c in ['precision','point_recall','event_recall','active_date_fraction','alerts']:
  assert np.allclose(reproduced[c+'_new'],reproduced[c+'_old'],equal_nan=True)
 assert metrics.groupby(['frequency','threshold','benchmark','model','level']).events.nunique().eq(1).all()
 assert all(sha(p)==h for p,h in previous.items())
 js(OUT/'validation.json',dict(status='PASS',checks=['all predecessor hashes unchanged','all source prediction hashes verified','all original alerts reconstructed exactly','0.10 and 0.15 references reproduced in 72 tasks','endpoint point recall reproduced','endpoint event recall reproduced','event denominator invariant across policies'],models=len(MODELS),policies=len(POLICIES),task_rows=len(metrics),future_labels_never_used_for_selection=True))
 print(summary.sort_values('precision',ascending=False).query('event_recall>=.4125').to_string(index=False),flush=True)
 print('target hits',int(summary.diagnostic_target_hit.sum()),flush=True)

if __name__=='__main__':run()
