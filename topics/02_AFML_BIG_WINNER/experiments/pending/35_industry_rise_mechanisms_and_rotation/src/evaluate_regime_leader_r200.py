"""Distinguish regime effects from mechanism increments on paired dates."""
from common import *
import pandas as pd
PAIRS={k:[('with_leader','controls')] for k in ['leader_main80','leader_strict100','catchup_main80','catchup_strict100']}
def run():
 out=ROOT/'outputs/r200';d=pd.read_csv(out/'date_metrics.csv',parse_dates=['date']);summaries=[]
 keys=['family','era','level','task','horizon']
 for key,g in d.groupby(keys):
  ident=dict(zip(keys,key));methods=list(g.method.unique())
  comparisons=[((m,a),(m,b),'regime') for m in methods for a,b in [('state','base'),('interaction','base'),('interaction','state')]]+[((a,v),(b,v),'mechanism') for a,b in PAIRS[ident['family']] for v in ['base','state','interaction']]
  periods=[('all',g)]+[(f'year:{y}',g[g.date.dt.year==y]) for y in sorted(g.date.dt.year.unique())]+[(f'state:{s}',g[g.regime==s]) for s in sorted(g.regime.unique())]
  for period,z in periods:
   for metric in ['utility','negative_mse'] if ident['task'] in ['return','catchup'] else ['utility']:
    w=z.pivot(index='date',columns=['method','variant'],values=metric)
    for a,b,kind in comparisons:
     if a not in w or b not in w:continue
     q=w[[a,b]].dropna();delta=q[a]-q[b]
     summaries.append(dict(ident,period=period,metric='ic' if metric=='utility' and ident['task'] in ['return','catchup'] else 'mse_reduction' if ident['task'] in ['return','catchup'] else 'brier_reduction',kind=kind,first='/'.join(a),second='/'.join(b),dates=len(q),delta=delta.mean(),positive_dates=int(delta.gt(0).sum())))
 s=pd.DataFrame(summaries);s.to_csv(out/'paired_comparisons.csv',index=False)
 print(s[(s.period=='all')&s.kind.eq('regime')&s['first'].eq('with_leader/interaction')&s.second.eq('with_leader/base')].to_string(index=False))
if __name__=='__main__':run()
