from common import *
import pandas as pd
CONFIG={197:['family','era','level','fy_offset','population','horizon','year'],198:['era','level','industry_code','horizon','year'],204:['era','level','cohort','method','horizon','year'],205:['family','era','level','target_type','horizon','year']}
def run():
 out=ROOT/'outputs/r234';out.mkdir(exist_ok=True);rows=[];summaries=[];reads=[];states=pd.read_parquet(ROOT/'outputs/r195/market_regimes.parquet').regime;reads.append(ROOT/'outputs/r195/market_regimes.parquet')
 for rnd,base in CONFIG.items():
  paths=[ROOT/f'outputs/r{rnd}/{f}' for f in ['models.json','fold_ledger.json','predictions.parquet']];reads+=paths;models=json.loads(paths[0].read_text());gate=json.loads(paths[1].read_text());p=pd.read_parquet(paths[2]);keys=base+([] if 'method' in base else ['method'])+['variant'];lookup={tuple(m[k] for k in keys):m for m in models};gates={tuple(f[k] for k in base):f for f in gate};assert len(lookup)==len(models) and len(gates)==len(gate);fixed=p[p.variant.eq('fixed')];q=p[~p.variant.eq('fixed')];assert rnd==204 or fixed.empty
  state_date=q.state_date if rnd==205 else q.date;assert q.regime.eq(state_date.map(states)).all()
  if rnd==205:assert q.state_date.lt(q.date).all()
  assert np.isfinite(q.prediction).all();seen=set()
  for key,z in q.groupby(keys):
   assert key in lookup;m=lookup[key];g=gates[tuple(m[k] for k in base)];assert g['status']=='fit';coef=np.asarray(m['coef']);n=len(m.get('columns',[0]));expected=n if m['variant']=='base' else n+3 if m['variant']=='state' else 4*n+3;assert coef.size==expected
   for field in ['coef','intercept',('scaler_mean' if rnd==197 else 'mean'),('scaler_scale' if rnd==197 else 'scale')]:assert np.isfinite(np.asarray(m[field],dtype=float)).all()
   identity=keys+[c for c in ['industry_code','date','event_id'] if c not in keys and c in z];assert not z.duplicated(identity).any();seen.add(key);rows.append(dict(source_round=rnd,model_key=json.dumps(dict(zip(keys,key)),sort_keys=True,default=lambda x:x.item()),prediction_rows=len(z),gate_status=g['status'],first_date=str(z.date.min().date()),last_date=str(z.date.max().date()),convergence='not_explicit_in_native_record',adoption=False))
  assert seen==set(lookup)
  if len(fixed):assert np.allclose(fixed.prediction,fixed.score)
  summaries.append(dict(source_round=rnd,models=len(models),prediction_rows=len(p),fitted_prediction_rows=len(q),fixed_rule_rows=len(fixed),scope='native annual/shared model linkage'))
 paths=[ROOT/f'outputs/r202/{f}.parquet' for f in ['sensitivities','fold_ledger','scores']];reads+=paths;f,g,s=[pd.read_parquet(p) for p in paths];base=['era','level','industry_code','row_id','date','lag'];mk=base+['variant'];assert not f.duplicated(mk).any() and not g.duplicated(base).any() and not s.duplicated(mk+['method']).any();joined=f.merge(g[base+['status']],on=base,how='left',validate='many_to_one');assert joined.status.eq('fit').all();assert f.regime.eq(f.date.map(states)).all();assert f.fit_last_date.lt(f.date).all()
 for row in f.to_dict('records'):
  for field in ['coef','intercept','mean','scale','design_mean','current_macro']:assert np.isfinite(np.asarray(row[field],dtype=float)).all()
  assert len(row['coef'])==({'base':2,'state':5,'interaction':11}[row['variant']])
 linked=s.merge(f[mk],on=mk,how='left',indicator=True,validate='many_to_one');assert linked._merge.eq('both').all();counts=s.groupby(mk).size().rename('score_rows').reset_index();coverage=f[mk].merge(counts,on=mk,how='left',validate='one_to_one');coverage.score_rows=coverage.score_rows.fillna(0).astype(int);coverage.to_parquet(out/'macro_origin_linkage.parquet',index=False);assert set(s.method)=={'F','F_exposure','F_macro'};assert np.isfinite(s.score).all()
 summaries.append(dict(source_round=202,models=len(f),prediction_rows=len(s),fitted_prediction_rows=int(s.method.ne('F').sum()),fixed_rule_rows=int(s.method.eq('F').sum()),fitted_origins_without_scores=int(coverage.score_rows.eq(0).sum()),scope='rolling sensitivity models; F is baseline; cross-sectional scores share20/60 horizons'))
 pd.DataFrame(rows).to_csv(out/'model_linkage.csv',index=False);js(out/'family_adapter_summary.json',summaries);js(out/'verification.json',dict(status='PASS',annual_models=len(rows),macro_models=len(f),source_output_rows=sum(x['prediction_rows'] for x in summaries),inputs={str(p):sha(p) for p in reads+[ROOT/'protocols/r234.json',Path(__file__)]},outputs={name:sha(out/name) for name in ['model_linkage.csv','macro_origin_linkage.parquet','family_adapter_summary.json']},scope='Native parameter/gate/output linkage only; remaining no-fit families retain R232; no numerical retraining or convergence certification',adoption=False));print(json.dumps(summaries,indent=2))
if __name__=='__main__':run()
