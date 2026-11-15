"""Independent reconstruction of current fixed-score inputs, not new training."""
from pathlib import Path
import json, hashlib
import numpy as np
import pandas as pd
from scipy.stats import rankdata
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/r241'
KEY=['era','level','date','industry_code','cohort','method']
F={'mom20':1/6,'mom60':1/6,'vol20':-1/3,'dd60':1/3}
WEIGHTS={'momentum':{'mom60':1},'F':F,
 'FD':dict({k:v/2 for k,v in F.items()},breadth21=1/4,breadth63=1/4),
 'FC':dict({k:v/2 for k,v in F.items()},turn_rank504=-1/2),
 'FG':dict({k:v/2 for k,v in F.items()},pe_rank504=-1/2),
 'FDG':dict({k:v/3 for k,v in F.items()},breadth21=1/6,breadth63=1/6,pe_rank504=-1/3)}
NEEDED={'F':list(F),'FD':['breadth21','breadth63'],'FC':['turn_rank504'],'FG':['pe_rank504'],'FDG':['breadth21','breadth63','pe_rank504']}
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run():
 OUT.mkdir(exist_ok=True)
 panel=pd.read_parquet(ROOT/'outputs/r130/monthly_panel.parquet')
 actual=pd.read_parquet(ROOT/'outputs/r204/scored_panel.parquet')
 frames=[]
 for _,g in panel.loc[panel.price_ready].groupby(['era','level','date']):
  for cohort,needed in NEEDED.items():
   z=g.dropna(subset=needed)
   if len(z)<20:continue
   ranks={}
   for c in set().union(*(set(w) for w in WEIGHTS.values())):
    vals=z[c].to_numpy();valid=pd.notna(vals);v=np.full(len(z),np.nan)
    if valid.any():v[valid]=(rankdata(vals[valid],method='average')-.5)/valid.sum()-.5
    ranks[c]=v
   for method in (['momentum','F'] if cohort=='F' else ['F',cohort]):
    q=z[['era','level','date','industry_code']].copy()
    q['cohort']=cohort;q['method']=method
    q['expected']=sum(ranks[c]*w for c,w in WEIGHTS[method].items())
    frames.append(q)
 expected=pd.concat(frames,ignore_index=True)
 assert not expected.duplicated(KEY).any() and not actual.duplicated(KEY).any()
 paired=expected.merge(actual[KEY+['score']],on=KEY,how='outer',validate='one_to_one',indicator=True)
 assert paired['_merge'].eq('both').all()
 assert paired.expected.isna().equals(paired.score.isna())
 paired['absolute_error']=(paired.expected-paired.score).abs()
 assert paired.absolute_error.fillna(0).le(1e-14).all()
 summary=paired.groupby(['era','level','cohort','method']).agg(rows=('score','size'),known=('score','count'),max_error=('absolute_error','max')).reset_index()
 summary.to_csv(OUT/'score_comparison.csv',index=False)
 (OUT/'expanded_weights.json').write_text(json.dumps(WEIGHTS,indent=2)+'\n')
 inputs=['outputs/r130/monthly_panel.parquet','outputs/r204/scored_panel.parquet','src/evaluate_r01.py','src/regime_fixed_rank_r204.py','protocols/r241.json','src/audit_hierarchical_weights_r241.py']
 result={'status':'PASS','rows':len(paired),'groups':len(summary),'missing_scores':int(paired.score.isna().sum()),'max_absolute_error':float(paired.absolute_error.max()),'all_identity_keys_match':True,'adoption':False,'new_performance_claim':False,'inputs':{x:digest(ROOT/x) for x in inputs},'outputs':{x:digest(OUT/x) for x in ['score_comparison.csv','expanded_weights.json']}}
 (OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:v for k,v in result.items() if k not in ['inputs','outputs']}))
if __name__=='__main__':run()
