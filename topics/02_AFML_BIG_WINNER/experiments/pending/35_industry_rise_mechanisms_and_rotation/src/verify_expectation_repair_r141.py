"""Check full eligible inputs and rerun independent original EPS audit."""
import pandas as pd
from common import *
import verify_r29
K=KEY+['date','fy_offset'];F=['mom20','mom60','vol20','dd60','past_excess20','past_excess60','log_members']
def run():
 out=ROOT/'outputs/r141';root=out/'evaluation';receipt=json.loads((out/'comparison.json').read_text())
 for p,h in receipt['reads'].items():assert sha(p)==h
 panel=pd.concat([pd.read_parquet(ROOT/'outputs/r130/monthly_panel.parquet'),pd.read_parquet(ROOT/'data/l1_monthly_panel.parquet')],ignore_index=True);panel['log_members']=np.log(panel.members);results=[]
 for variant in ['raw_proxy','share_context_guard']:
  cov=pd.read_parquet(ROOT/f'data/r29_{variant}_coverage.parquet');assert not cov.duplicated(K).any();q=cov.merge(panel,on=KEY+['date'],suffixes=('_coverage',''),validate='many_to_one');q=q[q.price_ready& q[F+['covered_member_median']].notna().all(axis=1)].set_index(K).sort_index();a=pd.read_parquet(out/f'{variant}_old_base.parquet').set_index(K).sort_index();b=pd.read_parquet(out/f'{variant}_new_base.parquet').set_index(K).sort_index();assert q.index.equals(b.index);cols=F+['covered_member_median','eligible','known','members_coverage','excess20','excess60','past_excess20','past_excess60','maturity20','maturity60'];cols=list(dict.fromkeys(cols));pd.testing.assert_frame_equal(q[cols],b[cols])
  b.loc[b.index.difference(a.index),['known','eligible','coverage','members_coverage']].reset_index().to_csv(out/f'{variant}_added_candidates.csv',index=False)
  # Audit all cohort counts and ranks before training, including failed populations.
  cohort=pd.read_csv(root/f'outputs/r29/{variant}/cohorts.csv');checked=0
  for row in cohort.to_dict('records'):
   g=q.reset_index();g=g[g.era.eq(row['era'])&g.level.eq(row['level'])&g.fy_offset.eq(row['fy_offset'])];g=g[g.eligible] if row['population']=='strict' else g[g.known.ge(5)&~g.eligible];g=g[g.groupby('date').date.transform('size').ge(2)];assert len(g)==row['rows'] and g.date.nunique()==row['months']
   old=a.reset_index();old=old[old.era.eq(row['era'])&old.level.eq(row['level'])&old.fy_offset.eq(row['fy_offset'])];old=old[old.eligible] if row['population']=='strict' else old[old.known.ge(5)&~old.eligible];old=old[old.groupby('date').date.transform('size').ge(2)]
   pd.testing.assert_frame_equal(old.set_index(K)[cols].sort_index(),g.set_index(K)[cols].sort_index());checked+=1
  pairs=pd.read_parquet(out/f'{variant}_prediction_pairs.parquet');assert pairs._merge.eq('both').all();assert np.allclose(pairs.prediction_old,pairs.prediction_new,atol=1e-12);assert np.allclose(pairs.target_old,pairs.target_new,equal_nan=True);assert (pairs.maturity_old.eq(pairs.maturity_new)|(pairs.maturity_old.isna()&pairs.maturity_new.isna())).all()
  results.append(dict(variant=variant,old_candidate_rows=len(a),new_candidate_rows=len(b),added_candidates=len(b.index.difference(a.index)),removed_candidates=len(a.index.difference(b.index)),cohorts_checked=checked,predictions=len(pairs)))
 verify_r29.ROOT=root;verify_r29.run()
 for row in receipt['artifacts']:
  if row['artifact']=='prediction_payload':continue
  a=ROOT/f"outputs/r29/{row['variant']}/{row['artifact']}";b=root/f"outputs/r29/{row['variant']}/{row['artifact']}";assert sha(a)==row['old_sha256'] and sha(b)==row['new_sha256'];assert row['bytes_equal']==(a.read_bytes()==b.read_bytes())
 js(out/'verification.json',dict(status='PASS',results=results,independent_model_audit_sha256=sha(root/'outputs/r29/verification.json'),verifier_sha256=sha(__file__),conclusion='Candidate coverage changes are separated from unchanged actual model cohorts; both variants retain identical model inputs, gates, coefficients, predictions and metrics; original strict/partial limits remain'))
 print('EPS REPAIR VERIFIED',results,flush=True)
if __name__=='__main__':run()
