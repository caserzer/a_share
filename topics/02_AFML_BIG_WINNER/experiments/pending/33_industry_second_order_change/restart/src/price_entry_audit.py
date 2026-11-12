import sys,json
from pathlib import Path
import pandas as pd,numpy as np
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import ID,KEY,sha,calendar_dates
from probability_pool import block_interval
OUT=EP/'restart/p06';OUT.mkdir(exist_ok=True)
prior=EP/'restart/p05';s=json.loads((prior/'prediction_seal.json').read_text());assert all(sha(prior/f)==h for f,h in s['artifacts'].items())
raw=pd.read_parquet(prior/'predictions.parquet');p=raw[raw.model.eq('B')].copy()
source=EP/'outputs/r11/coverage30/evaluation_panel.parquet';l=pd.read_parquet(source)
p=p.merge(l[ID+['day_i','week_i','rate60']],on=ID,validate='one_to_one')
stfile=EP/'restart/p03/selected_features.parquet';st=pd.read_parquet(stfile)
p=p.merge(st[ID+['candidate_low_date','state_age','state_drawup','state_eligible']],on=ID,how='left',validate='one_to_one')
p=p.sort_values(KEY+['date']).reset_index(drop=True)
p['reference_score']=p.groupby('date').raw_score.transform('mean');p['raw_gate']=p.raw_score.ge(.60)&p.raw_score.sub(p.reference_score).ge(.05)
a=p.sort_values(['date','raw_score','era','industry_code'],ascending=[True,False,True,True]);selected=a.groupby('date').cumcount().lt(np.ceil(a.groupby('date').date.transform('size')*.2));p['top20']=False;p.loc[a.index,'top20']=selected
cont=p.week_i.sub(p.groupby(KEY).week_i.shift()).eq(1)
for m in ['top20','raw_gate']:
 prev=p.groupby(KEY)[m].shift();p[m+'_edge']=p[m]&prev.eq(False)&cont;p[m+'_boundary']=p[m]&~cont;p[m+'_refit']=p[m+'_edge']&p.fit_cutoff.ne(p.groupby(KEY).fit_cutoff.shift());p[m+'_edge_cooldown126']=False
 for _,g in p[p[m+'_edge']].groupby(KEY):
  last=-100000
  for i,r in g.iterrows():
   if r.day_i-last>=126:p.loc[i,m+'_edge_cooldown126']=True;last=r.day_i
p.to_parquet(OUT/'selected_features.parquet',index=False)
inputs=[prior/'predictions.parquet',prior/'prediction_seal.json',source,stfile,Path(__file__),EP/'restart/P06_entry_plan.md',EP/'configs/pool_metric_v1.json']
(OUT/'selection_seal.json').write_text(json.dumps(dict(inputs={str(f):sha(f) for f in inputs},features_sha256=sha(OUT/'selected_features.parquet')),indent=2)+'\n')
p=p.merge(l[ID+[f'{c}{h}' for h in [63,126,252] for c in ['win','status']]],on=ID,validate='one_to_one')
dates=calendar_dates();dates=dates[dates>=p.date.min()];summary=[];annual=[];boundaries=[]
for m in ['top20','raw_gate']:
 for unit in ['edge','edge_cooldown126']:
  z=p[p[m+'_'+unit]];counts=z.groupby('date').size();ranked=p.sort_values(['date','rate60','industry_code'],ascending=[True,False,True]);mom=ranked[ranked.groupby('date').cumcount().lt(ranked.date.map(counts).fillna(0))]
  for h in [63,126,252]:
   col=f'win{h}';k=z[z[col].notna()].copy();base=p.groupby('date')[col].mean();mr=mom.groupby('date')[col].mean();k['delta']=k[col]-k.date.map(base);lo,hi=block_interval(k,dates,26 if h==126 else round(h/5))
   ident=KEY+['candidate_low_date'];knownid=z[z.candidate_low_date.notna()];repeated=knownid.duplicated(ident,keep='first').sum()
   summary.append(dict(method=m,unit=unit,horizon=h,total=len(z),known=len(k),immature=int(z[f'status{h}'].eq('IMMATURE').sum()),missing_path=int(z[f'status{h}'].eq('MISSING_PATH').sum()),win_rate=k[col].mean(),uplift=k.delta.mean(),lo=lo,hi=hi,momentum_delta=(k[col]-k.date.map(mr)).mean(),mean_raw_score=k.raw_score.mean(),absolute_score_gap=abs(k.raw_score.mean()-k[col].mean()),state_success_week_coverage=p.loc[p[m],col].sum()/p[col].sum(),boundary_total=int(p[m+'_boundary'].sum()),refit_fraction=z[m+'_refit'].mean(),median_age_days=z.state_age.median()*90,median_drawup=z.state_drawup.median(),early_fraction=z.state_eligible.eq(1).mean(),same_low_repeat_count=int(repeated),mean_new_events_per_week=len(z)/len(dates)))
   for year,g in k.groupby(k.date.dt.year):annual.append(dict(method=m,unit=unit,horizon=h,year=int(year),known=len(g),win_rate=g[col].mean(),uplift=g.delta.mean(),mean_score=g.raw_score.mean()))
 for h in [63,126,252]:
  b=p[p[m+'_boundary']];boundaries.append(dict(method=m,horizon=h,total=len(b),known=b[f'win{h}'].notna().sum(),win_rate=b[f'win{h}'].mean()))
p.to_parquet(OUT/'evaluated.parquet',index=False);pd.DataFrame(summary).to_csv(OUT/'summary.csv',index=False);pd.DataFrame(annual).to_csv(OUT/'annual.csv',index=False);pd.DataFrame(boundaries).to_csv(OUT/'boundaries.csv',index=False)
print(pd.DataFrame(summary).query('horizon==126').to_string(index=False))
