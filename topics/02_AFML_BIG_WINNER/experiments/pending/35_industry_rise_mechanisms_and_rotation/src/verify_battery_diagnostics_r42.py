"""Independently reconstruct ranks, labels, and calendar splits."""
import pandas as pd
from common import *
from battery_pilot_r41 import panel

def ranks(v):
 return np.array([1+sum(w<x for w in v)+(sum(w==x for w in v)-1)/2 for x in v])

def run():
 out=ROOT/'outputs/r42';receipt=json.loads((out/'receipt.json').read_text());p=panel()
 for path,digest in receipt['inputs'].items():assert sha(Path(path))==digest
 paired=json.loads((out/'paired_observations.json').read_text());associations=json.loads((out/'associations.json').read_text());folds=json.loads((out/'classifier_gates.json').read_text());protocol=json.loads((ROOT/'protocols/r42.json').read_text())
 for a in associations:
  q=[x for x in paired if all(x[k]==a[k] for k in KEY+['horizon']) and (a['period']=='all' or x['date'].startswith(a['period']))];assert len(q)==a['n']
  for variable in ['past','future']:
   u=ranks([x['log_yoy'] for x in q]);v=ranks([x[variable] for x in q]);rho=None
   if len(q)>=3 and np.std(u)>0 and np.std(v)>0:rho=float(np.dot(u-u.mean(),v-v.mean())/np.sqrt(np.dot(u-u.mean(),u-u.mean())*np.dot(v-v.mean(),v-v.mean())))
   assert rho is None and a['rho_'+variable] is None or rho is not None and abs(rho-a['rho_'+variable])<1e-12
 for fold in folds:
  g=p.copy()
  for k in KEY:g=g[g[k].eq(fold[k])]
  h=fold['horizon'];records=[]
  for x in g.to_dict('records'):
   eligible=x['past_excess20']<=0 if fold['task']=='onset' else x['past_excess60']>0 and x['mom60']>0
   if not eligible or pd.isna(x[f'excess{h}']):continue
   if fold['task']=='onset':label=int(x[f'return{h}']>=(.05 if h==20 else .10) and x[f'excess{h}']>=(.03 if h==20 else .05))
   else:
    if pd.isna(x[f'rel_trough{h}']):continue
    label=int(x[f'rel_trough{h}']<=(-.08 if h==20 else -.12))
   records.append((x['date'],x[f'maturity{h}'],label))
  start=pd.Timestamp(fold['year'],1,1);calstart=pd.Timestamp(fold['year']-1,7,1)
  tr=[x for x in records if x[0]<calstart and x[1]<calstart];ca=[x for x in records if calstart<=x[0]<start and x[1]<start]
  for name,rows in [('train',tr),('cal',ca)]:
   assert [x[0].isoformat() for x in rows]==fold[name+'_dates']
   assert len(rows)==fold[name+'_rows'] and sum(x[2] for x in rows)==fold[name+'_positive']
   assert min(sum(x[2] for x in rows),len(rows)-sum(x[2] for x in rows))==fold[name+'_each_class']
  assert fold['failed_gates']==[k for k,v in protocol['gates'].items() if fold[k]<v]
  assert fold['qualified']==(len(fold['failed_gates'])==0)
 js(out/'verification.json',dict(status='PASS',associations_checked=len(associations),folds_checked=len(folds),independent_label_and_date_split=True,scope='rank correlation arithmetic and frozen-framework compatibility; no predictive validation'))
 print('R42 VERIFIED',len(associations),'associations',len(folds),'classifier folds')

if __name__=='__main__':run()
