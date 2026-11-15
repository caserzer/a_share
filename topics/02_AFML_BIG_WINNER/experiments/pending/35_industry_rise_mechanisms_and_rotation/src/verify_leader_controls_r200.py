from common import *
import pandas as pd

def run():
 out=ROOT/'outputs/r200';p=pd.read_parquet(out/'predictions.parquet');ledger=pd.DataFrame(json.loads((out/'fold_ledger.json').read_text()));checks=[]
 for branch in ['leader','catchup']:
  rel='outputs/r145/evaluation/outputs/'+('r109/predictions.parquet' if branch=='leader' else 'r111/paired_predictions.parquet');old=pd.read_parquet(ROOT/rel)
  if branch=='catchup':
   old=old.melt(id_vars=KEY+['date','cohort','year'],value_vars=['controls','with_leader'],var_name='method',value_name='prediction');old['task']='catchup';old['horizon']=0
  for cohort in ['main80','strict100']:
   family=branch+'_'+cohort;a=old[old.cohort.eq(cohort)];b=p[p.family.eq(family)&p.variant.eq('base')];keys=KEY+['date','year','method','task','horizon'];q=a.merge(b,on=keys,suffixes=('_old','_new'),validate='one_to_one');assert len(q)==len(a)==len(b)
   fk=['era','level','method','task','horizon','year'];unchanged=ledger[ledger.family.eq(family)&ledger.status.eq('fit')&ledger.removed_fit_unknown_state.eq(0)][fk].drop_duplicates();v=q.merge(unchanged,on=fk,validate='many_to_one');err=float((v.prediction_old-v.prediction_new).abs().max()) if len(v) else None
   if len(v):assert err<1e-10
   checks.append(dict(family=family,paired_rows=len(q),unchanged_train_rows=len(v),max_error=err,original_sha256=sha(ROOT/rel)))
 js(out/'control_verification.json',dict(status='PASS',checks=checks,code_sha256=sha(__file__)));print(checks)
if __name__=='__main__':run()
