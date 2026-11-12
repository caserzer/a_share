import json,hashlib
from pathlib import Path
import numpy as np,pandas as pd
R=Path(__file__).resolve().parents[1];O=R/'p63';O.mkdir(exist_ok=True);assert not (O/'receipt.json').exists()
f=R/'p29/daily_industries.parquet';vf=Path('/home/xiaolv/.cache/a_share/ep32/forecast_v5/daily_industries.parquet');pf=R/'p30/training_panel.parquet';ids=['era','industry_code','date']
d=pd.read_parquet(f,columns=ids+['block','nav','day_i']);v=pd.read_parquet(vf,columns=ids+['level','volume_ratio']);v=v[v.level.eq('L3')];d=d.merge(v[ids+['volume_ratio']],on=ids,how='left',validate='one_to_one');p=pd.read_parquet(pf,columns=ids+['eligible','history_proxy60']);p=p[p.eligible];pieces=[];groups={}
for key,g in d[d.nav.notna()].groupby(['era','industry_code','block']):
 g=g.sort_values('date').copy();ret=np.log(g.nav).diff();vol=g.volume_ratio;roll=lambda x:x.rolling(60,min_periods=60)
 up=ret.gt(0);down=ret.lt(0);nu=roll(up.astype(float)).sum();nd=roll(down.astype(float)).sum();valid=roll(ret).count().eq(60)&roll(vol).count().eq(60)&nu.ge(15)&nd.ge(15)&g.day_i.diff(60).eq(60)
 g['directional_volume60']=(roll(vol.where(up,0)).sum()/nu-roll(vol.where(down,0)).sum()/nd).where(valid);g['volume_mean60']=roll(vol).mean().where(valid);g['volume_std60']=roll(vol).std().where(valid);g['up_fraction60']=(nu/60).where(valid);g['up_days']=nu;g['down_days']=nd;g['volume_days']=vol.rolling(60,min_periods=1).count();g['ret']=ret
 cols=['directional_volume60','volume_mean60','volume_std60','up_fraction60','up_days','down_days','volume_days'];pieces.append(g[ids+cols]);groups[key]=g
q=p.merge(pd.concat(pieces),on=ids,how='left',validate='one_to_one');q['supported']=q.directional_volume60.notna();q.to_parquet(O/'features.parquet',index=False)
q.groupby(q.date.dt.year).agg(rows=('date','size'),supported=('supported','sum'),dates=('date','nunique')).to_csv(O/'coverage.csv');q.groupby([q.date.dt.year,'history_proxy60']).supported.agg(['count','sum','mean']).to_csv(O/'proxy_coverage.csv');q[q.supported][cols[:4]].describe().to_csv(O/'distribution.csv')
lookup=d.set_index(ids);checks=0
for _,r in q[q.supported].sample(120,random_state=3363).iterrows():
 b=lookup.loc[(r.era,r.industry_code,r.date),'block'];g=groups[(r.era,r.industry_code,b)];w=g[g.date.le(r.date)].tail(60);assert len(w)==60 and w.day_i.diff().iloc[1:].eq(1).all();a=w.loc[w.ret.gt(0),'volume_ratio'].mean()-w.loc[w.ret.lt(0),'volume_ratio'].mean();assert np.isclose(a,r.directional_volume60);assert np.isclose(w.volume_ratio.mean(),r.volume_mean60);checks+=1
sha=lambda x:hashlib.sha256(x.read_bytes()).hexdigest();src=R.parent.parent/'32_industry_rotation_cycle_observation/extensions/v5_rdagent_onset_forecast/src/data.py';inputs=[f,vf,pf,src,R/'P63_directional_volume_feasibility_plan.md',Path(__file__)]
(O/'receipt.json').write_text(json.dumps(dict(status='PASS',future_labels_read=False,direct_window_checks=checks,inputs={str(x):sha(x) for x in inputs},outputs={x.name:sha(x) for x in O.iterdir() if x.is_file()}),indent=2)+'\n');print(pd.read_csv(O/'coverage.csv').to_string(index=False));print('2023+ supported',q[q.date.ge('2023-01-01')].supported.agg(['sum','count','mean']).to_dict())
