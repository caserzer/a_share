from common import *
import pandas as pd
from operating_reader_r250 import capture
import tempfile

def run():
 out=ROOT/'outputs/r250';source=pd.read_parquet(ROOT/'outputs/r248/industry_diagnostic.parquet');saved=pd.read_parquet(out/'industry_evidence.parquet');pd.testing.assert_frame_equal(source,saved[source.columns]);state=pd.read_parquet(ROOT/'outputs/r195/market_regimes.parquet').regime;assert saved.regime.equals(saved.snapshot.map(state))
 dictionary=json.loads((out/'factor_dictionary_extension.json').read_text());assert len(dictionary['definitions'])==11 and len({x['id'] for x in dictionary['definitions']})==11;assert sha(ROOT/dictionary['base_dictionary']['path'])==dictionary['base_dictionary']['sha256']
 for d in dictionary['definitions']:
  assert all(k in d for k in ['theory','direction','applicable','economic_date','publication_date','known_at','archive_clock','frequency','revision','missing','aggregation','failure','formula','unit','source','source_sha256']);assert sha(ROOT/d['source'])==d['source_sha256']
 gates=json.loads((out/'training_gates.json').read_text());assert len(gates)==72
 for g in gates:
  d=source[source.level.eq(g['level'])&source.variant.eq('q2_common')];usable=d[d.gate];past=usable[usable.snapshot<pd.Timestamp(g['year'],1,1)];assert g['usable_snapshot_months']==usable.snapshot.dt.to_period('M').nunique()==2 and g['prior_annual_training_months_upper_bound']==past.snapshot.dt.to_period('M').nunique()==0;assert g['required_prior_months']==18 and g['status']=='insufficient_history' and not g['fitted']
 expected={(level,task,objective,h,v) for level in ['L1','L2','L3'] for task,objective in [('onset','onset'),('return','return'),('return','rank'),('reversal','reversal')] for h in [20,60] for v in ['base','state','interaction']};assert {(g['level'],g['task'],g['objective'],g['horizon'],g['variant']) for g in gates}==expected
 cov=json.loads((out/'state_coverage.json').read_text())
 for g in cov:
  d=saved[saved.level.eq(g['level'])&saved.variant.eq('q2_common')&saved.gate];d=d[d.regime.isna()] if g['regime']=='unknown' else d[d.regime.eq(g['regime'])];assert len(d)==g['qualified_rows'] and d.snapshot.nunique()==g['qualified_months']
 counts={}
 for date in ['2026-07-31','2026-08-31','2026-09-30','2026-10-21']:
  dest=out/'snapshots'/date;assert capture(date,dest) in ['created','unchanged'];assert capture(date,dest)=='unchanged';actual=pd.read_parquet(dest/'operating_diagnostics.parquet');pd.testing.assert_frame_equal(saved[saved.snapshot.eq(date)].reset_index(drop=True),actual.reset_index(drop=True));counts[date]=len(actual)
 with tempfile.TemporaryDirectory() as temp:
  for date in ['2026-09-30 12:00','2026-09-30T00:00:00+08:00','NaT']:
   try:capture(date,Path(temp)/'bad')
   except ValueError:pass
   else:raise AssertionError('invalid date accepted')
  try:capture('2026-08-31',out/'snapshots/2026-09-30')
  except ValueError:pass
  else:raise AssertionError('conflict accepted')
 receipt=json.loads((out/'verification.json').read_text())
 for p,h in receipt['inputs'].items():assert sha(Path(p))==h
 for p,h in receipt['outputs'].items():assert sha(out/p)==h
 entry=json.loads((out/'research_entry.json').read_text())
 for route in entry['routes'].values():assert sha(ROOT/route['path'])==route['sha256']
 js(out/'independent_verification.json',dict(status='PASS',original_evidence_rows_preserved=len(source),definitions=11,gate_checks=72,state_coverage_checks=len(cov),snapshot_rows=counts,idempotence_checks=4,rejection_checks=4,new_models=0,code_sha256=sha(Path(__file__)),adoption=False));print('PASS',counts)
if __name__=='__main__':run()
