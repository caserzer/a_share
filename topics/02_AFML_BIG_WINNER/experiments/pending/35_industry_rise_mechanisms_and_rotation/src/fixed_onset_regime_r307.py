from common import *
import pandas as pd
from joint_alert_value_r306 import M
K=KEY+['date'];G=['era','level','strategy'];V=['base','state','interaction']
def run():
 out=ROOT/'outputs/r307';out.mkdir(exist_ok=True);p=json.loads((ROOT/'protocols/r307.json').read_text());a=pd.read_parquet(ROOT/p['inputs'][0]);a=a[a.variant.eq('base')].drop(columns=['variant','joint_alert']);assert not a.duplicated(K+['strategy']).any();alerts=pd.read_parquet(ROOT/p['inputs'][2],columns=K+['strategy','variant'])
 for v in V:
  selected=alerts[alerts.variant.eq(v)].drop(columns='variant').assign(**{'alert_'+v:True});a=a.merge(selected,on=K+['strategy'],how='left',validate='one_to_one');a['alert_'+v]=a['alert_'+v].eq(True)
 a.to_parquet(out/'fixed_observations.parquet',index=False);rows=[]
 for key,g in a.groupby(G+['date']):
  common=bool(g.complete_path.all() and all(0<g['alert_'+v].sum()<len(g) for v in V))
  for v in V:
   t=g[g['alert_'+v]];c=g[~g['alert_'+v]];valid=bool(len(t) and len(c) and g.complete_path.all());row=dict(zip(G+['date'],key),variant=v,cohort=len(g),alerted=len(t),unalerted=len(c),unknown=int((~g.complete_path).sum()),variant_supported=valid,common_supported=common)
   for m in M:row[m+'_contrast']=t[m].mean()-c[m].mean() if valid else np.nan
   rows.append(row)
 d=pd.DataFrame(rows);d.to_parquet(out/'date_contrasts.parquet',index=False)
 # Base estimates must exactly reproduce prior round before imposing three-way support.
 old=pd.read_parquet(ROOT/'outputs/r306/date_contrasts.parquet');old=old[old.variant.eq('base')];check=d[d.variant.eq('base')].merge(old,on=G+['date'],validate='one_to_one');assert check.variant_supported.eq(check.primary).all()
 for m in M:assert np.allclose(check[m+'_contrast'],check[m+'_difference'],equal_nan=True,atol=1e-12)
 common=d[d.common_supported];b=common[common.variant.eq('base')];paired=common[~common.variant.eq('base')].merge(b,on=G+['date'],suffixes=('','_base'),validate='many_to_one')
 for m in M:paired[m+'_increment']=paired[m+'_contrast']-paired[m+'_contrast_base']
 paired.to_parquet(out/'paired_increments.parquet',index=False);summaries=[]
 for key,g in d.groupby(G):
  for variant in ['state','interaction']:
   pp=paired[paired.variant.eq(variant)]
   for k,val in zip(G,key):pp=pp[pp[k].eq(val)]
   for period,z in [('all',g)]+[(str(y),s) for y,s in g.groupby(g.date.dt.year)]:
    q=pp if period=='all' else pp[pp.date.dt.year.eq(int(period))];months=q.date.dt.to_period('M').nunique();years=q.date.dt.year.nunique();row=dict(zip(G,key),variant=variant,period=period,total_dates=z.date.nunique(),common_dates=len(q),months=months,years=years,stability_eligible=months>=24 and years>=3)
    for m in M:row[m+'_increment']=q[m+'_increment'].mean()
    summaries.append(row)
 summary=pd.DataFrame(summaries);summary.to_csv(out/'summary.csv',index=False);full=summary[summary.period.eq('all')];result=dict(status='PASS',fixed_alert_rows=len(a),unique_origins=len(a[K].drop_duplicates()),unknown_rows=int((~a.complete_path).sum()),date_variant_records=len(d),common_dates=int(d[d.variant.eq('base')].common_supported.sum()),paired_increments=len(paired),comparison_groups=len(full),groups_with_support=int(full.common_dates.gt(0).sum()),higher_absolute_separation=int(full.worst_absolute_shortfall_increment.gt(0).sum()),higher_relative_separation=int(full.worst_relative_shortfall_increment.gt(0).sum()),higher_reversal_hit_separation=int(full.reversal_hit_increment.gt(0).sum()),stability_eligible=int(full.stability_eligible.sum()),adoption=False,new_models=0)
 js(out/'result.json',result);reads=p['inputs']+['protocols/r307.json','src/joint_alert_value_r306.py',str(Path(__file__).relative_to(ROOT))];js(out/'receipt.json',dict(inputs={x:sha(ROOT/x) for x in reads},outputs={x.name:sha(x) for x in out.iterdir() if x.name!='receipt.json'}));print(json.dumps(result,indent=2));print(full[['era','level','strategy','variant','common_dates','worst_absolute_shortfall_increment','terminal_return_increment']].to_string(index=False))
if __name__=='__main__':run()
