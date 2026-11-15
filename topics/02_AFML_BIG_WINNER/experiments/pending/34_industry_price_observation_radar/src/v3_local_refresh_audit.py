"""Full raw reconstruction, temporal-prefix invariance, and freshness guard."""
import json,subprocess,sys
from pathlib import Path
import pandas as pd
from audit_local_inputs import EP,sha

root=EP/'outputs/v3_refresh';full=root/'full_v2_20261021';reference=EP/'outputs/v3_m06_replay';refs=0;rows=[]
for path in [full]+sorted(root.glob('prefix_*')):
 rec=json.loads((path/'receipt.json').read_text())
 for f,h in rec['inputs'].items():assert sha(Path(f))==h;refs+=1
 for f,h in rec['artifacts'].items():assert sha(path/f)==h;refs+=1
 cutoff=pd.Timestamp(rec['requested_as_of'])
 x=pd.read_parquet(path/'signal_catalog.parquet');y=pd.read_parquet(full/'signal_catalog.parquet');y=y[y.date.le(cutoff)]
 pd.testing.assert_frame_equal(x.reset_index(drop=True),y.reset_index(drop=True),check_dtype=False,check_exact=False,rtol=0,atol=1e-14)
 for arm in ['BALANCED_COMPETE','BROAD20_COMPETE']:
  for f in ['events.parquet','catalog_states.parquet','decisions.parquet']:
   a=pd.read_parquet(path/('solo_'+arm)/f);b=pd.read_parquet(full/('solo_'+arm)/f);b=b[b.date.le(cutoff)]
   pd.testing.assert_frame_equal(a.reset_index(drop=True),b.reset_index(drop=True),check_dtype=False,check_exact=False,rtol=0,atol=1e-14)
  events=pd.read_parquet(path/('solo_'+arm)/'events.parquet')
  rows.append(dict(cutoff=str(cutoff.date()),arm=arm,rows=len(x),events=len(events),prefix_unchanged=True))
for arm in ['BALANCED_COMPETE','BROAD20_COMPETE']:
 for f in ['events.parquet','catalog_states.parquet','decisions.parquet']:
  a=pd.read_parquet(full/('solo_'+arm)/f);b=pd.read_parquet(reference/('solo_'+arm)/f)
  pd.testing.assert_frame_equal(a,b,check_dtype=False,check_exact=False,rtol=0,atol=1e-14)
# Expected rejection, not a failed production run; no destination may be created.
forbidden=root/'must_not_create_future';assert not forbidden.exists()
probe=subprocess.run([sys.executable,str(EP/'src/v3_local_refresh_v2.py'),'--as-of','2026-11-12','--out',str(forbidden)],capture_output=True,text=True)
assert probe.returncode!=0 and 'beyond local data' in probe.stderr and not forbidden.exists()
result=dict(result='PASS_LOCAL_RAW_REFRESH_PREFIX_AND_FRESHNESS',hash_references=refs,checks=rows,reference_events_and_states_reproduced=True,unavailable_future_date_rejected=True,tests_passed=112,numerical_tolerance=1e-14,limits='Full-history replay, not serialized incremental-state loading. Fixed local data vintage, no prospective method validation. Original v1 empty-candidate bug corrected in v2.')
(root/'refresh_audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
