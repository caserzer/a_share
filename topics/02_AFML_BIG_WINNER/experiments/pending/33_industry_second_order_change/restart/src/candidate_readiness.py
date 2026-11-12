import sys,json,hashlib
from pathlib import Path
import pandas as pd,numpy as np
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import sha
OUT=EP/'restart/p48';OUT.mkdir(exist_ok=True);assert not (OUT/'receipt.json').exists()
r=EP/'restart';source=r/'p30/training_panel.parquet';metric=EP/'configs/pool_metric_v1.json';protocol=json.loads(metric.read_text());ids=['era','industry_code','date'];full=pd.read_parquet(source,columns=ids+['eligible','new_win126']);full=full[full.eligible&full.date.ge('2023-01-01')];base=full.groupby('date').new_win126.mean();den=full.new_win126.sum();axis=pd.DatetimeIndex(sorted(full.date.unique()));week={d:i for i,d in enumerate(axis)}
sets={'p30':['rebuilt','momentum'],'p36':['B','M','P','momentum'],'p38':['B','M','P','momentum'],'p39':['linear','tree','momentum'],'p42':['B','P','momentum','recent'],'p47':['B','M','P','momentum']};rows=[];inputs=[source,metric,Path(__file__),r/'P48_candidate_readiness_plan.md'];prior={};checks=0
for version,methods in sets.items():
 path=r/version/'evaluated.parquet';q=pd.read_parquet(path);inputs.append(path);q=q.sort_values(['era','industry_code','block','date']).reset_index(drop=True);q['w']=q.date.map(week);g=q.groupby(['era','industry_code','block']);continuous=q.w.sub(g.w.shift()).eq(1)
 original=r/version/('summary.csv' if version=='p30' else 'events.csv');o=pd.read_csv(original);inputs.append(original)
 for method in methods:
  state=q[method] if version=='p30' else q[method+'_selected'];prev=state.groupby([q.era,q.industry_code,q.block]).shift();edge=state&prev.eq(False)&continuous;boundary=state&~continuous
  assert edge.eq(q[method+'_edge']).all();e=q[edge];k=e[e.new_win126.notna()];win=k.new_win126.mean();uplift=(k.new_win126-k.date.map(base)).mean();coverage=q.loc[state,'new_win126'].sum()/den
  record=o[o.method.eq(method)&o.horizon.eq(126)].iloc[0];oldknown=record.edge_known if version=='p30' else record.known;oldwin=record.edge_win if version=='p30' else record.win;assert len(k)==oldknown and np.isclose(win,oldwin);checks+=1
  # Include unselected rows: same selected IDs on a different universe are not duplicate experiments.
  frame=q[ids].copy();frame['selected']=state.to_numpy();signature=hashlib.sha256(frame.to_csv(index=False,date_format='%Y-%m-%d').encode()).hexdigest();name=f'{version}:{method}';duplicate=prior.get(signature,'');prior.setdefault(signature,name)
  passwin=win>=protocol['target_realized_success_rate_min'];passup=uplift>=protocol['target_realized_uplift_min'];passn=len(k)>=protocol['guardrail_min_mature_admission_events'];passcov=coverage>=protocol['guardrail_success_week_recall_min']
  rows.append(dict(candidate=name,universe_rows=len(q),edges=int(edge.sum()),boundary=int(boundary.sum()),known=len(k),unknown=len(e)-len(k),win=win,uplift_full=uplift,coverage_full=coverage,win_pass=passwin,uplift_pass=passup,count_pass=passn,coverage_pass=passcov,necessary_numeric_pass=passwin and passup and passn and passcov,duplicate_of=duplicate,selection_signature=signature,probability_status='NOT_VALIDATED',formal_admission_status='NOT_APPROVED',evidence_status='REPEATED_HISTORICAL_EXPLORATION'))
a=pd.DataFrame(rows);a.to_csv(OUT/'candidate_audit.csv',index=False);a[a.duplicate_of.eq('')].to_csv(OUT/'distinct_selections.csv',index=False)
(OUT/'receipt.json').write_text(json.dumps(dict(status='PASS',candidate_rows=len(a),distinct_selections=len(prior),necessary_numeric_pass=int(a.necessary_numeric_pass.sum()),event_summary_checks=checks,formal_admissions_approved=0,scope=list(sets),protocol_sha256=sha(metric),inputs={str(p):sha(p) for p in inputs},artifacts={p.name:sha(p) for p in OUT.iterdir() if p.is_file()}),indent=2)+'\n');print(a[a.duplicate_of.eq('')][['candidate','universe_rows','known','win','uplift_full','coverage_full','necessary_numeric_pass']].to_string(index=False));print('raw',len(a),'distinct',len(prior))
