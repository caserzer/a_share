import json,sys
from pathlib import Path
import numpy as np,pandas as pd
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import sha
OUT=EP/'restart/p28';OUT.mkdir(exist_ok=True);assert not (OUT/'receipt.json').exists()
def mark(p,chain,present,conflict):
 anchor=p[0];base=chain[0];value=np.full(len(p),np.nan);age=np.zeros(len(p),int)
 if not np.isfinite(anchor) or anchor<=0 or base is None or conflict[0]:return value,age
 last=anchor;stale=0;broken=False;value[0]=1.
 for i in range(1,len(p)):
  if present[i]:
   stale=0
   if chain[i] is not None and chain[i]!=base:broken=True
   valid=not broken and chain[i]==base and not conflict[i] and np.isfinite(p[i]) and p[i]>0
   last=p[i] if valid else np.nan
  else:stale+=1
  if not broken and np.isfinite(last):value[i]=last/anchor;age[i]=stale
 return value,age
# Known conflict cannot be carried; chain change persists; recovery cannot revise past marks.
v,a=mark(np.array([1.,np.nan,np.nan,1.3]),['a',None,None,'a'],[True,False,False,True],[False]*4);assert np.allclose(v,[1,1,1,1.3]) and list(a)==[0,1,2,0]
v,a=mark(np.array([1.,np.nan,np.nan,1.3]),['a','a',None,'a'],[True,True,False,True],[False,True,False,False]);assert np.isnan(v[1:3]).all() and v[3]==1.3
v,a=mark(np.array([1.,2.,1.3]),['a','b','a'],[True]*3,[False]*3);assert np.isnan(v[1:]).all()
protofile=EP/'restart/p23/monthly_prototype.parquet';proto=pd.read_parquet(protofile);identityfile=EP.parent/'32_industry_rotation_cycle_observation/extensions/v4_adaptive_6_18_months/outputs/audits/inputs.json';identity=json.loads(identityfile.read_text());release=Path(identity['price_release']);assign=Path('/home/xiaolv/.cache/a_share/ep32/extension_v2/products/assignments.parquet');j=pd.read_parquet(assign);j=j[j.level.eq('L3')];cal=pd.DatetimeIndex(pd.read_parquet(release/'inputs/inputs/baseline/normalized/calendar.parquet').date).sort_values();cache={};reads={};rows=[];prefix=0
proto['month']=proto.date.dt.to_period('M')
for (era,code,month),g in proto.groupby(['era','industry_code','month']):
 cohort=j[j.era.eq(era)&j.industry_code.eq(code)&j.month.eq(month-1)];anchor=g.anchor.iloc[0];dates=pd.DatetimeIndex([anchor]).append(pd.DatetimeIndex(sorted(g.date)));vals=[];ages=[]
 for sid in cohort.security_id:
  if sid not in cache:
   rel='normalized/prices_qfq/'+sid+'.parquet';path=release/rel;h=sha(path);assert h==identity['daily_read_files'][rel];reads[str(path)]=h;cache[sid]=pd.read_parquet(path,columns=['date','qfq_close','factor_chain_id','close_conflict']).set_index('date')
  b=cache[sid].reindex(dates);p=b.qfq_close.to_numpy();chains=[x if pd.notna(x) else None for x in b.factor_chain_id];present=dates.isin(cache[sid].index);conflict=b.close_conflict.eq(True).to_numpy();valid_anchor=np.isfinite(p[0]) and p[0]>0 and chains[0] is not None and b.close_conflict.iloc[0]==False
  if not valid_anchor:continue
  v,a=mark(p,chains,present,conflict);vals.append(v);ages.append(a)
  for k in range(1,len(dates)+1):
   vv,aa=mark(p[:k],chains[:k],present[:k],conflict[:k]);assert np.allclose(vv,v[:k],equal_nan=True) and np.array_equal(aa,a[:k]);prefix+=1
 matrix=np.asarray(vals).T;age=np.asarray(ages).T;nav=np.mean(matrix,axis=1);den=len(cohort)+int(cohort.unresolved.max());eligible=len(cohort)>=5 and len(vals)/den>=.8
 if not eligible:nav[:]=np.nan
 for i,date in enumerate(dates[1:],start=1):
  stale=age[i]>0;rows.append(dict(era=era,industry_code=code,date=date,mark_nav=nav[i],stale_members=int(stale.sum()),stale_equal_weight=float(stale.mean()),max_stale_days=int(age[i].max()),held_members=len(vals)))
a=pd.DataFrame(rows).merge(proto,on=['era','industry_code','date'],validate='one_to_one',suffixes=('','_strict'));known=a.fixed_relative_nav.notna();assert np.allclose(a.loc[known,'mark_nav'],a.loc[known,'fixed_relative_nav']);assert len(a)==len(proto)
a.to_parquet(OUT/'comparison.parquet',index=False)
summary=dict(rows=len(a),strict_known=int(known.sum()),proxy_valued=int(a.mark_nav.notna().sum()),stale_days=int(a.stale_members.gt(0).sum()),max_stale_days=int(a.max_stale_days.max()),max_stale_equal_weight=float(a.stale_equal_weight.max()),stock_prefix_checks=prefix)
(OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');(OUT/'receipt.json').write_text(json.dumps(dict(status='PASS',inputs={str(f):sha(f) for f in [protofile,identityfile,assign,Path(__file__),EP/'restart/P28_stale_mark_plan.md']},price_reads=reads,synthetic_cases=3,no_outcomes=True,summary=summary),indent=2)+'\n');print(json.dumps(summary));print(a[a.industry_code.eq('857652.SI')&a.date.between('2023-04-26','2023-04-28')][['date','old_relative_nav','fixed_relative_nav','mark_nav','stale_members','max_stale_days']].to_string(index=False))
