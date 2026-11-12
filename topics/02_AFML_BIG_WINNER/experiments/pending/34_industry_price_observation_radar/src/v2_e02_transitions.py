"""Old/new evaluation transitions; same immutable observations, no new model."""
import json
from pathlib import Path
import pandas as pd
from audit_local_inputs import EP,sha

def main():
 root=EP/'outputs/v2_revaluation02';out=root/'transitions';out.mkdir(exist_ok=False)
 manifest=json.loads((EP/'protocols/v2_revaluation02/frozen_event_manifest.json').read_text())
 for f,h in manifest.items():assert sha(Path(f))==h
 sums=pd.read_csv(root/'all_run_summary.csv');tables=[];changed=[];work=[]
 for run in sums.run_id:
  family=run.split('/')[0]
  if family=='refresh':old=EP/'outputs/evaluation_versions/s05_20261021/runs'/run.split('/')[-1]
  elif family in ['v2_b01','v2_b02','v2_b03','v2_b04','v2_b05']:old=EP/'outputs/v2_revaluation01/runs'/run
  else:old=EP/'outputs'/family/'evaluation_parent_child/runs'/run
  a=pd.read_parquet(old/'event_quality.parquet');b=pd.read_parquet(root/'runs'/run/'event_quality.parquet')
  m=a.merge(b,on='event_id',suffixes=('_old','_new'),validate='one_to_one');assert len(m)==len(a)==len(b)
  for col in ['date','era','industry_code','kind']:assert m[col+'_old'].equals(m[col+'_new'])
  x=m[m.kind_old.eq('NEW')]
  counts=x.groupby(['status_old','status_new'],dropna=False).size().rename('count').reset_index();counts['run']=run;tables.append(counts)
  c=x[x.status_old.ne(x.status_new)|x.timing_old.fillna('').ne(x.timing_new.fillna(''))].copy();c['run']=run;changed.append(c)
  w=pd.read_csv(root/'runs'/run/'workload.csv');assert len(w)==501
  unknown=w[['NEW','UPDATE','EXIT','pool']].isna().all(axis=1);assert unknown.sum()==5
  assert w.loc[~unknown,'NEW'].le(5).all() and w.loc[~unknown,'pool'].between(0,20).all()
  work.append(dict(run=run,supported_weeks=int((~unknown).sum()),unknown_weeks=int(unknown.sum())))
 pd.concat(tables).to_csv(out/'all_new_status_transitions.csv',index=False);pd.concat(changed).to_parquet(out/'changed_new_status_or_timing.parquet',index=False);pd.DataFrame(work).to_csv(out/'workload_boundary_checks.csv',index=False)
 summary={'runs':len(sums),'all_event_identities_unchanged':True,'all_manifest_hashes_unchanged':True,'all_5_unknown_calendar_weeks_null':True,'limits':'Changed labels/accounting, not changed method predictions. Repeated historical observations across runs are not independent samples.'}
 (out/'receipt.json').write_text(json.dumps({'summary':summary,'script_sha256':sha(Path(__file__)),'artifacts':{p.name:sha(p) for p in out.iterdir() if p.is_file()}},indent=2)+'\n');print(json.dumps(summary))

if __name__=='__main__':main()
