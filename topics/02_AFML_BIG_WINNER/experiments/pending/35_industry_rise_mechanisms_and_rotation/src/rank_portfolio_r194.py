from common import *
import pandas as pd
import rank_portfolio_engine_r194 as engine

def run():
 out=ROOT/'outputs/r194';out.mkdir(exist_ok=True)
 source=ROOT/'outputs/r192/predictions.parquet';p=pd.read_parquet(source);parts=[]
 for score in ['raw','rank','momentum']:
  z=p.copy();z['original_cohort']=z.cohort;z['original_method']=z.method;z['cohort']=z.original_cohort+'__'+z.original_method
  z['method']='F' if score=='raw' else z.cohort if score=='rank' else 'momentum';z['prediction']=z[score+'_score'];z['task']='return';z['excess']=z.y;parts.append(z)
 mapped=pd.concat(parts,ignore_index=True);assert len(mapped)==3*len(p)
 mapped.to_parquet(out/'mapped_predictions.parquet',index=False)
 p[['cohort','method']].drop_duplicates().assign(mapped_cohort=lambda x:x.cohort+'__'+x.method).to_csv(out/'mapping.csv',index=False)
 js(out/'mapping_receipt.json',dict(source_sha256=sha(source),output_sha256=sha(out/'mapped_predictions.parquet'),rows=len(mapped),code_sha256=sha(__file__)))
 engine.run()
 new=pd.read_csv(out/'intervals.csv');old=pd.read_csv(ROOT/'outputs/r189/intervals.csv');checks=0
 for (cohort,method),g in p.groupby(['cohort','method']):
  if cohort=='F':continue
  a=new[new.cohort.eq(cohort+'__'+method)&new.method.eq('F')];b=old[old.cohort.eq(cohort)&old.method.eq(method)]
  keys=['era','level','horizon','origin'];q=a.merge(b,on=keys,suffixes=('_new','_old'),validate='one_to_one');assert len(q)==len(a)==len(b)
  assert q.status_new.eq(q.status_old).all()
  for c in ['gross','net20','net50','turnover']:assert np.allclose(q[c+'_new'],q[c+'_old'],atol=1e-12,equal_nan=True)
  checks+=len(q)
 comparisons=[]
 for key,g in new.groupby(['era','level','cohort','horizon']):
  rank=g[g.method.eq(key[2])]
  for baseline in ['F','momentum','equal']:
   q=rank.merge(g[g.method.eq(baseline)],on=['origin'],suffixes=('_rank','_base'),validate='one_to_one');assert len(q)==len(rank)
   valid=q.status_rank.eq('valid')&q.status_base.eq('valid');v=q[valid]
   rec=dict(zip(['era','level','cohort','horizon'],key),baseline=baseline,scheduled=len(q),matched=int(valid.sum()),both_whole=bool(valid.all()))
   for c in ['gross','net20','net50','turnover']:rec['delta_'+c]=(v[c+'_rank']-v[c+'_base']).mean()
   comparisons.append(rec)
 pd.DataFrame(comparisons).to_csv(out/'all_controls.csv',index=False)
 js(out/'control_verification.json',dict(status='PASS',raw_prior_intervals_matched=checks,scope='All overlapping raw-control R189 interval status/return/turnover unchanged; all-control paired identity grid',source_sha256=sha(source),mapping_sha256=sha(out/'mapped_predictions.parquet'),all_controls_sha256=sha(out/'all_controls.csv'),code_sha256=sha(__file__)))
 print('RAW CONTROL MATCH',checks,flush=True)
if __name__=='__main__':run()
