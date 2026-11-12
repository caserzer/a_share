import sys,json
from pathlib import Path
import pandas as pd,numpy as np,joblib
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import sha,ID,calendar_dates,block_ci
OUT=EP/'restart/p05';s=json.loads((OUT/'prediction_seal.json').read_text())
assert all(sha(f)==h for f,h in s['inputs'].items());assert all(sha(OUT/f)==h for f,h in s['artifacts'].items())
raw=pd.read_parquet(OUT/'predictions.parquet');q=pd.read_parquet(OUT/'evaluated.parquet');assert not any(c.startswith(('win','end','status')) for c in raw)
p=pd.read_parquet(EP/'outputs/r11/coverage30/evaluation_panel.parquet');p=p[p.price_eligible].copy()
f=pd.read_parquet('/home/xiaolv/.cache/a_share/ep32/online_v7/state_features.parquet');f=f[f.level.eq('L3')&f.threshold.eq(.15)]
stage=[c for c in s['features']['S'] if c not in s['features']['B']];f=f[ID+stage].drop_duplicates(ID);p=p.merge(f,on=ID,how='left',validate='one_to_one').reset_index(drop=True)
assert raw.groupby(['model','sample_id']).size().eq(1).all()
replays=0
for rec in json.loads((OUT/'folds.json').read_text()):
 cut=pd.Timestamp(rec['cutoff']);tr=p[p.win126.notna()&p.end126.lt(cut)];te=p[p.date.ge(cut)&p.date.lt(cut+pd.DateOffset(months=3))]
 assert len(tr)==rec['train'] and len(te)==rec['test'];assert tr.end126.max()==pd.Timestamp(rec['max_label_end']) and tr.end126.lt(cut).all()
 for m in s['features']:
  z=raw[raw.model.eq(m)&raw.fit_cutoff.eq(cut)];assert set(z.sample_id)==set(te.index)
  bundle=joblib.load(OUT/'models'/f'{cut.date()}_{m}.joblib');subset=z.sample(min(20,len(z)),random_state=5);v=bundle['model'].predict_proba(p.loc[subset.sample_id,bundle['features']])[:,1];assert np.allclose(v,subset.raw_score,rtol=0,atol=1e-12);replays+=len(subset)
# Exact squared-error decomposition into date mean error and centered residual.
rows=[]
for (m,date),g in q[q.win126.notna()].groupby(['model','date']):
 a=g.raw_score.to_numpy();y=g.win126.to_numpy();mean_error=(a.mean()-y.mean())**2;within=np.mean(((a-a.mean())-(y-y.mean()))**2);loss=np.mean((a-y)**2);assert np.isclose(loss,mean_error+within)
 rows.append(dict(model=m,date=date,brier=loss,date_mean_error=mean_error,centered_error=within))
d=pd.DataFrame(rows);d.to_csv(OUT/'brier_decomposition_daily.csv',index=False);d.groupby('model')[['brier','date_mean_error','centered_error']].mean().to_csv(OUT/'brier_decomposition.csv')
# Same-date same-capacity momentum comparison, selected without future outcomes.
dates=calendar_dates();dates=dates[dates>=pd.Timestamp('2024-01-01')];base=q[q.model.eq('B')].merge(p[['rate60']],left_on='sample_id',right_index=True,validate='one_to_one')
k=base.groupby('date').selected.sum();a=base.sort_values(['date','rate60','industry_code'],ascending=[True,False,True]);mom=a[a.groupby('date').cumcount().lt(a.date.map(k))]
v=base[base.selected].groupby('date').win126.mean()-mom.groupby('date').win126.mean();lo,hi=block_ci(v.reindex(dates),26)
(OUT/'momentum_diagnostic.json').write_text(json.dumps(dict(status='post_primary_descriptive_check',date_win_delta=v.mean(),lo=lo,hi=hi,momentum_date_win_rate=mom.groupby('date').win126.mean().mean()),indent=2)+'\n')
(OUT/'validation.json').write_text(json.dumps(dict(status='PASS',prediction_replay_rows=replays,quarter_train_maturity_checks=12,identical_arm_population=True,selection_seal_verified=True,brier_decomposition_verified=True,efficacy_established=False),indent=2)+'\n')
print(d.groupby('model')[['brier','date_mean_error','centered_error']].mean().to_string());print(pd.read_csv(OUT/'annual.csv').query('horizon==126').to_string(index=False));print('B minus momentum',v.mean(),lo,hi)
