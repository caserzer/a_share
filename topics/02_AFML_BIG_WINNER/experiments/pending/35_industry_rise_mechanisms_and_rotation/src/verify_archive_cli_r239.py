from common import *
import pandas as pd
import tempfile,shutil
import research_archive_cli_r239 as api

def run():
 out=ROOT/'outputs/r239';before=out/'2026-08-31';after=out/'2026-09-30';comparison=out/'comparison';api.check(before);api.check(after);api.check(comparison)
 assert api.capture('2026-08-31',before)=='unchanged';assert api.capture('2026-09-30',after)=='unchanged';assert api.compare(before,after,comparison)=='unchanged'
 a=pd.read_parquet(before/'historical_score_view.parquet');b=pd.read_parquet(after/'historical_score_view.parquet');gold=pd.read_parquet(ROOT/'outputs/r235/historical_score_view.parquet');pd.testing.assert_frame_equal(b,gold);q=pd.read_parquet(comparison/'changes.parquet');keys=['family_registry','source_round','model_slice','era','level','industry_code'];aa={tuple(x[k] for k in keys):x for x in a[a.family_registry.ne('profit_events')].to_dict('records')};bb={tuple(x[k] for k in keys):x for x in b[b.family_registry.ne('profit_events')].to_dict('records')};assert len(q)==len(set(aa)|set(bb));checks=0
 for row in q.to_dict('records'):
  key=tuple(row[k] for k in keys);status='matched_configuration' if key in aa and key in bb else 'missing_after' if key in aa else 'new_after';assert row['status']==status
  if status=='matched_configuration':assert np.isclose(row['score_change'],bb[key]['research_score']-aa[key]['research_score']);assert row['rank_change']==bb[key]['display_rank']-aa[key]['display_rank']
  else:assert pd.isna(row['score_change']) and pd.isna(row['rank_change'])
  checks+=1
 # Independent exact-date source verification for the newly introduced earlier snapshot.
 sourcechecks=0
 for rnd,g in a.groupby('source_round'):
  src=pd.read_parquet(ROOT/f"outputs/r{rnd}/{'scores' if rnd==202 else 'predictions'}.parquet",filters=[('date','==',pd.Timestamp('2026-08-31'))]);modelkeys=list(json.loads(g.model_slice.iloc[0]));lookup={k:z for k,z in src.groupby(modelkeys,dropna=False)}
  for identity,z in g.groupby('model_slice'):
   ident=json.loads(identity);raw=lookup[tuple(ident[k] for k in modelkeys)].sort_values('industry_code');z=z.sort_values('industry_code');assert len(raw)==len(z);assert np.allclose(raw['score' if rnd==202 else 'prediction'],z.research_score);sourcechecks+=len(z)
 rejected=0
 for action in [lambda:api.capture('2026-08-31',after),lambda:api.capture('2026-11-14',out/'invalid'),lambda:api.capture('2026-09-30 10:00',out/'invalid'),lambda:api.compare(after,before,out/'invalid')]:
  try:action()
  except (ValueError,AssertionError):rejected+=1
  else:raise AssertionError('invalid request accepted')
 with tempfile.TemporaryDirectory() as temp:
  bad=Path(temp)/'tampered';shutil.copytree(after,bad);(bad/'snapshot.json').write_text('{}')
  try:api.check(bad)
  except AssertionError:rejected+=1
  else:raise AssertionError('modified archive accepted')
  # No archived model output on an otherwise valid trading day is allowed as an explicit empty view.
  empty=Path(temp)/'empty';api.capture('2022-02-08',empty);ev=pd.read_parquet(empty/'historical_score_view.parquet');assert ev.empty;assert len(json.loads((empty/'snapshot.json').read_text())['families'])==16
 # Event-origin identity is never equated across dates; annual-model boundary remains flagged.
 x=b.head(1).copy();y=x.copy();x['date']=pd.Timestamp('2025-12-31');y['date']=pd.Timestamp('2026-01-30');assert api.compare_frames(x,y).model_year_changed.all();x['family_registry']='profit_events';y['family_registry']='profit_events';assert api.compare_frames(x,y).empty
 js(out/'verification.json',dict(status='PASS',earlier_source_score_checks=sourcechecks,later_golden_rows=len(b),change_rows=checks,rejected_requests=rejected,idempotent_operations=3,empty_trading_date_supported=True,event_and_year_boundaries=True,inputs={str(ROOT/'src/archive_view_builder_r239.py'):sha(ROOT/'src/archive_view_builder_r239.py'),str(ROOT/'src/research_archive_cli_r239.py'):sha(ROOT/'src/research_archive_cli_r239.py'),str(Path(__file__)):sha(__file__),str(ROOT/'protocols/r239.json'):sha(ROOT/'protocols/r239.json')},scope='CLI artifact invariants, exact source/golden scores, every outer-join change, empty/nonmatched/event/year cases; not live or PIT certification'));print(len(a),len(b),checks,rejected)
if __name__=='__main__':run()
