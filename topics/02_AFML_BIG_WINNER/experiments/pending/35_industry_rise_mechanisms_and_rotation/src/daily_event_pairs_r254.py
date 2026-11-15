from common import *
import pandas as pd

EVENT=KEY+['block','date','day_i','strategy']

def summarize(p):
 rows=[]
 for scope,groups in [('pooled',['era','level','strategy','variant']),('annual',['era','level','strategy','variant','event_year'])]:
  for key,g in p.groupby(groups):
   v=g[g.evaluable];shared=v[v.cell.eq('shared')];d=shared.paired_lead
   rec=dict(zip(groups,key),scope=scope,events=len(v),left_censored=int((~g.evaluable).sum()))
   for c in ['new','lost','shared','neither']:rec[c]=int(v.cell.eq(c).sum())
   rec.update(earlier=int(d.gt(0).sum()),same=int(d.eq(0).sum()),later=int(d.lt(0).sum()),median_paired_lead=d.median(),mean_paired_lead=d.mean(),recall_delta=(rec['new']-rec['lost'])/len(v) if len(v) else np.nan)
   assert sum(rec[c] for c in ['new','lost','shared','neither'])==len(v)
   assert rec['earlier']+rec['same']+rec['later']==rec['shared']
   rows.append(rec)
 return pd.DataFrame(rows)

def run():
 out=ROOT/'outputs/r254';h=pd.read_parquet(ROOT/'outputs/r253/event_hits.parquet');base=h[h.variant.eq('base')].drop(columns='variant');parts=[]
 for name in ['state','interaction']:
  v=h[h.variant.eq(name)].merge(base,on=EVENT,how='outer',suffixes=('','_base'),validate='one_to_one',indicator=True)
  assert v._merge.eq('both').all() and v.evaluable.eq(v.evaluable_base).all()
  v['cell']=np.select([v.hit&v.hit_base,v.hit&~v.hit_base,~v.hit&v.hit_base],['shared','new','lost'],default='neither');v.loc[~v.evaluable,'cell']='left_censored'
  v['paired_lead']=(v.lead_sessions-v.lead_sessions_base).where(v.cell.eq('shared'))
  v['event_year']=v.date.dt.year;parts.append(v.drop(columns='_merge'))
 p=pd.concat(parts,ignore_index=True);p.to_parquet(out/'paired_events.parquet',index=False);summary=summarize(p);summary.to_csv(out/'summary.csv',index=False)
 prior=pd.read_csv(ROOT/'outputs/r253/summary.csv')
 for x in summary[summary.scope.eq('pooled')].itertuples():
  group=prior[prior.era.eq(x.era)&prior.level.eq(x.level)&prior.strategy.eq(x.strategy)].set_index('variant')
  assert x.new-x.lost==group.loc[x.variant,'hit_events']-group.loc['base','hit_events']
  assert x.events==group.loc[x.variant,'events']==group.loc['base','events']
 js(out/'receipt.json',dict(status='PASS',pairs=len(p),summary_rows=len(summary),inputs={f:sha(ROOT/f) for f in ['outputs/r253/event_hits.parquet','outputs/r253/alerts.parquet','outputs/r253/summary.csv','protocols/r254.json']},code_sha256=sha(__file__),adoption=False))
 print(summary[(summary.scope=='pooled')&(summary.strategy=='daily_cooldown20')].to_string(index=False))
if __name__=='__main__':run()
