from common import *
import pandas as pd

out=ROOT/'outputs/r215';mapping=pd.read_csv(out/'mapping.csv');intervals=pd.read_csv(out/'intervals.csv');summary=pd.read_csv(out/'summary.csv');pred=pd.read_parquet(out/'mapped_predictions.parquet');rows=[];risks=[];checks=0
for family in mapping.family.unique():
 pairs=[('price_plus_expectation','price_only'),('expectation_only','price_only')]
 m=mapping[mapping.family.eq(family)]
 if m.empty:continue
 for a,b in pairs:
  ac=m[m.method.eq(a)].mapped_cohort.iloc[0];bc=m[m.method.eq(b)].mapped_cohort.iloc[0]
  pa=pred[pred.cohort.eq(ac)&pred.method.eq('base')];pb=pred[pred.cohort.eq(bc)&pred.method.eq('base')];keys=KEY+['date','horizon'];q=pa.merge(pb,on=keys,how='outer',indicator=True,validate='one_to_one');assert q._merge.eq('both').all();checks+=len(q)
  for variant in ['base','state','interaction']:
   ia=intervals[intervals.cohort.eq(ac)&intervals.method.eq(variant)];ib=intervals[intervals.cohort.eq(bc)&intervals.method.eq(variant)];q=ia.merge(ib,on=['era','level','horizon','origin'],suffixes=('_a','_b'),how='outer',indicator=True,validate='one_to_one');assert q._merge.eq('both').all();assert q.entry_a.eq(q.entry_b).all() and q.exit_a.eq(q.exit_b).all()
   for key,g in q.groupby(['era','level','horizon']):
    valid=g.status_a.eq('valid')&g.status_b.eq('valid');v=g[valid];rec=dict(zip(['era','level','horizon'],key),family=family,mechanism=a,control=b,variant=variant,scheduled=len(g),matched=int(valid.sum()),both_whole=bool(valid.all()))
    for metric in ['gross','net20','net50','turnover']:rec['delta_'+metric]=(v[metric+'_a']-v[metric+'_b']).mean()
    rows.append(rec)
   sa=summary[summary.cohort.eq(ac)&summary.method.eq(variant)];sb=summary[summary.cohort.eq(bc)&summary.method.eq(variant)];q=sa.merge(sb,on=['era','level','horizon','cost'],suffixes=('_a','_b'),validate='one_to_one')
   for row in q.to_dict('records'):
    whole=bool(row['whole_path_valid_a'] and row['whole_path_valid_b']);rec={k:row[k] for k in ['era','level','horizon','cost']};rec.update(family=family,mechanism=a,control=b,variant=variant,both_whole=whole)
    for metric in ['cagr','drawdown','vol','beta','mean_turnover']:rec['delta_'+metric]=row[metric+'_a']-row[metric+'_b'] if whole else np.nan
    risks.append(rec)
pd.DataFrame(rows).to_csv(out/'mechanism_intervals.csv',index=False);pd.DataFrame(risks).to_csv(out/'mechanism_risk.csv',index=False)
q=pd.DataFrame(risks);q=q[q.both_whole];a=q[q.variant.eq('interaction')].merge(q[q.variant.eq('base')],on=['family','era','level','horizon','cost','mechanism','control'],suffixes=('_i','_b'),validate='one_to_one');a['change']=a.delta_cagr_i-a.delta_cagr_b;a.to_csv(out/'mechanism_increment_change.csv',index=False)
js(out/'mechanism_verification.json',dict(status='PASS',paired_source_rows=checks,interval_comparisons=len(rows),risk_comparisons=len(risks),scope='Exact same industry/date/horizon source universe and identical entry/exit schedules; whole-curve-only mechanism risk differences',adoption=False,code_sha256=sha(__file__),inputs={x:sha(out/x) for x in ['mapping.csv','intervals.csv','summary.csv','mapped_predictions.parquet']},outputs={x:sha(out/x) for x in ['mechanism_intervals.csv','mechanism_risk.csv','mechanism_increment_change.csv']}))
print(pd.DataFrame(risks).query("horizon==20 and cost=='net50' and both_whole").groupby(['family','variant']).delta_cagr.agg(['count','median',lambda x:sum(x>0)]).to_string())
