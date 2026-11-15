from common import *
import pandas as pd
from followup_r10 import exit_economics
from financing_components_model_r262 import COMPS
IDS=['era','level','horizon','method','variant']
def run():
 import sys
 clock=sys.argv[1];out=ROOT/'outputs/r271'/clock/'actions';out.mkdir(parents=True,exist_ok=True);p=pd.read_parquet(ROOT/f'outputs/r270/{clock}/predictions.parquet');p=p[p.task.eq('reversal')].copy();p['alert']=False
 for _,g in p.groupby(IDS+['date']):p.loc[g.sort_values(['prediction','industry_code'],ascending=[False,True]).head(int(np.ceil(len(g)*.2))).index,'alert']=True
 paths=pd.read_parquet(ROOT/'outputs/r220/paths.parquet');p=p.merge(paths,on=KEY+['date','horizon'],how='left',validate='many_to_one');assert p.status.notna().all();known=p.status.eq('valid')&p.y.notna();assert p.loc[known,'y'].eq(p.loc[known,'path_label']).all();p.to_parquet(out/'actions.parquet',index=False);rows=[]
 for key,g in p.groupby(IDS+['date']):
  ident=dict(zip(IDS+['date'],key));v=g[g.status.eq('valid')];a=v[v.alert];lab=g[g.y.notna()];tp=int((lab.alert&lab.y.eq(1)).sum());na=int(lab.alert.sum());pos=int(lab.y.eq(1).sum())
  for c in [0,.002,.005]:
   cash,market=exit_economics(v.ret,v.market,c);rows.append(dict(ident,cost=c,eligible=len(g),alerts=int(g.alert.sum()),known_paths=len(v),known_alert_paths=len(a),known_labels=len(lab),known_alert_labels=na,known_positives=pos,tp=tp,precision=tp/na if na else np.nan,recall=tp/pos if pos else np.nan,cash_policy_gain=(cash*v.alert).mean(),market_policy_gain=(market*v.alert).mean(),wrong_absolute_exit=a.ret.gt(0).mean(),wrong_relative_exit=a.ret.gt(a.market).mean(),missed_positive=a.ret.clip(lower=0).mean(),avoided_negative=(-a.ret.clip(upper=0)).mean()))
 d=pd.DataFrame(rows);d.to_csv(out/'date_metrics.csv',index=False);metrics=['precision','recall','cash_policy_gain','market_policy_gain','wrong_absolute_exit','wrong_relative_exit','missed_positive','avoided_negative'];d.groupby(IDS+['cost'])[metrics].mean().reset_index().to_csv(out/'summary.csv',index=False);pairs=[]
 for (era,level,h,c),g in d.groupby(['era','level','horizon','cost']):
  contrasts=[(a,v,b,v,'mechanism') for v in ['base','state','interaction'] for a,b in COMPS]+[(m,v,m,'base','regime') for m in g.method.unique() for v in ['state','interaction']]
  for a,av,b,bv,kind in contrasts:
   x=g[g.method.eq(a)&g.variant.eq(av)].merge(g[g.method.eq(b)&g.variant.eq(bv)],on='date',suffixes=('_a','_b'),validate='one_to_one');assert x.eligible_a.eq(x.eligible_b).all() and x.alerts_a.eq(x.alerts_b).all()
   for period,z in [('all',x)]+[(str(y),v) for y,v in x.groupby(x.date.dt.year)]:
    row=dict(era=era,level=level,horizon=h,cost=c,kind=kind,new=a+'/'+av,reference=b+'/'+bv,period=period,months=len(z))
    for met in metrics:row['delta_'+met]=(z[met+'_a']-z[met+'_b']).mean()
    pairs.append(row)
 pd.DataFrame(pairs).to_csv(out/'comparisons.csv',index=False);js(out/'receipt.json',dict(predictions=len(p),alerts=int(p.alert.sum()),unique_paths=len(p[KEY+['date','horizon']].drop_duplicates()),unknown_paths=int(p.status.ne('valid').sum()),inputs={s:sha(ROOT/s) for s in [f'outputs/r270/{clock}/predictions.parquet','outputs/r220/paths.parquet','protocols/r271.json','src/clock_actions_r271.py','src/followup_r10.py']},adoption=False));print('DONE',len(p),int(p.alert.sum()),len(pairs))
if __name__=='__main__':run()
