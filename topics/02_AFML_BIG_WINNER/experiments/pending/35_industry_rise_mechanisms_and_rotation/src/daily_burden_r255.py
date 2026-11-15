from common import *
import pandas as pd

G=['era','level','date']
def run():
 out=ROOT/'outputs/r255';a=pd.read_parquet(ROOT/'outputs/r253/alerts.parquet');a=a[a.strategy.eq('daily_cooldown20')].copy()
 dates=pd.read_parquet(ROOT/'outputs/r253/scores.parquet',columns=G).drop_duplicates().sort_values(G)
 events=pd.read_csv(ROOT/'outputs/r155/evaluation/outputs/r09/confirmation_events.csv',parse_dates=['date'])
 counts=a.groupby(G+['variant']).size().unstack('variant',fill_value=0);counts=dates.merge(counts.reset_index(),on=G,how='left').fillna({'base':0,'state':0,'interaction':0})
 capacity=[];assigned=[];matches=[]
 for variant in ['state','interaction']:
  c=counts.copy();c['K']=c[['base',variant]].min(axis=1).astype(int);c['comparison']=variant;capacity.append(c)
  for side in ['base',variant]:
   z=a[a.variant.eq(side)].merge(c[G+['K']],on=G,validate='many_to_one').sort_values(G+['score','industry_code'],ascending=[True,True,True,False,True])
   z['N']=z.groupby(G).score.transform('size');z['q']=z.K/z.N;z['retained']=z.groupby(G).cumcount()<z.K;z['comparison']=variant;assigned.append(z)
   look={k:g for k,g in z.groupby(KEY+['block'])}
   for e in events.itertuples():
    g=look.get((e.era,e.level,e.industry_code,e.block));w=g[g.day_i.between(e.day_i-20,e.day_i-1)] if g is not None else pd.DataFrame()
    assert len(w)<=1,'cooldown implies <=1 alert in 20-session window'
    known=bool(e.evaluable);present=len(w)==1
    matches.append(dict(era=e.era,level=e.level,industry_code=e.industry_code,block=e.block,date=e.date,comparison=variant,side=side,evaluable=known,original_hit=known and present,retained_hit=known and present and bool(w.iloc[0].retained),expected_hit=float(w.iloc[0].q) if known and present else (0. if known else np.nan)))
 c=pd.concat(capacity);z=pd.concat(assigned);h=pd.DataFrame(matches)
 c.to_csv(out/'date_capacity.csv',index=False);z.to_parquet(out/'alert_assignment.parquet',index=False);h.to_parquet(out/'event_expectations.parquet',index=False)
 rows=[]
 for scope in ['pooled','annual']:
  for (era,level,comparison),cg in c.groupby(['era','level','comparison']):
   years=[None] if scope=='pooled' else sorted(cg.date.dt.year.unique())
   for year in years:
    cc=cg if year is None else cg[cg.date.dt.year.eq(year)]
    for side in ['base',comparison]:
     aa=z[z.era.eq(era)&z.level.eq(level)&z.comparison.eq(comparison)&z.variant.eq(side)]
     hh=h[h.era.eq(era)&h.level.eq(level)&h.comparison.eq(comparison)&h.side.eq(side)]
     if year is not None:aa=aa[aa.date.dt.year.eq(year)];hh=hh[hh.date.dt.year.eq(year)]
     v=hh[hh.evaluable];kept=aa[aa.retained]
     rec=dict(scope=scope,year=year,era=era,level=level,comparison=comparison,side=side,dates=len(cc),zero_capacity_dates=int(cc.K.eq(0).sum()),original_alerts=len(aa),retained_alerts=len(kept),events=len(v),left_censored=int((~hh.evaluable).sum()),original_hits=int(v.original_hit.sum()),retained_hits=int(v.retained_hit.sum()),expected_hits=v.expected_hit.sum(),recall=v.retained_hit.mean(),expected_recall=v.expected_hit.mean(),known_positive=int(kept.y.eq(1).sum()),known_negative=int(kept.y.eq(0).sum()),unknown=int(kept.y.isna().sum()),expected_positive=aa.loc[aa.y.eq(1),'q'].sum(),expected_negative=aa.loc[aa.y.eq(0),'q'].sum(),expected_unknown=aa.loc[aa.y.isna(),'q'].sum())
     assert len(kept)==cc.K.sum() and np.isclose(aa.q.sum(),cc.K.sum())
     rec['precision']=kept.y.mean();den=rec['expected_positive']+rec['expected_negative'];rec['ratio_expected_positive_known']=rec['expected_positive']/den if den else np.nan
     rows.append(rec)
 summary=pd.DataFrame(rows);summary.to_csv(out/'summary.csv',index=False)
 pooled=summary[summary.scope.eq('pooled')];paired=pooled[pooled.side.ne('base')].merge(pooled[pooled.side.eq('base')],on=['era','level','comparison'],suffixes=('','_base'))
 for metric in ['recall','expected_recall','precision']:paired[metric+'_delta']=paired[metric]-paired[metric+'_base']
 paired.to_csv(out/'paired_summary.csv',index=False)
 js(out/'receipt.json',dict(status='PASS',inputs={p:sha(ROOT/p) for p in json.loads((ROOT/'protocols/r255.json').read_text())['inputs']},protocol_sha256=sha(ROOT/'protocols/r255.json'),code_sha256=sha(__file__),capacity_rows=len(c),assigned_rows=len(z),event_rows=len(h),adoption=False))
 print(summary[summary.scope.eq('pooled')][['era','level','comparison','side','zero_capacity_dates','retained_alerts','events','recall','expected_recall','precision']].to_string(index=False))
if __name__=='__main__':run()
