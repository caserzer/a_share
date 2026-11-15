from common import *
import pandas as pd
from collections import Counter
from heterogeneous_linkage_r234 import CONFIG

def run():
 out=ROOT/'outputs/r234';link=pd.read_csv(out/'model_linkage.csv');summary={x['source_round']:x for x in json.loads((out/'family_adapter_summary.json').read_text())};checked=0;total=0
 for rnd,base in CONFIG.items():
  models=json.loads((ROOT/f'outputs/r{rnd}/models.json').read_text());p=pd.read_parquet(ROOT/f'outputs/r{rnd}/predictions.parquet');keys=base+([] if 'method' in base else ['method'])+['variant'];z=p[p.variant.ne('fixed')];counts=Counter(z[keys].itertuples(index=False,name=None));expected={tuple(x[k] for k in keys) for x in models};assert set(counts)==expected;rows=link[link.source_round.eq(rnd)];assert len(rows)==len(expected)
  for row in rows.to_dict('records'):
   identity=json.loads(row['model_key']);assert row['prediction_rows']==counts[tuple(identity[k] for k in keys)];checked+=1
  assert len(p)==summary[rnd]['prediction_rows'] and len(z)==summary[rnd]['fitted_prediction_rows'];total+=len(p)
 f=pd.read_parquet(ROOT/'outputs/r202/sensitivities.parquet');s=pd.read_parquet(ROOT/'outputs/r202/scores.parquet');c=pd.read_parquet(out/'macro_origin_linkage.parquet');keys=['era','level','industry_code','row_id','date','lag','variant'];expected=set(f[keys].itertuples(index=False,name=None));assert set(c[keys].itertuples(index=False,name=None))==expected;counts=Counter(s[keys].itertuples(index=False,name=None));assert set(counts)<=expected
 for row in c.to_dict('records'):assert row['score_rows']==counts[tuple(row[k] for k in keys)]
 assert int(c.score_rows.eq(0).sum())==summary[202]['fitted_origins_without_scores'];assert len(s)==summary[202]['prediction_rows'];total+=len(s)
 js(out/'independent_verification.json',dict(status='PASS',annual_model_records=checked,macro_model_records=len(f),source_output_rows=total,scope='Independent native model key sets and source output counts; every macro scored/unscored origin',code_sha256=sha(__file__)));print(checked,len(f),total)
if __name__=='__main__':run()
