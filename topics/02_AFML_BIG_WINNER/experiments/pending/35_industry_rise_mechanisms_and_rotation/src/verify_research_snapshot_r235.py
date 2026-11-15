from common import *
import pandas as pd

def run():
 out=ROOT/'outputs/r235';view=pd.read_parquet(out/'historical_score_view.parquet');snap=json.loads((out/'snapshot.json').read_text());expected={x['family'] for x in json.loads((ROOT/'outputs/r195/experiment_registry.json').read_text())['families']};assert {x['family'] for x in snap['families']}==expected;assert not {'y','target','maturity','excess20','excess60'}.intersection(view.columns);assert view.date.eq(pd.Timestamp(snap['as_of'])).all();checks=0;slices=0
 for rnd,g in view.groupby('source_round'):
  source=pd.read_parquet(ROOT/f"outputs/r{rnd}/{'scores' if rnd==202 else 'predictions'}.parquet",filters=[('date','==',pd.Timestamp(snap['as_of']))]);template=json.loads(g.model_slice.iloc[0]);keys=list(template);lookup={k:z for k,z in source.groupby(keys,dropna=False)}
  for identity,z in g.groupby('model_slice'):
   model=json.loads(identity);raw=lookup[tuple(model[k] for k in keys)];assert len(raw)==len(z);sort=['industry_code']+(['event_id'] if 'event_id' in raw else []);a=raw.sort_values(sort);b=z.sort_values(sort);assert a.industry_code.tolist()==b.industry_code.tolist();value=a['score' if rnd==202 else 'prediction'].to_numpy();assert np.allclose(value,b.research_score);ranking=np.sign(a.slope.to_numpy())*a.score.to_numpy() if rnd==204 and model['variant']!='fixed' else a.score.to_numpy() if rnd==204 else value;assert np.allclose(ranking,b.ranking_value)
   unique,counts=np.unique(ranking,return_counts=True);rankmap={v:1+int(counts[unique>v].sum())+(int(counts[unique==v][0])-1)/2 for v in unique};assert np.allclose([rankmap[v] for v in ranking],b.display_rank);assert b.slice_count.eq(len(b)).all();checks+=len(b);slices+=1
 for family in snap['families']:
  assert len(view[view.family_registry.eq(family['family'])])==family['exact_date_rows'];assert not family['adoption']
  if family['status']=='no_exact_date_output':
   absent=pd.read_parquet(ROOT/family['source'],filters=[('date','==',pd.Timestamp(snap['as_of']))])
   if family['family']=='eps_expectations':absent=absent[absent.family.str.startswith('eps_')]
   if family['family']=='financing':absent=absent[absent.family.eq('financing')]
   assert absent.empty
 # Exact same-date partition of R196; no duplication across core/L1/rank directory entries.
 source=pd.read_parquet(ROOT/'outputs/r196/predictions.parquet',filters=[('date','==',pd.Timestamp(snap['as_of']))]);assert len(source)==len(view[view.source_round.eq(196)])
 js(out/'independent_verification.json',dict(status='PASS',families=16,score_rows=checks,model_slices=slices,scope='Every displayed source score and rank independently reconstructed, all family counts, exact date/no outcomes and R196 exhaustive partition',code_sha256=sha(__file__)));print(checks,slices)
if __name__=='__main__':run()
