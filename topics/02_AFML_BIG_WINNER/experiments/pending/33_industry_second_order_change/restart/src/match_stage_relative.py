import json,sys
from pathlib import Path
import pandas as pd,numpy as np
from scipy.optimize import linear_sum_assignment
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import ID,sha,calendar_dates,block_ci
OUT=EP/'restart/p04';OUT.mkdir(exist_ok=True)
source=EP/'restart/p03/selected_features.parquet';prior=json.loads((EP/'restart/p03/selection_seal.json').read_text());assert sha(source)==prior['features_sha256']
p=pd.read_parquet(source).reset_index(drop=True);p['age_days']=(p.date-p.candidate_low_date).dt.days
u=p[p.early&p.state_direction.eq(-1)];v=u[u.age_days.gt(0)]
rows=[]
for date,g in v.groupby('date'):
 a=g[g.relative_up].sort_values(ID);b=g[~g.relative_up].sort_values(ID)
 if not len(a) or not len(b):continue
 age=np.abs(a.age_days.to_numpy()[:,None]-b.age_days.to_numpy());gain=np.abs(a.state_drawup.to_numpy()[:,None]-b.state_drawup.to_numpy());valid=(age<=7)&(gain<=.02+1e-12)
 penalty=10*(min(len(a),len(b))+1);cost=np.where(valid,age/7+gain/.02,penalty)
 ii,jj=linear_sum_assignment(cost)
 for i,j in zip(ii,jj):
  if not valid[i,j]:continue
  x=a.iloc[i];y=b.iloc[j];rows.append(dict(date=date,left=int(a.index[i]),right=int(b.index[j]),age_diff=int(x.age_days-y.age_days),drawup_diff=float(x.state_drawup-y.state_drawup)))
r=pd.DataFrame(rows,columns=['date','left','right','age_diff','drawup_diff']);r.to_csv(OUT/'pairs.csv',index=False)
assert not r.left.duplicated().any() and not r.right.duplicated().any();assert r.age_diff.abs().le(7).all() and r.drawup_diff.abs().le(.02+1e-12).all()
feas=dict(early_unconfirmed=len(u),zero_age=int(u.age_days.eq(0).sum()),positive_age_lead=int(v.relative_up.sum()),positive_age_lag=int((~v.relative_up).sum()),pairs=len(r),dates=r.date.nunique(),lead_match_fraction=len(r)/v.relative_up.sum(),lag_match_fraction=len(r)/(~v.relative_up).sum(),mean_age_difference=r.age_diff.mean(),max_abs_age_difference=r.age_diff.abs().max(),mean_drawup_difference=r.drawup_diff.mean(),max_abs_drawup_difference=r.drawup_diff.abs().max())
(OUT/'selection_seal.json').write_text(json.dumps({'inputs':{str(f):sha(f) for f in [source,Path(__file__),EP/'restart/P04_matching_plan.md']},'pairs_sha256':sha(OUT/'pairs.csv'),'feasibility':feas},indent=2,default=lambda x:x.item())+'\n')
lfile=EP/'outputs/r09/evaluation_panel.parquet';l=pd.read_parquet(lfile);p=p.merge(l[ID+[f'win{h}' for h in [63,126,252]]],on=ID,how='left',validate='one_to_one')
dates=calendar_dates();summary=[];periods=[];composition=[]
for h in [63,126,252]:
 col=f'win{h}';x=p.loc[r.left,col].to_numpy();y=p.loc[r.right,col].to_numpy();r[f'left{h}']=x;r[f'right{h}']=y;r[f'delta{h}']=x-y
 z=r[r[f'delta{h}'].notna()];d=z.groupby('date')[f'delta{h}'].mean().reindex(dates);lo,hi=block_ci(d,26 if h==126 else round(h/5));summary.append(dict(horizon=h,complete_pairs=len(z),unknown_pairs=len(r)-len(z),left_known=int(np.isfinite(x).sum()),right_known=int(np.isfinite(y).sum()),paired_dates=d.notna().sum(),mean_date_delta=d.mean(),lo=lo,hi=hi,pair_weighted_delta=z[f'delta{h}'].mean(),left_win=z[f'left{h}'].mean(),right_win=z[f'right{h}'].mean(),diagnostic_sample_sufficient=len(z)>=100 and d.notna().sum()>=26,matched_left_success_week_coverage=p.loc[r.left,col].sum()/p[col].sum()))
 for year,g in d.groupby(d.index.year):periods.append(dict(horizon=h,period=str(year),dates=g.notna().sum(),delta=g.mean()))
 for name,mask in [('old_common',d.index<=pd.Timestamp('2024-09-30')),('later_seen',d.index>pd.Timestamp('2024-09-30'))]:
  g=d[mask];a,b=block_ci(g,26 if h==126 else round(h/5));periods.append(dict(horizon=h,period=name,dates=g.notna().sum(),delta=g.mean(),lo=a,hi=b))
 for name,idx in [('zero_age',u[u.age_days.eq(0)].index),('positive_age_lead',v[v.relative_up].index),('positive_age_lag',v[~v.relative_up].index)]:
  g=p.loc[idx];composition.append(dict(group=name,horizon=h,total=len(g),known=g[col].notna().sum(),win_rate=g[col].mean()))
r.to_csv(OUT/'evaluated_pairs.csv',index=False);pd.DataFrame(summary).to_csv(OUT/'summary.csv',index=False);pd.DataFrame(periods).to_csv(OUT/'periods.csv',index=False);pd.DataFrame(composition).to_csv(OUT/'composition.csv',index=False)
print(json.dumps(feas,indent=2,default=lambda x:x.item()));print(pd.DataFrame(summary).to_string(index=False));print(pd.DataFrame(periods).query('horizon==126').to_string(index=False))
