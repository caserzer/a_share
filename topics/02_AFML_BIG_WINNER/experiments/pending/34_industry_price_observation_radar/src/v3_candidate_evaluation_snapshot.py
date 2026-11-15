"""Versioned retrospective evaluation companion, separate from observations."""
import argparse,json
from pathlib import Path
import pandas as pd
from audit_local_inputs import EP,sha
from v3_candidate_delivery import CANDIDATES

parser=argparse.ArgumentParser()
parser.add_argument('--evaluation-dir',type=Path,default=EP/'outputs/evaluation_versions/v3_m06')
parser.add_argument('--comparison-dir',type=Path,default=EP/'outputs/v3_m06_comparison')
parser.add_argument('--out',type=Path,required=True)
a=parser.parse_args();assert not a.out.exists()
inputs=[Path(__file__)];version=json.loads((a.evaluation_dir/'version.json').read_text());cutoff=version['source_data_cutoff']
for root in [a.evaluation_dir,a.comparison_dir]:
 r=json.loads((root/'receipt.json').read_text());inputs.append(root/'receipt.json')
 for f,h in r['artifacts'].items():assert sha(root/f)==h
paths=pd.read_parquet(a.comparison_dir/'all_main_new_paths.parquet');a.out.mkdir(parents=True);summary=[]
for name,arm in CANDIDATES.items():
 run='solo_'+arm+'_COMPETE';root=a.evaluation_dir/'runs'/run;out=a.out/name;out.mkdir()
 for file in ['event_quality.parquet','parent_coverage.parquet','child_coverage.parquet','summary.json','workload.csv']:
  (out/file).write_bytes((root/file).read_bytes());inputs.append(root/file)
 q=pd.read_parquet(root/'event_quality.parquet');new=q[q.kind.eq('NEW')].copy();new['known']=~new.status.str.contains('UNKNOWN');new['effective']=new.status.eq('COVERED');new['unknown']=~new.known
 weekly=new.groupby('date').agg(new=('event_id','size'),evaluable=('known','sum'),effective=('effective','sum'),unknown=('unknown','sum'))
 weekly['effective_rate_as_of_cutoff']=weekly.effective/weekly.evaluable.where(weekly.evaluable.ne(0));weekly['label_as_of']=cutoff;weekly['interpretation']='提示周分组，截至本次数据末日的后验评价；不是提示周已知结果'
 weekly.to_csv(out/'alert_week_quality_as_of.csv')
 path=paths[paths.run_id.eq(run)].copy();assert set(path.event_id)==set(new.event_id)
 path['evaluated_as_of']=cutoff;path.to_parquet(out/'all_new_followup.parquet',index=False)
 pd.read_csv(a.comparison_dir/'main_followup.csv').query('run_id==@run').to_csv(out/'followup_summary.csv',index=False)
 s=json.loads((root/'summary.json').read_text());summary.append(dict(candidate=name,run=run,data_as_of=cutoff,**{k:s[k] for k in ['parent_total','parent_covered','parent_timely','parent_late','parent_missed','child_total','child_covered','new_total','new_evaluable','new_effective','new_unknown','new_effective_rate']}))
pd.DataFrame(summary).to_csv(a.out/'candidate_evaluation_summary.csv',index=False)
inputs.extend([a.evaluation_dir/'version.json',a.comparison_dir/'all_main_new_paths.parquet',a.comparison_dir/'main_followup.csv'])
(a.out/'receipt.json').write_text(json.dumps(dict(inputs={str(p):sha(p) for p in inputs},artifacts={str(p.relative_to(a.out)):sha(p) for p in a.out.rglob('*') if p.is_file()},interpretation='Retrospective evaluation snapshot; cannot join final process IDs into historical signal features.'),ensure_ascii=False,indent=2)+'\n')
print(pd.DataFrame(summary).to_string(index=False))
