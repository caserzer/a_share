import sys,json
from pathlib import Path
import numpy as np,pandas as pd
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import sha
OUT=EP/'restart/p29';OUT.mkdir(exist_ok=True);assert not (OUT/'receipt.json').exists(),'sealed'
identityfile=EP.parent/'32_industry_rotation_cycle_observation/extensions/v4_adaptive_6_18_months/outputs/audits/inputs.json';identity=json.loads(identityfile.read_text());release=Path(identity['price_release']);assign=Path('/home/xiaolv/.cache/a_share/ep32/extension_v2/products/assignments.parquet');raw=Path('/home/xiaolv/.cache/a_share/ep32/forecast_v5/daily_industries.parquet');calendar=release/'inputs/inputs/baseline/normalized/calendar.parquet'
j=pd.read_parquet(assign);j=j[j.level.eq('L3')];days=pd.DatetimeIndex(pd.read_parquet(calendar).date).sort_values();months=days.to_period('M');anchors=pd.Series(np.arange(len(days)),index=months).groupby(level=0).max();ids=sorted(j.security_id.unique());sidmap={s:i for i,s in enumerate(ids)}
prices=np.full((len(days),len(ids)),np.nan);chains=np.full(prices.shape,-1,dtype=np.int16);present=np.zeros(prices.shape,dtype=bool);reads={}
for i,sid in enumerate(ids):
 rel='normalized/prices_qfq/'+sid+'.parquet';path=release/rel;h=sha(path);assert h==identity['daily_read_files'][rel];reads[str(path)]=h
 original=pd.read_parquet(path,columns=['date','qfq_close','close_conflict','factor_chain_id']).set_index('date');present[:,i]=days.isin(original.index);b=original.reindex(days)
 prices[:,i]=pd.to_numeric(b.qfq_close).where(b.close_conflict.eq(False)&b.qfq_close.gt(0));chains[:,i]=pd.factorize(b.factor_chain_id)[0]
 if (i+1)%500==0:print('verified stock partitions',i+1,'/',len(ids),flush=True)
def month_values(p,c,pr,unresolved=0):
 held=np.isfinite(p[0])&(c[0]>=0);coverage=held.sum()/(p.shape[1]+unresolved);eligible=p.shape[1]>=5 and coverage>=.8
 vals=np.full(len(p),np.nan);age=np.zeros((len(p),int(held.sum())),int)
 if not eligible:return vals,held,coverage,eligible,age
 x=p[:,held];chain=c[:,held];exists=pr[:,held];last=x[0].copy();base=chain[0];broken=np.zeros(len(last),bool);stale=np.zeros(len(last),int);vals[0]=1.
 for t in range(1,len(p)):
  seen=exists[t];broken|=seen&(chain[t]>=0)&(chain[t]!=base)
  valid=seen&~broken&np.isfinite(x[t])&(chain[t]==base)
  last=np.where(seen,np.where(valid,x[t],np.nan),last);last[broken]=np.nan
  stale=np.where(seen,0,stale+1);age[t]=np.where(np.isfinite(last),stale,0)
  if np.isfinite(last).all():vals[t]=np.mean(last/x[0])
 return vals,held,coverage,eligible,age
p=np.ones((4,5));c=np.zeros((4,5),int);pr=np.ones((4,5),bool);p[1:3,0]=np.nan;pr[1:3,0]=False
v,h,cv,ok,ages=month_values(p,c,pr);assert np.allclose(v,1) and ages[2,0]==2
pr[1,0]=True;v,*_=month_values(p,c,pr);assert np.isnan(v[1:3]).all()
p=np.ones((4,5));pr[:]=True;c[1,0]=1;v,*_=month_values(p,c,pr);assert np.isnan(v[1:]).all()
c[:]=0;p[0,4]=np.nan;p[1:,4]=100;v,h,*_=month_values(p,c,pr);assert h.sum()==4 and np.allclose(v,1)
records=[];audit=[]
for (era,code),g in j.groupby(['era','industry_code'],sort=True):
 parts=[];last_i=None;last_nav=np.nan;last_stale=False
 for month,cohort in g.groupby('month',sort=True):
  target=month+1
  if (era=='SW2014' and target>pd.Period('2021-11')) or (era=='SW2021' and target<pd.Period('2022-01')):continue
  ix=np.flatnonzero(months==target)
  if not len(ix) or month not in anchors:continue
  ai=int(anchors[month]);si=np.asarray([sidmap[s] for s in cohort.security_id]);ti=np.r_[ai,ix];p=prices[np.ix_(ti,si)];c=chains[np.ix_(ti,si)];unresolved=int(cohort.unresolved.max());v,held,cov,eligible,age=month_values(p,c,present[np.ix_(ti,si)],unresolved)
  connected=last_i==ai and np.isfinite(last_nav);scale=last_nav if connected else 1.
  if last_i!=ai:parts.append(pd.DataFrame(dict(date=[days[ai]],day_i=[ai],nav=[1. if eligible else np.nan],relative_nav=[1. if eligible else np.nan],anchor=[days[ai]],anchor_coverage=[cov],members=[len(si)],held_members=[int(held.sum())],status=['ORIGIN' if eligible else 'ANCHOR_INSUFFICIENT'],stale_members=[0],max_stale_days=[0],boundary_proxy=[False])))
  stale_count=(age>0).sum(axis=1);max_age=age.max(axis=1) if age.shape[1] else np.zeros(len(ti),int);boundary=np.zeros(len(ix),bool);boundary[0]=connected and last_stale
  status=np.where(np.isfinite(v[1:]),np.where(stale_count[1:]>0,'STALE_PROXY','OBSERVED'),'HARD_UNKNOWN') if eligible else np.repeat('ANCHOR_INSUFFICIENT',len(ix))
  parts.append(pd.DataFrame(dict(date=days[ix],day_i=ix,nav=v[1:]*scale,relative_nav=v[1:],anchor=days[ai],anchor_coverage=cov,members=len(si),held_members=int(held.sum()),status=status,stale_members=stale_count[1:],max_stale_days=max_age[1:],boundary_proxy=boundary)))
  # All original members priced through month: reproduce old mean without future selection.
  complete=np.isfinite(p).all() and (c==c[0]).all() and (c>=0).all()
  if complete and eligible:assert np.allclose(v,np.mean(p/p[0],axis=1))
  audit.append(dict(era=era,industry_code=code,month=str(target),days=len(ix),known=int(np.isfinite(v[1:]).sum()),members=len(si),held=int(held.sum()),anchor_coverage=cov,eligible=eligible,complete=bool(complete),connected=connected,stale_days=int((stale_count[1:]>0).sum()),proxy_boundary=bool(boundary[0])))
  last_i=int(ix[-1]);last_nav=float(v[-1]*scale);last_stale=bool(stale_count[-1]>0)
 if not parts:continue
 f=pd.concat(parts,ignore_index=True).sort_values('date');assert not f.date.duplicated().any();known=f.nav.notna();starts=known&(~known.shift(fill_value=False)|f.day_i.diff().ne(1));f['block']=starts.cumsum().where(known).astype('Int64');f['era']=era;f['industry_code']=code;f['level']='L3';f['industry_name']=g.industry_name.iloc[-1];records.append(f)
d=pd.concat(records,ignore_index=True);d.to_parquet(OUT/'daily_industries.parquet',index=False);pd.DataFrame(audit).to_csv(OUT/'month_audit.csv',index=False)
for _,g in d[d.nav.notna()].groupby(['era','industry_code','block']):assert np.all(np.diff(g.day_i)==1)
proto=pd.read_parquet(EP/'restart/p28/comparison.parquet');a=proto.merge(d[['era','industry_code','date','relative_nav']],on=['era','industry_code','date'],validate='one_to_one');assert len(a)==len(proto) and np.allclose(a.mark_nav,a.relative_nav,equal_nan=True)
# Preserve unknown dates and catalog denominator; report path availability without return labels.
week_s=pd.Series(days,index=days).groupby(days.to_period('W-FRI')).max();weeks=week_s[[p.end_time.normalize()<=days.max() for p in week_s.index]]
rows=[]
for _,g in d.groupby(['era','industry_code']):
 g=g.sort_values('date').copy();g['history60']=g.nav.notna()&g.block.eq(g.block.shift(60))&g.day_i.sub(g.day_i.shift(60)).eq(60)&g.status.ne('ORIGIN');g['history60']=g.history60.fillna(False);proxy=g.stale_members.gt(0)|g.boundary_proxy;g['history_proxy60']=proxy.rolling(61,min_periods=61).max()
 for h in [63,126,252]:
  g[f'calendar_mature{h}']=g.day_i+h+1<len(days);g[f'path{h}']=(g.nav.notna()&g.block.eq(g.block.shift(-h-1))&g.day_i.shift(-h-1).sub(g.day_i).eq(h+1)).fillna(False)
 for h in [63,126,252]:
  g[f'path_proxy{h}']=proxy.iloc[::-1].rolling(h+2,min_periods=h+2).max().iloc[::-1].where(g[f'path{h}']);g[f'entry_stale{h}']=g.stale_members.shift(-1).gt(0).where(g[f'path{h}']);g[f'end_stale{h}']=g.stale_members.shift(-h-1).gt(0).where(g[f'path{h}'])
 rows.append(g[g.date.isin(weeks)])
w=pd.concat(rows,ignore_index=True);w.to_parquet(OUT/'weekly_path_support.parquet',index=False)
w.groupby(w.date.dt.year).agg(catalog_rows=('date','size'),known_nav=('nav','count'),history60=('history60','sum'),path63=('path63','sum'),path126=('path126','sum'),path252=('path252','sum')).to_csv(OUT/'annual_support.csv')
old=pd.read_parquet(raw);old=old[old.level.eq('L3')].sort_values(['era','industry_code','block','date']);old['old_eligible']=old.groupby(['era','industry_code','block']).nav.shift(60).notna()&old.coverage.ge(.8)&old.members.ge(5);old=old[old.date.isin(weeks)]
a=w.merge(old[['era','industry_code','date','old_eligible']],on=['era','industry_code','date'],how='outer',validate='one_to_one',indicator=True);a['old_eligible']=a.old_eligible.fillna(False).astype(bool);a['history60']=a.history60.fillna(False).astype(bool)
a.groupby([a.date.dt.year,'old_eligible','history60'],observed=True).size().rename('rows').to_csv(OUT/'eligibility_transition.csv')
inputs=[identityfile,assign,raw,calendar,EP/'restart/p28/comparison.parquet',Path(__file__),EP/'restart/P29_stale_history_plan.md']
(OUT/'receipt.json').write_text(json.dumps(dict(status='PASS',inputs={str(p):sha(p) for p in inputs},price_reads=reads,daily_rows=len(d),prototype_rows=len(proto),complete_months=int(pd.DataFrame(audit).complete.sum()),synthetic_cases=4,continuous_blocks_verified=True,artifacts={f.name:sha(f) for f in OUT.glob('*') if f.is_file()},no_return_outcomes_computed=True),indent=2)+'\n')
print(pd.read_csv(OUT/'annual_support.csv').to_string(index=False));print('daily',len(d),'months',len(audit),'prototypes',len(proto),flush=True)
