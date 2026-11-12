import json,hashlib
from pathlib import Path
import numpy as np,pandas as pd
R=Path(__file__).resolve().parents[1];O=R/'p59';O.mkdir(exist_ok=True);assert not (O/'receipt.json').exists()
f=R/'p30/training_panel.parquet';mf=Path('/home/xiaolv/.cache/a_share/ep32/forecast_v5/CSI_ALL.parquet');cols=['era','industry_code','date','day_i','eligible']+[f'new_{x}{h}' for h in [63,126,252] for x in ['return','end','win']]
p=pd.read_parquet(f,columns=cols);p=p[p.eligible & p.date.ge('2023-01-01')];m=pd.read_parquet(mf).close.sort_index();daily=[];checks=0
for h in [63,126,252]:
 y=p[f'new_win{h}'];g=p[y.notna()].copy();entry=m.iloc[g.day_i.to_numpy(int)+1].to_numpy();br=g[f'new_end{h}'].map(m).to_numpy()/entry-1;ret=g[f'new_return{h}'].to_numpy();joint=(ret>0)&(ret>br);assert np.array_equal(joint.astype(float),g[f'new_win{h}']);checks+=len(g)
 g['nonpositive']=(ret<=0).astype(float);g['positive_not_excess']=((ret>0)&(ret<=br)).astype(float);g['success']=joint.astype(float);g['relative_only']=((ret<=0)&(ret>br)).astype(float);g['market_negative']=(br<0).astype(float)
 a=g.groupby('date')[['nonpositive','positive_not_excess','success','relative_only','market_negative']].mean();a['known']=g.groupby('date').size();a['total']=p.groupby('date').size();a['horizon']=h;assert np.allclose(a[['nonpositive','positive_not_excess','success']].sum(axis=1),1);daily.append(a.reset_index())
d=pd.concat(daily);d.to_csv(O/'daily.csv',index=False)
a=d.groupby(['horizon',d.date.dt.year.rename('year')]).agg(dates=('date','size'),known=('known','sum'),total=('total','sum'),success=('success','mean'),nonpositive=('nonpositive','mean'),positive_not_excess=('positive_not_excess','mean'),relative_only=('relative_only','mean'),market_negative=('market_negative','mean'));a['nonpositive_share_of_failures']=a.nonpositive/(1-a.success);a.to_csv(O/'annual.csv')
# Preserve all unknown rows, including fully immature dates absent from outcome means.
u=[]
for h in [63,126,252]:
 for year,g in p.groupby(p.date.dt.year):u.append(dict(horizon=h,year=year,total=len(g),known=int(g[f'new_win{h}'].notna().sum()),unknown=int(g[f'new_win{h}'].isna().sum()),all_dates=g.date.nunique()))
pd.DataFrame(u).to_csv(O/'unknown.csv',index=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();inputs=[f,mf,R/'P59_market_scarcity_plan.md',Path(__file__),R.parent/'configs/pool_metric_v1.json']
(O/'receipt.json').write_text(json.dumps(dict(status='PASS',joint_label_recomputations=checks,inputs={str(x):sha(x) for x in inputs},outputs={x.name:sha(x) for x in O.glob('*.csv')}),indent=2)+'\n');print(a.loc[126].to_string())
