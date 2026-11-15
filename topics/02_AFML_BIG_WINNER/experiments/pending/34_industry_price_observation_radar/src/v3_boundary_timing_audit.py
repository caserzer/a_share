from pathlib import Path
import json
import numpy as np
import pandas as pd
import hashlib
P=Path('/home/xiaolv/code/a_share/topics/02_AFML_BIG_WINNER/experiments/pending/34_industry_price_observation_radar')
out=P/'outputs/v3_boundary_timing_audit'
assert not out.exists();out.mkdir()
version=json.loads((P/'outputs/evaluation_versions/v3_m04/version.json').read_text())
calpath=Path(version['calendar_path']);cal=pd.read_parquet(calpath);cal['week']=cal.date.dt.to_period('W-SUN');reviews=cal.groupby('week').date.max()
if cal.date.max().weekday()<4:reviews=reviews.iloc[:-1]
reviews=reviews.to_numpy();parents=pd.read_parquet(P/'outputs/v2_s12_full_directory_duration/processes.parquet').set_index('process_id');children=pd.read_parquet(P/'outputs/v2_s13_duration_enhancements/children.parquet').set_index('child_id')
def deadline(d):
 j=np.searchsorted(reviews,np.datetime64(d));return pd.Timestamp(reviews[min(j+1,len(reviews)-1)])
records=[];summary=[];inputs=[Path(__file__),calpath,P/'protocols/v2_revaluation02/plan.md',P/'protocols/v3_r00/evaluation_alignment.md',P/'outputs/v2_s12_full_directory_duration/processes.parquet',P/'outputs/v2_s13_duration_enhancements/children.parquet']
for experiment in ['v3_m01','v3_m02','v3_m03','v3_m04']:
 root=P/'outputs/evaluation_versions'/experiment
 inputs.append(root/'receipt.json')
 for run in sorted((root/'runs').iterdir()):
  for kind,source,key,ref in [('parent',parents,'process_id','visible_date'),('child',children,'process_id','start_date')]:
   file=run/(kind+'_coverage.parquet');df=pd.read_parquet(file);inputs.append(file)
   changed=0;newtimely=0
   for r in df[df.covered].itertuples():
    identity=getattr(r,key);limit=deadline(source.loc[identity,ref]);is_timely=pd.Timestamp(r.first_date)<=limit;newtimely+=int(is_timely)
    if is_timely!=(r.timing=='TIMELY'):
     changed+=1;records.append(dict(experiment=experiment,run_id=run.name,kind=kind,identity=identity,reference=source.loc[identity,ref],first_date=r.first_date,true_deadline=str(limit.date()),old_timing=r.timing,corrected_timing='TIMELY' if is_timely else 'LATE'))
   summary.append(dict(experiment=experiment,run_id=run.name,kind=kind,total=len(df),covered=int(df.covered.sum()),old_timely=int(df.timing.eq('TIMELY').sum()),corrected_timely=newtimely,changed=changed))
pd.DataFrame(records).to_csv(out/'changed_records.csv',index=False);pd.DataFrame(summary).to_csv(out/'all_run_timing.csv',index=False)
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
(out/'receipt.json').write_text(json.dumps(dict(inputs={str(f):sha(f) for f in inputs},artifacts={f.name:sha(f) for f in out.iterdir() if f.is_file()},scope='Read-only boundary audit. Full calendar deadline; no change to observations, labels, matches, coverage, quality or returns. Not method improvement.'),indent=2)+'\n')
print(pd.DataFrame(summary).groupby(['experiment','kind']).agg(runs=('run_id','size'),changes=('changed','sum'),max_per_run=('changed','max')).to_string())
print(pd.DataFrame(summary).query('experiment=="v3_m04" and kind=="parent"').tail(7).to_string(index=False))
