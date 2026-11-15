from common import *
import pandas as pd
STATES=['down_low','down_high','up_low','up_high']
def families(rnd,row):
 if rnd==196:return (['l1_three_tasks'] if row['family']=='l1' else ['core_three_tasks'])+(['rank_target'] if row['task']=='return' else [])
 if rnd==197:return ['profit_expectations' if row['family']=='profit_expectations' else 'eps_expectations']
 if rnd==199:return [row['family']]
 return [{198:'battery',200:'leader_catchup',201:'financial_dual_clock',202:'macro_interaction',203:'early_financial',204:'fixed_factor_rank',205:'profit_events',206:'capital_accounting'}[rnd]]
def run():
 out=ROOT/'outputs/r232';out.mkdir(exist_ok=True);rows=[];reads=[]
 for rnd in range(196,207):
  directory=ROOT/f'outputs/r{rnd}';paths=sorted(directory.glob('*ledger.json'))+sorted(directory.glob('*ledger.parquet'))+sorted(directory.glob('*gates.json'));assert paths
  for path in paths:
   reads.append(path);data=pd.read_parquet(path).to_dict('records') if path.suffix=='.parquet' else json.loads(path.read_text())
   for i,raw in enumerate(data):
    raw=json.loads(json.dumps(raw,default=str));train_name=next((k for k in ['state_fit_dates','state_train_months'] if k in raw),None);cal_name='state_cal_dates' if 'state_cal_dates' in raw else None;task=raw.get('task');is_classifier=task in ['onset','reversal'];status=raw.get('status');rec=dict(record_id=f'r{rnd}/{path.name}/{i}',source_round=rnd,source_path=str(path.relative_to(ROOT)),source_row=i,families=json.dumps(families(rnd,raw)),raw_record=json.dumps(raw,ensure_ascii=False,sort_keys=True),source_status=status,source_reason=json.dumps(raw.get('reason',raw.get('failed_gates')),ensure_ascii=False),task=task,year=raw.get('year'),level=raw.get('level'),era=raw.get('era'),horizon=raw.get('horizon'),family_native=raw.get('family'),method=raw.get('method'),gate_unit='rolling_industry_origin' if rnd==202 else 'annual_or_shared_native_fold',fit_gate_passed=status=='fit',convergence='not_assessed_by_gate',calibration_status='pooled_gate_passed_quality_not_certified' if is_classifier and status=='fit' else 'gate_failed_or_unavailable' if is_classifier else 'not_a_classifier_gate',state_training_count_unit=train_name,state_calibration_count_unit=cal_name,adoption=False)
    for state in STATES:
     rec['train_'+state]=raw[train_name].get(state,0) if train_name else None;rec['cal_'+state]=raw[cal_name].get(state,0) if cal_name else None
    rows.append(rec)
 d=pd.DataFrame(rows);assert d.record_id.is_unique;d.to_parquet(out/'qualification_records.parquet',index=False);reg=json.loads((ROOT/'outputs/r195/experiment_registry.json').read_text());summaries=[]
 for f in reg['families']:
  name=f['family'];z=d[d.families.map(lambda s:name in json.loads(s))];assert len(z);summaries.append(dict(family=name,records=len(z),source_rounds=sorted(z.source_round.unique().tolist()),fit_gate_records=int(z.fit_gate_passed.sum()),other_gate_records=int((~z.fit_gate_passed).sum()),status_counts=z.source_status.value_counts().to_dict(),source_reason_counts=z.source_reason.value_counts().to_dict(),state_training_support_recorded=int(z.state_training_count_unit.notna().sum()),state_calibration_support_recorded=int(z.state_calibration_count_unit.notna().sum()),scope='historical gate ledger; shared family records not independent model counts',adoption=False))
 js(out/'family_qualification.json',dict(families=summaries,scope='All16 registered families; exact source granularity retained',no_live_model_eligibility=True))
 classifier=d[d.calibration_status.eq('pooled_gate_passed_quality_not_certified')];js(out/'classifier_support.json',dict(fitted_gate_records=len(classifier),state_slots=len(classifier)*4,zero_calibration_state_slots=sum(int(classifier['cal_'+s].eq(0).sum()) for s in STATES),missing_calibration_state_slots=sum(int(classifier['cal_'+s].isna().sum()) for s in STATES),meaning='A pooled calibration gate can pass while one market state has no calibration dates; no per-state quality certification',adoption=False))
 js(out/'monitor_contract.json',dict(schema='ep35.model_qualification_archive.v1',state_monitor='src/regime_monitor_r231.py',join_boundary='State knowledge must never imply model qualification; this archive is not as-of availability and does not autojoin a live state',records='qualification_records.parquet',fields={'fit_gate_passed':'native planned/shared gate only','convergence':'not assessed here; model artifact required','calibration_status':'pooled gate only, not reliability guarantee','train_STATE/cal_STATE':'0 only when original map exists and state absent; null when map unavailable','source_reason':'original reason or failed_gates, never guessed'},prediction_exposure='none',adoption=False,production_enabled=False))
 reads += [ROOT/'outputs/r195/experiment_registry.json',ROOT/'protocols/r232.json',Path(__file__)]
 js(out/'verification.json',dict(status='PASS',records=len(d),families=len(summaries),source_ledgers=len(reads)-3,inputs={str(p):sha(p) for p in reads},outputs={p.name:sha(p) for p in out.glob('*') if p.is_file() and p.name!='verification.json'},adoption=False));print(len(d),len(summaries));print(json.loads((out/'classifier_support.json').read_text()))
if __name__=='__main__':run()
