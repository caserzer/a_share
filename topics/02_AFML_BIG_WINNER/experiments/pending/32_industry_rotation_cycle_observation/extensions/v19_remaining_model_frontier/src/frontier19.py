from pathlib import Path
import sys,json
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];E=ROOT.parent;OUT=ROOT/'outputs';V15=E/'v15_rank_separation';V16=E/'v17_precision_recall_frontier'
sys.path.insert(0,str(E/'v6_economic_diffusion/src'))
from context6 import sha,js
CACHE=Path('/home/xiaolv/.cache/a_share/ep32/forecast_v5')
MODELS=['rank_half', 'rank_one', 'risk_prior_blend', 'pool_tree', 'rd_conditional', 'history_prior_blend', 'history_tree', 'rd_state', 'history_blend', 'context_tree', 'context_cap', 'pool_blend', 'delay_weighted_tree', 'lag12_tree', 'context_blend', 'lag24_tree', 'pool_logistic', 'static_tree', 'logistic', 'prior']
POLICIES=[(f'top_{b:g}',b,0.) for b in [.01,.025,.05,.075,.1]]+[(f'{name}_p{p:g}',b,p) for name,b in [('all',1.),('top10',.1)] for p in [.025,.05,.075,.1,.15,.2]]

def run():
 previous=json.loads((V16/'outputs/predecessors.json').read_text());m=json.loads((V16/'outputs/manifest.json').read_text())
 previous.update({str(V16/f['path']):f['sha256'] for f in m['files']});previous[str(V16/'outputs/manifest.json')]=sha(V16/'outputs/manifest.json')
 assert all(sha(p)==h for p,h in previous.items());js(OUT/'predecessors.json',previous)
 receipt=json.loads((V15/'outputs/prediction_receipt.json').read_text())
 labels=pd.read_parquet(CACHE/'stage_b_labels.parquet')
 phases=pd.read_parquet(CACHE/'daily_phases.parquet').set_index('phase_id').start_date
 js(OUT/'frozen_policy.json',dict(models=MODELS,policies=POLICIES,plan_sha256=sha(ROOT/'research_plan.md'),code_sha256=sha(__file__),labels_sha256=sha(CACHE/'stage_b_labels.parquet'),phases_sha256=sha(CACHE/'daily_phases.parquet'),target_precision=.235,target_event_recall=.4125))
 rows=[];years=[]
 for artifact in receipt['tasks']:
  assert sha(artifact['path'])==artifact['sha256']
  f=pd.read_parquet(artifact['path'],filters=[('model','in',MODELS),('date','>=',pd.Timestamp('2021-01-01')),('date','<=',pd.Timestamp('2024-09-30'))])
  f=f.merge(labels,on=['row_id','threshold','benchmark'],validate='many_to_one')
  f.loc[f.label_available_at.gt(f.date+pd.DateOffset(months=24)),'y']=np.nan
  f['year']=f.date.dt.year
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
     row=dict(zip(['frequency','threshold','benchmark','model','level'],key),policy=name,year=year,
      precision=selected.groupby('date').y.mean().mean(),micro_precision=tp/nk if nk else np.nan,
      point_recall=tp/len(positive) if len(positive) else np.nan,event_recall=len(hits)/events if events else np.nan,
      positives=len(positive),events=events,detected_events=len(hits),true_alerts=int(tp),alerts=k,known_alerts=nk,
      alert_unknown_fraction=(k-nk)/k if k else np.nan,
      dates=h.date.nunique(),active_dates=h.loc[h.selected,'date'].nunique(),
      known_active_dates=selected.date.nunique(),active_date_fraction=h.loc[h.selected,'date'].nunique()/h.date.nunique(),
      median_delay_days=delay.median(),mean_delay_days=delay.mean())
     (rows if year==0 else years).append(row)
  print('scored',artifact['task'],flush=True)
 metrics=pd.DataFrame(rows);annual=pd.DataFrame(years)
 metrics.to_csv(OUT/'metrics.csv',index=False);annual.to_csv(OUT/'annual_metrics.csv',index=False)
 def summarize(frame,group):
  values=['precision','micro_precision','point_recall','event_recall','active_date_fraction','median_delay_days','mean_delay_days','alert_unknown_fraction']
  out=frame.groupby(group)[values].mean()
  out['tasks']=frame.groupby(group).size();out['precision_defined_tasks']=frame.groupby(group).precision.count()
  out['alerts']=frame.groupby(group).alerts.sum();out['known_alerts']=frame.groupby(group).known_alerts.sum()
  out['diagnostic_target_hit']=out.precision.ge(.235)&out.event_recall.ge(.4125)&out.tasks.eq(out.precision_defined_tasks)
  return out.reset_index()
 summary=summarize(metrics,['model','policy']);summary.to_csv(OUT/'summary.csv',index=False)
 summarize(metrics,['model','policy','frequency']).to_csv(OUT/'frequency_summary.csv',index=False)
 summarize(annual,['model','policy','year']).to_csv(OUT/'annual_summary.csv',index=False)
 baseline=pd.read_csv(V15/'outputs/metrics.csv').query("cohort=='fixed24' and model in @MODELS")
 orig=metrics[metrics.policy.eq('top_0.1')].merge(baseline,on=['frequency','threshold','benchmark','model','level'],validate='one_to_one')
 assert np.allclose(orig.precision,orig.top10_precision) and np.allclose(orig.point_recall,orig.top10_recall)
 ev=pd.read_csv(V15/'outputs/event_detection.csv').query("cohort=='fixed24' and model in @MODELS")
 orig=metrics[metrics.policy.eq('top_0.1')].merge(ev,on=['frequency','threshold','benchmark','model','level'],validate='one_to_one',suffixes=('_new','_old'))
 assert np.allclose(orig.event_recall_new,orig.event_recall_old)
 assert metrics.groupby(['frequency','threshold','benchmark','model','level']).events.nunique().eq(1).all()
 assert all(sha(p)==h for p,h in previous.items())
 js(OUT/'validation.json',dict(status='PASS',checks=['all predecessor hashes unchanged','all source prediction hashes verified','all original alerts reconstructed exactly','original precision reproduced','original point recall reproduced','original event recall reproduced','event denominator invariant across policies'],models=len(MODELS),policies=len(POLICIES),task_rows=len(metrics),future_labels_never_used_for_selection=True))
 print(summary.sort_values('precision',ascending=False).query('event_recall>=.4125').to_string(index=False),flush=True)
 print('target hits',int(summary.diagnostic_target_hit.sum()),flush=True)

if __name__=='__main__':run()
