import sys,json
from pathlib import Path
import pandas as pd,numpy as np,joblib
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import sha
OUT=EP/'restart/p40';OUT.mkdir(exist_ok=True);assert not (OUT/'receipt.json').exists()
base=EP/'restart/p30';ids=['era','industry_code','date'];ef=base/'evaluated.parquet';pf=base/'predictions.parquet';tf=base/'training_panel.parquet'
q=pd.read_parquet(ef,columns=ids+['block','week_i','raw_score','rebuilt','rebuilt_edge','rebuilt_boundary']);pred=pd.read_parquet(pf,columns=ids+['fit_cutoff']);q=q.merge(pred,on=ids,validate='one_to_one')
features=joblib.load(base/'models/2023-01-01.joblib')['features'];p=pd.read_parquet(tf,columns=ids+features);q=q.merge(p,on=ids,validate='one_to_one');q=q.sort_values(['era','industry_code','block','date']).reset_index(drop=True)
q['accel']=q.rate5-q.rate20;g=q.groupby(['era','industry_code','block']);q['continuous']=q.week_i.sub(g.week_i.shift()).eq(1)
for c in ['rate20','rate60','accel','raw_score','fit_cutoff']:
 q['previous_'+c]=g[c].shift().where(q.continuous)
q['same_model']=q.fit_cutoff.eq(q.previous_fit_cutoff)&q.continuous
for c in ['rate20','rate60','accel']:
 q[c+'_increased']=q[c].gt(q['previous_'+c])&q.continuous
q['stable_score_not_increased']=q.same_model&q.raw_score.le(q.previous_raw_score)
assert q.loc[q.rebuilt_edge,'continuous'].all()
q['rollover_week']=False;q['old_model_selected']=pd.Series(pd.NA,index=q.index,dtype='boolean');q['old_model_score']=np.nan
cuts=sorted(q.fit_cutoff.unique());model_files=[];checks=0
for j,cut in enumerate(cuts):
 if j==0:continue
 date=q.loc[q.fit_cutoff.eq(cut),'date'].min();ix=q.index[q.date.eq(date)];z=q.loc[ix].copy();path=base/'models'/f'{pd.Timestamp(cuts[j-1]).date()}.joblib';nowpath=base/'models'/f'{pd.Timestamp(cut).date()}.joblib'
 old=joblib.load(path);now=joblib.load(nowpath);model_files.extend([path,nowpath]);score=old['model'].predict_proba(z[old['features']])[:,1];replay=now['model'].predict_proba(z[now['features']])[:,1];assert np.allclose(replay,z.raw_score,atol=1e-12,rtol=0);checks+=len(z)
 z['score']=score;a=z.sort_values(['score','era','industry_code'],ascending=[False,True,True]);k=int(np.ceil(len(z)*.2));selected=a.index[:k]
 assert int(z.rebuilt.sum())==k
 q.loc[ix,'rollover_week']=True;q.loc[ix,'old_model_score']=score;q.loc[ix,'old_model_selected']=False;q.loc[selected,'old_model_selected']=True
q['entry_depends_on_update']=q.rebuilt_edge&q.rollover_week&q.old_model_selected.eq(False).fillna(False)
e=q[q.rebuilt_edge].copy();e.to_parquet(OUT/'entry_diagnostics.parquet',index=False);q[q.rollover_week].to_parquet(OUT/'rollover_counterfactual.parquet',index=False)
rows=[]
for year in ['ALL',2023,2024,2025,2026]:
 z=e if year=='ALL' else e[e.date.dt.year.eq(year)];allq=q if year=='ALL' else q[q.date.dt.year.eq(year)]
 rows.append(dict(year=year,entries=len(z),observation_dates=allq.date.nunique(),mean_new_entries_per_week=len(z)/allq.date.nunique(),rollover_entries=int(z.rollover_week.sum()),update_dependent_entries=int(z.entry_depends_on_update.sum()),rate20_increased=int(z.rate20_increased.sum()),rate60_increased=int(z.rate60_increased.sum()),accel_increased=int(z.accel_increased.sum()),none_increased=int((~z[['rate20_increased','rate60_increased','accel_increased']].any(axis=1)).sum()),stable_model_entries=int(z.same_model.sum()),stable_score_not_increased=int(z.stable_score_not_increased.sum())))
r=pd.DataFrame(rows);r.to_csv(OUT/'summary.csv',index=False)
inputs=[ef,pf,tf,Path(__file__),EP/'restart/P40_entry_identity_plan.md']+list(set(model_files));(OUT/'receipt.json').write_text(json.dumps(dict(status='PASS',no_future_labels_read=True,current_model_replays=checks,rollover_dates=int(q.loc[q.rollover_week,'date'].nunique()),original_entries=len(e),original_boundaries=int(q.rebuilt_boundary.sum()),inputs={str(p):sha(p) for p in inputs},artifacts={p.name:sha(p) for p in OUT.iterdir() if p.is_file()}),indent=2)+'\n');print(r.to_string(index=False))
