from common import *
import pandas as pd
from financing_components_model_r262 import COMPS
from followup_r10 import exit_economics
IDS=['era','level','horizon','method','variant']
def run():
 out=ROOT/'outputs/r265';out.mkdir(exist_ok=True);p=pd.read_parquet(ROOT/'outputs/r264/actions.parquet');rows=[]
 unknown=p[p.status.ne('valid')][KEY+['date','horizon']].drop_duplicates();assert len(unknown)==1;unknown.to_csv(out/'unknown_path.csv',index=False)
 for k,g in p.groupby(IDS+['date']):
  ident=dict(zip(IDS+['date'],k));v=g[g.status.eq('valid')];u=g[g.status.ne('valid')];n=len(g);q=g.alert.mean()
  for c in [0,.002,.005]:
   cash,market=exit_economics(v.ret,v.market,c)
   for policy,gain in [('cash',cash),('market',market)]:
    selected=float((gain*v.alert).sum());random=float(q*gain.sum());rows.append(dict(ident,cost=c,policy=policy,n=n,k=int(g.alert.sum()),known=len(v),complete=len(u)==0,selection_known_conditional=selected/len(v),random_known_conditional=random/len(v),selection_constant=selected/n,random_constant=random/n,selection_unknown_coefficient=float(u.alert.sum()/n),random_unknown_coefficient=float(q*len(u)/n)))
 d=pd.DataFrame(rows);d.to_csv(out/'date_metrics.csv',index=False);summary=[];symbolic=[]
 for k,g in d.groupby(IDS+['cost','policy']):
  ident=dict(zip(IDS+['cost','policy'],k))
  for period,z in [('all',g)]+[(str(y),v) for y,v in g.groupby(g.date.dt.year)]:
   for scope,v in [('known_paths',z),('complete_dates',z[z.complete])]:
    summary.append(dict(ident,period=period,scope=scope,dates=len(v),model_gain=v.selection_known_conditional.mean(),random_gain=v.random_known_conditional.mean(),model_minus_random=(v.selection_known_conditional-v.random_known_conditional).mean()))
  a=(g.selection_constant-g.random_constant).mean();b=(g.selection_unknown_coefficient-g.random_unknown_coefficient).mean();symbolic.append(dict(ident,kind='model_minus_random',new=ident['method']+'/'+ident['variant'],reference='uniform_K_of_N',constant=a,unknown_coefficient=b,break_even_unknown_gain=-a/b if b else np.nan,missing_cancels=b==0))
 for (era,level,h,c,policy),g in d.groupby(['era','level','horizon','cost','policy']):
  pairs=[(a,v,b,v) for a,b in COMPS for v in ['base','state','interaction']]+[(m,v,m,'base') for m in g.method.unique() for v in ['state','interaction']]
  for a,av,b,bv in pairs:
   z=g[g.method.eq(a)&g.variant.eq(av)].merge(g[g.method.eq(b)&g.variant.eq(bv)],on='date',suffixes=('_a','_b'),validate='one_to_one');aa=(z.selection_constant_a-z.selection_constant_b).mean();bb=(z.selection_unknown_coefficient_a-z.selection_unknown_coefficient_b).mean();symbolic.append(dict(era=era,level=level,horizon=h,cost=c,policy=policy,kind='model_pair',new=a+'/'+av,reference=b+'/'+bv,constant=aa,unknown_coefficient=bb,break_even_unknown_gain=-aa/bb if bb else np.nan,missing_cancels=bb==0))
 pd.DataFrame(summary).to_csv(out/'summary.csv',index=False);pd.DataFrame(symbolic).to_csv(out/'missing_sensitivity.csv',index=False);js(out/'receipt.json',dict(status='PASS',dates=p.date.nunique(),unknown_unique=len(unknown),summary_rows=len(summary),symbolic_rows=len(symbolic),inputs={x:sha(ROOT/x) for x in ['outputs/r264/actions.parquet','protocols/r265.json','src/financing_random_r265.py','src/followup_r10.py']},adoption=False));print('DONE',len(rows),len(summary),len(symbolic))
if __name__=='__main__':run()
