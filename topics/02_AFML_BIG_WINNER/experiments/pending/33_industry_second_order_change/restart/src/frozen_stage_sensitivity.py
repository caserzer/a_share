import json,hashlib
from pathlib import Path
import numpy as np,pandas as pd,joblib
R=Path(__file__).resolve().parents[1];EP=R.parent;O=R/'p58';O.mkdir(exist_ok=True)
assert not (O/'receipt.json').exists()
seal=json.loads((R/'p05/prediction_seal.json').read_text());arms=seal['features'];S=[c for c in arms['S'] if c not in arms['B']];ids=['era','industry_code','date'];fullids=['era','industry_code','block','date']
f=EP/'outputs/r11/coverage30/evaluation_panel.parquet';oldf=Path('/home/xiaolv/.cache/a_share/ep32/online_v7/state_features.parquet');newf=R/'p57/rebuilt_states.parquet';pf=R/'p05/predictions.parquet'
cols=list(dict.fromkeys(fullids+['price_eligible']+arms['B']+[c for c in arms['D'] if c not in arms['B']]))
p=pd.read_parquet(f,columns=cols);p=p[p.price_eligible].copy()
s=pd.read_parquet(oldf,columns=fullids+['level','threshold']+S);s=s[s.level.eq('L3')&s.threshold.eq(.15)][fullids+S].drop_duplicates(fullids)
p=p.merge(s,on=fullids,how='left',validate='one_to_one').reset_index(drop=True);p['sample_id']=p.index
n=pd.read_parquet(newf,columns=ids+S);assert not n.duplicated(ids).any()
p=p.merge(n,on=ids,how='left',suffixes=('','_new'),validate='one_to_one').set_index('sample_id');p['replaceable']=p[[c+'_new' for c in S]].notna().all(axis=1)
raw=pd.read_parquet(pf);raw=raw[raw.model.isin(['S','SD'])];rows=[];models=[];checks=0
for (model,cut),g in raw.groupby(['model','fit_cutoff']):
 mf=R/'p05/models'/f'{cut.date()}_{model}.joblib';bundle=joblib.load(mf);models.append(mf);x=p.loc[g.sample_id,bundle['features']].copy();assert np.array_equal(p.loc[g.sample_id,'date'].values,g.date.values)
 v=bundle['model'].predict_proba(x)[:,1];assert np.allclose(v,g.raw_score,rtol=0,atol=1e-12);checks+=len(g)
 mask=p.loc[g.sample_id,'replaceable']
 for c in S:x.loc[mask,c]=p.loc[g.sample_id,c+'_new'].loc[mask]
 new=bundle['model'].predict_proba(x)[:,1];z=g.copy();z['new_score']=new;z['replaceable']=mask.to_numpy();rows.append(z)
q=pd.concat(rows,ignore_index=True);q['abs_delta']=(q.new_score-q.raw_score).abs()
for score,flag in [('raw_score','old_selected'),('new_score','new_selected')]:
 order=q.sort_values(['model','date',score,'era','industry_code'],ascending=[True,True,False,True,True]);sel=order.groupby(['model','date']).cumcount().lt(np.ceil(order.groupby(['model','date']).date.transform('size')*.2));q[flag]=sel.reindex(q.index)
q.to_parquet(O/'scores.parquet',index=False);daily=[]
for (m,d),g in q.groupby(['model','date']):
 a=g.old_selected;b=g.new_selected;assert a.sum()==b.sum()
 daily.append(dict(model=m,date=d,rows=len(g),replaceable=int(g.replaceable.sum()),selected=int(a.sum()),replaced=int((a&~b).sum()),replacement_fraction=(a&~b).sum()/a.sum(),rank_correlation=g.raw_score.corr(g.new_score,method='spearman')))
d=pd.DataFrame(daily);d.to_csv(O/'daily.csv',index=False);stats=[]
for m,g in q.groupby('model'):
 for year in ['ALL',2024,2025,2026]:
  t=g if year=='ALL' else g[g.date.dt.year.eq(year)];v=d[d.model.eq(m)];v=v if year=='ALL' else v[v.date.dt.year.eq(year)]
  stats.append(dict(model=m,year=year,rows=len(t),unreplaced=int((~t.replaceable).sum()),score_changes=int(t.abs_delta.gt(1e-12).sum()),delta_median=t.abs_delta.median(),delta_q95=t.abs_delta.quantile(.95),delta_max=t.abs_delta.max(),selected=int(v.selected.sum()),replaced=int(v.replaced.sum()),replacement_fraction=v.replaced.sum()/v.selected.sum(),mean_rank_correlation=v.rank_correlation.mean()))
a=pd.DataFrame(stats);a.to_csv(O/'summary.csv',index=False)
sha=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
inputs=[f,oldf,newf,pf,R/'p05/prediction_seal.json',R/'P58_frozen_stage_sensitivity_plan.md',Path(__file__)]+models
(O/'receipt.json').write_text(json.dumps(dict(status='PASS',prediction_replays=checks,models=len(models),future_labels_read=False,inputs={str(x):sha(x) for x in inputs},outputs={x.name:sha(x) for x in O.iterdir() if x.is_file()}),indent=2)+'\n');print(a.to_string(index=False))
