import sys,json
from pathlib import Path
import numpy as np,pandas as pd
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import sha
OUT=EP/'restart/p31';OUT.mkdir(exist_ok=True);assert not (OUT/'receipt.json').exists()
identityfile=EP.parent/'32_industry_rotation_cycle_observation/extensions/v4_adaptive_6_18_months/outputs/audits/inputs.json';identity=json.loads(identityfile.read_text());release=Path(identity['price_release']);assign=Path('/home/xiaolv/.cache/a_share/ep32/extension_v2/products/assignments.parquet');j=pd.read_parquet(assign);j=j[j.level.eq('L3')];cal=pd.DatetimeIndex(pd.read_parquet(release/'inputs/inputs/baseline/normalized/calendar.parquet').date).sort_values();ids=sorted(j.security_id.unique());mapping={s:i for i,s in enumerate(ids)};r21=np.full((len(cal),len(ids)),np.nan);reads={}
for i,sid in enumerate(ids):
 rel='normalized/prices_qfq/'+sid+'.parquet';path=release/rel;h=sha(path);assert h==identity['daily_read_files'][rel];reads[str(path)]=h;b=pd.read_parquet(path,columns=['date','qfq_close','close_conflict','factor_chain_id']).set_index('date').reindex(cal);p=b.qfq_close.where(b.close_conflict.eq(False)&b.qfq_close.gt(0));valid=b.factor_chain_id.notna()&b.factor_chain_id.eq(b.factor_chain_id.shift(21));r21[:,i]=(p/p.shift(21)-1).where(valid)
 if (i+1)%1000==0:print('feature sources',i+1,flush=True)
# Read only identified as-of columns from existing panel, never label columns.
source=EP/'restart/p30/training_panel.parquet';p=pd.read_parquet(source,columns=['era','industry_code','date','eligible','rate60']);p=p[p.date.ge('2023-01-01')&p.eligible].copy();p['membership_month']=p.date.dt.to_period('M')-1;groups={k:g for k,g in j.groupby(['era','industry_code','month'])};rows=[]
for _,row in p.iterrows():
 g=groups.get((row.era,row.industry_code,row.membership_month));a=dict(era=row.era,industry_code=row.industry_code,date=row.date,rate60=row.rate60,concentration=np.nan,mean21=np.nan,breadth=np.nan,valid_members=0,coverage=0.)
 if g is not None:
  ix=[mapping[s] for s in g.security_id];ret=r21[cal.get_loc(row.date),ix];ret=ret[np.isfinite(ret)];a['valid_members']=len(ret);a['coverage']=len(ret)/(len(g)+int(g.unresolved.max()))
  if len(ret)>=5 and a['coverage']>=.8:
   a['mean21']=float(ret.mean());a['breadth']=float(np.mean(ret>0));pos=ret[ret>0]
   if len(pos)>=2:
    weights=pos/pos.sum();a['concentration']=float(((weights**2).sum()-1/len(pos))/(1-1/len(pos)))
 rows.append(a)
a=pd.DataFrame(rows);a['candidate']=a.mean21.gt(0)&a.concentration.notna();a['matched']=False;a['arm']='UNKNOWN';a['cell']=''
for date,g in a[a.candidate].groupby('date'):
 g=g.sort_values(['era','industry_code']);n=len(g);g['momentum_bin']=np.minimum((g.rate60.rank(method='first')-1)*3//n,2).astype(int);g['size_bin']=g.valid_members.rank(method='first').gt(n/2).astype(int);g['breadth_bin']=g.breadth.rank(method='first').gt(n/2).astype(int)
 for key,b in g.groupby(['momentum_bin','size_bin','breadth_bin']):
  if len(b)<6:continue
  b=b.sort_values(['concentration','era','industry_code']);k=len(b)//2;a.loc[b.index,'matched']=True;a.loc[b.index,'cell']='_'.join(map(str,key));a.loc[b.index[:k],'arm']='DISPERSED';a.loc[b.index[k:],'arm']='CONCENTRATED'
a.to_parquet(OUT/'feature_panel.parquet',index=False);a.groupby(a.date.dt.year).agg(rows=('date','size'),feature_known=('concentration','count'),candidate=('candidate','sum'),matched=('matched','sum')).to_csv(OUT/'coverage.csv')
a[a.candidate][['concentration','breadth','mean21','rate60','valid_members']].corr(method='spearman').to_csv(OUT/'correlations.csv');a[a.matched].groupby(['date','cell','arm']).agg(n=('date','size'),concentration=('concentration','mean'),breadth=('breadth','mean'),members=('valid_members','mean'),rate60=('rate60','mean')).to_csv(OUT/'matched_balance.csv')
assert a.loc[a.matched,'concentration'].between(-1e-12,1+1e-12).all();balance=pd.read_csv(OUT/'matched_balance.csv');assert balance.n.ge(3).all()
# Independent direct concentration calculation for sampled observations.
for _,row in a[a.concentration.notna()].sample(30,random_state=3331).iterrows():
 g=groups[(row.era,row.industry_code,row.date.to_period('M')-1)];ret=r21[cal.get_loc(row.date),[mapping[s] for s in g.security_id]];pos=ret[np.isfinite(ret)&(ret>0)];v=(sum(float(x)**2 for x in pos)/sum(float(x) for x in pos)**2-1/len(pos))/(1-1/len(pos));assert np.isclose(v,row.concentration)
(OUT/'receipt.json').write_text(json.dumps(dict(inputs={str(f):sha(f) for f in [identityfile,assign,source,Path(__file__),EP/'restart/P31_contribution_feasibility_plan.md']},price_reads=reads,no_future_label_columns_read=True,feature_sha256=sha(OUT/'feature_panel.parquet'),feature_rows=len(a),matched_rows=int(a.matched.sum()),matched_dates=int(a.loc[a.matched,'date'].nunique()),formula_checks=30),indent=2)+'\n')
print(pd.read_csv(OUT/'coverage.csv').to_string(index=False));print(a[a.candidate][['concentration','breadth','mean21','rate60','valid_members']].corr(method='spearman').concentration.to_string())
