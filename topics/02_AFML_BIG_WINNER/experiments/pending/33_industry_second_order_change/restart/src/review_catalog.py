import sys,json,hashlib
from pathlib import Path
import numpy as np,pandas as pd
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import sha
OUT=EP/'restart/p33';OUT.mkdir(exist_ok=True);assert not (OUT/'receipt.json').exists()
cf=EP/'restart/p30/catalog_status.parquet';pf=EP/'restart/p30/training_panel.parquet';sf=EP/'restart/p30/predictions.parquet';ids=['era','industry_code','date'];c=pd.read_parquet(cf)
cols=ids+['industry_name','nav','status','anchor','anchor_coverage','members','held_members','stale_members','max_stale_days','boundary_proxy','block','history60','history_proxy60','rate5','rate20','rate60','market126','vol60']
f=pd.read_parquet(pf,columns=cols).rename(columns={'status':'price_status'});q=c[ids+['raw_score']].merge(f,on=ids,how='left',validate='one_to_one');assert len(q)==len(c);assert q.industry_name.notna().all()
version='EP33_P30_B_P29_PRICE_REVIEW_ONLY';q['method_version']=version;q['price_version']='EP33_P29_STALE_MARK_PROXY';q['protocol_version']='pool_metric_v1';q['diagnostic_model_score']=q.pop('raw_score');q['diagnostic_score_percentile']=q.groupby('date').diagnostic_model_score.rank(method='average',pct=True);q['calibrated_probability']=np.nan;q['admitted']=False;q['opportunity_id']=pd.Series([None]*len(q),dtype='string')
q['observation_id']=[hashlib.sha256(f'{version}|{r.era}|{r.industry_code}|{r.date.date()}'.encode()).hexdigest()[:24] for r in q.itertuples()];q['review_status']=np.where(q.diagnostic_model_score.notna(),'OBSERVABLE_METHOD_UNVALIDATED','DATA_INSUFFICIENT')
reasons=[]
for r in q.itertuples():
 a=['METHOD_NOT_VALIDATED','PROBABILITY_NOT_ESTABLISHED','OPPORTUNITY_ID_NOT_ESTABLISHED']
 if pd.isna(r.nav):a.append('CURRENT_PRICE_UNKNOWN')
 if not r.history60:a.append('INSUFFICIENT_CONTINUOUS_60_SESSION_HISTORY')
 if r.stale_members>0:a.append('CURRENT_STALE_PRICE_PROXY')
 if r.boundary_proxy:a.append('PROXY_MONTH_TRANSITION')
 if pd.notna(r.history_proxy60) and r.history_proxy60==1:a.append('LOOKBACK_CONTAINS_PROXY')
 if pd.isna(r.diagnostic_model_score) and r.history60:a.append('MODEL_INPUT_OR_SCORE_UNAVAILABLE')
 reasons.append('|'.join(a))
q['reason_codes']=reasons;q['review_requirement']='Next complete week: refresh prices/membership; verify missing/conflict/chain flags; recompute observation. No admission until method and probability pass frozen acceptance.'
q=q.sort_values(['date','era','industry_code']);assert not q.duplicated(ids).any() and q.observation_id.is_unique;assert not q.admitted.any();assert q.calibrated_probability.isna().all();assert q.opportunity_id.isna().all();assert not any(x.startswith(('new_win','new_return','new_end','path')) for x in q.columns)
q.to_parquet(OUT/'research_observations.parquet',index=False);latest=q[q.date.eq(q.date.max())].copy();latest.to_csv(OUT/'latest_observations.csv',index=False);latest.to_json(OUT/'latest_observations.json',orient='records',force_ascii=False,date_format='iso',indent=2)
pd.DataFrame(columns=['era','industry_code','admission_date','opportunity_id','calibrated_probability','method_version']).to_csv(OUT/'approved_admissions.csv',index=False)
q.groupby(['date','review_status']).size().rename('rows').to_csv(OUT/'status_counts.csv')
# Verify every exported score is exactly its frozen source, including nulls.
z=q.merge(c[ids+['raw_score']],on=ids,validate='one_to_one');assert np.allclose(z.diagnostic_model_score,z.raw_score,equal_nan=True)
metadata=dict(purpose='Research review only; no validated high-win admission method',method_version=version,probability_available=False,admitted_count=0,rows=len(q),dates=int(q.date.nunique()),latest_date=str(q.date.max().date()),latest_rows=len(latest),latest_scored=int(latest.diagnostic_model_score.notna().sum()),latest_insufficient=int(latest.diagnostic_model_score.isna().sum()),not_live_as_of_current_date=True,no_future_outcome_columns=True)
(OUT/'metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
(OUT/'receipt.json').write_text(json.dumps(dict(status='PASS',inputs={str(f):sha(f) for f in [cf,pf,sf,EP/'configs/pool_metric_v1.json',Path(__file__),EP/'restart/P33_review_catalog_plan.md']},artifacts={f.name:sha(f) for f in OUT.glob('*') if f.is_file()},identity_exact=True,score_exact=True,admission_count=0),indent=2)+'\n');print(json.dumps(metadata,ensure_ascii=False))
