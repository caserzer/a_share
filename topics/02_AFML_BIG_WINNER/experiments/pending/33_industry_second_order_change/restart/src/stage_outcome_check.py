import sys,json,hashlib
from pathlib import Path
import pandas as pd,numpy as np
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R.parent/'src'))
from pool_evaluation import block_ci
O=R/'p58/outcome_check';O.mkdir(exist_ok=True);assert not (O/'receipt.json').exists()
f=R/'p58/scores.parquet';lf=R/'p05/evaluated.parquet';q=pd.read_parquet(f);old=pd.read_parquet(lf,columns=['model','sample_id','date','selected','win63','win126','win252']);assert not old.duplicated(['model','sample_id']).any()
q=q.merge(old.drop(columns=['date','selected']),on=['model','sample_id'],validate='one_to_one');axis=pd.DatetimeIndex(sorted(old.date.unique()));daily=[];summ=[];annual=[];checks=0
for h in [63,126,252]:
 label=f'win{h}'
 for model in ['B','D','S','SD']:
  for variant in (['old','replaced'] if model in ['S','SD'] else ['old']):
   if variant=='old':t=old[old.model.eq(model)];z=t[t.selected]
   else:t=q[q.model.eq(model)];z=t[t.new_selected]
   win=z.groupby('date')[label].mean().reindex(axis)
   for date,value in win.items():daily.append(dict(model=model,variant=variant,horizon=h,date=date,win=value))
   summ.append(dict(model=model,variant=variant,horizon=h,selected=len(z),known=int(z[label].notna().sum()),unknown=int(z[label].isna().sum()),win=win.mean()))
   for year,v in win.groupby(win.index.year):annual.append(dict(model=model,variant=variant,horizon=h,year=year,dates=int(v.notna().sum()),win=v.mean()))
a=pd.DataFrame(summ);original=pd.read_csv(R/'p05/summary.csv')
for _,v in a[a.variant.eq('old')].iterrows():
 b=original[(original.model==v.model)&(original.horizon==v.horizon)].iloc[0]
 assert v.selected==b.selected and v.known==b.known and np.isclose(v.win,b.date_win_rate);checks+=3
d=pd.DataFrame(daily);out=[]
for h in [63,126,252]:
 p=d[d.horizon.eq(h)].pivot(index='date',columns=['model','variant'],values='win').reindex(axis)
 for model,base in [('S','B'),('SD','D')]:
  for contrast,delta in [('replacement_effect',p[model,'replaced']-p[model,'old']),('old_increment',p[model,'old']-p[base,'old']),('replaced_increment',p[model,'replaced']-p[base,'old'])]:
   lo,hi=block_ci(delta,26 if h==126 else round(h/5));out.append(dict(model=model,base=base,contrast=contrast,horizon=h,dates=int(delta.notna().sum()),delta=delta.mean(),lo=lo,hi=hi))
a.to_csv(O/'summary.csv',index=False);d.to_csv(O/'daily.csv',index=False);pd.DataFrame(annual).to_csv(O/'annual.csv',index=False);c=pd.DataFrame(out);c.to_csv(O/'comparisons.csv',index=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();inputs=[f,lf,R/'p05/summary.csv',R/'p58/outcome_check_plan.md',Path(__file__)]
(O/'receipt.json').write_text(json.dumps(dict(status='PASS',original_statistics_reproduced=checks,axis_dates=len(axis),inputs={str(p):sha(p) for p in inputs},outputs={p.name:sha(p) for p in O.glob('*.csv')}),indent=2)+'\n');print(a.query('horizon==126').to_string(index=False));print(c.query('horizon==126').to_string(index=False));print(c.query('contrast=="replaced_increment"').to_string(index=False))
