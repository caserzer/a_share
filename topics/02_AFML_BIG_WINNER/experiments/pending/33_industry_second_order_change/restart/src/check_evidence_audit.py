import json,sys
from pathlib import Path
import pandas as pd,numpy as np
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import ID,KEY,sha
OUT=EP/'restart/p21';q=pd.read_parquet(OUT/'evaluated.parquet');old=pd.read_parquet(EP/'restart/p11/selected_features.parquet');a=q.merge(old[ID+['raw_score','top20','candidate','edge','boundary','cooldown']],on=ID,suffixes=('','_old'),validate='one_to_one')
for new,prior in [('raw_score','raw_score_old'),('top20','top20_old'),('nonup','candidate'),('nonup_edge','edge'),('nonup_boundary','boundary'),('nonup_edge_cooldown126','cooldown')]:assert a[new].equals(a[prior]),(new,prior)
checks=0
for _,g in q.groupby(KEY):
 g=g.sort_values('date');prev=None;last={m:-100000 for m in ['top20','nonup','raw_gate']}
 for _,r in g.iterrows():
  continuous=prev is not None and r.week_i==prev.week_i+1
  for m in last:
   edge=bool(r[m]) and continuous and not bool(prev[m]);boundary=bool(r[m]) and not continuous;cool=edge and r.day_i-last[m]>=126
   assert edge==r[m+'_edge'] and boundary==r[m+'_boundary'] and cool==r[m+'_edge_cooldown126']
   if cool:last[m]=r.day_i
   checks+=1
  prev=r
s=pd.read_csv(OUT/'summary.csv');gates=[];bounds=[]
for _,r in s[s.horizon.eq(126)&s.unit.eq('edge')].iterrows():
 z=q[q[r.method+'_edge']];win=z.win126.sum();known=int(z.win126.notna().sum());assert known==r.known and len(z)==r.total;assert np.isclose(win/known,r.win_rate);assert r.total==r.known+r.immature+r.missing_path
 bounds.append(dict(method=r.method,total=int(r.total),known=known,wins=int(win),all_signals_lower=win/r.total,all_signals_upper=(win+r.total-known)/r.total))
 for metric,value,passed in [('realized_win',r.win_rate,r.win_rate>=.6),('realized_uplift',r.uplift,r.uplift>=.05),('coverage',r.state_success_week_coverage,r.state_success_week_coverage>=.1),('mature_events',r.known,r.known>=100),('uplift_ci_lower',r.lo,r.lo>0)]:gates.append(dict(method=r.method,criterion=metric,value=value,status='PASS' if passed else 'FAIL',scope='historical_diagnostic'))
 for metric in ['calibrated_admission_probability','calibrated_predicted_uplift','calibration_gap']:
  gates.append(dict(method=r.method,criterion=metric,value=None,status='NOT_ESTABLISHED',scope='raw_score_not_calibrated_probability'))
 gates.append(dict(method=r.method,criterion='overall_admission',value=None,status='FAIL',scope='not_approved'))
pd.DataFrame(gates).to_csv(OUT/'acceptance_gaps.csv',index=False);pd.DataFrame(bounds).to_csv(OUT/'unknown_bounds.csv',index=False)
seal=json.loads((OUT/'selection_seal.json').read_text());assert sha(OUT/'selected_features.parquet')==seal['features_sha256']
for path,value in seal['inputs'].items():assert sha(Path(path))==value
reports=list((EP/'restart').glob('p*/report.md'))
(OUT/'evidence_sources.json').write_text(json.dumps({str(p.relative_to(EP)):sha(p) for p in reports},indent=2)+'\n')
(OUT/'validation.json').write_text(json.dumps(dict(status='PASS',p11_aligned_rows=len(a),independent_edge_boundary_cooldown_checks=checks,counts_and_bounds_verified=True,selection_and_inputs_sealed=True),indent=2)+'\n')
print(pd.DataFrame(bounds).to_string(index=False))
