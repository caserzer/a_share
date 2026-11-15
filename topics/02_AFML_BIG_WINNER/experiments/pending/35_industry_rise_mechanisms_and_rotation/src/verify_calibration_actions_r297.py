from common import *
import pandas as pd
from collections import defaultdict

def run():
 out=ROOT/'outputs/r297';p=pd.read_parquet(ROOT/'outputs/r295/predictions.parquet');a=pd.read_parquet(out/'alerts.parquet');old=pd.read_parquet(ROOT/'outputs/r287/alerts.parquet');cal=pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').index.sort_values();ordinal={d:i for i,d in enumerate(cal)};ends={}
 for d in cal:
  if d.to_period('M').end_time.normalize()<=cal.max():ends[(d.year,d.month)]=d
 monthly=set(ends.values());groups=defaultdict(list)
 for row in p.itertuples():groups[(row.era,row.level,row.variant,row.date)].append(row)
 expected=set();last={};orders_changed=0
 for key,rows in sorted(groups.items(),key=lambda kv:(kv[0][3],kv[0][:3])):
  era,level,variant,date=key;ordered=sorted(rows,key=lambda x:(-x.daily_probability,x.industry_code));prior=sorted(rows,key=lambda x:(-x.monthly_probability,x.industry_code));orders_changed+=([x.industry_code for x in ordered]!=[x.industry_code for x in prior])
  for row in ordered[:(len(rows)+4)//5]:
   ident=(era,level,row.industry_code,date,variant);expected.add(ident+('daily',))
   if date in monthly:expected.add(ident+('monthly',))
   k=(era,level,variant,row.industry_code)
   if k not in last or ordinal[date]>last[k]+20:expected.add(ident+('daily_cooldown20',));last[k]=ordinal[date]
 cols=KEY+['date','variant','strategy'];actual=set(a[cols].itertuples(index=False,name=None));previous=set(old[cols].itertuples(index=False,name=None));assert actual==expected and len(actual)==len(a)
 summary=json.loads((out/'summary.json').read_text());assert len(actual^previous)==summary['changed_alert_identities'] and orders_changed==summary['changed_full_orders'];assert summary['can_reuse_original_action_results']==(actual==previous)
 rec=json.loads((out/'receipt.json').read_text())
 for name,h in rec['inputs'].items():assert sha(ROOT/name)==h
 for name,h in rec['outputs'].items():assert sha(out/name)==h
 assert rec['calendar_sha256']==sha(CACHE/'forecast_v5/CSI_ALL.parquet')
 # Preserve exact source action artifacts rather than fabricate a new backtest.
 reused={}
 if actual==previous:
  for rnd in range(287,294):
   proof=ROOT/f'outputs/r{rnd}/independent_verification.json';assert json.loads(proof.read_text())['status']=='PASS';reused[str(rnd)]=dict(proof=str(proof.relative_to(ROOT)),sha256=sha(proof))
 js(out/'action_reuse.json',dict(reuse=actual==previous,evidence=reused,scope='Same original origins, capacities, timings and cost/risk policies only; no probability-threshold or sizing claims; no new backtest'))
 js(out/'independent_verification.json',dict(status='PASS',predictions=len(p),alerts=len(actual),date_variant_groups=len(groups),changed_full_orders=orders_changed,symmetric_difference=len(actual^previous),verifier_sha256=sha(__file__),adoption=False));print('VERIFIED',len(actual),len(actual^previous),orders_changed)
if __name__=='__main__':run()
