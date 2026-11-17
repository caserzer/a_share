"""Post-result feature-level accounting only; no new predictive tests."""
from e1_mapping_drift import *
def main():
 verify();verify('structure_complete');verify('analysis_complete');days,models,dictionary=load();start=pd.read_parquet(PRIVATE/PAST/'scores.parquet').signal_date.min();rows=[];condition=[];checks=[]
 for date,(g,raw) in days.items():
  if date<start:continue
  transform,model=models[str(date.to_period('Q'))];gamma,x,y,score=cell((transform,model),g,raw);_,residual,q,rank=project(x,y);parts=demean(transform.transform(raw)*model.coef_/score.std(),g.industry);res=parts-q@(q.T@parts)
  assert np.allclose(res.sum(axis=1),residual,atol=1e-10);checks.append(dict(date=str(date),check='78 residual features sum to full residual',passed=True))
  singular=np.linalg.svd(x,compute_uv=False);condition.append(dict(signal_date=date,rank=rank,n=len(g),condition_number=float(singular[0]/singular[-1])))
  alloc=res.T@residual;energy=float(residual@residual)
  for j,col in enumerate(dictionary.feature):rows.append(dict(signal_date=date,feature=col,group=dictionary.mechanism_group.iloc[j],signed_allocation=float(alloc[j]),residual_total_energy=energy,coefficient=float(model.coef_[j]),raw_effective_coefficient=float(model.coef_[j]/transform.sd[j])))
 f=pd.DataFrame(rows);write(f,'feature_residual_allocation.csv');summary=f.groupby(['feature','group']).agg(signed_allocation=('signed_allocation','sum'),residual_total_energy=('residual_total_energy','sum'),min_coefficient=('coefficient','min'),max_coefficient=('coefficient','max')).reset_index();summary['signed_share']=summary.signed_allocation/summary.residual_total_energy;assert abs(summary.signed_share.sum()-1)<1e-10;write(summary,'feature_residual_summary.csv');write(pd.DataFrame(condition),'projection_conditioning.csv')
 save_json(D/'feature_audit.json',dict(status='PASS',count=len(checks)+1,checks=checks,after_results=True,scope='accounting subdivision of pre-frozen feature groups; no per-feature future-return tests',files=record([Path(__file__),D/'feature_residual_allocation.csv',D/'feature_residual_summary.csv',D/'projection_conditioning.csv'])))
 print(summary[summary.group=='range_position'].to_string(index=False));print(pd.DataFrame(condition).condition_number.describe().to_string())
if __name__=='__main__':main()
