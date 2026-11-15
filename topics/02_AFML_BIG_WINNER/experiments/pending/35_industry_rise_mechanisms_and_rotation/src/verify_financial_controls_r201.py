from common import *
import pandas as pd

def run():
 out=ROOT/'outputs/r201';p=pd.read_parquet(out/'predictions.parquet');l=pd.DataFrame(json.loads((out/'fold_ledger.json').read_text()));checks=[]
 for branch,rel,methods in [('separate','r122/paired_predictions.parquet',['controls','with_financial']),('common','r123/predictions.parquet',['controls','notice_model','update_model'])]:
  path=ROOT/'outputs/r146/evaluation/outputs'/rel;old=pd.read_parquet(path)
  for clock in ['notice','update'] if branch=='separate' else ['common']:
   a=old[old.clock.eq(clock)] if branch=='separate' else old
   for cohort in ['main80','strict100']:
    family=clock+'_'+cohort;a1=a[a.cohort.eq(cohort)];a1=a1.melt(id_vars=KEY+['date','year','horizon'],value_vars=methods,var_name='method',value_name='prediction');b=p[p.family.eq(family)&p.variant.eq('base')];keys=KEY+['date','year','horizon','method'];q=a1.merge(b,on=keys,validate='one_to_one',suffixes=('_old','_new'));assert len(q)==len(a1)==len(b)
    if len(q):
     assert l[l.family.eq(family)&l.status.eq('fit')].removed_fit_unknown_state.eq(0).all();err=float((q.prediction_old-q.prediction_new).abs().max());assert err<1e-12
    else:err=None
    checks.append(dict(family=family,rows=len(q),max_error=err,source_sha256=sha(path)))
 # Preserve each original scheduled fold, including no-test populations.
 ledger=l.drop_duplicates(['family','era','level','task','horizon','year']);assert len(ledger)==980
 js(out/'control_verification.json',dict(status='PASS',original_controls=checks,unique_scheduled_folds=len(ledger),eligible=int(ledger.status.eq('fit').sum()),skipped=int(ledger.status.eq('skip').sum()),code_sha256=sha(__file__)))
 print(checks)
if __name__=='__main__':run()
