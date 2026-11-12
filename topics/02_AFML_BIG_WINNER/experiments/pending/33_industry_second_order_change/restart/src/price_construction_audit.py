import sys,json
from pathlib import Path
import numpy as np,pandas as pd
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import KEY,sha
OUT=EP/'restart/p22';OUT.mkdir(exist_ok=True);assert not (OUT/'receipt.json').exists()
owner=EP.parent/'32_industry_rotation_cycle_observation/extensions/v5_rdagent_onset_forecast/src/data.py';identityfile=owner.parents[2]/'v4_adaptive_6_18_months/outputs/audits/inputs.json';identity=json.loads(identityfile.read_text());release=Path(identity['price_release']);assign=Path('/home/xiaolv/.cache/a_share/ep32/extension_v2/products/assignments.parquet');raw=Path('/home/xiaolv/.cache/a_share/ep32/forecast_v5/daily_industries.parquet')
d=pd.read_parquet(raw);d=d[d.level.eq('L3')].sort_values(KEY+['date']);g=d.groupby(KEY)
d['previous_date']=g.date.shift();d['previous_nav']=g.nav.shift();d['previous_coverage']=g.coverage.shift();d['return']=d.nav/d.previous_nav-1;d['coverage_change']=d.coverage-d.previous_coverage
d['within_month']=d.date.dt.to_period('M').eq(d.previous_date.dt.to_period('M'))
u=d[d.date.ge('2023-01-01')&d['return'].notna()&d.coverage.notna()&d.previous_coverage.notna()].copy();v=u[u.within_month].copy();changed=v.coverage_change.abs().gt(1e-12)
prevalence=dict(daily_rows=len(u),within_month_rows=len(v),coverage_changed=int(changed.sum()),changed_fraction=float(changed.mean()),changed_median_abs_return=float(v.loc[changed,'return'].abs().median()),stable_median_abs_return=float(v.loc[~changed,'return'].abs().median()))
(OUT/'prevalence.json').write_text(json.dumps(prevalence,indent=2)+'\n')
selection=pd.concat([v[changed].assign(magnitude=lambda x:x.coverage_change.abs()).sort_values(['magnitude','date','industry_code'],ascending=[False,True,True]).head(20).assign(sample='largest_coverage_change'),v[~changed].sample(20,random_state=3322).assign(sample='random_stable')],ignore_index=True)
selection.to_parquet(OUT/'selected_checks.parquet',index=False)
j=pd.read_parquet(assign);j=j[j.level.eq('L3')];prices={};reads={};rows=[]
def getprice(sid):
 if sid not in prices:
  rel='normalized/prices_qfq/'+sid+'.parquet';path=release/rel;h=sha(path);assert h==identity['daily_read_files'][rel];reads[str(path)]=h;prices[sid]=pd.read_parquet(path,columns=['date','qfq_close','close_conflict','factor_chain_id']).set_index('date')
 return prices[sid]
for _,r in selection.iterrows():
 cohort=j[j.era.eq(r.era)&j.industry_code.eq(r.industry_code)&j.month.eq(r.date.to_period('M')-1)];assert len(cohort)==r.members
 assert r.membership_asof<r.date and r.membership_asof.to_period('M')==r.date.to_period('M')-1
 values=[]
 for sid in cohort.security_id:
  b=getprice(sid).reindex([r.membership_asof,r.previous_date,r.date]);p=pd.to_numeric(b.qfq_close).where(b.close_conflict.eq(False)&pd.to_numeric(b.qfq_close).gt(0));chain=b.factor_chain_id.fillna('__MISSING__');ok=chain.eq(chain.iloc[0])&chain.ne('__MISSING__');rel=(p/p.iloc[0]-1).where(ok);values.append([rel.iloc[1],rel.iloc[2]])
 arr=np.asarray(values);den=len(cohort)+int(cohort.unresolved.max());cov=np.isfinite(arr).sum(axis=0)/den;assert np.allclose(cov,[r.previous_coverage,r.coverage]);means=np.nanmean(arr,axis=0);original=(1+means[1])/(1+means[0])-1;assert np.isclose(original,r['return'],atol=1e-10)
 common=np.isfinite(arr).all(axis=1);cm=arr[common].mean(axis=0);fixed=(1+cm[1])/(1+cm[0])-1
 rows.append(dict(era=r.era,industry_code=r.industry_code,date=r.date,sample=r['sample'],members=r.members,coverage_change=r.coverage_change,original_return=original,common_return=fixed,composition_difference=original-fixed,common_members=int(common.sum()),changed_availability=int(np.logical_xor(np.isfinite(arr[:,0]),np.isfinite(arr[:,1])).sum())))
a=pd.DataFrame(rows);a.to_csv(OUT/'reconstruction.csv',index=False)
(OUT/'receipt.json').write_text(json.dumps(dict(inputs={str(p):sha(p) for p in [owner,identityfile,assign,raw,Path(__file__),EP/'restart/P22_price_construction_audit_plan.md']},price_reads=reads,selection_sha256=sha(OUT/'selected_checks.parquet'),status='PASS',reconstruction_checks=len(a),no_future_outcomes_read=True),indent=2)+'\n')
print(json.dumps(prevalence));print(a.groupby('sample').agg(n=('date','size'),max_abs_composition=('composition_difference',lambda x:x.abs().max()),median_abs_composition=('composition_difference',lambda x:x.abs().median()),max_availability_change=('changed_availability','max')).to_string());print(a.sort_values('composition_difference',key=abs,ascending=False).head(5).to_string(index=False))
