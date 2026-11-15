from common import *
import pandas as pd
BASE=['era','level','cohort','method','task','horizon','year','family'];MODEL=BASE+['objective','variant']
def run():
 out=ROOT/'outputs/r233';out.mkdir(exist_ok=True);states=pd.read_parquet(ROOT/'outputs/r195/market_regimes.parquet').regime;rows=[];gaps=[];snap=[];reads=[ROOT/'outputs/r195/market_regimes.parquet'];total=0
 for rnd in [196,199,200,201]:
  paths=[ROOT/f'outputs/r{rnd}/{f}' for f in ['fold_ledger.json','models.json','predictions.parquet']];reads+=paths;gates=json.loads(paths[0].read_text());models=json.loads(paths[1].read_text());p=pd.read_parquet(paths[2]);total+=len(p);gate={tuple(x[k] for k in BASE):x for x in gates};model={tuple(x[k] for k in MODEL):x for x in models};assert len(gate)==len(gates) and len(model)==len(models);assert not p.duplicated(MODEL+['industry_code','date']).any();seen={};assert p.regime.eq(p.date.map(states)).all();assert np.isfinite(p.prediction).all()
  for key,g in p.groupby(MODEL):
   assert key in model;m=model[key];f=gate[key[:len(BASE)]];assert f['status']=='fit';assert g.converged.eq(m['converged']).all();n=len(m['columns']);width=n if m['variant']=='base' else n+3 if m['variant']=='state' else 4*n+3;assert np.asarray(m['coefficient']).size==width;assert len(m['scaler_mean'])==len(m['scaler_scale'])==n
   for k in ['coefficient','intercept','scaler_mean','scaler_scale']:assert np.isfinite(np.asarray(m[k],dtype=float)).all()
   classification=m['task'] in ['onset','reversal']
   if classification:
    assert g.prediction.between(0,1).all()
    for k in ['calibration_coefficient','calibration_intercept']:assert m[k] is not None and np.isfinite(np.asarray(m[k])).all()
   expected=g.regime.map(lambda s:f.get('state_fit_dates',{}).get(s,0)>0);assert expected.eq(g.regime_seen_in_fit).all();seen[key]=len(g)
   rec=dict(zip(MODEL,key),source_round=rnd,prediction_rows=len(g),first_prediction=str(g.date.min().date()),last_prediction=str(g.date.max().date()),converged=m['converged'],classification=classification,calibration_parameters_present=classification,unseen_fit_state_rows=int((~expected).sum()),zero_calibration_state_rows=int(g.regime.map(lambda s:f.get('state_cal_dates',{}).get(s,0)==0).sum()) if classification else None,adoption=False);rows.append(rec)
   z=g[g.date.eq(pd.Timestamp('2026-09-30'))]
   if len(z):snap.append(dict(rec,as_of='2026-09-30',exact_date_rows=len(z),regimes=sorted(z.regime.unique().tolist()),prediction_fields_exposed=False,availability='historical_archive_only_not_live_eligibility'))
  assert set(seen)==set(model)
  used={k[:len(BASE)] for k in model}
  for key,f in gate.items():gaps.append(dict(zip(BASE,key),source_round=rnd,source_status=f['status'],reason=f.get('reason'),test_rows=f.get('test_rows'),has_model=key in used))
 pd.DataFrame(rows).to_csv(out/'model_linkage.csv',index=False);pd.DataFrame(gaps).to_csv(out/'gate_output_coverage.csv',index=False);js(out/'historical_snapshot_2026-09-30.json',dict(as_of='2026-09-30',scope='Exact-date historical records only; no outcomes or probability outputs; missing model/date not filled',models=snap,adoption=False,production_enabled=False))
 js(out/'verification.json',dict(status='PASS',model_records=len(rows),gate_records=len(gaps),prediction_rows=total,unseen_fit_state_rows=sum(x['unseen_fit_state_rows'] for x in rows),nonconverged_models=sum(not x['converged'] for x in rows),inputs={str(p):sha(p) for p in reads+[ROOT/'protocols/r233.json',Path(__file__)]},outputs={f:sha(out/f) for f in ['model_linkage.csv','gate_output_coverage.csv','historical_snapshot_2026-09-30.json']},scope='R196/R199/R200/R201 structural source linkage; not rerun prediction math, prospective proof or all16 adapter completion',adoption=False));print(len(rows),len(gaps),total,len(snap))
if __name__=='__main__':run()
