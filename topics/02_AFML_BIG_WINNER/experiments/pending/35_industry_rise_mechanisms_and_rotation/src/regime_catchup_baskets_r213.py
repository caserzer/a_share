from common import *
import pandas as pd
K=KEY+['date'];GROUP=['family','era','level','method','variant']
def run():
 out=ROOT/'outputs/r213';out.mkdir(exist_ok=True);paths=[ROOT/'outputs/r200/predictions.parquet',ROOT/'outputs/r145/evaluation/outputs/r110/member_outcomes.parquet',ROOT/'outputs/r145/evaluation/outputs/r110/industry_outcomes.parquet'];p=pd.read_parquet(paths[0]);p=p[p.task.eq('catchup')].copy();m=pd.read_parquet(paths[1]);z=pd.read_parquet(paths[2]);industry=[]
 for key,g in m.groupby(K,sort=False):
  valid=g.future_return.notna().all() and set(g.side)=={'leader','follower'} and g.entry_expected.notna().all() and g.exit_expected.notna().all()
  row=dict(zip(K,key),complete=bool(valid),members=len(g),entry=g.entry_expected.iloc[0],exit=g.exit_expected.iloc[0]);row['follower']=g[g.side.eq('follower')].future_return.mean() if valid else np.nan;row['leader']=g[g.side.eq('leader')].future_return.mean() if valid else np.nan;industry.append(row)
 ind=pd.DataFrame(industry);t=ind.merge(z[K+['catchup']],on=K,validate='one_to_one');assert np.allclose(t.follower-t.leader,t.catchup,equal_nan=True);ind.to_parquet(out/'industry_baskets.parquet',index=False)
 eq=p[p.variant.eq('base')&p.method.eq('controls')].copy();eq['method']='equal';eq['variant']='fixed';p=pd.concat([p,eq],ignore_index=True);rows=[];selected=[]
 for key,g in p.groupby(GROUP+['date']):
  ident=dict(zip(GROUP+['date'],key));chosen=g.sort_values(['prediction','industry_code'],ascending=[False,True]).head(len(g) if ident['method']=='equal' else max(1,int(np.ceil(len(g)*.2))));a=chosen.merge(ind,on=K,how='left',validate='one_to_one');n=len(a);valid=a.complete.eq(True).all();row=dict(ident,universe=len(g),selected=n,status='valid' if valid else 'unknown_selected_members',unknown=int((~a.complete.eq(True)).sum()),entry=a.entry.iloc[0],exit=a.exit.iloc[0])
  for c in a.industry_code:selected.append(dict(ident,industry_code=c,industry_weight=1/n))
  if valid:
   f=a.follower.mean();l=a.leader.mean();row.update(follower=f,leader=l,gross=f-l)
   for name,cost in [('net20',.002),('net50',.005)]:row[name]=f-l-cost*(4+f+l);row['follower_'+name]=f-cost*(2+f);row['leader_'+name]=l-cost*(2+l)
  rows.append(row)
 d=pd.DataFrame(rows);d.to_csv(out/'intervals.csv',index=False);pd.DataFrame(selected).to_parquet(out/'selected_industries.parquet',index=False)
 summary=d.groupby(GROUP).agg(scheduled=('status','size'),valid=('gross','count'),mean_gross=('gross','mean'),mean_net20=('net20','mean'),mean_net50=('net50','mean'),mean_follower=('follower','mean'),mean_leader=('leader','mean')).reset_index();summary.to_csv(out/'summary.csv',index=False)
 comparisons=[]
 for key,g in d.groupby(['family','era','level']):
  cases=[((method,v),(method,'base'),'regime') for method in ['controls','with_leader'] for v in ['state','interaction']]+[(('with_leader',v),('controls',v),'mechanism') for v in ['base','state','interaction']]+[(('with_leader',v),('equal','fixed'),'equal') for v in ['base','state','interaction']]
  for (am,av),(bm,bv),kind in cases:
   q=g[g.method.eq(am)&g.variant.eq(av)].merge(g[g.method.eq(bm)&g.variant.eq(bv)],on='date',suffixes=('_a','_b'),validate='one_to_one');assert len(q)==len(g[g.method.eq(am)&g.variant.eq(av)]);valid=q.status_a.eq('valid')&q.status_b.eq('valid');v=q[valid];row=dict(zip(['family','era','level'],key),kind=kind,first=am+'_'+av,second=bm+'_'+bv,scheduled=len(q),matched=int(valid.sum()))
   for metric in ['gross','net20','net50','follower','leader']:row['delta_'+metric]=(v[metric+'_a']-v[metric+'_b']).mean()
   comparisons.append(row)
 pd.DataFrame(comparisons).to_csv(out/'comparisons.csv',index=False)
 js(out/'verification.json',dict(status='PASS',intervals=len(d),valid=int(d.status.eq('valid').sum()),strategies=len(summary),source_target_reconstruction=len(t),adoption=False,inputs={str(x):sha(x) for x in paths+[ROOT/'protocols/r213.json',Path(__file__)]},outputs={x:sha(out/x) for x in ['industry_baskets.parquet','intervals.csv','selected_industries.parquet','summary.csv','comparisons.csv']}));print(len(d),sum(d.status.eq('valid')),len(summary));print(pd.DataFrame(comparisons).groupby(['kind','first']).delta_net50.agg(['count','median',lambda x:sum(x>0)]).to_string())
if __name__=='__main__':run()
