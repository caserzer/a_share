"""Prove the boundary correction changes only timing and derived counts."""
from pathlib import Path
import json
import pandas as pd
from audit_local_inputs import EP,sha

out=EP/'outputs/v3_boundary_verification'
assert not out.exists();out.mkdir()
rows=[];hashes={};count=0
for experiment in ['v3_m01','v3_m02','v3_m03','v3_m04']:
 old=EP/'outputs/evaluation_versions'/experiment;new=old.with_name(experiment+'_e02b')
 for root in [old,new]:
  receipt=json.loads((root/'receipt.json').read_text());hashes[str(root/'receipt.json')]=sha(root/'receipt.json')
  for f,h in receipt['artifacts'].items():assert sha(root/f)==h
 for run in sorted((old/'runs').iterdir()):
  dest=new/'runs'/run.name
  for f in run.iterdir():
   if f.suffix=='.parquet':
    a=pd.read_parquet(f);b=pd.read_parquet(dest/f.name)
    pd.testing.assert_frame_equal(a.drop(columns=['timing'],errors='ignore'),b.drop(columns=['timing'],errors='ignore'))
    changed=(a.timing.fillna('NULL')!=b.timing.fillna('NULL')) if 'timing' in a else pd.Series(False,index=a.index)
    if changed.any():assert a.loc[changed,'timing'].eq('TIMELY').all() and b.loc[changed,'timing'].eq('LATE').all()
    rows.append(dict(experiment=experiment,run_id=run.name,artifact=f.name,changed=int(changed.sum())))
   elif f.name=='summary.json':
    a=json.loads(f.read_text());b=json.loads((dest/f.name).read_text())
    for k in a:
     if k not in ['parent_timely','parent_late']:assert a[k]==b[k],(experiment,run.name,k)
    assert a['parent_timely']+a['parent_late']==b['parent_timely']+b['parent_late']
   else:assert sha(f)==sha(dest/f.name),(experiment,run.name,f.name)
  count+=1
assert count==131
pd.DataFrame(rows).to_csv(out/'all_changes.csv',index=False)
(out/'receipt.json').write_text(json.dumps(dict(result='PASS_ONLY_TIMING_CHANGED',runs=count,inputs=hashes,artifacts={'all_changes.csv':sha(out/'all_changes.csv')},source_sha256=sha(Path(__file__))),indent=2)+'\n')
print('PASS:',count,'runs; only timing and timely/late counts changed')
