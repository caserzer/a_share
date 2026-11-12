import sys,json
from pathlib import Path
import pandas as pd,numpy as np
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import sha
OUT=EP/'restart/p51';OUT.mkdir(exist_ok=True);assert not (OUT/'receipt.json').exists()
f=EP/'restart/p50/daily.csv';cf=EP/'restart/p50/comparisons.csv';d=pd.read_csv(f,parse_dates=['date']);axis=pd.DatetimeIndex(sorted(d.date.unique()));a=d[d.horizon.eq(126)].pivot(index='date',columns='method',values='win').reindex(axis);original=pd.read_csv(cf);rows=[];summary=[]
for control in ['B','S','Z','momentum']:
 delta=a.P-a[control];block=np.arange(len(axis))//26;n=int(delta.notna().sum());mean=delta.mean();o=original[(original.horizon==126)&original.control.eq(control)].iloc[0];assert np.isclose(mean,o.delta)
 parts=[]
 for k in sorted(set(block)):
  mask=block==k;z=delta[mask];nk=int(z.notna().sum());contribution=z.sum()/n;rest=delta[~mask];leave=rest.mean() if nk else np.nan
  if nk:assert np.isclose(leave,(delta.sum()-z.sum())/(n-nk))
  row=dict(control=control,block=int(k),first=str(z.index.min().date()),last=str(z.index.max().date()),observation_dates=len(z),mature_dates=nk,delta=z.mean(),contribution_to_full_mean=contribution,leave_block_out_mean=leave)
  rows.append(row);parts.append(row)
 assert np.isclose(sum(r['contribution_to_full_mean'] for r in parts),mean)
 valid=[r for r in parts if r['mature_dates']];positive=sum(r['mature_dates']*max(r['delta'],0) for r in valid);largest=max((r['mature_dates']*max(r['delta'],0) for r in valid),default=0)
 summary.append(dict(control=control,mature_dates=n,full_mean=mean,blocks_with_results=len(valid),positive_blocks=sum(r['delta']>0 for r in valid),negative_blocks=sum(r['delta']<0 for r in valid),leave_out_min=min(r['leave_block_out_mean'] for r in valid),leave_out_max=max(r['leave_block_out_mean'] for r in valid),largest_positive_block_share=largest/positive if positive else np.nan))
pd.DataFrame(rows).to_csv(OUT/'blocks.csv',index=False);pd.DataFrame(summary).to_csv(OUT/'summary.csv',index=False)
inputs=[f,cf,Path(__file__),EP/'restart/P51_temporal_support_plan.md'];(OUT/'receipt.json').write_text(json.dumps(dict(status='PASS',observation_dates=len(axis),block_observation_weeks=26,independent_cycles_not_estimated=True,checks=['P50 mean reconciliation','sum of contributions','leave block out identity'],inputs={str(p):sha(p) for p in inputs},artifacts={p.name:sha(p) for p in OUT.iterdir() if p.is_file()}),indent=2)+'\n');print(pd.DataFrame(rows).query('control=="B"').to_string(index=False));print(pd.DataFrame(summary).to_string(index=False))
