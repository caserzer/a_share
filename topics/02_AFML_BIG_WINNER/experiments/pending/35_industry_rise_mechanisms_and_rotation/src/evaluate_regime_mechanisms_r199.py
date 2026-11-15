"""Distinguish regime effects from mechanism increments on paired dates."""
from common import *
import pandas as pd
PAIRS={'market_style':[('FSD','FS'),('FSM','FS'),('FSMD','FSM')],'size_diffusion':[('FD','F'),('FS','F'),('FDS','FS')],'financing':[('FSE','FS')]}
def run():
 out=ROOT/'outputs/r199';d=pd.read_csv(out/'date_metrics.csv',parse_dates=['date']);summaries=[]
 keys=['family','era','level','task','horizon']
 for key,g in d.groupby(keys):
  ident=dict(zip(keys,key));methods=list(g.method.unique())
  comparisons=[((m,a),(m,b),'regime') for m in methods for a,b in [('state','base'),('interaction','base'),('interaction','state')]]+[((a,v),(b,v),'mechanism') for a,b in PAIRS[ident['family']] for v in ['base','state','interaction']]
  periods=[('all',g)]+[(f'year:{y}',g[g.date.dt.year==y]) for y in sorted(g.date.dt.year.unique())]+[(f'state:{s}',g[g.regime==s]) for s in sorted(g.regime.unique())]
  for period,z in periods:
   for metric in ['utility','negative_mse'] if ident['task']=='return' else ['utility']:
    w=z.pivot(index='date',columns=['method','variant'],values=metric)
    for a,b,kind in comparisons:
     if a not in w or b not in w:continue
     q=w[[a,b]].dropna();delta=q[a]-q[b]
     summaries.append(dict(ident,period=period,metric='ic' if metric=='utility' and ident['task']=='return' else 'mse_reduction' if ident['task']=='return' else 'brier_reduction',kind=kind,first='/'.join(a),second='/'.join(b),dates=len(q),delta=delta.mean(),positive_dates=int(delta.gt(0).sum())))
 s=pd.DataFrame(summaries);s.to_csv(out/'paired_comparisons.csv',index=False)
 pred=pd.read_parquet(out/'predictions.parquet');ledger=pd.DataFrame(json.loads((out/'fold_ledger.json').read_text()));checks=[]
 locations={'market_style':('outputs/r135','r55','r56'),'size_diffusion':('outputs/r142/evaluation/outputs','r31','r32'),'financing':('outputs/r143/evaluation/outputs','r46','r47')}
 for family,(root,ret,clf) in locations.items():
  for taskset,loc in [(['return'],ret),(['onset','reversal'],clf)]:
   old=pd.read_parquet(ROOT/root/loc/'predictions.parquet')
   if 'task' not in old:old['task']='return'
   original=old.rename(columns={'prediction':'old_prediction'})
   new=pred[pred.family.eq(family)&pred.task.isin(taskset)&pred.variant.eq('base')];keys=KEY+['date','method','task','horizon','year']
   q=new.merge(original[keys+['old_prediction']],on=keys,validate='one_to_one')
   fk=['era','level','method','task','horizon','year'];valid=ledger[ledger.family.eq(family)&ledger.removed_fit_unknown_state.eq(0)&ledger.status.eq('fit')][fk].drop_duplicates()
   same=q.merge(valid,on=fk,validate='many_to_one');err=float((same.prediction-same.old_prediction).abs().max()) if len(same) else None
   if len(same):assert err<1e-10
   checks.append(dict(family=family,tasks=taskset,original_rows=len(old),new_rows=len(new),paired_rows=len(q),unchanged_training_rows=len(same),max_control_error=err,source=str(ROOT/root/loc/'predictions.parquet'),source_sha256=sha(ROOT/root/loc/'predictions.parquet')))
 js(out/'control_verification.json',dict(status='PASS',checks=checks,boundary='Original control equality tested only when state filter removes no training rows; state-filtered early fits are matched new comparisons'))
 print(s[(s.period=='all')&(s.horizon==20)&(s.kind=='regime')&s['first'].str.endswith('/interaction')&s.second.str.endswith('/base')].groupby(['family','task','metric']).agg(groups=('delta','size'),positive=('delta',lambda x:int(x.gt(0).sum())),median=('delta','median')).to_string())
if __name__=='__main__':run()
